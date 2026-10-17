"""Calorie and energy maths for the food feature. The only place these formulas live:
the frontend only displays what these return."""

# (up to and including this many training days, activity factor). Tune here.
ACTIVITY_FACTORS = ((0, 1.2), (2, 1.375), (5, 1.55), (6, 1.725), (7, 1.9))

# Weight-loss paces, kg per week. Tune here.
WEIGHT_LOSS_PACES = {"mild": 0.25, "moderate": 0.5, "aggressive": 0.75, "extreme": 1.0}
KCAL_PER_KG = 7700  # roughly the energy in a kilo of body fat


def kcal(kcal_per_100g: float, grams: float) -> float:
    return kcal_per_100g * grams / 100


def activity_factor(training_days: int) -> float:
    for max_days, factor in ACTIVITY_FACTORS:
        if training_days <= max_days:
            return factor
    return ACTIVITY_FACTORS[-1][1]


def bmr(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    # Mifflin-St Jeor
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "male" else base - 161


def tdee(bmr_kcal: float, training_days: int) -> float:
    return bmr_kcal * activity_factor(training_days)


def daily_deficit(kg_per_week: float) -> float:
    return kg_per_week * KCAL_PER_KG / 7


# Within this many kcal a day of the goal counts as on the deficit
INTAKE_TOLERANCE_KCAL = 100


def intake_status(avg_kcal: float, goal_kcal: float) -> str:
    """How the weekly average intake compares with the goal: "less", "on_deficit" or "more"."""
    diff = avg_kcal - goal_kcal
    if diff > INTAKE_TOLERANCE_KCAL:
        return "more"
    if diff < -INTAKE_TOLERANCE_KCAL:
        return "less"
    return "on_deficit"
