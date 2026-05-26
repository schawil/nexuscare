"""
Modèle SQLAlchemy — table `rule`
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Boolean, func, CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from nexuscare.core.database import Base


class Rule(Base):
    __tablename__ = "rule"
    __table_args__ = (
        CheckConstraint(
            "rule_type IN ('SCREEN_LIMIT','APP_BLOCK','APP_TIME_LIMIT','TIME_SLOT')",
            name="ck_rule_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("child.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # JSON sérialisé — structure variable selon rule_type :
    # SCREEN_LIMIT   : {"daily_limit_seconds": 7200}
    # APP_BLOCK      : {"package_name": "com.xxx", "app_name": "TikTok"}
    # APP_TIME_LIMIT : {"package_name": "com.xxx", "daily_limit_seconds": 2700}
    # TIME_SLOT      : {"slot_name": "NIGHT", "days_of_week": [1..7],
    #                   "start_time": "21:00", "end_time": "07:00", "allowed_packages": []}
    config: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    child: Mapped["Child"] = relationship("Child", back_populates="rules")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Rule id={self.id} type={self.rule_type} active={self.is_active}>"
