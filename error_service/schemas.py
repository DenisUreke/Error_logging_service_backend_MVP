from datetime import datetime
from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field, EmailStr

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

class UserIn(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    phone_number: Optional[str] = Field(None, max_length=30)

class UserOut(BaseModel):
    id: int
    created_at: datetime
    first_name: str
    last_name: str
    role: str
    email: str
    phone_number: Optional[str] = None


class ServiceIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    group: str = Field(..., min_length=1, max_length=100)

class ServiceOut(BaseModel):
    id: int
    created_at: datetime
    name: str
    group: str

class RuleIn(BaseModel):
    # Either provide user_id OR user
    user_id: Optional[int] = None
    user: Optional[RuleUserCreateIn] = None

    service_id: int
    min_severity: Severity = "ERROR"

    enabled: bool = True
    do_email: bool = False
    do_call: bool = False
    do_halo_ticket: bool = False


class RuleOut(BaseModel):
    id: int
    created_at: datetime

    user_id: int
    service_id: int
    min_severity: str

    enabled: bool
    do_email: bool
    do_call: bool
    do_halo_ticket: bool

class RuleUserOut(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None

    # rule data
    rule_id: int
    enabled: bool
    min_severity: str
    do_email: bool
    do_call: bool
    do_halo_ticket: bool

    
class RuleUserCreateIn(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., min_length=3, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=30)



