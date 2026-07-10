"""YouTube URL parsing and hero video selection."""
from __future__ import annotations

import re
from dataclasses import dataclass

from django.db.models import Q

_YOUTUBE_ID_RE = re.compile(
    r"(?:youtube\.com/(?:embed/|watch\?.*v=|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def extract_youtube_id(text: str) -> str:
    """Return 11-char YouTube video id from HTML or plain URL, else empty string."""
    if not text:
        return ""
    match = _YOUTUBE_ID_RE.search(text)
    return match.group(1) if match else ""


def youtube_embed_url(video_id: str) -> str:
    return f"https://www.youtube.com/embed/{video_id}?rel=0"


def youtube_watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


@dataclass(frozen=True)
class HeroVideoItem:
    title: str
    youtube_id: str
    article_url: str = ""

    @property
    def embed_url(self) -> str:
        return youtube_embed_url(self.youtube_id)

    @property
    def watch_url(self) -> str:
        return youtube_watch_url(self.youtube_id)


_DEFAULT_VIDEOS: tuple[HeroVideoItem, ...] = (
    HeroVideoItem(
        title="ФПУ — 35 років",
        youtube_id="1JGTu6WONJY",
    ),
    HeroVideoItem(
        title="ФПУ",
        youtube_id="yGO6NNIQjUs",
    ),
)


def get_hero_videos(limit: int = 5) -> list[HeroVideoItem]:
    """Latest published articles with a YouTube link, else site defaults.

    If SiteSettings.hero_youtube_url is set, that video is pinned first.
    """
    from apps.core.models import SiteSettings
    from apps.news.models import Article

    pinned: list[HeroVideoItem] = []
    seen: set[str] = set()

    try:
        settings = SiteSettings.get()
        if settings.hero_youtube_url:
            pin_id = extract_youtube_id(settings.hero_youtube_url)
            if pin_id:
                pinned = [HeroVideoItem(title="", youtube_id=pin_id)]
                seen.add(pin_id)
    except Exception:
        pass

    candidates = (
        Article.objects.filter(is_published=True)
        .filter(Q(body__icontains="youtube.com") | Q(body__icontains="youtu.be"))
        .order_by("-published_at")[: limit * 4]
    )
    items: list[HeroVideoItem] = list(pinned)
    for article in candidates:
        if len(items) >= limit:
            break
        video_id = extract_youtube_id(article.body)
        if not video_id or video_id in seen:
            continue
        seen.add(video_id)
        items.append(
            HeroVideoItem(
                title=article.title,
                youtube_id=video_id,
                article_url=article.get_absolute_url(),
            )
        )

    if items:
        return items
    return list(_DEFAULT_VIDEOS[:limit])
