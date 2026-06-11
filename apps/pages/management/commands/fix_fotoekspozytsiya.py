"""Persist fotoekspozytsiya page link rewrites to the database."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.core.media_utils import rewrite_joomla_body_html
from apps.pages.models import StaticPage


class Command(BaseCommand):
    help = "Rewrite fotoekspozytsiya StaticPage body links and images for local URLs."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]
        page = StaticPage.objects.filter(url_path="/fotoekspozytsiya").first()
        if not page:
            self.stderr.write("StaticPage /fotoekspozytsiya not found.")
            return

        original = page.body or ""
        updated = rewrite_joomla_body_html(original)
        external_before = original.count("fpsu.org.ua")
        external_after = updated.count("fpsu.org.ua")

        if dry_run:
            self.stdout.write(f"External links before: {external_before}, after: {external_after}")
            return

        if updated != original:
            page.body = updated
            page.save(update_fields=["body"])
            from apps.pages.fotoekspozytsiya import fotoeksp_article_joomla_ids

            fotoeksp_article_joomla_ids.cache_clear()
            self.stdout.write(self.style.SUCCESS(
                f"Updated fotoekspozytsiya body ({external_before} → {external_after} external links)"
            ))
        else:
            self.stdout.write("No changes needed.")
