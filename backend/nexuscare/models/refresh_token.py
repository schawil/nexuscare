"""
Modèle SQLAlchemy — table `refresh_token`
Stocke les refresh tokens actifs pour permettre la révocation côté serveur.
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexuscare.core.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("parent.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Token hashé en SHA-256 — on ne stocke jamais le token brut
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    parent: Mapped["Parent"] = relationship("Parent")  # noqa: F821

    def __repr__(self) -> str:
        return f"<RefreshToken parent_id={self.parent_id} revoked={self.is_revoked}>"