from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.core.spo_blog_sync import fetch_all_spo_blog_posts, rewrite_spo_body_html, unique_article_slug
from apps.core.spo_content import SPO_NEWS_ALL_URL
from apps.news.models import Article, Category


SAMPLE_WP_POST = {
    "id": 17016,
    "slug": "zasidannya-spo-test",
    "link": "https://spo.fpsu.org.ua/podiyi/zasidannya-spo-test/",
    "date": "2026-05-27T14:17:20",
    "title": {"rendered": "Засідання СПО тест"},
    "excerpt": {"rendered": "<p>Короткий опис.</p>"},
    "content": {"rendered": "<p>Повний текст.</p>"},
    "_embedded": {"wp:featuredmedia": []},
}


@pytest.mark.django_db
def test_spo_news_list_empty(client):
    response = client.get(reverse("core:spo_news"))
    assert response.status_code == 200
    assert "core/spo_news_list.html" in [t.name for t in response.templates if t.name]


@pytest.mark.django_db
def test_spo_news_list_shows_imported_posts(client):
    category = Category.objects.create(alias="spo-wp-novyny", path="spo-wp-novyny", title="Новини СПО")
    Article.objects.create(
        title="Засідання СПО",
        slug="zasidannya-spo",
        summary="Опис",
        body="<p>Текст</p>",
        wp_post_id=17016,
        is_spo=True,
        category=category,
        is_published=True,
    )
    response = client.get(reverse("core:spo_news"))
    body = response.content.decode("utf-8")
    assert "Засідання СПО" in body


@pytest.mark.django_db
def test_spo_news_detail(client):
    category = Category.objects.create(alias="spo-wp-novyny", path="spo-wp-novyny", title="Новини СПО")
    Article.objects.create(
        title="Детальна новина",
        slug="detalna-novyna",
        body="<p>Контент</p>",
        wp_post_id=999,
        is_spo=True,
        category=category,
        is_published=True,
    )
    response = client.get(reverse("core:spo_news_detail", kwargs={"slug": "detalna-novyna"}))
    assert response.status_code == 200
    assert "Детальна новина" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_spo_page_uses_local_news(client):
    category = Category.objects.create(alias="spo-wp-novyny", path="spo-wp-novyny", title="Новини СПО")
    Article.objects.create(
        title="Локальна новина СПО",
        slug="local-spo-news",
        summary="excerpt",
        body="<p>body</p>",
        wp_post_id=12345,
        is_spo=True,
        category=category,
        is_published=True,
    )
    response = client.get(reverse("core:spo"))
    body = response.content.decode("utf-8")
    assert "Локальна новина СПО" in body
    assert "/spo-ob-iednan-profspilok/novyny/local-spo-news/" in body
    assert SPO_NEWS_ALL_URL in body


def test_fetch_all_spo_blog_posts_parses_api():
    with patch(
        "apps.core.spo_blog_sync._fetch_json",
        side_effect=[[SAMPLE_WP_POST], []],
    ):
        posts = fetch_all_spo_blog_posts()
    assert len(posts) == 1
    assert posts[0].wp_post_id == 17016
    assert posts[0].title == "Засідання СПО тест"


@pytest.mark.django_db
def test_unique_article_slug_avoids_collision():
    Article.objects.create(title="Existing", slug="same-slug", is_published=True)
    slug = unique_article_slug("same-slug", 42)
    assert slug == "same-slug-42"


def test_rewrite_spo_body_html_localizes_images(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    html = '<img src="https://spo.fpsu.org.ua/wp-content/uploads/2026/05/test.jpg">'
    with patch("apps.core.spo_blog_sync.download_spo_media", return_value="spo/2026/05/test.jpg"):
        result = rewrite_spo_body_html(html, media_root=tmp_path)
    assert "/media/spo/2026/05/test.jpg" in result
