"""
Management command: populate GalleryPhoto/GalleryAlbum images from image_map.json.

For each GalleryAlbum that has an event_date, finds images in image_map.json
that were uploaded in the same year+month (from date-structured paths like
images/images/{year}/{Month}/{day}/file.webp) and assigns them as GalleryPhoto
records with Cloudinary URLs.

Albums with no date match are skipped by default (use --fallback to assign
images from the same year).

Usage:
    python manage.py populate_gallery_from_map --dry-run
    python manage.py populate_gallery_from_map --photos-per-album 20
    python manage.py populate_gallery_from_map
    python manage.py populate_gallery_from_map --clear-photos
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.gallery.models import GalleryAlbum, GalleryPhoto

BASE = Path(__file__).resolve().parents[4]
DEFAULT_MAP = BASE / "tools" / "image_map.json"

# Map Python month numbers → folder name variants in image_map
_MONTH_ALIASES: dict[int, list[str]] = {
    1:  ["january", "januar"],
    2:  ["february", "februar"],
    3:  ["march", "marz"],
    4:  ["april"],
    5:  ["may"],
    6:  ["june"],
    7:  ["july", "yuli"],
    8:  ["august"],
    9:  ["september"],
    10: ["october", "oktober"],
    11: ["november"],
    12: ["december"],
}

_DATE_PATH = re.compile(
    r"^images/images/(?P<year>\d{4})/(?P<month>[a-z]+)/\d{6}/",
    re.IGNORECASE,
)


def _build_buckets(image_map: dict[str, str]) -> dict[tuple[int, int], list[str]]:
    """Return {(year, month_num): [cdn_url, ...]} from date-structured map keys."""
    # Build reverse alias: folder_name_lower → month_num
    alias_to_num: dict[str, int] = {}
    for num, aliases in _MONTH_ALIASES.items():
        for a in aliases:
            alias_to_num[a.lower()] = num

    buckets: dict[tuple[int, int], list[str]] = defaultdict(list)
    for key, cdn_url in image_map.items():
        m = _DATE_PATH.match(key)
        if not m:
            continue
        year = int(m.group("year"))
        month_str = m.group("month").lower()
        month_num = alias_to_num.get(month_str)
        if month_num is None:
            continue
        buckets[(year, month_num)].append(cdn_url)
    return dict(buckets)


def _year_bucket(
    buckets: dict[tuple[int, int], list[str]], year: int
) -> list[str]:
    """Collect all images for a given year across all months."""
    result: list[str] = []
    for m in range(1, 13):
        result.extend(buckets.get((year, m), []))
    return result


class Command(BaseCommand):
    help = "Populate GalleryPhoto images from image_map.json (Cloudinary URLs)"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--image-map",
            default=str(DEFAULT_MAP),
            help="Path to tools/image_map.json",
        )
        parser.add_argument(
            "--photos-per-album",
            type=int,
            default=20,
            help="Max photos per album (default: 20)",
        )
        parser.add_argument(
            "--clear-photos",
            action="store_true",
            help="Delete existing GalleryPhoto records before populating",
        )
        parser.add_argument(
            "--fallback",
            action="store_true",
            help="If no month match, use images from same year",
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        map_path = Path(options["image_map"])
        per_album: int = options["photos_per_album"]
        clear: bool = options["clear_photos"]
        fallback: bool = options["fallback"]
        dry_run: bool = options["dry_run"]

        if not map_path.exists():
            raise CommandError(f"image_map.json not found: {map_path}")

        image_map: dict[str, str] = json.loads(
            map_path.read_text(encoding="utf-8")
        )
        self.stdout.write(f"Image map: {len(image_map)} entries")

        buckets = _build_buckets(image_map)
        self.stdout.write(
            f"Date-structured buckets: {len(buckets)} "
            f"({sum(len(v) for v in buckets.values())} images)"
        )

        if clear and not dry_run:
            deleted, _ = GalleryPhoto.objects.all().delete()
            self.stdout.write(f"Cleared {deleted} existing GalleryPhoto records")

        albums = list(
            GalleryAlbum.objects.filter(is_published=True).order_by("event_date", "id")
        )
        self.stdout.write(f"Albums to process: {len(albums)}")

        created_total = 0
        skipped = 0

        for album in albums:
            if album.event_date:
                yr, mo = album.event_date.year, album.event_date.month
                cdn_list = buckets.get((yr, mo), [])
                if not cdn_list and fallback:
                    cdn_list = _year_bucket(buckets, yr)
            else:
                cdn_list = []

            if not cdn_list:
                skipped += 1
                print(
                    f"  SKIP album {album.pk} '{album.title[:40]}' "
                    f"(event_date={album.event_date}) — no images in map",
                    flush=True,
                )
                continue

            candidates = cdn_list[:per_album]
            if dry_run:
                print(
                    f"  DRY album {album.pk} '{album.title[:40]}' "
                    f"({album.event_date}) → {len(candidates)} photos",
                    flush=True,
                )
                created_total += len(candidates)
                continue

            photos_to_create = []
            for order, cdn_url in enumerate(candidates):
                photos_to_create.append(
                    GalleryPhoto(
                        album=album,
                        image=cdn_url,
                        image_local="",
                        title="",
                        order=order,
                        is_published=True,
                    )
                )

            with transaction.atomic():
                GalleryPhoto.objects.bulk_create(photos_to_create, ignore_conflicts=True)
                # Set album cover from first photo
                if photos_to_create:
                    GalleryAlbum.objects.filter(pk=album.pk).update(
                        cover_image=candidates[0]
                    )

            created_total += len(photos_to_create)
            print(
                f"  album {album.pk} '{album.title[:40]}' → {len(photos_to_create)} photos",
                flush=True,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone: {created_total} photos created/planned, "
                f"{skipped} albums skipped (no date match)"
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
        self.stdout.flush()
