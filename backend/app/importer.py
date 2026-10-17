"""CSV import for the food and exercise libraries. Pure parsing and matching; the routes do the saving."""

import csv
import io

MAX_BYTES = 1_000_000  # 1 MB
KCAL_MAX = 900  # per 100 g: above this the row is invalid
KCAL_WARN = 600  # per 100 g: above this the row imports with a warning, so a per-serving value gets caught


class ImportFileError(Exception):
    """The file itself is unusable (too big, not UTF-8, or missing columns). Nothing is imported."""

    def __init__(self, detail: str, status: int = 422):
        super().__init__(detail)
        self.detail = detail
        self.status = status


def read_rows(content: bytes, required: tuple[str, ...]) -> list[tuple[int, dict]]:
    """Return (line number, {column: value}) for each data row. Column names are lower-cased and trimmed."""
    if len(content) > MAX_BYTES:
        raise ImportFileError("The file is larger than 1 MB", status=413)
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportFileError("The file must be saved as UTF-8 CSV")

    first_line = text.split("\n", 1)[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = [h.strip().lower() for h in next(reader, [])]
    missing = [c for c in required if c not in header]
    if missing:
        raise ImportFileError(f"Missing columns: {', '.join(missing)}")

    rows = []
    for line, cells in enumerate(reader, start=2):  # line 1 is the header
        if not any(c.strip() for c in cells):
            continue  # blank lines are ignored
        rows.append((line, {col: (cells[i].strip() if i < len(cells) else "") for i, col in enumerate(header)}))
    return rows


def to_number(text: str) -> float | None:
    """Blank gives None. Accepts 12.5 and 12,5. Raises ValueError for anything else."""
    cleaned = text.strip().replace(",", ".")
    if cleaned == "":
        return None
    return float(cleaned)
