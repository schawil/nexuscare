#!/usr/bin/env bash
# =============================================================================
#  NexusCare — Deploy module Children
#  Lance depuis : ~/nexuscare/backend/
#  Usage        : bash deploy_children.sh
# =============================================================================
set -euo pipefail

BASE="$HOME/nexuscare/backend/nexuscare"
TESTS="$HOME/nexuscare/backend/tests"

echo ">> Création des dossiers..."
mkdir -p "$BASE"/{models,schemas,routers,services}
mkdir -p "$TESTS"

# =============================================================================
# models/rule.py
# =============================================================================
cat > "$BASE/models/rule.py" << 'PYEOF'
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
PYEOF
echo "   [OK] models/rule.py"

# =============================================================================
# models/app_usage.py
# =============================================================================
cat > "$BASE/models/app_usage.py" << 'PYEOF'
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
PYEOF
echo "   [OK] models/app_usage.py"

# =============================================================================
# models/alert.py
# =============================================================================
cat > "$BASE/models/alert.py" << 'PYEOF'
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
PYEOF
echo "   [OK] models/alert.py"

# =============================================================================
# models/permission_request.py
# =============================================================================
cat > "$BASE/models/permission_request.py" << 'PYEOF'
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
PYEOF
echo "   [OK] models/permission_request.py"

# =============================================================================
# models/child.py
# =============================================================================
cat > "$BASE/models/child.py" << 'PYEOF'
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
PYEOF
echo "   [OK] models/child.py"

# =============================================================================
# models/__init__.py
# =============================================================================
cat > "$BASE/models/__init__.py" << 'PYEOF'
"""
Export de tous les modèles SQLAlchemy.
L'ordre d'import est important : résout les forward references entre modèles.
"""
from nexuscare.models.parent import Parent
from nexuscare.models.child import Child
from nexuscare.models.refresh_token import RefreshToken
from nexuscare.models.rule import Rule
from nexuscare.models.app_usage import AppUsage
from nexuscare.models.alert import Alert
from nexuscare.models.permission_request import PermissionRequest

__all__ = ["Parent", "Child", "RefreshToken", "Rule", "AppUsage", "Alert", "PermissionRequest"]
PYEOF
echo "   [OK] models/__init__.py"

# =============================================================================
# schemas/children.py  — 100% Pydantic, zéro SQLAlchemy
# =============================================================================
cat > "$BASE/schemas/children.py" << 'PYEOF'
"""
Schémas Pydantic v2 — Module Children
Aucun import SQLAlchemy ici — uniquement Pydantic BaseModel.
"""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class ChildCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100, examples=["Léo"])
    age: int = Field(ge=6, le=15, examples=[8])

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class ChildUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    age: int | None = Field(default=None, ge=6, le=15)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class LinkDeviceRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$", examples=["482916"])
    device_id: str = Field(min_length=1, max_length=255, examples=["android-uuid-xxxx"])


class ChildResponse(BaseModel):
    id: int
    name: str
    age: int
    profile_tier: Literal["CHILDHOOD", "PREADOLESCENCE"]
    device_id: str | None
    is_linked: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_child(cls, child: object) -> "ChildResponse":
        return cls(
            id=child.id,               # type: ignore[attr-defined]
            name=child.name,           # type: ignore[attr-defined]
            age=child.age,             # type: ignore[attr-defined]
            profile_tier=child.profile_tier,   # type: ignore[attr-defined]
            device_id=child.device_id, # type: ignore[attr-defined]
            is_linked=child.device_id is not None,  # type: ignore[attr-defined]
            created_at=child.created_at,  # type: ignore[attr-defined]
        )


class LinkCodeResponse(BaseModel):
    child_id: int
    code: str
    expires_in: int


class MessageResponse(BaseModel):
    message: str
PYEOF
echo "   [OK] schemas/children.py"

# =============================================================================
# services/children_service.py
# =============================================================================
cat > "$BASE/services/children_service.py" << 'PYEOF'
"""
Service Children — logique métier isolée des routes FastAPI.
"""
import secrets
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from nexuscare.core.security import hash_token
from nexuscare.models.child import Child
from nexuscare.models.parent import Parent
from nexuscare.schemas.children import (
    ChildCreateRequest,
    ChildUpdateRequest,
    ChildResponse,
    LinkCodeResponse,
)

_LINK_CODE_TTL_SECONDS = 600


def _get_child_or_404(child_id: int, parent: Parent, db: Session) -> Child:
    child = db.get(Child, child_id)
    if child is None or child.parent_id != parent.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enfant introuvable.")
    return child


def list_children(parent: Parent, db: Session) -> list[ChildResponse]:
    children = (
        db.query(Child)
        .filter(Child.parent_id == parent.id)
        .order_by(Child.created_at.asc())
        .all()
    )
    return [ChildResponse.from_orm_child(c) for c in children]


def create_child(data: ChildCreateRequest, parent: Parent, db: Session) -> ChildResponse:
    try:
        tier = Child.compute_tier(data.age)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    child = Child(parent_id=parent.id, name=data.name, age=data.age, profile_tier=tier)
    db.add(child)
    db.commit()
    db.refresh(child)
    return ChildResponse.from_orm_child(child)


def get_child(child_id: int, parent: Parent, db: Session) -> ChildResponse:
    return ChildResponse.from_orm_child(_get_child_or_404(child_id, parent, db))


def update_child(child_id: int, data: ChildUpdateRequest, parent: Parent, db: Session) -> ChildResponse:
    child = _get_child_or_404(child_id, parent, db)
    if data.name is not None:
        child.name = data.name
    if data.age is not None:
        try:
            child.age = data.age
            child.profile_tier = Child.compute_tier(data.age)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    db.commit()
    db.refresh(child)
    return ChildResponse.from_orm_child(child)


def delete_child(child_id: int, parent: Parent, db: Session) -> None:
    child = _get_child_or_404(child_id, parent, db)
    db.delete(child)
    db.commit()


def generate_link_code(child_id: int, parent: Parent, db: Session) -> LinkCodeResponse:
    child = _get_child_or_404(child_id, parent, db)
    raw_code = str(secrets.randbelow(1_000_000)).zfill(6)
    child.link_code_hash = hash_token(raw_code)
    db.commit()
    return LinkCodeResponse(child_id=child.id, code=raw_code, expires_in=_LINK_CODE_TTL_SECONDS)


def link_device(child_id: int, code: str, device_id: str, parent: Parent, db: Session) -> ChildResponse:
    child = _get_child_or_404(child_id, parent, db)
    if child.link_code_hash is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun code de liaison actif. Génère-en un nouveau.",
        )
    if hash_token(code) != child.link_code_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code de liaison incorrect.")
    existing = db.query(Child).filter(Child.device_id == device_id).first()
    if existing and existing.id != child_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet appareil est déjà lié à un autre profil.")
    child.device_id = device_id
    child.link_code_hash = None
    db.commit()
    db.refresh(child)
    return ChildResponse.from_orm_child(child)
PYEOF
echo "   [OK] services/children_service.py"

# =============================================================================
# routers/children.py
# =============================================================================
cat > "$BASE/routers/children.py" << 'PYEOF'
"""
Router Children — CRUD profils enfants + liaison appareil.
Préfixe : /api/v1/children
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from nexuscare.core.database import get_db
from nexuscare.core.dependencies import get_current_parent
from nexuscare.models.parent import Parent
from nexuscare.schemas.children import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    LinkCodeResponse,
    LinkDeviceRequest,
    MessageResponse,
)
from nexuscare.services import children_service

router = APIRouter(prefix="/children", tags=["Enfants"])


@router.get("", response_model=list[ChildResponse], summary="Lister les enfants")
def list_children(
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> list[ChildResponse]:
    return children_service.list_children(current_parent, db)


@router.post("", response_model=ChildResponse, status_code=status.HTTP_201_CREATED,
             summary="Créer un profil enfant")
def create_child(
    data: ChildCreateRequest,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ChildResponse:
    return children_service.create_child(data, current_parent, db)


@router.get("/{child_id}", response_model=ChildResponse, summary="Détail d'un enfant")
def get_child(
    child_id: int,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ChildResponse:
    return children_service.get_child(child_id, current_parent, db)


@router.patch("/{child_id}", response_model=ChildResponse, summary="Modifier un enfant")
def update_child(
    child_id: int,
    data: ChildUpdateRequest,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ChildResponse:
    return children_service.update_child(child_id, data, current_parent, db)


@router.delete("/{child_id}", response_model=MessageResponse, summary="Supprimer un enfant")
def delete_child(
    child_id: int,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> MessageResponse:
    children_service.delete_child(child_id, current_parent, db)
    return MessageResponse(message="Profil enfant supprimé.")


@router.post("/{child_id}/link-code", response_model=LinkCodeResponse,
             summary="Générer un code de liaison")
def generate_link_code(
    child_id: int,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> LinkCodeResponse:
    return children_service.generate_link_code(child_id, current_parent, db)


@router.post("/{child_id}/link-device", response_model=ChildResponse,
             summary="Lier un appareil Android")
def link_device(
    child_id: int,
    data: LinkDeviceRequest,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ChildResponse:
    return children_service.link_device(child_id, data.code, data.device_id, current_parent, db)
PYEOF
echo "   [OK] routers/children.py"

# =============================================================================
# main.py
# =============================================================================
cat > "$BASE/main.py" << 'PYEOF'
"""
NexusCare Backend — Point d'entrée FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from nexuscare.core.config import settings
from nexuscare.core.database import engine, Base
import nexuscare.models  # noqa: F401 — importe tous les modèles pour SQLAlchemy
from nexuscare.routers import auth as auth_router
from nexuscare.routers import children as children_router


def create_application() -> FastAPI:
    application = FastAPI(
        title="NexusCare API",
        version="1.0.0",
        description="Backend de contrôle parental NexusCare — Projet Master 1",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url=None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    Base.metadata.create_all(bind=engine)
    application.include_router(auth_router.router,     prefix="/api/v1")
    application.include_router(children_router.router, prefix="/api/v1")

    @application.get("/health", tags=["Système"])
    def health_check():
        return {"status": "ok", "version": "1.0.0"}

    return application


app = create_application()
PYEOF
echo "   [OK] main.py"

# =============================================================================
# tests/test_children.py
# =============================================================================
cat > "$TESTS/test_children.py" << 'PYEOF'
"""
Tests d'intégration — Module Children (37 tests au total avec Auth)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from nexuscare.core.database import Base, get_db
from nexuscare.main import app

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict:
    client.post("/api/v1/auth/register", json={
        "full_name": "Sandrine Dupont",
        "email": "sandrine@test.com",
        "password": "motdepasse123",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "sandrine@test.com",
        "password": "motdepasse123",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def created_child(client: TestClient, auth_headers: dict) -> dict:
    resp = client.post("/api/v1/children", json={"name": "Léo", "age": 8}, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


class TestCreateChild:
    def test_create_childhood(self, client, auth_headers):
        resp = client.post("/api/v1/children", json={"name": "Léo", "age": 8}, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Léo"
        assert body["profile_tier"] == "CHILDHOOD"
        assert body["is_linked"] is False

    def test_create_preadolescence(self, client, auth_headers):
        resp = client.post("/api/v1/children", json={"name": "Emma", "age": 13}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["profile_tier"] == "PREADOLESCENCE"

    def test_age_boundary_min(self, client, auth_headers):
        resp = client.post("/api/v1/children", json={"name": "Mini", "age": 6}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["profile_tier"] == "CHILDHOOD"

    def test_age_boundary_max(self, client, auth_headers):
        resp = client.post("/api/v1/children", json={"name": "Ado", "age": 15}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["profile_tier"] == "PREADOLESCENCE"

    def test_age_too_young(self, client, auth_headers):
        resp = client.post("/api/v1/children", json={"name": "Bébé", "age": 5}, headers=auth_headers)
        assert resp.status_code == 422

    def test_age_too_old(self, client, auth_headers):
        resp = client.post("/api/v1/children", json={"name": "Adulte", "age": 16}, headers=auth_headers)
        assert resp.status_code == 422

    def test_requires_auth(self, client):
        resp = client.post("/api/v1/children", json={"name": "Léo", "age": 8})
        assert resp.status_code == 403


class TestListChildren:
    def test_list_empty(self, client, auth_headers):
        resp = client.get("/api/v1/children", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_multiple(self, client, auth_headers):
        client.post("/api/v1/children", json={"name": "Léo", "age": 8}, headers=auth_headers)
        client.post("/api/v1/children", json={"name": "Emma", "age": 13}, headers=auth_headers)
        resp = client.get("/api/v1/children", headers=auth_headers)
        assert len(resp.json()) == 2

    def test_isolation_between_parents(self, client, auth_headers):
        client.post("/api/v1/children", json={"name": "Léo", "age": 8}, headers=auth_headers)
        client.post("/api/v1/auth/register", json={
            "full_name": "Autre", "email": "autre@test.com", "password": "motdepasse123"
        })
        r = client.post("/api/v1/auth/login", json={"email": "autre@test.com", "password": "motdepasse123"})
        h2 = {"Authorization": f"Bearer {r.json()['access_token']}"}
        assert client.get("/api/v1/children", headers=h2).json() == []


class TestGetChild:
    def test_get_existing(self, client, auth_headers, created_child):
        resp = client.get(f"/api/v1/children/{created_child['id']}", headers=auth_headers)
        assert resp.status_code == 200

    def test_get_not_found(self, client, auth_headers):
        assert client.get("/api/v1/children/9999", headers=auth_headers).status_code == 404

    def test_cannot_access_other_parent_child(self, client, auth_headers, created_child):
        client.post("/api/v1/auth/register", json={
            "full_name": "Autre", "email": "autre@test.com", "password": "motdepasse123"
        })
        r = client.post("/api/v1/auth/login", json={"email": "autre@test.com", "password": "motdepasse123"})
        h2 = {"Authorization": f"Bearer {r.json()['access_token']}"}
        assert client.get(f"/api/v1/children/{created_child['id']}", headers=h2).status_code == 404


class TestUpdateChild:
    def test_update_name(self, client, auth_headers, created_child):
        resp = client.patch(f"/api/v1/children/{created_child['id']}",
                            json={"name": "Léo Updated"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Léo Updated"

    def test_update_age_changes_tier(self, client, auth_headers, created_child):
        resp = client.patch(f"/api/v1/children/{created_child['id']}",
                            json={"age": 12}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["profile_tier"] == "PREADOLESCENCE"

    def test_partial_update(self, client, auth_headers, created_child):
        resp = client.patch(f"/api/v1/children/{created_child['id']}",
                            json={"name": "Léo Nouveau"}, headers=auth_headers)
        assert resp.json()["age"] == created_child["age"]


class TestDeleteChild:
    def test_delete(self, client, auth_headers, created_child):
        resp = client.delete(f"/api/v1/children/{created_child['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert client.get(f"/api/v1/children/{created_child['id']}", headers=auth_headers).status_code == 404

    def test_delete_not_found(self, client, auth_headers):
        assert client.delete("/api/v1/children/9999", headers=auth_headers).status_code == 404


class TestLinkDevice:
    def test_generate_code(self, client, auth_headers, created_child):
        resp = client.post(f"/api/v1/children/{created_child['id']}/link-code", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["code"]) == 6 and body["code"].isdigit()
        assert body["expires_in"] == 600

    def test_link_success(self, client, auth_headers, created_child):
        code = client.post(f"/api/v1/children/{created_child['id']}/link-code",
                           headers=auth_headers).json()["code"]
        resp = client.post(f"/api/v1/children/{created_child['id']}/link-device",
                           json={"code": code, "device_id": "android-001"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_linked"] is True

    def test_wrong_code(self, client, auth_headers, created_child):
        client.post(f"/api/v1/children/{created_child['id']}/link-code", headers=auth_headers)
        resp = client.post(f"/api/v1/children/{created_child['id']}/link-device",
                           json={"code": "000000", "device_id": "android-001"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_no_code_generated(self, client, auth_headers, created_child):
        resp = client.post(f"/api/v1/children/{created_child['id']}/link-device",
                           json={"code": "123456", "device_id": "android-001"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_code_single_use(self, client, auth_headers, created_child):
        code = client.post(f"/api/v1/children/{created_child['id']}/link-code",
                           headers=auth_headers).json()["code"]
        client.post(f"/api/v1/children/{created_child['id']}/link-device",
                    json={"code": code, "device_id": "android-001"}, headers=auth_headers)
        resp = client.post(f"/api/v1/children/{created_child['id']}/link-device",
                           json={"code": code, "device_id": "android-002"}, headers=auth_headers)
        assert resp.status_code == 400
PYEOF
echo "   [OK] tests/test_children.py"

# =============================================================================
# __init__.py vides pour les packages
# =============================================================================
touch "$BASE/schemas/__init__.py"
touch "$BASE/services/__init__.py"
touch "$BASE/routers/__init__.py"
echo "   [OK] __init__.py packages"

# =============================================================================
# Lancer les tests
# =============================================================================
echo ""
echo ">> Lancement des tests..."
cd "$HOME/nexuscare/backend"
source .venv/bin/activate
python -m pytest tests/ -v --tb=short
