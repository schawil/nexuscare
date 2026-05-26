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
