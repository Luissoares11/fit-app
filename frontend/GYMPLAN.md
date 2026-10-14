# Gym feature plan

## Context

This repo is a self-hosted personal fitness tracker (weight and progress photos), used mostly on a phone by a single user. Backend: FastAPI + SQLite. Frontend: React (Vite, plain JavaScript), served by FastAPI in production. Existing pages: Login, Dashboard, Register, Progress, Profile.

This document adds gym training: a weekly plan, an exercise library, per-exercise logging with personal records (PRs), and a guided workout view.

**Read the existing code first** (`backend/app`, `backend/tests`, `frontend/src`) and follow its conventions. The repo has grown since its first scaffold. Where this document names files or patterns that differ from the repo, the repo wins.

## Conventions to keep

- Backend: plain SQL with `sqlite3`, no ORM, no repository or service layer. Thin routes in `backend/app/routes/`, pydantic models in `schemas.py`, schema created in `db.py` with `CREATE TABLE IF NOT EXISTS`. Every new route sits behind the existing `require_token` dependency and under the `/api` prefix.
- Pure logic (record calculations) lives in its own module (`backend/app/records.py`) so it can be unit tested without HTTP, the same way `images.py` is.
- Frontend: plain JavaScript (no TypeScript), no router library, no state library, plain `fetch` through `src/api.js`. Pages are held in state in `App.jsx`, and navigation is a left drawer (☰ in the top bar), not a tab bar. There is no chart library: charts are hand-built SVG (see `WeightChart.jsx`). Keep the single `index.css` approach.
- Mobile-first. Inputs use 16px font (stops iOS zoom), tap targets at least 44px, `inputMode="decimal"` for weight, `inputMode="numeric"` for reps. Weight inputs accept both `80.5` and `80,5` (the Register page already parses this, reuse that logic).
- Units are kg only.
- Dates are local `YYYY-MM-DD` strings, never UTC-derived.
- Weekdays are stored as integers 0 to 6 with **0 = Monday** (Python `date.weekday()`). JavaScript `getDay()` has Sunday = 0, so convert with `(getDay() + 6) % 7`. Profile's check-in day uses the same convention. Both share `WEEKDAY_NAMES` and `weekdayIndex` in `frontend/src/dates.js`.
- Commit messages are concise one-liners.

## Working agreement

- Work **one phase at a time**. After each phase: run all tests, summarize what changed, and stop. Do not start the next phase.
- If something is ambiguous, pick the simplest option, note the assumption in the summary, and keep going. Do not ask more than one question at a time.
- Do not add dependencies unless needed. If one is needed, say why.
- All backend tests stay in `backend/tests/tests.py` (decided: no `conftest.py`).

## Decisions already made

1. Profile stays personal only (no gym section, no dropdowns).
2. New **Gym** entry in the drawer with three sections: **Today**, **Plan**, **Exercises**. Drawer order: Dashboard, Register, Gym, Progress, Profile.
3. Muscle groups are separate items. A training day selects one or more of them (for example "chest + triceps" is two groups). Never store a combined label as one string.
4. The same muscle group may appear on more than one day.
5. "Days per week" is not a stored field. It is the count of training days in the plan.
6. The plan is a suggestion, never a lock. Today always allows switching to another day's workout or training on a rest day.
7. Each exercise belongs to exactly one muscle group (its main one).
8. Exercises are archived, never hard-deleted, because logged sets reference them.
9. **PRs are derived from logged sets, never entered separately.** There is no PR table. Every set is stored once, and records are computed from the sets, so they can never disagree with the history.
10. Sets can be logged in two ways, and both write to the same tables:
    - **Quick log** from the exercise detail view (tap an exercise in the Exercises section). Saved immediately. Built in phase 2.
    - **Guided workout** in the Today section. Built on the phone, saved once on Finish. Built in phase 3.
11. The quick log date defaults to today and can be changed to a past date (never a future date). This is also how PRs from before the app existed are entered.
12. Quick log adds the sets to the most recent workout on that date, creating the workout if none exists for that date.
13. The in-progress guided workout lives in `localStorage` until Finish.

## Data model

```sql
CREATE TABLE IF NOT EXISTS muscle_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    muscle_group_id INTEGER NOT NULL REFERENCES muscle_groups(id),
    archived INTEGER NOT NULL DEFAULT 0,
    UNIQUE (name, muscle_group_id)
);

CREATE TABLE IF NOT EXISTS plan_days (
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    muscle_group_id INTEGER NOT NULL REFERENCES muscle_groups(id),
    PRIMARY KEY (weekday, muscle_group_id)
);

-- Phase 2
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workout_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
    set_order INTEGER NOT NULL,
    weight_kg REAL NOT NULL,
    reps INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_workout_sets_exercise ON workout_sets(exercise_id);
CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(date);
```

Notes:
- A weekday with no rows in `plan_days` is a rest day.
- Multiple workouts on the same date are allowed (no unique constraint on `date`).
- `set_order` is the position of the set within its exercise inside that workout (1, 2, 3, ...).
- Foreign keys are already enabled per connection (`PRAGMA foreign_keys = ON`). Keep it that way.

### Seed data

Seed in `init_db`, idempotently (running it twice must not duplicate anything).

Muscle groups: `chest`, `back`, `shoulders`, `biceps`, `triceps`, `legs`, `glutes`, `abs`, `forearms`. The defaults are seeded once per database (tracked in `app_meta`), so renamed or deleted groups stay that way. Databases seeded earlier with Portuguese names are renamed on startup (`LEGACY_NAMES` in `db.py`).

Starter exercises, inserted **only if the `exercises` table is empty** (so exercises the user archives do not come back on restart):

| Group | Exercises |
|---|---|
| chest | Flat barbell bench press, Incline dumbbell press, Cable crossover |
| back | Lat pulldown, Seated cable row, Bent-over barbell row |
| shoulders | Dumbbell shoulder press, Lateral raise, Face pull |
| biceps | Barbell curl, Alternating dumbbell curl, Hammer curl |
| triceps | Triceps pushdown, EZ-bar skull crusher, Dips |
| legs | Squat, Leg press, Lying leg curl, Calf raise |
| glutes | Hip thrust |
| abs | Plank, Leg raise |

## Records (PR logic)

Computed in `backend/app/records.py` from the sets of one exercise, across all dates. Pure functions, no database access inside them.

Definitions:

- **heaviest**: the set with the highest `weight_kg` among sets with `weight_kg > 0`. Ties: more reps wins, then the most recent date.
- **by_reps**: for each distinct rep count among sets with `weight_kg > 0`, the highest weight lifted at exactly that rep count, with the date of its most recent occurrence.
- **best_e1rm**: the highest estimated one-rep max, `weight_kg * (1 + reps / 30)` (Epley), among sets with `weight_kg > 0` and `reps <= 12`. Rounded to one decimal.
- **most_reps**: the highest `reps` among sets with `weight_kg = 0` (bodyweight exercises such as pull-ups). Null if there are none.

A newly logged set is a **new PR** of a given type when it **strictly beats** the previous value of that type (ties do not count). A type needs an earlier value to beat: the very first set ever logged for an exercise reports no PRs, and the first time a rep count appears does not count as a `rep_best` PR.

Evaluation rules:
- Compare against all sets already in the database for that exercise, regardless of date ("all-time best at the moment of logging").
- When several sets arrive in one request, evaluate them in array order, each against everything before it, including the earlier sets of the same request.
- Sets with `weight_kg = 0` can only produce `most_reps`. Sets with `weight_kg > 0` can produce `heaviest`, `rep_best` and `e1rm`.

New PRs are reported as a list. Shapes:

```json
[
  { "type": "heaviest", "weight_kg": 100, "reps": 3 },
  { "type": "rep_best", "reps": 5, "weight_kg": 90 },
  { "type": "e1rm", "value": 112.5 },
  { "type": "most_reps", "reps": 15 }
]
```

## API

All routes under `/api`, all authenticated.

### Phase 1

| Method | Path | Notes |
|---|---|---|
| GET | `/muscle-groups` | `[{id, name}]` |
| POST | `/muscle-groups` | `{name}`. Trim and lowercase the name. 201 with `{id, name}`. 409 if the name already exists. 422 for an empty name or one longer than 40 characters |
| PATCH | `/muscle-groups/{id}` | `{name}`, same rules as POST. 200 with `{id, name}`. 404 if missing, 409 on duplicate. Exercises and plan days follow the group by id |
| DELETE | `/muscle-groups/{id}` | 204. 409 if any exercise (archived ones too) or any plan day uses the group. 404 if missing |
| GET | `/exercises` | Non-archived only. Optional `?muscle_group_id=`. Each item: `{id, name, muscle_group_id}` |
| POST | `/exercises` | `{name, muscle_group_id}`. Trim the name. 409 if the same name already exists in that group. 422 for an unknown group or empty name |
| PATCH | `/exercises/{id}` | Optional `name` and `muscle_group_id`. 404 if missing, 409 on duplicate |
| POST | `/exercises/{id}/archive` | Archives (sets `archived = 1`), returns 204. Idempotent. 404 if missing |
| DELETE | `/exercises/{id}` | Permanently deletes the exercise, returns 204. 409 if it has logged sets (archive it instead). 404 if missing |
| GET | `/plan` | `{days: [{weekday, muscle_group_ids: [..]}]}`, training days only, sorted by weekday |
| PUT | `/plan` | Replaces the whole plan atomically in one transaction. Same shape as GET |

`PUT /plan` validation (422 on failure): weekday between 0 and 6, no duplicate weekdays, every day has at least one group, every group id exists, no duplicate group ids within a day.

### Phase 2 (quick log and records)

| Method | Path | Notes |
|---|---|---|
| POST | `/exercises/{id}/sets` | Body: `{date, sets: [{weight_kg, reps}]}`. Finds the most recent workout on `date` or creates one, then inserts the sets with `set_order` continuing after the exercise's existing sets in that workout. Returns 201 with `{workout_id, set_ids, new_prs}`. 404 if the exercise is missing or archived |
| GET | `/exercises/{id}/records` | See shape below |
| PATCH | `/sets/{id}` | Optional `weight_kg` and `reps`, same validation as creation. 404 if missing. Returns the updated set |
| DELETE | `/sets/{id}` | 204. If the workout is left with no sets, delete the workout too |

Validation for sets: `weight_kg` between 0 and 1000 (0 allowed for bodyweight exercises), `reps` an integer between 1 and 200, `sets` has at least 1 and at most 50 items, `date` is a valid date and **not in the future** (compare with the server's local date). If anything is invalid, nothing is saved.

`GET /exercises/{id}/records` response:

```json
{
  "exercise_id": 12,
  "heaviest": { "weight_kg": 100, "reps": 3, "date": "2026-10-13" },
  "best_e1rm": { "value": 110.0, "weight_kg": 100, "reps": 3, "date": "2026-10-13" },
  "by_reps": [
    { "reps": 3, "weight_kg": 100, "date": "2026-10-13" },
    { "reps": 8, "weight_kg": 80, "date": "2026-10-06" }
  ],
  "most_reps": null,
  "history": [
    {
      "date": "2026-10-13",
      "sets": [{ "id": 41, "weight_kg": 100, "reps": 3 }]
    }
  ]
}
```

`heaviest`, `best_e1rm` and `most_reps` are null when there is no qualifying set. `by_reps` is sorted by reps ascending. `history` is newest date first, sets in `set_order`.

### Phase 3 (guided workout)

| Method | Path | Notes |
|---|---|---|
| POST | `/workouts` | `{date, note?, sets: [{exercise_id, weight_kg, reps}]}`. Creates the workout and all sets in one transaction. `set_order` is assigned from the array order, per exercise. Returns 201 with `{id, new_prs}` where `new_prs` is grouped per exercise id. Same set validation as phase 2; every `exercise_id` must exist (archived is allowed) |
| GET | `/exercises/last-sets?exercise_ids=1,2,3` | For each exercise, the sets from its most recent workout: `{"1": {"date": "...", "sets": [{"weight_kg": 60, "reps": 8}]}}`. Exercises never logged are omitted |

**Route order matters in FastAPI:** declare `/exercises/last-sets` before any `/exercises/{id}` route, otherwise `last-sets` is parsed as an id and returns 422.

### Phase 4 (history)

| Method | Path | Notes |
|---|---|---|
| GET | `/workouts` | Newest first. Each item: `{id, date, note, exercise_count, set_count, muscle_groups: [names]}` |
| GET | `/workouts/{id}` | Workout with its sets grouped by exercise |
| DELETE | `/workouts/{id}` | 204, sets cascade |

## Frontend

### Structure

- New **Gym** page in the drawer (`App.jsx`). Inside it, a segmented control with **Today / Plan / Exercises**.
- Gym code lives in `src/components/Gym/`: `Gym.jsx`, `Plan.jsx`, `Exercises.jsx`, `ExerciseForm.jsx`, `ExerciseDetail.jsx`. `Today.jsx` comes in phase 3.
- Load muscle groups, exercises and the plan once when the Gym tab opens and refresh after each save. No global store.
- Default section: **Plan** during phases 1 and 2 (Today does not exist yet), **Today** from phase 3 on.
- Navigation inside Gym (list to exercise detail and back) is plain component state, no router.

### Plan section

- Seven rows, Monday to Sunday. Tapping a row toggles it between rest and training.
- A training row shows the muscle groups as multi-select chips (chest, back, ...).
- Read-only summary at the top: "N training days per week". Not editable.
- Explicit **Save plan** button that sends `PUT /plan`. A training day with no group selected blocks saving with a clear message.
- Show success and error states like the Check-in screen does.

### Exercises section

- Exercises grouped by muscle group (collapsible sections or filter chips, whichever fits the existing style).
- **Add exercise** with a name field and a group selector, defaulting to the group the user is currently looking at.
- Empty groups show a short hint instead of a blank area.
- **Tapping an exercise opens its detail view** (phase 2, built). The Edit button in that view handles rename, move to another group, and archive with confirmation.

### Exercise detail view (phase 2)

Opens when tapping an exercise. Full-screen on mobile with a back button.

- **Header:** exercise name and muscle group. An **Edit** button opens rename, move to another group, and archive (with confirmation). These moved here from the list.
- **Log form** at the top:
  - Date, defaulting to today (local) and changeable to a past date, never a future date.
  - Weight (kg) and reps. Weight 0 is allowed, with a short hint such as "0 for bodyweight".
  - **Log set** button.
  - After a successful save: keep the date and weight, clear the reps field and focus it (several sets at the same weight are common), add the set to a "Logged now" list under the form, and refresh records and history.
  - If the response contains `new_prs`, show a clear "New PR" banner naming each PR (for example "Heaviest: 100 kg x 3", "Estimated 1RM: 112.5 kg").
  - Validation errors are shown inline. Weight accepts a comma or a dot.
- **Records card:** heaviest, best estimated 1RM, best weight per rep count (compact table, only rep counts that have data), and most reps (only shown if bodyweight sets exist). Empty state: "No sets logged yet".
- **History:** grouped by date, newest first. Each set shows `weight x reps` with **edit** and **delete** (delete asks for confirmation). Mistakes are common when typing between sets, so editing and deleting are required, not optional.
- Show weights without a trailing `.0` (80 not 80.0).

### Today section (phase 3)

Behavior:
1. Work out today's weekday (0 = Monday). If the plan has groups for it, show those groups' exercises, ordered by group then by id.
2. On a rest day, show "Rest day" with a **Train anyway** button. Also offer **Train something else** which lets the user pick another weekday's plan or choose muscle groups manually.
3. Each exercise is a card with:
   - Name and a "Last time" hint, for example `Last time: 3 sets, 60 kg x 8` (from `/exercises/last-sets`).
   - A list of set rows, each with a weight input, a reps input, and a done checkmark.
   - **Add set** button. The new set copies the previous set's weight and reps.
   - A way to skip or remove the whole exercise for today.
4. **Prefill rule:** when an exercise has history, its sets start as copies of the last session's sets (same count, same weight and reps), all unchecked. With no history, start with one empty set.
5. **Add exercise** to today's workout from the library (any group).
6. **Finish workout** sends only checked sets with valid values. If none are checked, show a message instead of saving. On success, show a summary including any `new_prs`, using the same banner style as the exercise detail view.
7. **Discard workout** with confirmation.

Draft persistence:
- Store the draft in `localStorage` under one key (for example `gym-draft`) on every change. Wrap reads and writes in try/catch.
- On load, if a draft exists, restore it and show a "Resume workout" state.
- Clear the draft only after a successful save or an explicit discard.
- Suggested shape (keep input values as strings):

```json
{
  "date": "2026-10-14",
  "exercises": [
    {
      "exercise_id": 12,
      "sets": [{ "weight": "60", "reps": "8", "done": false }]
    }
  ]
}
```

## Phases

### Phase 1: setup (library and plan)

**Status: done.** Built as `routes/exercises.py` and `routes/plan.py`, with the Plan and Exercises screens in `components/Gym/`. Tests are in `tests.py`.

Backend: tables, seeding, muscle group, exercise and plan routes, tests.
Frontend: Gym tab with Plan and Exercises sections (Today shows a short "coming next" placeholder or is hidden). Tapping an exercise opens the small edit form.

Done when:
- Seeded groups and exercises appear on a fresh database, and restarting the server does not duplicate them.
- The user can add, rename, move and archive exercises.
- The user can build a plan (for example Mon chest + triceps, Tue back + biceps, Wed legs, Thu shoulders, Fri chest + back), save it, reload the page, and see it again.
- All tests pass and no existing test broke.

### Phase 2: exercise detail, quick log and records

**Status: done.** Built as `records.py` (pure PR logic), `routes/sets.py` (quick log, records, set edit and delete), and `components/Gym/ExerciseDetail.jsx`. Tests are in `tests.py`.

Backend: `workouts` and `workout_sets` tables, `records.py`, quick log, records, set edit and delete routes, tests.
Frontend: exercise detail view replacing the small edit form.

Done when:
- Tapping an exercise opens the detail view with a log form defaulting to today.
- Logging a set saves it, and logging several sets in a row works without retyping the weight.
- A past date can be logged, a future date is rejected.
- Records and history update after every save, edit and delete.
- A set that beats the previous best shows the "New PR" banner, and the first set ever logged for an exercise does not.
- Deleting the last set of a workout removes the empty workout.
- All tests pass.

### Phase 3: guided workout (Today)

**Status: done, then changed to display-only.** The Today screen is now a read-only view: today's planned exercises, each with its PR below. The logging UI (drafts, Finish, Discard, start and switch screens) was removed, and `draft.js` and `Workout.jsx` were deleted. The backend endpoints (`POST /workouts`, `last-sets`) remain and the UI does not use them. Originally built as `routes/workouts.py` (`POST /workouts`), `last-sets` in `routes/exercises.py`, and `components/Gym/` (`Today.jsx` for start and switch screens, `Workout.jsx` for the active workout, `draft.js` for localStorage and prefill, `format.js` for shared number and PR formatting). Decisions made while building: "Train anyway" on a rest day starts an empty workout; "Train something else" offers other days' plans or manual group chips; a workout takes up to 200 sets; Finish saves only sets marked done, and the draft is cleared only after a successful save or Discard.

Backend: `POST /workouts`, `last-sets`, tests.
Frontend: Today section with prefill and the localStorage draft.

Done when:
- Starting a workout on a planned day preloads the right exercises.
- Refreshing the page mid-workout restores the draft.
- Finishing saves everything in one request, shows PR banners, and the next workout shows last time's numbers prefilled.
- Rest day, train anyway, and train something else all work.

### Phase 4: history and charts (only after phases 1 to 3 are in real use)

- Workout history list and detail view.
- Per-exercise progress charts (heaviest weight and estimated 1RM over time).
- Dashboard card: workouts completed this week versus planned training days.

Do not start phase 4 without being asked.

## Tests (backend, pytest)

Follow the existing test style (temporary `DATA_DIR`, `TestClient`, login via `/api/login`).

Phase 1:
- Every new route returns 401 without credentials.
- Seeding is idempotent (calling `init_db` twice leaves the same row counts).
- Exercise create, list (with and without the group filter), rename, move group, archive hides it from the list.
- Duplicate exercise name in the same group returns 409, the same name in a different group is allowed.
- Unknown muscle group returns 422.
- `PUT /plan`: valid plan round-trips through `GET /plan`; duplicate weekday, weekday out of range, empty day, unknown group, and duplicate group in a day all return 422; a failed PUT leaves the previous plan untouched; a second PUT fully replaces the first.

Phase 2:
- `records.py` unit tests (no HTTP): Epley calculation, e1RM ignored above 12 reps, heaviest tie-breaking, best weight per rep count, `most_reps` only from weight 0 sets, ties are not PRs, the first set ever reports no PRs, the first time a rep count appears is not a `rep_best` PR, several sets in one request are evaluated in order.
- `POST /exercises/{id}/sets`: creates a workout when none exists for the date, appends to the existing workout on the same date, `set_order` continues correctly, past date accepted, future date rejected (422), weight 0 accepted, negative weight and reps 0 rejected, archived or missing exercise returns 404, an invalid set in a batch saves nothing.
- `GET /exercises/{id}/records`: empty state returns nulls and empty lists, populated state matches the definitions, history is newest first.
- `PATCH /sets/{id}` and `DELETE /sets/{id}`: edit validates like creation, deleting the last set removes the workout, deleting one of several keeps the workout.
- Archived exercises still return their records and history.
- Every new route returns 401 without credentials.

Phase 3:
- `POST /workouts` saves the workout and all sets in one transaction; an invalid exercise id or invalid set saves nothing; `new_prs` is grouped per exercise.
- `last-sets` returns the most recent workout's sets per exercise and omits never-logged exercises.
- `/exercises/last-sets` is not captured by the `/exercises/{id}` routes.

## Out of scope

Rest timer, drag-to-reorder exercises, supersets, plate calculator, templates beyond the weekly plan, offline sync queue, social features, calorie tracking, AI suggestions, multi-user support, renaming muscle groups from the UI, a separate manual PR table.

## Assumptions to confirm later

- Starter exercise list is only a convenience and is fully editable.
- Exercise order inside a day is group order, then creation order.
- Estimated 1RM uses the Epley formula and is only calculated up to 12 reps.
- **Decided: backdated sets are compared against all logged sets.** A set logged for an earlier date is compared against everything already stored, so it can be a PR. This is how PRs from before the app are entered (decision 11).
- An archived exercise still blocks re-adding the same name in the same group (409). Restoring archived exercises is not built.
- **Decided: the quick log saves one set per press.** The batch endpoint accepts several sets for later use.
- Editing or deleting a set does not show PR banners.
- **Decided: ties are not PRs.**