"""
Pydantic Schemas for the Audit Trail.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID
    details: Dict[str, Any]
    user_name: Optional[str] = "System"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

