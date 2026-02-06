from datetime import datetime
from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field

Severity = Literal["INFO", "WARN", "ERROR", "CRITICAL"]


class ErrorIn(BaseModel):
    machine: str = Field(..., min_length=1, max_length=50)
    message: str = Field(..., min_length=1, max_length=2000)
    severity: Optional[Severity] = "ERROR"
    timestamp: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None


class ErrorOut(BaseModel):
    id: int
    created_at: datetime
    machine: str
    message: str
    severity: str
