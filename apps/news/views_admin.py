"""Admin-only helper views for the news editor."""
from __future__ import annotations

import uuid
from pathlib import Path

from django.core.files.storage import default_storage
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_POST

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@require_POST
def upload_image(request: HttpRequest) -> JsonResponse:
    """Upload an inline image to local media and return its URL."""
    image = request.FILES.get("image") or request.FILES.get("file")
    if not image:
        return JsonResponse({"error": "Файл не передано"}, status=400)

    if image.content_type not in _ALLOWED_CONTENT_TYPES:
        return JsonResponse(
            {"error": "Дозволені формати: JPEG, PNG, GIF, WebP"}, status=400
        )

    if image.size > _MAX_SIZE_BYTES:
        return JsonResponse(
            {"error": "Файл завеликий — максимум 10 МБ"}, status=400
        )

    ext = Path(image.name).suffix.lower() or ".jpg"
    rel_path = f"uploads/articles/{uuid.uuid4().hex}{ext}"
    saved = default_storage.save(rel_path, image)

    return JsonResponse({"url": default_storage.url(saved)})
