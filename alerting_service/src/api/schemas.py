from pydantic import BaseModel, Field


class AlertTrigger(BaseModel):
    """Internal request for triggering an alert."""
    tenant_id: str = Field(..., description="Tenant UUID.")
    user_id: str | None = Field(default=None, description="Optional user UUID.")
    meter_id: str | None = Field(default=None, description="Optional meter UUID.")
    analytics_output_id: str | None = Field(default=None, description="Optional analytics output UUID.")
    severity: str = Field(default="warning", description="info|warning|critical")
    title: str = Field(..., min_length=1, max_length=200, description="Alert title.")
    message: str = Field(..., min_length=1, max_length=2000, description="Alert message.")
    channel: str = Field(default="in_app", description="in_app|email|sms|webhook")


class AlertOut(BaseModel):
    """Alert response."""
    id: str
    tenant_id: str
    user_id: str | None = None
    meter_id: str | None = None
    analytics_output_id: str | None = None
    severity: str
    title: str
    message: str
    status: str
    channel: str
    created_at: str | None = Field(default=None, description="Alert creation timestamp (ISO8601).")

    # Notification stubs (future extensibility)
    delivered_at: str | None = Field(default=None, description="When delivery occurred (if applicable).")
    read_at: str | None = Field(default=None, description="When recipient read the alert (if applicable).")
