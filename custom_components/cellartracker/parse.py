"""Turn raw CellarTracker rows into compact wine / bottle records."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date
from typing import Any


def pick(row: dict[str, str], *names: str) -> str | None:
    """First non-empty value for any of the given column names (case-insensitive)."""
    lower = {k.lower(): v for k, v in row.items()}
    for name in names:
        val = lower.get(name.lower())
        if val is not None and str(val).strip() not in ("", "Unknown"):
            return str(val).strip()
    return None


def num(val: str | None) -> float | None:
    """Parse a number like '17', '17.5' or '17,5'."""
    if val is None:
        return None
    try:
        return float(str(val).replace(",", "."))
    except ValueError:
        return None


def vintage(val: str | None) -> str | None:
    """1001 is CellarTracker's code for non-vintage."""
    if val in (None, "", "1001"):
        return "NV" if val == "1001" else val
    return val


def parse_date(val: str | None) -> str | None:
    """Return ISO date for 'm/d/yyyy' or 'yyyy-mm-dd' strings."""
    if not val:
        return None
    val = val.split(" ")[0]
    try:
        if "/" in val:
            m, d, y = (int(x) for x in val.split("/"))
            return date(y, m, d).isoformat()
        return date.fromisoformat(val).isoformat()
    except ValueError:
        return val


BIN_RC = re.compile(r"^\s*R(\d+)\s*C(\d+)\s*$", re.I)


def bin_position(bin_: str | None) -> dict[str, int]:
    """'R05C02' -> {'row': 5, 'col': 2}; a plain number is a row (shelf)."""
    if not bin_:
        return {}
    m = BIN_RC.match(bin_)
    if m:
        return {"row": int(m.group(1)), "col": int(m.group(2))}
    if bin_.strip().isdigit():
        return {"row": int(bin_.strip())}
    return {}


def wine_details(row: dict[str, str]) -> dict[str, Any]:
    """Fields describing the wine itself (shared by inventory and consumed)."""
    return {
        "iWine": pick(row, "iWine"),
        "wine": pick(row, "Wine"),
        "producer": pick(row, "Producer"),
        "vintage": vintage(pick(row, "Vintage")),
        "type": pick(row, "Type"),
        "color": pick(row, "Color"),
        "category": pick(row, "Category"),
        "varietal": pick(row, "Varietal", "MasterVarietal"),
        "country": pick(row, "Country"),
        "region": pick(row, "Region"),
        "appellation": pick(row, "Appellation"),
        "size": pick(row, "Size"),
    }


def build_inventory(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Group inventory rows (one per bottle) into wines, plus totals."""
    by_wine: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        iwine = pick(row, "iWine")
        if iwine:
            by_wine[iwine].append(row)

    wines: list[dict[str, Any]] = []
    total_value = 0.0
    currency = None
    for iwine, bottles in by_wine.items():
        first = bottles[0]
        values = [num(pick(b, "Valuation", "Value")) for b in bottles]
        values = [v for v in values if v is not None]
        prices = [num(pick(b, "Price")) for b in bottles]
        prices = [p for p in prices if p is not None]
        places = Counter(
            (pick(b, "Location") or "", pick(b, "Bin") or "") for b in bottles
        )
        currency = currency or pick(first, "Currency")
        value = round(sum(values) / len(values), 2) if values else None
        total_value += sum(values)
        wine = wine_details(first)
        wine.update(
            {
                "qty": len(bottles),
                "value": value,
                "price": round(sum(prices) / len(prices), 2) if prices else None,
                "begin": pick(first, "BeginConsume"),
                "end": pick(first, "EndConsume"),
                "score": num(pick(first, "CT", "CScore")),
                "my_score": num(pick(first, "MY", "PScore")),
                "places": [
                    {"location": loc, "bin": bin_, "qty": qty, **bin_position(bin_)}
                    for (loc, bin_), qty in sorted(places.items())
                ],
            }
        )
        wines.append(wine)

    def sort_key(w: dict[str, Any]):
        end = w.get("end") or ""
        return (int(end) if end.isdigit() else 9999, w.get("producer") or "")

    wines.sort(key=sort_key)
    totals = {
        "bottles": len(rows),
        "wines": len(wines),
        "value": round(total_value, 2),
        "currency": currency,
    }
    return wines, totals


def build_consumed(
    rows: list[dict[str, str]], limit: int, producers: dict[str, str] | None = None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """One record per consumed bottle, newest first, plus yearly counts.

    The Consumed table has no Producer column; it is filled from the inventory
    (by iWine) when that wine is still in the cellar.
    """
    producers = producers or {}
    items: list[dict[str, Any]] = []
    for row in rows:
        item = wine_details(row)
        if not item.get("producer"):
            item["producer"] = producers.get(item.get("iWine") or "")
        item.update(
            {
                "date": parse_date(pick(row, "Consumed", "ConsumptionDate", "Date")),
                "how": pick(row, "ShortType", "Type2", "ConsumptionType"),
                "value": num(pick(row, "Value", "Valuation")),
                "note": pick(row, "ConsumptionNote", "Note", "Notes"),
                "location": pick(row, "Location"),
                "bin": pick(row, "Bin"),
                **bin_position(pick(row, "Bin")),
            }
        )
        # The Consumed table's own "Type" can be the consumption type (Drank, ...);
        # keep the wine colour from Color in that case.
        if item.get("type") in ("Drank", "Gave away", "Spilled", "Sold", "Missing", "Other"):
            item["how"] = item["how"] or item["type"]
            item["type"] = item.get("color")
        items.append(item)
    items.sort(key=lambda i: i.get("date") or "", reverse=True)
    per_year = Counter((i.get("date") or "")[:4] for i in items if i.get("date"))
    this_year = str(date.today().year)
    stats = {
        "total": len(items),
        "this_year": per_year.get(this_year, 0),
        "per_year": dict(sorted(per_year.items(), reverse=True)),
    }
    return items[:limit], stats
