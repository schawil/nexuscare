"""
Modèle SQLAlchemy — table `permission_request`
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, func, CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from nexuscare.core.database import Base


class PermissionRequest(Base):
    __tablename__ = "permission_request"
    __table_args__ = (
        CheckConstraint(
            "request_type IN ('EXTRA_TIME','APP_UNBLOCK','SCHEDULE_CHANGE')",
            name="ck_request_type",
        ),
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED')",
            name="ck_request_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("child.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_type: Mapped[str] = mapped_column(String(20), nullable=False)
    child_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    package_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="PENDING", nullable=False, index=True)
    parent_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    child: Mapped["Child"] = relationship("Child", back_populates="permission_requests")  # noqa: F821

    def __repr__(self) -> str:
        return f"<PermissionRequest id={self.id} type={self.request_type} status={self.status}>"
