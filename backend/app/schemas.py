from datetime import date as date_type
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

Angle = Literal["front", "back", "side"]

ExerciseName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
# Lowercase like the seeded groups ("chest", "forearms")
MuscleGroupName = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=40)
]


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
    # The day the start weight was logged; the dashboard counts weeks from it
    start_date: date_type | None = None
    # Mifflin-St Jeor needs sex. No default: null until the user picks one
    sex: Literal["male", "female"] | None = None
    # Pace of weight loss; goal calories are calculated from it, never typed in
    weight_loss_pace: Literal["mild", "moderate", "aggressive", "extreme"] | None = None
    # 0 = Monday, same as Python's date.weekday()
    checkin_weekday: int = Field(0, ge=0, le=6)
    checkin_every_weeks: int = Field(1, ge=1, le=4)


FoodName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
MealName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class FoodIn(BaseModel):
    name: FoodName
    kcal_per_100g: float = Field(ge=0, le=1000)
    protein_per_100g: float | None = Field(None, ge=0, le=100)
    carbs_per_100g: float | None = Field(None, ge=0, le=100)
    fat_per_100g: float | None = Field(None, ge=0, le=100)


class FoodPatch(BaseModel):
    name: FoodName | None = None
    kcal_per_100g: float | None = Field(None, ge=0, le=1000)
    protein_per_100g: float | None = Field(None, ge=0, le=100)
    carbs_per_100g: float | None = Field(None, ge=0, le=100)
    fat_per_100g: float | None = Field(None, ge=0, le=100)


class PlanItemIn(BaseModel):
    food_id: int
    grams: float = Field(gt=0, le=5000)


class PlanMealIn(BaseModel):
    name: MealName
    items: list[PlanItemIn] = Field(default_factory=list, max_length=50)


class FoodPlanIn(BaseModel):
    meals: list[PlanMealIn] = Field(max_length=10)


PlanName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class FoodPlanNameIn(BaseModel):
    name: PlanName


class WeekdayPlanIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    plan_id: int | None = None


class WeekdayPlansIn(BaseModel):
    days: list[WeekdayPlanIn] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def one_per_weekday(self):
        if sorted(d.weekday for d in self.days) != list(range(7)):
            raise ValueError("Give each weekday exactly once")
        return self


class MuscleGroupIn(BaseModel):
    name: MuscleGroupName


class ExerciseIn(BaseModel):
    name: ExerciseName
    muscle_group_id: int


class ExercisePatch(BaseModel):
    name: ExerciseName | None = None
    muscle_group_id: int | None = None


class PlanDay(BaseModel):
    weekday: int = Field(ge=0, le=6)
    muscle_group_ids: list[int]


class PlanIn(BaseModel):
    days: list[PlanDay]

    @model_validator(mode="after")
    def check_days(self):
        weekdays = [d.weekday for d in self.days]
        if len(set(weekdays)) != len(weekdays):
            raise ValueError("Each weekday can appear only once")
        for day in self.days:
            if not day.muscle_group_ids:
                raise ValueError("Every training day needs at least one muscle group")
            if len(set(day.muscle_group_ids)) != len(day.muscle_group_ids):
                raise ValueError("A muscle group can appear only once per day")
        return self


class SetIn(BaseModel):
    weight_kg: float = Field(ge=0, le=1000)  # 0 is allowed for bodyweight exercises
    reps: int = Field(ge=1, le=200)


def _not_in_future(value: date_type) -> date_type:
    if value > date_type.today():
        raise ValueError("Date cannot be in the future")
    return value


class SetsLogIn(BaseModel):
    date: date_type
    sets: list[SetIn] = Field(min_length=1, max_length=50)

    _not_in_future = field_validator("date")(classmethod(lambda cls, v: _not_in_future(v)))


class WorkoutSetIn(SetIn):
    exercise_id: int


class WorkoutIn(BaseModel):
    date: date_type
    note: str | None = Field(None, max_length=500)
    sets: list[WorkoutSetIn] = Field(min_length=1, max_length=200)

    _not_in_future = field_validator("date")(classmethod(lambda cls, v: _not_in_future(v)))


class SetPatch(BaseModel):
    weight_kg: float | None = Field(None, ge=0, le=1000)
    reps: int | None = Field(None, ge=1, le=200)
