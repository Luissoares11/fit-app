from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, Field

Angle = Literal["front", "back", "side"]


class SessionIn(BaseModel):
    date: date_type
    weight_kg: float = Field(gt=20, lt=400)
    note: str | None = None


class ProfileIn(BaseModel):
    name: str | None = Field(None, max_length=80)
    start_weight_kg: float | None = Field(None, gt=20, lt=400)
    goal_weight_kg: float | None = Field(None, gt=20, lt=400)
    height_cm: float | None = Field(None, gt=50, lt=260)
    age: int | None = Field(None, ge=5, lt=120)
    checkin_every_days: int = Field(7, ge=1, le=60)