from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text, UniqueConstraint, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship


from .db import Base


class ErrorRecord(Base):
    __tablename__ = "errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    machine: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="ERROR", nullable=False)

    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    role: Mapped[str] = mapped_column(String(50), nullable=False)

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(30), nullable=True)

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    group: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("name", "group", name="uq_services_name_group"),
    )

class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False, index=True)

    min_severity: Mapped[str] = mapped_column(String(20), nullable=False)  # INFO/WARN/ERROR/CRITICAL
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    do_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    do_call: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    do_halo_ticket: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User")
    service = relationship("Service")

    __table_args__ = (
        UniqueConstraint("user_id", "service_id", "min_severity", name="uq_rule_user_service_minsev"),
    )

