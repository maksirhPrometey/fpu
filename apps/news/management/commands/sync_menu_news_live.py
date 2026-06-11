"""
Sync menu news feeds with live fpsu.org.ua listings (order, dates, excerpts).

Usage:
    python manage.py sync_menu_news_live
    python manage.py sync_menu_news_live --dry-run
    python manage.py sync_menu_news_live --path napryamki-diyalnosti/pravovij-zakhist
"""
from __future__ import annotations

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.news.live_sync import fetch_menu_listing
from apps.news.models import Article, Category
from apps.pages.menu_news import MENU_TO_NEWS_CATEGORY

_KYIV = ZoneInfo("Europe/Kyiv")


def _primary_menu_paths() -> dict[str, str]:
    """One live listing URL per news category (prefer napryamki-diyalnosti)."""
    by_category: dict[str, list[str]] = {}
    for menu_path, news_path in MENU_TO_NEWS_CATEGORY.items():
        by_category.setdefault(news_path, []).append(menu_path)
    primary: dict[str, str] = {}
    for news_path, menus in by_category.items():
        preferred = next(
            (menu for menu in menus if menu.startswith("napryamki-diyalnosti/")),
            menus[0],
        )
        primary[news_path] = preferred
    return primary


class Command(BaseCommand):
    help = "Sync napryamki menu news listings with live fpsu.org.ua"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--path",
            help="Sync only this menu path (e.g. napryamki-diyalnosti/pravovij-zakhist)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        only_path: str | None = options.get("path")

        if only_path:
            only_path = only_path.strip("/")
            if only_path not in MENU_TO_NEWS_CATEGORY:
                self.stderr.write(self.style.ERROR(f"Unknown menu path: {only_path}"))
                return
            sync_pairs = [(only_path, MENU_TO_NEWS_CATEGORY[only_path])]
        else:
            primary = _primary_menu_paths()
            sync_pairs = [(menu, cat) for cat, menu in primary.items()]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))

        total_updated = total_hidden = 0

        for menu_path, news_path in sync_pairs:
            self.stdout.write(f"Fetching {menu_path} …")
            try:
                live_items = fetch_menu_listing(menu_path)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  Failed: {exc}"))
                continue

            if not live_items:
                self.stdout.write(self.style.WARNING(f"  No items parsed for {menu_path}"))
                continue

            try:
                category = Category.objects.get(path=news_path, is_active=True)
            except Category.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Category missing: {news_path}"))
                continue

            live_ids = {item.joomla_id for item in live_items}
            articles = {
                art.joomla_id: art
                for art in Article.objects.filter(category=category, joomla_id__isnull=False)
            }

            updated = 0
            with transaction.atomic():
                for rank, item in enumerate(live_items):
                    art = articles.get(item.joomla_id)
                    if art is None:
                        continue
                    published = item.published_at
                    if published is not None:
                        published = timezone.make_aware(
                            datetime.combine(published.date(), time(12, 0)),
                            _KYIV,
                        )
                        published = published.replace(
                            hour=12,
                            minute=min(rank, 59),
                            second=min(rank * 3, 59),
                        )
                    updates: dict[str, Any] = {
                        "summary": item.excerpt[:500],
                        "is_published": True,
                        "order": -rank,
                    }
                    if published is not None:
                        updates["published_at"] = published
                    if not dry_run:
                        for field, value in updates.items():
                            setattr(art, field, value)
                        art.save(update_fields=list(updates.keys()))
                    updated += 1

                hidden_qs = Article.objects.filter(category=category).exclude(
                    joomla_id__in=live_ids,
                )
                hidden_count = hidden_qs.count()
                if not dry_run and hidden_count:
                    hidden_qs.update(is_published=False)
                total_hidden += hidden_count
                total_updated += updated

                if dry_run:
                    transaction.set_rollback(True)

            self.stdout.write(
                self.style.SUCCESS(
                    f"  {menu_path}: {len(live_items)} live items, "
                    f"{updated} updated, {hidden_count} hidden locally"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {total_updated} articles updated, {total_hidden} unpublished."
            )
        )
