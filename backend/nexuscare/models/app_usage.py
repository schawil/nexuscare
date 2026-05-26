"""
Modèle SQLAlchemy — table `app_usage`
"""
from datetime import date, datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Date, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from nexuscare.core.database import Base


class AppUsage(Base):
    __tablename__ = "app_usage"
    __table_args__ = (
        UniqueConstraint("child_id", "package_name", "usage_date", name="uq_usage_child_app_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("child.id", ondelete="CASCADE"), nullable=False, index=True
    )
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    app_name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    child: Mapped["Child"] = relationship("Child", back_populates="app_usages")  # noqa: F821

    def __repr__(self) -> str:
        return f"<AppUsage child={self.child_id} app={self.package_name} date={self.usage_date}>"
