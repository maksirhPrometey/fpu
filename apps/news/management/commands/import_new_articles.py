"""
Import new articles from fpsu.org.ua that are absent from the local DB.

For each configured feed, fetches live listing pages, identifies articles
with joomla_ids not yet in the Article table, then fetches and stores them.

Usage:
    python manage.py import_new_articles
    python manage.py import_new_articles --feed materiali
    python manage.py import_new_articles --max-pages 5
    python manage.py import_new_articles --dry-run
"""
from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.utils.timezone import make_aware

from apps.news.models import Article, Category

_BASE = "https://www.fpsu.org.ua"
_KYIV = ZoneInfo("Europe/Kyiv")

_UA_MONTHS = {
    "січня": 1, "лютого": 2, "березня": 3, "квітня": 4,
    "травня": 5, "червня": 6, "липня": 7, "серпня": 8,
    "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12,
}

_ITEM_RE = re.compile(r'class="item\s', re.IGNORECASE)
_LINK_RE = re.compile(r'href="(/[^"]+/(\d+)-([\w-]+)\.html)"', re.IGNORECASE)
_DATE_RE = re.compile(r"Опубліковано:\s*(\d+\s+\w+\s+\d{4})", re.IGNORECASE)
_IMG_SRC_RE = re.compile(r'(src|href)="(/images/[^"]+)"', re.IGNORECASE)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "uk,en;q=0.9",
}

# menu_path  — URL slug на fpsu.org.ua (буде: /{menu_path}.html?start=N)
# cat_path   — path категорії в нашій БД
# path_filter — підрядок, що має бути в href статті (якщо не задано — /{menu_path}/)
FEEDS: list[dict] = [
    # Головна стрічка новин (на сайті /materialy/, у БД — materiali)
    {
        "menu_path": "materialy",
        "cat_path": "materiali",
        "path_filter": "/materialy/",
    },
    # Головна новина (на сайті /256-holovna-novyna/)
    {
        "menu_path": "256-holovna-novyna",
        "cat_path": "holovna-novyna",
        "path_filter": "/256-holovna-novyna/",
    },
    # Новини членських організацій (на сайті /65-nasha-borotba/novini-chlenskikh-organizatsij/)
    {
        "menu_path": "65-nasha-borotba/novini-chlenskikh-organizatsij",
        "cat_path": "nasha-borotba/novini-chlenskikh-organizatsij",
        "path_filter": "/65-nasha-borotba/novini-chlenskikh-organizatsij/",
    },
    # Щоденні новини оборони
    {
        "menu_path": "cherhovyi-den-heroichnoho-sprotyvu",
        "cat_path": "cherhovyi-den-heroichnoho-sprotyvu",
    },
]


@dataclass
class _Item:
    joomla_id: int
    href: str
    slug: str
    published_at: datetime | None


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


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def _parse_listing(html: str, path_filter: str) -> list[_Item]:
    items: list[_Item] = []
    for chunk in _ITEM_RE.split(html)[1:]:
        m = _LINK_RE.search(chunk)
        if not m or path_filter not in m.group(1):
            continue
        jid = int(m.group(2))
        href = m.group(1)
        slug = m.group(3)
        date_m = _DATE_RE.search(chunk)
        published = _parse_ua_date(date_m.group(1)) if date_m else None
        items.append(_Item(joomla_id=jid, href=href, slug=slug, published_at=published))
    return items


def _fetch_listing(menu_path: str, path_filter: str, max_pages: int) -> list[_Item]:
    seen: set[int] = set()
    result: list[_Item] = []
    start = 0
    for _ in range(max_pages):
        suffix = f"?start={start}" if start else ""
        url = f"{_BASE}/{menu_path}.html{suffix}"
        html = _get(url)
        if not html:
            break
        page = _parse_listing(html, path_filter)
        if not page:
            break
        new = 0
        for item in page:
            if item.joomla_id not in seen:
                seen.add(item.joomla_id)
                result.append(item)
                new += 1
        if new == 0:
            break
        start += len(page)
    return result


def _extract_article(html: str) -> tuple[str, str]:
    """Return (title, body_html) from a Joomla article page."""
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    for sel in [".page-header", "h1[itemprop='name']", "h1.contentheading", "h1"]:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(strip=True)
            break

    body_el = (
        soup.select_one("div.item-page")
        or soup.select_one("[itemprop='articleBody']")
        or soup.select_one("div.com-content-article__body")
    )
    if not body_el:
        return title, ""

    for tag in body_el.select("h1, .pager, .tags, .article-info-term, .btn-toolbar, nav"):
        tag.decompose()

    body_html = str(body_el)
    body_html = _IMG_SRC_RE.sub(r'\1="/media/joomla_images\2"', body_html)
    return title, body_html


def _unique_slug(base: str, used: set[str]) -> str:
    s = base[:400] or "article"
    if s not in used:
        used.add(s)
        return s
    i = 2
    while True:
        candidate = f"{base[:390]}-{i}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        i += 1


class Command(BaseCommand):
    help = "Fetch and import new articles from fpsu.org.ua missing from the local DB."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--feed", help="Only sync this menu_path (e.g. materiali)")
        parser.add_argument("--max-pages", type=int, default=10, dest="max_pages")
        parser.add_argument("--delay", type=float, default=0.5)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        only_feed: str | None = options.get("feed")
        max_pages: int = options["max_pages"]
        delay: float = options["delay"]
        dry_run: bool = options["dry_run"]

        feeds = FEEDS
        if only_feed:
            feeds = [f for f in FEEDS if f["menu_path"] == only_feed]
            if not feeds:
                names = [f["menu_path"] for f in FEEDS]
                self.stderr.write(self.style.ERROR(f"Unknown feed: {only_feed}. Available: {names}"))
                return

        existing_jids: set[int] = set(
            Article.objects.filter(joomla_id__isnull=False).values_list("joomla_id", flat=True)
        )
        used_slugs: set[str] = set(Article.objects.values_list("slug", flat=True))
        self.stdout.write(f"DB: {len(existing_jids)} articles with joomla_id\n")

        total_created = 0

        for feed in feeds:
            menu_path: str = feed["menu_path"]
            cat_path: str = feed["cat_path"]
            path_filter: str = feed.get("path_filter") or f"/{menu_path}/"

            self.stdout.write(self.style.MIGRATE_HEADING(f"Feed: {menu_path}"))

            try:
                cat = Category.objects.get(path=cat_path, is_active=True)
            except Category.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Category not found: {cat_path}, skip\n"))
                continue

            items = _fetch_listing(menu_path, path_filter, max_pages)
            self.stdout.write(f"  Live site: {len(items)} items (max {max_pages} pages fetched)")

            new_items = [it for it in items if it.joomla_id not in existing_jids]
            self.stdout.write(f"  New (not in DB): {len(new_items)}")

            if not new_items:
                self.stdout.write("  Nothing to import.\n")
                continue

            if dry_run:
                for it in new_items[:5]:
                    self.stdout.write(f"  DRY: jid={it.joomla_id} slug={it.slug[:50]}")
                if len(new_items) > 5:
                    self.stdout.write(f"  ... and {len(new_items) - 5} more")
                self.stdout.write("")
                continue

            created = 0
            for it in new_items:
                url = f"{_BASE}{it.href}"
                html = _get(url)
                if not html:
                    self.stdout.write(self.style.WARNING(f"  ✗ fetch failed: {url}"))
                    time.sleep(delay)
                    continue

                title, body = _extract_article(html)
                if not title:
                    title = it.slug.replace("-", " ").title()

                pub_dt = None
                if it.published_at:
                    pub_dt = make_aware(
                        it.published_at.replace(hour=12, minute=0, second=0),
                        _KYIV,
                    )

                slug = _unique_slug(it.slug, used_slugs)

                art = Article(
                    joomla_id=it.joomla_id,
                    title=title[:255],
                    slug=slug,
                    body=body,
                    summary="",
                    is_published=True,
                    category=cat,
                )
                if pub_dt:
                    art.published_at = pub_dt
                art.save()

                existing_jids.add(it.joomla_id)
                created += 1
                total_created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ jid={it.joomla_id} {title[:65]}")
                )
                time.sleep(delay)

            self.stdout.write(f"  Created: {created}\n")

        self.stdout.write(self.style.SUCCESS(f"Done. Total new articles: {total_created}"))
