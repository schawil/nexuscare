"""
Module de sécurité — JWT (HS256) + bcrypt + hashing utilitaires.
Toute la logique cryptographique est isolée ici pour faciliter les tests
et l'éventuelle rotation d'algorithme.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
import bcrypt

from nexuscare.core.config import settings

# ─── Contexte bcrypt ─────────────────────────────────────────────────────────
# Coût de hachage bcrypt (12 = bon équilibre sécurité/performance en 2024-2025)
BCRYPT_COST = 12


def hash_password(plain: str) -> str:
    """
    Hash un mot de passe en clair avec bcrypt.
    Retourne le hash au format $2b$XX$... (compatible vérification)
    Limite la longueur à 72 bytes (limite bcrypt) avant hachage.
    """
    # Bcrypt limite à 72 bytes - on encode puis on tronque si nécessaire
    password_bytes = plain.encode('utf-8')[:72]
    salt = bcrypt.gensalt(rounds=BCRYPT_COST)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """
    Vérifie un mot de passe en clair contre son hash bcrypt.
    Gère automatiquement la limite de 72 bytes.
    """
    password_bytes = plain.encode('utf-8')[:72]
    try:
        return bcrypt.checkpw(password_bytes, hashed.encode('utf-8'))
    except (ValueError, AttributeError):
        # En cas d'erreur sur le hash (format invalide), retourner False
        return False


# ─── JWT ─────────────────────────────────────────────────────────────────────

def create_access_token(parent_id: int) -> str:
    """
    Crée un access token JWT signé HS256.
    Expire dans ACCESS_TOKEN_EXPIRE_MINUTES (config).
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(parent_id),
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token() -> tuple[str, datetime]:
    """
    Crée un refresh token opaque (256 bits aléatoires).
    Retourne (token_brut, date_expiration).
    Le token brut est transmis au client ; seul son hash SHA-256 est stocké en base.
    """
    raw_token = secrets.token_hex(32)  # 64 chars hex = 256 bits
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    return raw_token, expires_at


def hash_token(raw_token: str) -> str:
    """Hash SHA-256 d'un token pour stockage en base (évite les fuites si dump DB)."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def decode_access_token(token: str) -> int:
    """
    Décode et valide un access token JWT.
    Retourne le parent_id (int) si valide.
    Lève JWTError si invalide ou expiré.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    if payload.get("type") != "access":
        raise JWTError("Type de token invalide.")

    sub = payload.get("sub")
    if sub is None:
        raise JWTError("Token sans sujet.")

    return int(sub)