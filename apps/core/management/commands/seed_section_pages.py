"""
Management command: seed body content for the main navigation section pages.

These pages are Joomla category index pages — they aggregate sub-sections
rather than linking to a single article, so import_bodies leaves them empty.
This command populates them with a description + sub-section link list.

For activity direction pages (/napryamki-diyalnosti/*), the body also includes
a direct link to the corresponding news category, since those pages in Joomla
showed a live news list, not static content.

Idempotent: uses update_or_create keyed on url_path.

Usage:
    python manage.py seed_section_pages
    python manage.py seed_section_pages --dry-run
"""
from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.pages.models import StaticPage
from apps.pages.section_hubs import SECTION_PAGE_DEFS, build_section_body


class Command(BaseCommand):
    help = "Seed body content for main navigation section pages (idempotent)"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        created_count = updated_count = 0

        for section in SECTION_PAGE_DEFS:
            url_path = section["url_path"]
            news_cat = section.get("news_category_path")
            body = build_section_body(section["description"], section["children"], news_cat)
            defaults = {
                "title": section["title"],
                "body": body,
                "is_published": True,
                "joomla_type": "menu",
            }

            for variant in (url_path, url_path + ".html"):
                if dry_run:
                    exists = StaticPage.objects.filter(url_path=variant).exists()
                    action = "UPDATE" if exists else "CREATE"
                    self.stdout.write(f"  {action} {variant} — {section['title']}")
                    if exists:
                        updated_count += 1
                    else:
                        created_count += 1
                    continue

                _, was_created = StaticPage.objects.update_or_create(
                    url_path=variant,
                    defaults=defaults,
                )
                if was_created:
                    created_count += 1
                    self.stdout.write(f"  CREATED  {variant}")
                else:
                    updated_count += 1
                    self.stdout.write(f"  UPDATED  {variant}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Section pages: {created_count} created, {updated_count} updated."
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
