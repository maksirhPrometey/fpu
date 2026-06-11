"""Gallery views — album list and album detail with photos."""
from __future__ import annotations

from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from apps.core.debug_log import debug_log

from .models import GalleryAlbum, GalleryPhoto
from .utils import local_file_exists


def _gallery_audit(page_albums) -> None:
    """Log gallery media stats for debug session."""
    sample = page_albums[0] if page_albums else None
    on_disk = sum(1 for a in page_albums if a.cover_url)
    with_local = sum(1 for a in page_albums if a.cover_local)
    sample_exists = (
        local_file_exists(sample.cover_local)
        if sample and sample.cover_local
        else False
    )
    debug_log(
        location="gallery/views.py:album_list",
        message="gallery page media audit",
        hypothesis_id="H2-H4",
        data={
            "page_albums": len(page_albums),
            "with_cover_local": with_local,
            "with_resolved_cover_url": on_disk,
            "total_photos_db": GalleryPhoto.objects.filter(is_published=True).count(),
            "sample_title": (sample.title[:60] if sample else ""),
            "sample_cover_local": (sample.cover_local if sample else ""),
            "sample_file_exists": sample_exists,
            "sample_cover_url": (sample.cover_url if sample else ""),
        },
    )


@require_GET
def album_list(request: HttpRequest) -> HttpResponse:
    """List of all published albums, paginated 24/page."""
    qs = GalleryAlbum.objects.filter(is_published=True).order_by("-event_date", "-created_at")
    paginator = Paginator(qs, 24)
    page_obj = paginator.get_page(request.GET.get("page"))

    _gallery_audit(list(page_obj.object_list))

    canonical = request.build_absolute_uri("/gallery/")
    context = {
        "page_obj": page_obj,
        "page_meta_title": _("Фотогалерея"),
        "page_meta_description": _("Фотогалерея Федерації профспілок України — фотозвіти заходів та подій."),
        "canonical_url": canonical,
        "breadcrumbs": [
            {"title": _("Головна"), "url": "/"},
            {"title": _("Фотогалерея"), "url": "/gallery/"},
        ],
    }
    return render(request, "gallery/album_list.html", context)


@require_GET
def album_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Single album page with all photos for lightbox."""
    album = get_object_or_404(GalleryAlbum, slug=slug, is_published=True)
    photos = GalleryPhoto.objects.filter(album=album, is_published=True).order_by("order", "id")

    canonical = request.build_absolute_uri(album.get_absolute_url())
    context = {
        "album": album,
        "photos": photos,
        "page_meta_title": album.title,
        "page_meta_description": (album.description or "")[:160] or f"Фотоальбом «{album.title}» — Федерація профспілок України.",
        "canonical_url": canonical,
        "og_image": album.cover_url,
        "breadcrumbs": [
            {"title": _("Головна"), "url": "/"},
            {"title": _("Фотогалерея"), "url": "/gallery/"},
            {"title": album.title, "url": album.get_absolute_url()},
        ],
    }
    return render(request, "gallery/album_detail.html", context)
