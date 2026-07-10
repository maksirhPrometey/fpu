"""Unfold sidebar navigation that mirrors the public site structure.

Built at request time (Unfold accepts a callable for ``SIDEBAR["navigation"]``)
so that ``reverse()`` and DB lookups are safe to use here.

Design goals:
- Sidebar groups mirror the site menu (apps/core/nav.py).
- «Про ФПУ» — редагування статичного контенту (Історія, Керівництво тощо).
- «Напрями діяльності» — список статей категорії.
- SPO is a dedicated section (own news + homepage content).
"""
from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlencode

from django.urls import reverse

from apps.core.nav import NAV_SECTIONS
from apps.pages.menu_news import news_category_for_menu_path


def _nav_section(url: str) -> dict[str, Any]:
    target = url.rstrip("/")
    for section in NAV_SECTIONS:
        if section["url"].rstrip("/") == target:
            return section
    return {"label": "", "url": url, "children": []}


def _page_link(path: str) -> Callable[[Any], str]:
    """Direct link to a StaticPage edit form, resolved by url_path."""
    clean = path.rstrip("/") or path

    def _callback(request: Any, _path: str = clean) -> str:
        return reverse("admin:pages_staticpage_go") + "?" + urlencode({"path": _path})

    return _callback


def _news_cat_link(menu_path: str) -> str | None:
    """Link to admin article list filtered by the news category for this menu path.

    Resolves the category path → DB id at nav-build time so the URL uses
    the standard Django admin ``?category=<id>`` filter format.
    """
    clean = menu_path.strip("/")
    cat_path = news_category_for_menu_path(clean)
    if not cat_path:
        return None
    try:
        from apps.news.models import Category
        cat = Category.objects.get(path=cat_path, is_active=True)
        return f"/admin/news/article/?category={cat.pk}"
    except Exception:
        return f"/admin/news/article/?category__path={cat_path}"


def _doc_link(slug: str) -> Callable[[Any], str]:
    """Direct link to a DocumentCategory edit form, resolved by slug."""

    def _callback(request: Any, _slug: str = slug) -> str:
        return (
            reverse("admin:documents_documentcategory_go")
            + "?"
            + urlencode({"slug": _slug})
        )

    return _callback


def _document_items() -> list[dict]:
    """All document categories as direct edit links + the full list."""
    from apps.documents.models import DocumentCategory

    items: list[dict] = []
    for category in DocumentCategory.objects.order_by("order", "title"):
        items.append(
            {
                "title": category.title,
                "icon": "folder",
                "link": _doc_link(category.slug),
            }
        )
    items.append(
        {"title": "Усі документи", "icon": "description", "link": "/admin/documents/document/"}
    )
    items.append(
        {
            "title": "Категорії документів",
            "icon": "category",
            "link": "/admin/documents/documentcategory/",
        }
    )
    return items


def _pro_fpu_items() -> list[dict]:
    """Сторінки розділу «Про ФПУ» — статичний контент або стрічка новин."""
    section = _nav_section("/pro-fpu")
    items: list[dict] = []
    for child in section.get("children", []):
        child_url = child["url"]
        news_link = _news_cat_link(child_url)
        if news_link:
            items.append({"title": str(child["label"]), "icon": "feed", "link": news_link})
        else:
            items.append(
                {"title": str(child["label"]), "icon": "article", "link": _page_link(child_url)}
            )
    return items


def _napryamki_items() -> list[dict]:
    """Only news-category children of 'Напрями діяльності' — no static pages."""
    section = _nav_section("/napryamki-diyalnosti")
    items: list[dict] = []
    for child in section.get("children", []):
        news_link = _news_cat_link(child["url"])
        if news_link:
            items.append({"title": str(child["label"]), "icon": "feed", "link": news_link})
    return items


def _holovna_novyna_link() -> str:
    """Admin link to articles in holovna-novyna category."""
    try:
        from apps.news.models import Category
        cat = Category.objects.get(path="holovna-novyna", is_active=True)
        return f"/admin/news/article/?category={cat.pk}"
    except Exception:
        return "/admin/news/article/?category__path=holovna-novyna"


def _home_section_link(section_type: str) -> str:
    """Direct link to a specific PageSection for home page."""
    try:
        from apps.core.models import PageSection
        obj = PageSection.objects.get(page="home", section_type=section_type)
        return f"/admin/core/pagesection/{obj.pk}/change/"
    except Exception:
        return f"/admin/core/pagesection/add/?page=home&section_type={section_type}"


def build_navigation(request: Any) -> list[dict]:
    """Return the Unfold sidebar navigation mirroring the public site."""
    return [
        {
            "title": "Головна сторінка",
            "separator": False,
            "collapsible": False,
            "items": [
                {"title": "Перейти на сайт", "icon": "public", "link": "/"},
                {
                    "title": "Hero: статті, відео, анонс",
                    "icon": "tune",
                    "link": "/admin/core/sitesettings/1/change/",
                },
                {
                    "title": "Анонси блок (hero)",
                    "icon": "campaign",
                    "link": _home_section_link("announce"),
                },
                {
                    "title": "Пріоритети ФПУ",
                    "icon": "star",
                    "link": "/admin/core/priority/",
                },
                {
                    "title": "Налаштування сайту",
                    "icon": "settings",
                    "link": "/admin/core/sitesettings/1/change/",
                },
            ],
        },
        {
            "title": "Про ФПУ",
            "separator": True,
            "collapsible": True,
            "items": _pro_fpu_items(),
        },
        {
            "title": "Напрями діяльності",
            "separator": True,
            "collapsible": True,
            "items": _napryamki_items(),
        },
        {
            "title": "Документи ФПУ",
            "separator": True,
            "collapsible": True,
            "items": _document_items(),
        },
        {
            "title": "Новини",
            "separator": True,
            "collapsible": False,
            "items": [
                {"title": "Усі новини", "icon": "newspaper", "link": "/admin/news/article/"},
                {"title": "Категорії новин", "icon": "label", "link": "/admin/news/category/"},
            ],
        },
        {
            "title": "Галерея",
            "separator": True,
            "collapsible": False,
            "items": [
                {"title": "Альбоми", "icon": "photo_library", "link": "/admin/gallery/galleryalbum/"},
            ],
        },
        {
            "title": "Фотовиставка",
            "separator": True,
            "collapsible": False,
            "items": [
                {"title": "Головна сторінка", "icon": "photo_library", "link": "/admin/pages/fotoeksppage/"},
                {"title": "Сторінки з фото", "icon": "collections", "link": "/admin/pages/fotoekspalbum/"},
            ],
        },
        {
            "title": "Членські організації",
            "separator": True,
            "collapsible": True,
            "items": [
                {"title": "Сторінки організацій", "icon": "domain", "link": "/admin/core/memorgpage/"},
                {"title": "Перелік (логотипи)", "icon": "account_balance", "link": "/admin/core/memberorganization/"},
            ],
        },
        {
            "title": "Контакти та звернення",
            "separator": True,
            "collapsible": False,
            "items": [
                {
                    "title": "Звернення",
                    "icon": "mail",
                    "link": "/admin/core/contactmessage/",
                    "badge": "apps.core.admin.unread_messages_badge",
                },
                {
                    "title": "Заявки на вступ",
                    "icon": "how_to_reg",
                    "link": "/admin/core/joinrequest/",
                    "badge": "apps.core.admin.pending_join_badge",
                },
            ],
        },
        {
            "title": "Доступ",
            "separator": True,
            "collapsible": False,
            "items": [
                {
                    "title": "Користувачі адмінки",
                    "icon": "manage_accounts",
                    "link": "/admin/auth/user/",
                },
                {
                    "title": "Додати адміна",
                    "icon": "person_add",
                    "link": "/admin/auth/user/add/",
                },
                {"title": "Групи доступу", "icon": "groups", "link": "/admin/auth/group/"},
            ],
        },
    ]
