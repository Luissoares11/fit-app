# Fitness tracker

A self-hosted personal fitness tracker for one user, mostly used from a phone.
It tracks body weight and progress photos, and it has a gym section for weekly
training plans, an exercise library and personal records (PRs).

## Features

- **Dashboard:** a greeting with your first name and the week number since your start date, today's gym plan (tap it to open Gym), progress from start weight to goal weight, with the time left at your pace (tap it to open Progress), a weight chart of the last five registers, and today's meals (tap to open Nutrition).
- **Register:** log weight and up to three photos (front, back, side). A countdown shows the next check-in, with a "Log now" button for early check-ins. Dates are typed as `dd/mm/yyyy`.
- **Gym**
  - **Today:** today's planned muscle groups and exercises, each with its PR. Tap an exercise to open it.
  - **Plan:** a weekly schedule (Monday to Sunday). Each day is rest or training, with one or more muscle groups.
  - **Exercises:** the library grouped by muscle group, with a new-group button and a CSV import at the top. Add exercises, and edit a group to rename or delete it. Its exercises are listed in that popup, and each opens its edit form. Deleting an exercise also deletes its logged sets, and the app warns you first.
  - **Exercise popup:** log sets (date, weight, reps), see records (heaviest, estimated 1RM, best weight per rep count, most reps for bodyweight) and the full history. Edit and delete sets, and edit the exercise, all in popups.
- **Progress:** current and goal BMI, starting and latest photos, and the full history of weights and photos. Sessions can be deleted.
- **Profile:** name, age, sex, height, start weight and its date, goal weight, weight loss pace (mild to extreme), and the check-in day and repeat (every 1 to 4 weeks).
- **Nutrition:** a food library (kcal and macros per 100 g), weekly meal plans, and an overview.
  - **Meals:** the food library. Add, edit and delete foods, or import them from a CSV.
  - **Plan:** a weekly schedule that picks a plan for each day, and a box per plan. Tapping a box opens its meals in a popup, where you set the number of meals and add foods by grams.
  - **Overview:** BMR (Mifflin-St Jeor), TDEE (BMR times an activity factor from your training days), goal calories calculated from your weight loss pace and goal weight, the time to reach the goal, and whether this week's meal plans put you eating less, on your deficit, or more than the goal. Missing profile values show N/A with the list of what is missing.
  - The full design is in `FOODFEATURE.md`.

PRs are never entered by hand. They are calculated from the logged sets, so the records always match the history. A set beats a PR only when it is strictly better than every earlier set, including sets logged for past dates. Ties are not PRs.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLite (plain `sqlite3`, no ORM), Pillow and pillow-heif for photos.
- **Frontend:** React 19, Vite, plain JavaScript. Charts are hand-written SVG. No router or state library.
- **Storage:** everything is under `data/` (the SQLite database and the photos).

## Setup

1. Copy `.env.example` to `.env` and set `APP_TOKEN` to a long random string. That is the password you type on the login screen.
2. Start the app with Docker:

   ```bash
   docker compose up --build
   ```

   The app listens on `127.0.0.1:8100` (localhost only) and stores data in `./data`.

   The image builds the frontend and serves it from the same port, so there is no separate web server to run.

## Access from your devices (Tailscale)

The app is only reachable from the server itself. Tailscale serve publishes it to your tailnet over HTTPS, so your other devices reach it without opening any port to the internet.

The tailnet publishing rules are shared by every app on the same machine. Before you change anything, look at what is already published:

```bash
tailscale serve status
```

1. In the Tailscale admin console, enable **MagicDNS** and **HTTPS certificates** (DNS page). You only do this once.
2. Choose a free HTTPS port. The default `443` gives a clean address (`https://<server>.<tailnet>.ts.net`), but it is often already taken. Check with `sudo ss -tlnp`. The app listens on local port `8100` (set in `docker-compose.yml`); pick a free HTTPS port such as `8444`.
3. Set `COOKIE_SECURE=true` in `.env`, then start the app with `docker compose up -d --build`.
4. Publish the app, using your chosen port:

   ```bash
   sudo tailscale serve --bg --https=8444 http://127.0.0.1:8100
   tailscale serve status
   ```

5. On each device, turn on Tailscale, open the address from the status, and log in.

To stop sharing only this app, remove its rule (for example `sudo tailscale serve --https=8444 off`). Do not run `tailscale serve reset`: it removes every published app on the machine, including other apps. Do not use `tailscale funnel`: it publishes the app to the whole internet.

## Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
APP_TOKEN=change-me DATA_DIR=../data uvicorn app.main:app --port 8000
```

Frontend (needs Node 22 or newer):

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`. Open the URL it prints, and log in with `APP_TOKEN`.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/tests.py
```

The tests use a temporary data directory and do not touch `data/`.

Lint and build the frontend:

```bash
cd frontend
npm run lint
npm run build
```

## Configuration

| Variable        | Default              | Meaning                                       |
|-----------------|----------------------|-----------------------------------------------|
| `APP_TOKEN`     | required             | Login token                                   |
| `COOKIE_SECURE` | `false`              | Set `true` when served over HTTPS             |
| `DATA_DIR`      | `data`               | Where the database and photos are stored      |
| `FRONTEND_DIR`  | `../frontend`        | Folder served at `/`                          |

## Project layout

```
backend/app/        FastAPI app: routes, database schema, PR logic (records.py), food routes (routes/food.py)
backend/tests/      Backend tests (tests.py)
frontend/src/       React app: pages in components/, gym screens in components/Gym/, nutrition screens in components/Food/
GYMPLAN.md          Design notes and decisions for the gym feature
FOODFEATURE.md      Design notes for the nutrition feature
IMPORTPLAN.md       Design notes for the CSV import of foods and exercises
backend/app/nutrition.py  Calorie, BMR, activity-factor and weight-loss formulas (the only place they live)
backend/app/importer.py   CSV reading and validation for the imports
data/               Runtime data (git-ignored)
```

## Back up your data

Stop the app, then copy the `data/` folder. It holds `fitness.db` and the `photos/` folder.
