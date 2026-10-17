# CSV Import Plan (foods and exercises)

Context: existing FastAPI + SQLite backend, React (Vite, plain JS) frontend, mobile-first. Add CSV import to the food library and the exercise library.

## Endpoints

Shared import helper, one endpoint per library:

- `POST /foods/import`
- `POST /exercises/import`

Flow for both: upload CSV -> preview -> confirm -> commit. Nothing is saved until the user confirms.

## Foods template

Columns: `name, kcal_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g`

- `name` and `kcal_per_100g` required, macros optional.
- Validate kcal between 0 and 900 per 100g, flag outliers in the preview.
- Instructions shown on screen: "All values are per 100g, not per serving."

## Exercises template

Columns: `exercise, muscle_group`

- Both required, one exercise per row.
- If the muscle group does not exist, create it automatically.
- Instructions shown on screen: "One row per exercise. Use the same muscle group name for exercises that belong together, for example Chest or Back."

## Shared rules

- Trim whitespace and match names case-insensitively.
- Duplicates (same name, or same exercise + muscle group) are skipped, never overwritten.
- Reject files with missing required columns and say which ones.
- Preview returns: rows to add, duplicates skipped, invalid rows with reasons, and for exercises the list of new muscle groups that will be created.
- Each import screen has a "Download template" button and the instructions above.

## Frontend

- Import button on the food library screen and on the exercise library screen.
- Steps: choose file, see preview, confirm or cancel.
- Preview shows counts (to add, skipped, invalid) and the details of invalid rows.
- For exercises, the preview highlights new muscle groups that will be created so typos are caught before confirming.

## Tests (pytest)

- Valid import
- Duplicates skipped
- Case-insensitive matching
- Missing columns
- Invalid kcal
- New muscle group created
- Existing muscle group reused

## Decisions made

- **Confirm re-sends the file.** The server stores nothing between preview and confirm. `confirm=false` previews, `confirm=true` imports.
- **Paths use the existing prefixes:** `POST /food/foods/import` (the foods are under `/food`) and `POST /exercises/import`.
- **Invalid rows are skipped; the rest of the file imports.** Invalid means a missing or non-numeric value, kcal outside 0 to 900, macros outside 0 to 100, or a name or muscle group that is empty or too long.
- **Warnings import anyway.** Kcal above 600 per 100 g, or protein + carbs + fat above 100 g, is listed under "Check these" so a per-serving value gets caught.
- **Separator and decimals:** the header line decides between `,` and `;`. Both `.` and `,` work as decimal points.
- **Size limit:** 1 MB. Larger files get a 413.
- **Matching:** names are trimmed and compared case-insensitively. A repeat inside the same file is skipped, as is anything already in the library.
- **Muscle groups** are lower-cased, like the seeded groups. Unknown ones are created only when the import is confirmed.
- **Templates** are static files in `frontend/public/templates/`.

