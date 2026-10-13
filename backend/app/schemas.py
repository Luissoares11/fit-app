from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, Field

Angle = Literal["front", "back", "side"]


class SessionIn(BaseModel):
    date: date_type
    weight_kg: float = Field(gt=20, lt=400)
    note: str | None = None