"""Scrape fpsu.org.ua menu news listings for sync with local category feeds."""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from html import unescape

from apps.news.body_excerpt import sanitize_listing_text

_BASE = "https://www.fpsu.org.ua"
_ITEM_SPLIT_RE = re.compile(r'class="item\s')
_LINK_RE = re.compile(
    r'href="(/[^"]+/(\d+)-[\w-]+\.html)"',
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"Опубліковано:\s*([^<]+)", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

_UA_MONTHS = {
    "січня": 1,
    "лютого": 2,
    "березня": 3,
    "квітня": 4,
    "травня": 5,
    "червня": 6,
    "липня": 7,
    "серпня": 8,
    "вересня": 9,
    "жовтня": 10,
    "листопада": 11,
    "грудня": 12,
}


@dataclass(frozen=True)
class LiveListingItem:
    joomla_id: int
    published_at: datetime | None
    excerpt: str


def _parse_ua_date(raw: str) -> datetime | None:
    parts = raw.strip().split()
    if len(parts) != 3:
        return None
    try:
        day = int(parts[0])
        month = _UA_MONTHS.get(parts[1].lower())
        year = int(parts[2])
    except (ValueError, TypeError):
        return None
    if not month:
        return None
    return datetime(year, month, day)


def _plain(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    return unescape(_WS_RE.sub(" ", text)).strip()


def _parse_listing_html(html: str, menu_path: str) -> list[LiveListingItem]:
    items: list[LiveListingItem] = []
    path_marker = f"/{menu_path.strip('/')}/"
    for chunk in _ITEM_SPLIT_RE.split(html)[1:]:
        link = _LINK_RE.search(chunk)
        if not link or path_marker not in link.group(1):
            continue
        jid = int(link.group(2))
        date_match = _DATE_RE.search(chunk)
        published = _parse_ua_date(date_match.group(1)) if date_match else None
        plain = _plain(chunk)
        if date_match:
            marker = f"Опубліковано: {date_match.group(1).strip()}"
            idx = plain.find(marker)
            excerpt = plain[idx + len(marker) :].strip() if idx >= 0 else plain
        else:
            excerpt = plain
        items.append(
            LiveListingItem(
                joomla_id=jid,
                published_at=published,
                excerpt=sanitize_listing_text(excerpt, max_len=500),
            )
        )
    return items


def _fetch(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "FPSU-mirror-sync/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_menu_listing(menu_path: str, *, max_pages: int = 80) -> list[LiveListingItem]:
    """All listing items for a menu URL, in live site order."""
    menu_path = menu_path.strip("/")
    seen: set[int] = set()
    ordered: list[LiveListingItem] = []
    start = 0

    for _ in range(max_pages):
        suffix = f"?start={start}" if start else ""
        url = f"{_BASE}/{menu_path}.html{suffix}"
        try:
            html = _fetch(url)
        except (urllib.error.URLError, TimeoutError):
            break

        page_items = _parse_listing_html(html, menu_path)
        if not page_items:
            break

        new_count = 0
        for item in page_items:
            if item.joomla_id in seen:
                continue
            seen.add(item.joomla_id)
            ordered.append(item)
            new_count += 1

        if new_count == 0:
            break
        start += len(page_items)

    return ordered
