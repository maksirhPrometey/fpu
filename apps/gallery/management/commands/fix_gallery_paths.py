"""Fix GalleryPhoto.image_local paths using JoomGallery catpath."""
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.gallery.models import GalleryAlbum, GalleryPhoto
from apps.gallery.utils import local_file_exists, photo_local_path

BASE = Path(__file__).resolve().parents[4]
DEFAULT_CATS = BASE / "tools" / "gallery_cats.json"
DEFAULT_PHOTOS = BASE / "tools" / "gallery.json"


class Command(BaseCommand):
    help = "Rewrite gallery image_local paths to JoomGallery originals layout."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--cats", default=str(DEFAULT_CATS))
        parser.add_argument("--photos", default=str(DEFAULT_PHOTOS))
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options) -> None:
        cats_path = Path(options["cats"])
        photos_path = Path(options["photos"])
        dry_run: bool = options["dry_run"]

        if not cats_path.exists():
            raise CommandError(f"File not found: {cats_path}")
        if not photos_path.exists():
            raise CommandError(f"File not found: {photos_path}")

        catpath_map = {
            c["id"]: (c.get("catpath") or "").strip()
            for c in json.loads(cats_path.read_text(encoding="utf-8"))
        }
        photos_data = json.loads(photos_path.read_text(encoding="utf-8"))

        photo_by_joomla_id = {int(p["id"]): p for p in photos_data if p.get("id")}
        updated = found_on_disk = 0

        with transaction.atomic():
            for photo in GalleryPhoto.objects.select_related("album").iterator():
                raw = photo_by_joomla_id.get(photo.joomla_id or -1)
                if not raw:
                    continue
                catid = raw.get("catid", "")
                filename = (raw.get("filename") or "").strip()
                if not filename:
                    continue
                new_path = photo_local_path(filename, catpath_map.get(catid, ""))
                if new_path == photo.image_local:
                    if local_file_exists(new_path):
                        found_on_disk += 1
                    continue
                if local_file_exists(new_path):
                    found_on_disk += 1
                if not dry_run:
                    photo.image_local = new_path
                    photo.save(update_fields=["image_local"])
                updated += 1

            cover_updates = 0
            for album in GalleryAlbum.objects.iterator():
                first = album.photos.filter(is_published=True).order_by("order", "id").first()
                if not first or not first.image_local:
                    continue
                if album.cover_local != first.image_local:
                    if not dry_run:
                        album.cover_local = first.image_local
                        album.save(update_fields=["cover_local"])
                    cover_updates += 1

        self.stdout.write(
            f"Photos paths updated: {updated} | files on disk: {found_on_disk} | "
            f"covers updated: {cover_updates}"
        )
        if found_on_disk == 0:
            self.stdout.write(self.style.WARNING(
                "Жодного файлу JoomGallery на диску не знайдено. "
                "Оригінали відсутні на Joomla-сервері — потрібне відновлення з резервної копії."
            ))
