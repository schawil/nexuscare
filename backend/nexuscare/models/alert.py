"""
Modèle SQLAlchemy — table `alert`
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Boolean, func, CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from nexuscare.core.database import Base


class Alert(Base):
    __tablename__ = "alert"
    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('LIMIT_REACHED','BLOCKED_ATTEMPT','BEDTIME','SERVICE_DISABLED','NEW_APP')",
            name="ck_alert_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("child.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    child: Mapped["Child"] = relationship("Child", back_populates="alerts")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Alert id={self.id} type={self.alert_type} read={self.is_read}>"
