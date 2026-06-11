from __future__ import annotations

from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.core.models import SpoHomeCache
from apps.core.spo_content import SPO_HERO_LEAD, SPO_MEMBERS, SPO_NEWS_ALL_URL


SAMPLE_HOME = {
    "news": [
        {
            "date": "27.05.2026",
            "url": "https://spo.fpsu.org.ua/example/",
            "title": "Засідання СПО",
            "excerpt": "Рішення № 73-1",
            "image_url": "https://spo.fpsu.org.ua/wp-content/uploads/example.jpg",
        }
    ],
    "videos": [
        {
            "embed_url": "https://www.youtube.com/embed/abc123XYZ01",
            "watch_url": "https://www.youtube.com/watch?v=abc123XYZ01",
            "title": "SPO video",
        }
    ],
    "gallery": [
        {
            "link": "https://spo.fpsu.org.ua/gallery/1/",
            "image_url": "https://spo.fpsu.org.ua/wp-content/uploads/g1.jpg",
        }
    ],
    "partners": [
        {
            "image_url": "https://spo.fpsu.org.ua/wp-content/uploads/partner.png",
            "alt": "Partner",
        }
    ],
}


@pytest.fixture
def spo_cache(db):
    cache = SpoHomeCache.load()
    cache.news = SAMPLE_HOME["news"]
    cache.videos = SAMPLE_HOME["videos"]
    cache.gallery = SAMPLE_HOME["gallery"]
    cache.partners = SAMPLE_HOME["partners"]
    cache.save()
    return cache


@pytest.mark.django_db
def test_spo_page_returns_200(client, spo_cache):
    response = client.get(reverse("core:spo"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_spo_page_uses_correct_template(client, spo_cache):
    response = client.get(reverse("core:spo"))
    template_names = [t.name for t in response.templates if t.name]
    assert "core/spo.html" in template_names


@pytest.mark.django_db
def test_spo_page_static_content(client, spo_cache):
    response = client.get(reverse("core:spo"))
    assert response.context["spo_hero_lead"] == SPO_HERO_LEAD
    assert list(response.context["spo_members"]) == list(SPO_MEMBERS)
    assert response.context["spo_news_all_url"] == SPO_NEWS_ALL_URL


@pytest.mark.django_db
def test_spo_page_renders_live_blocks(client, spo_cache):
    response = client.get(reverse("core:spo"))
    body = response.content.decode("utf-8")
    assert "spo-intro" in body
    assert "spo-members__link" in body
    assert "page--spo" in body
    assert "spo-news__card" in body
    assert "spo-gallery" in body
    assert "spo-partners" in body
    assert "Засідання СПО" in body
    assert "Читати всі новини" in body
    assert "referrerpolicy=\"strict-origin-when-cross-origin\"" in body
    assert "zalp.org.ua" in body


@pytest.mark.django_db
def test_spo_page_fetches_when_cache_empty(client):
    with patch("apps.core.spo_live_sync.fetch_spo_homepage", return_value=SAMPLE_HOME):
        response = client.get(reverse("core:spo"))
    assert response.status_code == 200
    cache = SpoHomeCache.load()
    assert len(cache.news) == 1


def test_fetch_spo_homepage_parses_news():
    from apps.core.spo_live_sync import fetch_spo_homepage

    html = """
    <article id="post-1">
      <time class="entry-time">27.05.2026</time>
      <div class="entry-header"><a href="https://spo.fpsu.org.ua/post/">Title</a></div>
      <div class="entry-text">Excerpt text here.</div>
      <img src="https://spo.fpsu.org.ua/img.jpg">
    </article>
    <iframe src="https://www.youtube.com/embed/ykezo3qO660" title="Video"></iframe>
    """
    with patch("apps.core.spo_live_sync._fetch", return_value=html):
        data = fetch_spo_homepage()
    assert len(data["news"]) == 1
    assert data["news"][0]["date"] == "27.05.2026"
    assert data["news"][0]["title"] == "Title"
    assert "Excerpt" in data["news"][0]["excerpt"]
    assert data["videos"][0]["embed_url"].endswith("ykezo3qO660?rel=0")
    assert data["videos"][0]["watch_url"].endswith("v=ykezo3qO660")
