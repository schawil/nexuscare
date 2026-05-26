"""
Modèle SQLAlchemy — table `child`
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from nexuscare.core.database import Base


class Child(Base):
    __tablename__ = "child"
    __table_args__ = (
        CheckConstraint(
            "profile_tier IN ('CHILDHOOD','PREADOLESCENCE')",
            name="ck_child_profile_tier",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("parent.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    profile_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    link_code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    parent: Mapped["Parent"] = relationship("Parent", back_populates="children")  # noqa: F821
    rules: Mapped[list["Rule"]] = relationship(  # noqa: F821
        "Rule", back_populates="child", cascade="all, delete-orphan"
    )
    app_usages: Mapped[list["AppUsage"]] = relationship(  # noqa: F821
        "AppUsage", back_populates="child", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(  # noqa: F821
        "Alert", back_populates="child", cascade="all, delete-orphan"
    )
    permission_requests: Mapped[list["PermissionRequest"]] = relationship(  # noqa: F821
        "PermissionRequest", back_populates="child", cascade="all, delete-orphan"
    )

    @staticmethod
    def compute_tier(age: int) -> str:
        if 6 <= age <= 9:
            return "CHILDHOOD"
        elif 10 <= age <= 15:
            return "PREADOLESCENCE"
        raise ValueError(f"Âge {age} hors plage supportée (6-15 ans).")

    def __repr__(self) -> str:
        return f"<Child id={self.id} name={self.name} tier={self.profile_tier}>"
