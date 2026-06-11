"""Tests for Joomla-compatible URL patterns and article/category views."""
from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.news.factories import ArticleFactory, CategoryFactory


@pytest.fixture
def cat(db):
    return CategoryFactory(
        joomla_id=999,
        alias="test-cat",
        path="test-cat",
        is_active=True,
    )


@pytest.fixture
def article(cat, db):
    return ArticleFactory(
        joomla_id=12345,
        slug="test-article",
        category=cat,
        is_published=True,
    )


@pytest.mark.django_db
def test_article_in_cat_returns_200(client: Client, article):
    url = f"/test-cat/12345-test-article.html"
    resp = client.get(url)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_article_slug_mismatch_still_200(client: Client, article):
    """Wrong slug: canonical URL in response ensures SEO correctness."""
    url = "/test-cat/12345-wrong-slug.html"
    resp = client.get(url)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_unknown_joomla_id_returns_404(client: Client, cat):
    url = "/test-cat/99999-missing-article.html"
    resp = client.get(url)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_category_list_returns_200(client: Client, cat):
    resp = client.get("/test-cat/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_single_article_category_shows_body(client: Client, cat):
    ArticleFactory(
        joomla_id=115,
        slug="istoriya-fpu",
        title="Історія Федерації професійних спілок України",
        body="<p>Текст історії ФПУ для перевірки.</p>",
        category=cat,
        is_published=True,
    )
    resp = client.get("/test-cat/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "Текст історії ФПУ для перевірки." in body
    assert "news-list" not in body


@pytest.mark.django_db
def test_category_list_skips_category_landing_article(client: Client):
    cat = CategoryFactory(
        joomla_id=114,
        alias="viborchi-organi-fpu",
        path="pro-fpu/viborchi-organi-fpu",
        title="Виборчі organi ФPU",
        is_active=True,
    )
    ArticleFactory(joomla_id=119, slug="prezidiya", title="Президія", category=cat, is_published=True)
    ArticleFactory(
        joomla_id=116,
        slug="viborchi-organi-fpu",
        title="Виборні organi ФPU",
        category=cat,
        is_published=True,
    )
    resp = client.get("/pro-fpu/viborchi-organi-fpu/")
    body = resp.content.decode("utf-8")
    assert "Президія" in body
    assert "116-viborchi-organi-fpu" not in body


@pytest.mark.django_db
def test_article_context_has_seo_fields(client: Client, article):
    url = f"/test-cat/12345-test-article.html"
    resp = client.get(url)
    assert "page_meta_title" in resp.context
    assert "page_meta_description" in resp.context
    assert "canonical_url" in resp.context


@pytest.mark.django_db
def test_empty_category_falls_back_to_static_page(client: Client):
    from apps.pages.models import StaticPage

    CategoryFactory(
        joomla_id=268,
        alias="chlenski-organizatsiji",
        path="pro-fpu/chlenski-organizatsiji",
        title="Членські організації ФПУ",
        is_active=True,
    )
    StaticPage.objects.create(
        url_path="/pro-fpu/chlenski-organizatsiji",
        title="Членські організації ФПУ",
        body='<p class="section-intro">Intro</p><ul class="section-nav"><li><a href="/sub/">Sub</a></li></ul>',
        is_published=True,
    )
    resp = client.get("/pro-fpu/chlenski-organizatsiji/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "Intro" in body
    assert "empty-notice" not in body


@pytest.mark.django_db
def test_member_org_no_ext_redirects_to_category_list(client: Client):
    cat = CategoryFactory(
        joomla_id=245,
        alias="vseukrajinski-galuzevi-profspilki",
        path="pro-fpu/chlenski-organizatsiji/vseukrajinski-galuzevi-profspilki",
        title="Всеукраїнські галузеві профспілки",
        is_active=True,
    )
    ArticleFactory(
        joomla_id=195,
        slug="profspilka-aviabudivnikiv-ukrajini",
        title="Професійна спілка працівників авіабудування",
        category=cat,
        is_published=True,
    )
    from apps.pages.models import StaticPage

    StaticPage.objects.create(
        url_path="/pro-fpu/chlenski-organizatsiji/vseukrajinski-galuzevi-profspilki",
        title="Всеукраїнські галузеві профспілки",
        body="",
        is_published=True,
    )
    resp = client.get("/pro-fpu/chlenski-organizatsiji/vseukrajinski-galuzevi-profspilki")
    assert resp.status_code == 301
    assert resp["Location"].endswith("/pro-fpu/chlenski-organizatsiji/vseukrajinski-galuzevi-profspilki/")


@pytest.mark.django_db
def test_member_org_category_uses_directory_template(client: Client):
    cat = CategoryFactory(
        joomla_id=245,
        alias="vseukrajinski-galuzevi-profspilki",
        path="pro-fpu/chlenski-organizatsiji/vseukrajinski-galuzevi-profspilki",
        title="Всеукраїнські галузеві профспілки",
        is_active=True,
    )
    ArticleFactory(
        joomla_id=195,
        slug="profspilka-aviabudivnikiv-ukrajini",
        title="Професійна спілка працівників авіабудування",
        category=cat,
        is_published=True,
    )
    resp = client.get("/pro-fpu/chlenski-organizatsiji/vseukrajinski-galuzevi-profspilki/")
    body = resp.content.decode("utf-8")
    assert resp.status_code == 200
    assert "ms-orgs-list" in body
    assert "Професійна спілка працівників авіабудування" in body
    assert "news-list" not in body


@pytest.mark.django_db
def test_napryamki_menu_path_shows_news_feed(client: Client):
    news_cat = CategoryFactory(
        joomla_id=70,
        alias="pravovij-zakhist",
        path="informatsiya-za-napryamkami-diyalnosti/pravovij-zakhist",
        title="Правовий захист (новини)",
        is_active=True,
    )
    ArticleFactory(
        joomla_id=9001,
        slug="yuridichna-konsultatsiya-test",
        title="Юридичні консультації Центру правової допомоги ФПУ",
        category=news_cat,
        is_published=True,
    )
    from apps.pages.models import StaticPage

    StaticPage.objects.create(
        url_path="/napryamki-diyalnosti/pravovij-zakhist",
        title="Правовий захист",
        body="<p>intro</p>",
        is_published=True,
    )
    resp = client.get("/napryamki-diyalnosti/pravovij-zakhist/")
    body = resp.content.decode("utf-8")
    assert resp.status_code == 200
    assert "Юридичні консультації" in body
    assert "section-intro" not in body
    assert "blog-list" in body


@pytest.mark.django_db
def test_napryamki_no_ext_redirects_to_news_feed(client: Client):
    news_cat = CategoryFactory(
        joomla_id=70,
        alias="pravovij-zakhist",
        path="informatsiya-za-napryamkami-diyalnosti/pravovij-zakhist",
        is_active=True,
    )
    ArticleFactory(joomla_id=9002, slug="test-law", category=news_cat, is_published=True)
    from apps.pages.models import StaticPage

    StaticPage.objects.create(
        url_path="/napryamki-diyalnosti/pravovij-zakhist",
        title="Правовий захист",
        body="",
        is_published=True,
    )
    resp = client.get("/napryamki-diyalnosti/pravovij-zakhist")
    assert resp.status_code == 301
    assert resp["Location"].endswith("/napryamki-diyalnosti/pravovij-zakhist/")


@pytest.mark.django_db
def test_robots_txt(client: Client):
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert b"User-agent" in resp.content
    assert b"Disallow: /admin/" in resp.content


@pytest.mark.django_db
def test_sitemap_xml(client: Client):
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert b"urlset" in resp.content
