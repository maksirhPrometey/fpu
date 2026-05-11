"""
Management command: seed all production data once on first deploy.

Checks whether the database is already seeded by looking for Priority records.
If data is present — skips everything silently (safe to call on every deploy).
If empty — runs the full seeding pipeline in dependency order.

What gets seeded automatically (all hardcoded, no external files required):
  1. seed_priorities          — 4 cards in «Наші Пріоритети»
  2. seed_team                — leadership team members
  3. seed_member_organizations — union member orgs
  4. seed_document_categories — document category list
  5. seed_section_pages       — static nav-section page bodies (HTML)

What gets seeded if data files are present in tools/:
  6. import_gallery           — albums + photos (tools/gallery_cats.json + tools/gallery.json)

Joomla article/page data (tools/cats.tsv, articles.tsv, content_bodies.json, menu.tsv)
is NOT imported here — those files are large and excluded from the repo.
Run `python manage.py import_all` manually after uploading data files to the server.

Usage:
    python manage.py seed_production           # called from build.sh
    python manage.py seed_production --force   # re-seed even if data exists
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand

BASE = Path(__file__).resolve().parents[4]


class Command(BaseCommand):
    help = "Seed all production data once (skips if already seeded)"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-run seeding even if data already exists in the DB.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.core.models import Priority

        if not options["force"] and Priority.objects.exists():
            self.stdout.write("seed_production: data already present — skipping.")
            return

        if options["force"]:
            self.stdout.write(self.style.WARNING("--force: re-seeding regardless of existing data."))

        t0 = time.monotonic()
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))
        self.stdout.write(self.style.MIGRATE_HEADING("  First-deploy seed"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))

        self._run("seed_priorities")
        self._run("seed_team")
        self._run("seed_member_organizations")
        self._run("seed_document_categories")
        self._run("seed_section_pages")

        # Gallery — only if JSON data files are bundled in the repo
        cats_file = BASE / "tools" / "gallery_cats.json"
        photos_file = BASE / "tools" / "gallery.json"
        if cats_file.exists() and photos_file.exists():
            self._run("import_gallery")
        else:
            self.stdout.write(
                self.style.WARNING(
                    "  Gallery files not found (tools/gallery_cats.json, tools/gallery.json) — skipping.\n"
                    "  Upload them to the server and run: python manage.py import_gallery"
                )
            )

        elapsed = time.monotonic() - t0
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))
        self.stdout.write(self.style.SUCCESS(f"  seed_production complete in {elapsed:.1f}s"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))

    def _run(self, name: str, **kwargs: Any) -> None:
        self.stdout.write(self.style.SQL_KEYWORD(f"  → {name}"))
        call_command(name, **kwargs)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {name}"))
