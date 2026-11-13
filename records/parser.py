"""Parse the rendered RF4 records DOM (nested div-based tables)."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

WEIGHT_RE = re.compile(r"^([\d\s\u00a0.,]+)\s*(кг|г)$", re.IGNORECASE)
IMAGE_RE = re.compile(r"background-image\s*:\s*url\(\s*['\"]?([^)'\"]+)", re.IGNORECASE)


def _direct_col(row: Tag, name: str) -> Tag | None:
    return row.find("div", class_=lambda classes: classes and name in classes.split(), recursive=False)


def _text(row: Tag, name: str) -> str | None:
    col = _direct_col(row, name)
    return col.get_text(" ", strip=True) if col else None


def _image_url(node: Tag | None, source_url: str) -> str | None:
    if not node:
        return None
    matched = IMAGE_RE.search(node.get("style", ""))
    return urljoin(source_url, matched.group(1)) if matched else None


def _weight(raw: str | None) -> tuple[int, str] | None:
    if not raw:
        return None
    match = WEIGHT_RE.fullmatch(raw.strip())
    if not match:
        return None
    value = match.group(1).replace("\u00a0", "").replace(" ", "").replace(",", ".")
    unit = match.group(2).lower()
    # RF4 displays kilograms to three decimal places; store integer grams.
    if unit == "кг":
        from decimal import Decimal
        grams = int(Decimal(value) * 1000)
    else:
        grams = int(value)
    return grams, unit


def parse_records(html: str, source_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one(".records.flex_table")
    if root is None:
        raise ValueError("Records table not found: .records.flex_table")
    groups = root.select(":scope > .rows > .row > .records_subtable")
    if not groups:
        raise ValueError("No fish groups found under records table")

    records = []
    empty_fish = []
    problems = []
    for group in groups:
        header = group.select_one(":scope > .row.header")
        if header is None:
            problems.append({"fish": None, "reason": "missing fish header"})
            continue
        fish_col = _direct_col(header, "fish")
        fish = fish_col.get_text(" ", strip=True) if fish_col else ""
        if not fish:
            problems.append({"fish": None, "reason": "empty fish name"})
            continue
        fish_icon = _image_url(fish_col.select_one(".item_icon") if fish_col else None, source_url)
        extra = group.select_one(":scope > .rows")
        rows = [header]
        if extra:
            rows.extend(extra.find_all("div", class_="row", recursive=False))
        fish_count = 0
        for position, row in enumerate(rows, start=1):
            raw_weight = _text(row, "weight")
            if not raw_weight:
                continue  # Some fish exist in the catalog but have zero records.
            parsed = _weight(raw_weight)
            if parsed is None:
                problems.append({"fish": fish, "rank": position, "reason": f"invalid weight: {raw_weight}"})
                continue
            grams, unit = parsed
            date_raw = _text(row, "data")
            try:
                caught_date = datetime.strptime(date_raw, "%d.%m.%y").date().isoformat() if date_raw else None
            except ValueError:
                caught_date = None
                problems.append({"fish": fish, "rank": position, "reason": f"invalid date: {date_raw}"})
            bait_col = _direct_col(row, "bait")
            bait_icon = bait_col.select_one(".bait_icon") if bait_col else None
            records.append({
                "fish": fish,
                "fish_icon_url": fish_icon,
                "rank": position,
                "weight_g": grams,
                "weight_original": raw_weight,
                "waterbody": _text(row, "location"),
                "bait": bait_icon.get("title") if bait_icon else None,
                "bait_icon_url": _image_url(bait_icon, source_url),
                "player": _text(row, "gamername"),
                "caught_date": caught_date,
            })
            fish_count += 1
        if fish_count == 0:
            empty_fish.append(fish)

    return {
        "source_url": source_url,
        "fish_group_count": len(groups),
        "record_count": len(records),
        "fish_without_records": empty_fish,
        "warnings": problems,
        "records": records,
    }


def parse_file(html_path: Path, source_url: str) -> dict:
    return parse_records(html_path.read_text(encoding="utf-8"), source_url)
