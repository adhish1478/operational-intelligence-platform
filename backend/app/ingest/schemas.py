from typing import Any
from pydantic import BaseModel

class WebhookPayload(BaseModel):
    """
    Pydantic schema representing a generic webhook payload.
    Configured to allow arbitrary fields to accommodate Slack, GitHub, Jira, and Gmail inputs.
    """
    model_config = {
        "extra": "allow"
    }
