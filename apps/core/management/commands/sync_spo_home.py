"""Sync SPO homepage content from spo.fpsu.org.ua."""
from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import SpoHomeCache
from apps.core.spo_live_sync import fetch_spo_homepage


class Command(BaseCommand):
    help = "Sync SPO homepage blocks from spo.fpsu.org.ua"

    def handle(self, *args: Any, **options: Any) -> None:
        data = fetch_spo_homepage()
        cache = SpoHomeCache.load()
        cache.news = data["news"]
        cache.videos = data["videos"]
        cache.gallery = data["gallery"]
        cache.partners = data["partners"]
        cache.synced_at = timezone.now()
        cache.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"Synced SPO homepage: {len(cache.news)} news, "
                f"{len(cache.videos)} videos, {len(cache.gallery)} gallery, "
                f"{len(cache.partners)} partners."
            )
        )
