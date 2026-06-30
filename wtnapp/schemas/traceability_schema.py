"""Schemas da timeline de rastreabilidade (Feature 014, US7)."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class TimelineEntryOut(BaseModel):
    occurred_at: datetime
    kind: str
    ref_id: uuid.UUID
    label: str
    detail: str
