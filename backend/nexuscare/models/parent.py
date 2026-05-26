"""
Modèle SQLAlchemy — table `parent`
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexuscare.core.database import Base


class Parent(Base):
    __tablename__ = "parent"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relation vers les enfants (lazy="select" = chargement à la demande)
    children: Mapped[list["Child"]] = relationship(  # noqa: F821
        "Child", back_populates="parent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Parent id={self.id} email={self.email}>"