"""Discover actual ranking-region links from RF4's rendered navigation."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup

BASE = "https://rf4game.ru"
REGION_NAMES = {
    "GL": "Международный", "RU": "Россия и СНГ", "DE": "Германия",
    "US": "США", "FR": "Франция", "CN": "Китай", "PL": "Польша",
    "KR": "Корея", "JP": "Япония", "EN": "Остальные страны",
}
TYPES = {"weekly": BASE + "/records/weekly", "absolute": BASE + "/records"}
REGION_PATH = re.compile(r"^/records(?P<weekly>/weekly)?/region/(?P<region>[A-Za-z]{2})/?$")


@dataclass(frozen=True)
class Source:
    record_type: str
    region: str
    url: str

    def as_dict(self) -> dict:
        return {"record_type": self.record_type, "region": self.region,
                "region_name": REGION_NAMES.get(self.region, self.region), "url": self.url}


def classify_url(url: str) -> tuple[str | None, str | None]:
    path = urlparse(url).path.rstrip("/")
    m = REGION_PATH.fullmatch(path + "/")
    if m:
        return ("weekly" if m.group("weekly") else "absolute", m.group("region").upper())
    if path == "/records/weekly":
        return "weekly", None
    if path == "/records":
        return "absolute", None
    return None, None


def discover_sources(html: str, record_type: str) -> list[Source]:
    """Read actual hyperlinks, rejecting foreign hosts and unexpected URL paths."""
    if record_type not in TYPES:
        raise ValueError(f"Unknown ranking type: {record_type}")
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, Source] = {}
    for link in soup.select("a[href]"):
        url = link.get("href", "")
        if url.startswith("/") and not url.startswith("//"):
            url = BASE + url
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {"rf4game.ru", "www.rf4game.ru"}:
            continue
        kind, region = classify_url(url)
        if kind != record_type or not region or region not in REGION_NAMES:
            continue
        clean = urlunparse(("https", "rf4game.ru", parsed.path.rstrip("/") + "/", "", "", ""))
        found[region] = Source(kind, region, clean)
    return [found[region] for region in REGION_NAMES if region in found]
