from __future__ import annotations

import pytest

from apps.core.youtube import extract_youtube_id, get_hero_videos, youtube_embed_url


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://www.youtube.com/watch?v=ODlwxvSCSbo", "ODlwxvSCSbo"),
        ("https://youtu.be/1JGTu6WONJY", "1JGTu6WONJY"),
        ('<iframe src="https://www.youtube.com/embed/yGO6NNIQjUs"></iframe>', "yGO6NNIQjUs"),
        ("no video here", ""),
    ],
)
def test_extract_youtube_id(text: str, expected: str) -> None:
    assert extract_youtube_id(text) == expected


def test_youtube_embed_url() -> None:
    assert youtube_embed_url("abc123XYZ01") == "https://www.youtube.com/embed/abc123XYZ01?rel=0"


def test_youtube_watch_url() -> None:
    from apps.core.youtube import youtube_watch_url

    assert youtube_watch_url("abc123XYZ01") == "https://www.youtube.com/watch?v=abc123XYZ01"


@pytest.mark.django_db
def test_get_hero_videos_from_articles() -> None:
    from apps.news.models import Article

    Article.objects.create(
        title="Відео новина",
        body='<a href="https://www.youtube.com/watch?v=ODlwxvSCSbo">watch</a>',
        is_published=True,
    )
    items = get_hero_videos(limit=3)
    assert items
    assert items[0].youtube_id == "ODlwxvSCSbo"
    assert items[0].title == "Відео новина"


@pytest.mark.django_db
def test_get_hero_videos_fallback() -> None:
    items = get_hero_videos()
    assert len(items) >= 2
    assert items[0].youtube_id == "1JGTu6WONJY"


@pytest.mark.django_db
def test_home_renders_youtube_embed(client) -> None:
    from django.urls import reverse

    response = client.get(reverse("core:home"))
    body = response.content.decode("utf-8")
    assert "hero-mosaic__video-embed" in body
    assert "youtube.com/embed/" in body
    assert "hero-mosaic__video-youtube" in body
    assert "youtube.com/watch?v=" in body
