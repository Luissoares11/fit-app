"""PR logic over logged sets. Pure functions, no database access.

A set is a dict with: id (increases in logging order), date ("YYYY-MM-DD"), weight_kg, reps.
"""


def epley(weight_kg: float, reps: int) -> float:
    return weight_kg * (1 + reps / 30)


def _loaded(sets: list[dict]) -> list[dict]:
    return [s for s in sets if s["weight_kg"] > 0]


def heaviest(sets: list[dict]) -> dict | None:
    # Ties: more reps wins, then the most recent date
    loaded = _loaded(sets)
    if not loaded:
        return None
    return max(loaded, key=lambda s: (s["weight_kg"], s["reps"], s["date"], s["id"]))


def best_e1rm(sets: list[dict]) -> dict | None:
    # Up to 12 reps only; returns the unrounded value so comparisons stay exact
    candidates = [s for s in _loaded(sets) if s["reps"] <= 12]
    if not candidates:
        return None
    best = max(candidates, key=lambda s: (epley(s["weight_kg"], s["reps"]), s["date"], s["id"]))
    return {"raw": epley(best["weight_kg"], best["reps"]), "set": best}


def best_by_reps(sets: list[dict]) -> dict[int, dict]:
    # For each rep count: the heaviest set, and among equal weights the most recent one
    best: dict[int, dict] = {}
    for s in _loaded(sets):
        cur = best.get(s["reps"])
        if cur is None or (s["weight_kg"], s["date"], s["id"]) > (cur["weight_kg"], cur["date"], cur["id"]):
            best[s["reps"]] = s
    return best


def most_reps(sets: list[dict]) -> int | None:
    reps = [s["reps"] for s in sets if s["weight_kg"] == 0]
    return max(reps) if reps else None


def new_prs(previous: list[dict], s: dict) -> list[dict]:
    """PRs earned by set `s`, compared with every set logged before it. Ties are not PRs,
    and a type needs an earlier value to beat."""
    prs = []
    if s["weight_kg"] > 0:
        prev_heavy = heaviest(previous)
        if prev_heavy and (s["weight_kg"], s["reps"]) > (prev_heavy["weight_kg"], prev_heavy["reps"]):
            prs.append({"type": "heaviest", "weight_kg": s["weight_kg"], "reps": s["reps"]})

        prev_at_reps = best_by_reps(previous).get(s["reps"])
        if prev_at_reps and s["weight_kg"] > prev_at_reps["weight_kg"]:
            prs.append({"type": "rep_best", "reps": s["reps"], "weight_kg": s["weight_kg"]})

        if s["reps"] <= 12:
            value = epley(s["weight_kg"], s["reps"])
            prev_e1rm = best_e1rm(previous)
            if prev_e1rm and value > prev_e1rm["raw"]:
                prs.append({"type": "e1rm", "value": round(value, 1)})
    else:
        prev_reps = most_reps(previous)
        if prev_reps is not None and s["reps"] > prev_reps:
            prs.append({"type": "most_reps", "reps": s["reps"]})
    return prs


def evaluate(history: list[dict], new_sets: list[dict]) -> list[dict]:
    """history: sets stored before this request. new_sets: in the order they were sent.
    Each new set is compared against history plus the new sets before it."""
    seen = list(history)
    prs: list[dict] = []
    for s in new_sets:
        prs.extend(new_prs(seen, s))
        seen.append(s)
    return prs
