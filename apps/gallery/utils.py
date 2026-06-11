"""Helpers for JoomGallery local media paths."""
from __future__ import annotations

from pathlib import Path

from django.conf import settings

from apps.core.media_utils import joomla_media_url

JOOMGALLERY_ORIGINALS_PREFIX = "images/joomgallery/originals"


def photo_local_path(filename: str, catpath: str = "") -> str:
    """
    Build relative path under media/joomla_images/ for a JoomGallery photo.

    JoomGallery stores originals at:
        images/joomgallery/originals/<catpath>/<filename>
    """
    filename = filename.strip()
    if not filename:
        return ""
    if filename.startswith("images/"):
        return filename
    catpath = catpath.strip().strip("/")
    if catpath:
        return f"{JOOMGALLERY_ORIGINALS_PREFIX}/{catpath}/{filename}"
    return f"images/stories/{filename}"


def media_root_path(relative: str) -> Path:
    """Absolute path on disk for a joomla_images-relative path."""
    rel = relative.strip().lstrip("/")
    if rel.startswith("media/"):
        rel = rel[len("media/") :]
    if not rel.startswith("joomla_images/"):
        rel = f"joomla_images/{rel}"
    return Path(settings.MEDIA_ROOT) / rel


def local_file_exists(relative: str) -> bool:
    if not relative:
        return False
    return media_root_path(relative).is_file()


def resolved_media_url(relative: str) -> str:
    """Return /media/ URL only when the file exists locally."""
    if not local_file_exists(relative):
        return ""
    return joomla_media_url(relative)
