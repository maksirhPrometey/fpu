"""Fetch team member photos from fpsu.org.ua leadership pages."""
from __future__ import annotations

import io
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.core.models import TeamMember

BASE_URL = "https://fpsu.org.ua"
LISTING_URL = f"{BASE_URL}/pro-fpu/kerivnitstvo-fpu"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

TIMEOUT = 15


def _get(url: str) -> requests.Response:
    return requests.get(url, headers=HEADERS, timeout=TIMEOUT)


def _scrape_leadership_links() -> list[tuple[str, str]]:
    """Return list of (full_name, detail_url) from the listing page."""
    r = _get(LISTING_URL)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    seen = set()
    for a in soup.select("a[href*='kerivnitstvo-fpu']"):
        href = a["href"]
        if "/kerivnitstvo-fpu/" not in href or href in seen:
            continue
        seen.add(href)
        name = a.get_text(strip=True)
        # Strip role prefix, e.g. "Голова ФПУ Бизов …" → "Бизов …"
        for prefix in (
            "Голова ФПУ ",
            "Перший заступник Голови ФПУ ",
            "Заступник Голови ФПУ ",
            "В.о. заступника Голови ФПУ ",
            "В.о. Голови ФПУ ",
        ):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        results.append((name, urljoin(BASE_URL, href)))
    return results


def _scrape_photo_url(detail_url: str) -> str | None:
    """Return absolute URL of the first content image on a person detail page."""
    r = _get(detail_url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    selectors = [
        "article img",
        ".item-page img",
        ".blog img",
        ".com-content-article img",
        "main img",
    ]
    for sel in selectors:
        imgs = soup.select(sel)
        if imgs:
            src = imgs[0].get("src", "")
            if src:
                return urljoin(BASE_URL, src)
    return None


def _last_name(full: str) -> str:
    """Return first word (прізвище) in lower case for fuzzy matching."""
    return full.split()[0].lower()


class Command(BaseCommand):
    help = "Scrape fpsu.org.ua and download team member photos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing photos.",
        )

    def handle(self, *args, **options) -> None:
        force: bool = options["force"]
        members = list(TeamMember.objects.all())

        if not members:
            self.stdout.write(self.style.WARNING("No TeamMember records found."))
            return

        self.stdout.write("Fetching leadership list from fpsu.org.ua …")
        try:
            remote = _scrape_leadership_links()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Failed to fetch listing: {exc}"))
            return

        self.stdout.write(f"  found {len(remote)} remote entries")
        for name, url in remote:
            self.stdout.write(f"  • {name} → {url}")

        for member in members:
            if member.photo and not force:
                self.stdout.write(f"  skip {member.full_name} (photo exists, use --force to replace)")
                continue

            # match by last name (прізвище)
            local_last = _last_name(member.full_name)
            match_url = None
            for remote_name, remote_url in remote:
                if _last_name(remote_name) == local_last:
                    match_url = remote_url
                    break

            if not match_url:
                self.stdout.write(
                    self.style.WARNING(f"  ✗ no match on site for '{member.full_name}'")
                )
                continue

            self.stdout.write(f"  ↓ {member.full_name} …", ending=" ")
            try:
                photo_url = _scrape_photo_url(match_url)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"error fetching page: {exc}"))
                continue

            if not photo_url:
                self.stdout.write(self.style.WARNING("no image found on page"))
                continue

            try:
                img_resp = _get(photo_url)
                img_resp.raise_for_status()
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"error downloading image: {exc}"))
                continue

            ext = photo_url.rsplit(".", 1)[-1].split("?")[0].lower() or "jpg"
            # Use transliterated ASCII filename to avoid URL-encoding issues.
            ascii_last = (
                local_last
                .replace("'", "")
                .encode("ascii", errors="replace")
                .decode()
                .replace("?", "x")
            )
            filename = f"{ascii_last or local_last}.{ext}"
            member.photo.save(filename, ContentFile(img_resp.content), save=True)
            self.stdout.write(self.style.SUCCESS(f"saved ({len(img_resp.content) // 1024} KB)"))

        self.stdout.write(self.style.SUCCESS("Done."))
