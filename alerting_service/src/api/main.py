from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.core.db import get_db, lifespan
from src.api.schemas import AlertOut, AlertTrigger

openapi_tags = [
    {"name": "health", "description": "Service health and diagnostics."},
    {"name": "internal", "description": "Internal APIs used by backend_api_service."},
]


app = FastAPI(
    title="Energy Insights Platform - Alerting Service",
    description=(
        "Internal alerting microservice.\n\n"
        "Persists in-app alerts and tracks delivery/read/ack state.\n"
        "This service is intended to be called by backend_api_service."
    ),
    version="0.3.0",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"], summary="Health check", operation_id="health_check")
# PUBLIC_INTERFACE
def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"message": "Healthy"}


@app.post(
    "/internal/alerts/trigger",
    tags=["internal"],
    summary="Trigger an alert (persist)",
    operation_id="internal_trigger_alert",
    response_model=AlertOut,
)
# PUBLIC_INTERFACE
async def internal_trigger_alert(payload: AlertTrigger) -> AlertOut:
    """Persist an alert.

    Args:
        payload: AlertTrigger

    Returns:
        Newly created alert row.
    """
    db = get_db()
    rows = await db.fetch_all(
        """
        INSERT INTO alerts (
            tenant_id, user_id, meter_id, analytics_output_id, severity, title, message, channel
        )
        VALUES (
            :tenant_id::uuid, :user_id::uuid, :meter_id::uuid, :analytics_output_id::uuid,
            :severity, :title, :message, :channel
        )
        RETURNING id::text AS id,
                  tenant_id::text AS tenant_id,
                  user_id::text AS user_id,
                  meter_id::text AS meter_id,
                  analytics_output_id::text AS analytics_output_id,
                  severity, title, message, status, channel
        """,
        payload.model_dump(),
    )
    return AlertOut(**rows[0])


@app.get(
    "/internal/alerts",
    tags=["internal"],
    summary="List alerts for tenant",
    operation_id="internal_list_alerts",
    response_model=List[AlertOut],
)
# PUBLIC_INTERFACE
async def internal_list_alerts(
    tenant_id: str = Query(..., description="Tenant UUID."),
    user_id: Optional[str] = Query(default=None, description="Optional user UUID to filter."),
    status: Optional[str] = Query(default=None, description="Optional status filter."),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> List[AlertOut]:
    """List alerts for a tenant."""
    db = get_db()
    rows = await db.fetch_all(
        """
        SELECT id::text AS id,
               tenant_id::text AS tenant_id,
               user_id::text AS user_id,
               meter_id::text AS meter_id,
               analytics_output_id::text AS analytics_output_id,
               severity, title, message, status, channel
        FROM alerts
        WHERE tenant_id = :tenant_id::uuid
          AND (:user_id IS NULL OR user_id = :user_id::uuid)
          AND (:status IS NULL OR status = :status)
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """,
        {"tenant_id": tenant_id, "user_id": user_id, "status": status, "limit": limit, "offset": offset},
    )
    return [AlertOut(**r) for r in rows]


@app.post(
    "/internal/alerts/{alert_id}/ack",
    tags=["internal"],
    summary="Acknowledge an alert",
    operation_id="internal_ack_alert",
)
# PUBLIC_INTERFACE
async def internal_ack_alert(alert_id: str) -> Dict[str, Any]:
    """Acknowledge an alert by setting status=acknowledged."""
    db = get_db()
    await db.execute(
        """
        UPDATE alerts
        SET status = 'acknowledged', updated_at = now()
        WHERE id = :alert_id::uuid
        """,
        {"alert_id": alert_id},
    )
    return {"ok": True, "alert_id": alert_id}


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Any, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": "internal_server_error", "detail": str(exc)})
