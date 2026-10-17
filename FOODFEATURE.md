# Nutrition Feature Plan

Context: existing FastAPI + SQLite backend, React (Vite, plain JS) frontend, mobile-first. Add a Nutrition section as a separate page with 3 tabs.

## 1. Profile change (do this first, BMR depends on it)

- Backend: add a `sex` column to the profile table/model, values `male` or `female`. Include it in the profile schemas (create, update, read).
- Existing profile row: migrate safely, `sex` and `weight_loss_pace` start as null.
- Backend: add a `weight_loss_pace` column to the profile (`mild`, `moderate`, `aggressive`, `extreme`), same migration rules. Drop the old `goal_kcal` column.
- Frontend: add a Sex selector (male / female) and a Weight loss pace selector to the personal section of the profile form, saved with the rest of the profile data.
- Missing values: if any of `sex`, `height_cm`, `age`, `weight_used`, `weight_loss_pace`, or `goal_weight_kg` is missing, the Nutrition Overview shows `N/A (missing: <list>)` in place of the affected numbers, listing every missing value, e.g. `N/A (missing: sex, weight loss pace)`. Never guess a default.

## 2. Backend

### Tables

- `foods`: id, name, kcal_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g (macros nullable, unused in UI for now)
- `food_plans`: id, name (unique)
- `plan_meals`: id, plan_id, position (1..N), name
- `plan_items`: id, plan_meal_id, food_id (references `foods`), grams
- `food_weekdays`: weekday (0 = Monday .. 6 = Sunday), plan_id (nullable). Each weekday points at one plan, or none.

There is no log table. Meals and logs are out of scope for this version.

### Calorie logic (single helper, used everywhere)

```
kcal = kcal_per_100g * grams / 100
```

### Endpoints

All under `/food`.

- CRUD `/food/foods`. Deleting a food also removes it from every plan (`plan_items` rows that use it), after the confirmation described in Notes.
- Plans: `GET /food/plans` (list with meal count, day kcal, and weekdays), `POST /food/plans`, `GET|PATCH|DELETE /food/plans/{id}`
- `PUT /food/plans/{id}/meals`: replace that plan's meals (count + items) in one transaction. Rejects unknown food ids with 422.
- Weekdays: `GET /food/weekdays` and `PUT /food/weekdays` (all 7 days, each once; plan ids must exist)
- `GET /food/today?weekday=N`: the plan for a weekday, with its meals and day kcal (defaults to today)
- `GET /food/overview?weekday=N`:
  - `weight_used` and `weight_source` ("checkin" or "profile_start")
  - `bmr`, `tdee`, `goal_kcal`, `deficit` (the daily deficit from the pace), `weight_loss_pace`, `weekly_loss_kg`, `goal_weight_kg`, `weeks_to_goal`
  - `training_days_per_week` (count of Gym plan days)
  - `plan_name`, `planned_meals` with kcal per meal, and `day_kcal` for that weekday
  - `week_days` (each weekday's planned kcal, and whether it is below the weekly average), `week_kcal_avg` (average of the seven weekday plans), `intake_vs_goal` (average minus goal kcal), `intake_status` (`less`, `on_deficit`, `more`). Needs a plan on every day, otherwise these are null and `meal plan on every day` is listed as missing. Within 100 kcal a day of the goal counts as `on_deficit`; the tolerance is in `nutrition.py`.
  - `missing`: list of missing values (see section 1). When not empty, the numbers that depend on them are null.

### BMR

Mifflin-St Jeor, using `weight_used`, profile height, age and sex.

```
male:   10*kg + 6.25*cm - 5*age + 5
female: 10*kg + 6.25*cm - 5*age - 161
```

`weight_used` = latest check-in weight, else profile start weight. If neither exists, `weight_used` is missing.

TDEE = BMR * activity factor.

The activity factor comes from `training_days_per_week`

```
0 days   -> 1.2
1-2 days -> 1.375
3-5 days -> 1.55
6 days -> 1.725
7 days   -> 1.9
```

Keep the factor table in one backend helper so it is easy to tune.

### Goal calories

Goal calories are not typed in. They are calculated from the weight loss pace and goal weight:

```
pace (kg a week): mild 0.25, moderate 0.5, aggressive 0.75, extreme 1.0
daily deficit   = kg_per_week * 7700 / 7
goal_kcal       = tdee - daily deficit
weeks_to_goal   = (weight_used - goal_weight_kg) / kg_per_week
```

If `weight_used` is already at or below `goal_weight_kg`, the deficit is 0, goal kcal equals TDEE, and weeks to goal is 0. The paces and the 7700 kcal per kg are in one backend helper (`nutrition.py`).

## 3. Frontend

A fourth tab in the app, next to Gym and Progress, switched the same way as the others (no URL routing, since the app has none). It has 3 sub-tabs: Overview, Plan, Meals.

### Overview

- Energy card: BMR, TDEE, goal kcal, deficit
- Goal card: weight now (and where it came from), goal weight, pace, time to goal, training days
- This week card: the average intake from the week's plans against the goal, with one of three statuses: eating less, on your deficit, or eating more. Below it, each weekday's planned kcal, with the days under the weekly average flagged.
- Deficit box: shows red accents if the deficit is ever negative (it cannot be with the paces above, so this is a safeguard)
- List of today's planned meals, each with kcal, plus day total
- Read only, shows the plan only
- Missing values show the N/A text from section 1

### Plan

- Top: a weekly schedule (Mon to Sun), each day picks a plan or "No plan"
- Below: one box per plan (name, meals, kcal a day, days it is used on). Tapping a box opens its meals in a popup. "+ New plan" creates one.
- Inside the popup: choose number of meals, per meal add items by picking a food and entering grams. "Rename or delete" opens a smaller form for those two actions.
- Kcal per item, per meal, and day total come from the backend. They update after each change is saved. There is no live preview while typing.
- Inline "add new food" if the food is not in the library, opened as a popup like the other add buttons

### Meals

- The food library: add, edit and delete foods that the user usually eats, so they can be used in plans
- Add, edit and delete each open a popup form

## 4. Dashboard

- "Today's Meals" card: the plan set for today's weekday (its name in the heading), each meal with kcal, and the day total
- Reads `GET /food/today?weekday=N`. Tapping the card opens the Food tab.

## 5. Notes

- Keep all kcal math in the backend helper, the frontend only displays.
- Each weekday uses one plan, so a training day and a rest day can have different plans.
- Any add or edit button opens a form in a popup, as in the rest of the app.
- Deleting a food that is used in a meal or plan asks for confirmation first, showing how many plan entries it appears in. After confirming, the food is deleted and removed from those meals and plans.
- The deficit comes from the chosen pace (see Goal calories). If it is negative, the deficit box shows red accents.

## 6. Tests (pytest)

- kcal helper
- BMR for both sexes
- Activity factor at each boundary: 0, 1, 2, 3, 4, 5, 6, 7 training days
- Weight fallback: check-in, then profile start, then missing
- Missing cases: sex, height, age, weight, weight loss pace, goal weight. Each returns the N/A list and null dependent numbers.
- Pace: each pace gives the right daily deficit and goal kcal, weeks to goal, and eating at maintenance when already at goal weight
- Overview with all values set
- `PUT /food/plans/{id}/meals` validation: unknown food id, zero grams, empty meal name, too many meals. A rejected save leaves the old meals in place.
- Plan names: duplicates rejected, rename, and delete (weekdays using it fall back to no plan)
- Weekdays: each weekday exactly once, unknown plan ids rejected, a day with no plan shows no meals
- Deleting a food removes it from plans
- Intake status: the boundaries (100 kcal band), and the status for a week with plans on every day
- Per-day list: days below the weekly average are flagged
