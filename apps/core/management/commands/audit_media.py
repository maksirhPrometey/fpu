"""Audit local media vs original fpsu.org.ua availability."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.core.debug_log import debug_log
from apps.core.media_utils import rewrite_body_html_images
from apps.gallery.models import GalleryAlbum, GalleryPhoto
from apps.gallery.utils import JOOMGALLERY_ORIGINALS_PREFIX, local_file_exists, photo_local_path
from apps.pages.models import StaticPage


class Command(BaseCommand):
    help = "Audit gallery and fotoekspozytsiya media availability."

    def handle(self, *args, **options) -> None:
        tools = Path("tools")
        cats = {
            c["id"]: (c.get("catpath") or "").strip()
            for c in json.loads((tools / "gallery_cats.json").read_text(encoding="utf-8"))
        }
        photos_json = json.loads((tools / "gallery.json").read_text(encoding="utf-8"))

        gallery_photos = GalleryPhoto.objects.filter(is_published=True).count()
        gallery_on_disk = sum(
            1
            for p in GalleryPhoto.objects.filter(is_published=True).iterator()
            if p.image_local and local_file_exists(p.image_local)
        )
        albums_total = GalleryAlbum.objects.filter(is_published=True).count()
        albums_with_url = sum(
            1 for a in GalleryAlbum.objects.filter(is_published=True) if a.cover_url
        )

        sample_photo = photos_json[0]
        fn = sample_photo["filename"]
        catpath = cats.get(sample_photo["catid"], "")
        original_urls = [
            f"https://www.fpsu.org.ua/images/stories/{fn}",
            f"https://www.fpsu.org.ua/{photo_local_path(fn, catpath)}",
        ]
        original_status = {}
        for url in original_urls:
            code = subprocess.run(
                ["curl", "-sI", "-o", "/dev/null", "-w", "%{http_code}", url],
                capture_output=True,
                text=True,
            ).stdout.strip()
            original_status[url] = code

        debug_log(
            location="audit_media:gallery",
            message="gallery audit summary",
            hypothesis_id="H1-H3",
            data={
                "photos_db": gallery_photos,
                "photos_on_disk": gallery_on_disk,
                "albums_db": albums_total,
                "albums_with_cover_url": albums_with_url,
                "joomgallery_prefix": JOOMGALLERY_ORIGINALS_PREFIX,
                "sample_filename": fn,
                "sample_catpath": catpath,
                "sample_local_path": photo_local_path(fn, catpath),
                "sample_local_exists": local_file_exists(photo_local_path(fn, catpath)),
                "original_http_status": original_status,
            },
        )

        page = StaticPage.objects.filter(url_path="/fotoekspozytsiya").first()
        foto_src = ""
        foto_local_exists = False
        foto_original_status = ""
        if page and page.body:
            m = re.search(r'src="([^"]+)"', page.body) or re.search(r"src='([^']+)'", page.body)
            if m:
                foto_src = m.group(1)
                rewritten = rewrite_body_html_images(f'src="{foto_src}"')
                rel_m = re.search(r"/media/joomla_images/(.+?)\"", rewritten)
                if rel_m:
                    rel = rel_m.group(1)
                    foto_local_exists = local_file_exists(rel)
                foto_original_status = subprocess.run(
                    ["curl", "-sI", "-o", "/dev/null", "-w", "%{http_code}", foto_src],
                    capture_output=True,
                    text=True,
                ).stdout.strip()

        debug_log(
            location="audit_media:fotoekspozytsiya",
            message="fotoekspozytsiya audit",
            hypothesis_id="H5",
            data={
                "page_found": bool(page),
                "raw_src": foto_src,
                "local_file_exists": foto_local_exists,
                "original_http_status": foto_original_status,
            },
        )

        self.stdout.write(
            f"Gallery: {gallery_on_disk}/{gallery_photos} on disk, "
            f"{albums_with_url}/{albums_total} album covers"
        )
        self.stdout.write(
            f"Fotoekspozytsiya local exists={foto_local_exists}, "
            f"original HTTP={foto_original_status}"
        )
        self.stdout.write(self.style.SUCCESS(f"Log: .cursor/debug-ef1f56.log"))
