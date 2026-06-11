"""Import fotoekspozytsiya table rows from legacy StaticPage HTML."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.news.models import Article
from apps.pages.fotoekspozytsiya import get_fotoeksp_page, import_fotoeksp_from_html
from apps.pages.models import FotoekspEntry, FotoekspSettings, StaticPage


class Command(BaseCommand):
    help = "Parse /fotoekspozytsiya/ HTML body into structured FotoekspEntry rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Replace existing entries.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        page = StaticPage.objects.filter(url_path="/fotoekspozytsiya").first()
        if not page or not page.body:
            self.stderr.write("StaticPage /fotoekspozytsiya not found or empty.")
            return

        if FotoekspEntry.objects.exists() and not options["force"]:
            self.stdout.write(
                f"Skipped — {FotoekspEntry.objects.count()} entries already exist. Use --force."
            )
            return

        data = import_fotoeksp_from_html(page.body)
        settings = FotoekspSettings.load()
        for field, value in data["settings"].items():
            if value:
                setattr(settings, field, value)
        settings.save()

        if options["force"]:
            FotoekspEntry.objects.all().delete()

        created = 0
        for item in data["entries"]:
            article = None
            if item.get("joomla_id"):
                article = Article.objects.filter(joomla_id=item["joomla_id"]).first()
            FotoekspEntry.objects.create(
                page=page,
                section=item["section"],
                order=item["order"],
                title=item["title"],
                article=article,
                is_published=True,
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Imported {created} entries and updated page settings.")
        )
