from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class ErrorRecord(Base):
    __tablename__ = "errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    machine: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="ERROR", nullable=False)

    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
