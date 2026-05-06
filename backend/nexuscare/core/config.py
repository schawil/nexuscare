"""
Configuration centralisée via variables d'environnement.
Crée un fichier .env à la racine du backend pour surcharger les valeurs.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "NexusCare"
    DEBUG: bool = True

    # JWT — Génère une clé forte avec : openssl rand -hex 32
    SECRET_KEY: str = "CHANGE_ME_BEFORE_PRODUCTION_USE_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Base de données
    DATABASE_URL: str = "sqlite:///./nexuscare.db"


settings = Settings()
