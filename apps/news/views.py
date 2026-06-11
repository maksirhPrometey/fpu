"""News views — article detail and category listing."""
from __future__ import annotations

from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from apps.pages.fotoekspozytsiya import is_fotoeksp_article
from apps.pages.menu_news import news_category_for_menu_path
from apps.pages.models import StaticPage
from apps.pages.views import _build_breadcrumbs as _static_page_breadcrumbs, _render_static

from .models import Article, Category

MEMBER_ORG_CATEGORY_PATHS: frozenset[str] = frozenset({
    "pro-fpu/chlenski-organizatsiji/vseukrajinski-galuzevi-profspilki",
    "pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok",
})

_CATEGORY_PAGE_SIZE = 10


def _category_articles_queryset(category: Category, *, menu_feed: bool = False):
    qs = Article.objects.filter(category=category, is_published=True).select_related("category")
    if category.path in MEMBER_ORG_CATEGORY_PATHS:
        return qs.order_by("title", "joomla_id")
    if menu_feed:
        return qs.order_by("-order", "-published_at", "-joomla_id")
    return qs.order_by("-published_at")


def _filter_category_landing(articles: list[Article], category: Category) -> list[Article]:
    path_leaf = category.path.rsplit("/", 1)[-1]
    skip_slugs = {path_leaf, category.alias}
    return [article for article in articles if article.slug not in skip_slugs]


def _category_list_articles(category: Category) -> list[Article]:
    """Articles for a category listing, minus Joomla category landing duplicates."""
    qs = _category_articles_queryset(category)
    limit = 100 if category.path in MEMBER_ORG_CATEGORY_PATHS else 50
    return _filter_category_landing(list(qs[:limit]), category)


def _resolve_category_list(
    path_clean: str,
) -> tuple[Category, str, StaticPage | None] | None:
    """Map menu URL to news category; return (category, menu_path, optional StaticPage)."""
    static_page = _static_page_for_category(path_clean)
    try:
        category = Category.objects.get(path=path_clean, is_active=True)
        return category, path_clean, static_page
    except Category.DoesNotExist:
        pass

    news_path = news_category_for_menu_path(path_clean)
    if not news_path:
        return None
    try:
        category = Category.objects.get(path=news_path, is_active=True)
    except Category.DoesNotExist:
        return None
    return category, path_clean, static_page


@require_GET
def article_in_cat(
    request: HttpRequest,
    cat_path: str,
    joomla_id: str,
    slug: str,
) -> HttpResponse:
    """Article accessed via /<cat_path>/<joomla_id>-<slug>.html."""
    try:
        jid = int(joomla_id)
    except (ValueError, TypeError):
        from django.http import Http404
        raise Http404("Invalid article id")

    article = get_object_or_404(Article, joomla_id=jid, is_published=True)
    # Note: slug mismatch is allowed — the canonical URL in <head> ensures
    # search engines treat the correct URL as authoritative.

    category = article.category
    canonical = request.build_absolute_uri(article.get_absolute_url())

    context = {
        "article": article,
        "category": category,
        "page_meta_title": article.effective_meta_title,
        "page_meta_description": article.meta_description,
        "page_meta_keywords": article.meta_keywords,
        "canonical_url": canonical,
        "og_image": article.image_url,
        "og_type": "article",
        "breadcrumbs": _build_breadcrumbs(category, article),
    }
    return render(request, "news/article_detail.html", context)


@require_GET
def category_list(request: HttpRequest, cat_path: str) -> HttpResponse:
    """Category listing page: /<cat_path>/"""
    from django.http import HttpResponsePermanentRedirect

    path_clean = cat_path.strip("/")
    resolved = _resolve_category_list(path_clean)
    if resolved is None:
        return HttpResponsePermanentRedirect(f"/{path_clean}")

    category, menu_path, static_page = resolved
    is_member_org_list = path_clean in MEMBER_ORG_CATEGORY_PATHS
    is_menu_news_feed = news_category_for_menu_path(menu_path) is not None
    page_obj = None

    if is_member_org_list:
        articles = _category_list_articles(category)
    else:
        paginator = Paginator(
            _category_articles_queryset(category, menu_feed=is_menu_news_feed),
            _CATEGORY_PAGE_SIZE,
        )
        page_obj = paginator.get_page(request.GET.get("page", 1))
        articles = _filter_category_landing(list(page_obj.object_list), category)

    single_article = None
    if len(articles) == 1 and news_category_for_menu_path(menu_path) is None:
        if is_member_org_list or page_obj is None or page_obj.paginator.count == 1:
            single_article = articles[0]

    if not articles:
        if static_page is not None:
            return _render_static(request, static_page)

    display_title = static_page.title if static_page else category.title
    canonical = request.build_absolute_uri(f"/{menu_path}/")
    breadcrumbs = _static_page_breadcrumbs(f"/{menu_path}") if static_page else None

    context = {
        "category": category,
        "articles": articles,
        "single_article": single_article,
        "is_member_org_list": is_member_org_list,
        "is_menu_news_feed": is_menu_news_feed,
        "menu_path": menu_path,
        "page_obj": page_obj,
        "display_title": display_title,
        "breadcrumbs": breadcrumbs,
        "page_meta_title": display_title,
        "page_meta_description": category.meta_description or (
            single_article.meta_description if single_article else ""
        ),
        "page_meta_keywords": category.meta_keywords,
        "canonical_url": canonical,
    }
    template = "news/member_org_list.html" if is_member_org_list else "news/category_list.html"
    return render(request, template, context)


@require_GET
def article_by_slug(request: HttpRequest, slug: str) -> HttpResponse:
    """Article accessed via /news/<slug>/ — for articles without a Joomla ID."""
    article = get_object_or_404(Article, slug=slug, is_published=True)
    category = article.category
    canonical = request.build_absolute_uri(article.get_absolute_url())

    context = {
        "article": article,
        "category": category,
        "page_meta_title": article.effective_meta_title,
        "page_meta_description": article.meta_description,
        "page_meta_keywords": article.meta_keywords,
        "canonical_url": canonical,
        "og_image": article.image_url,
        "og_type": "article",
        "breadcrumbs": _build_breadcrumbs(category, article),
    }
    return render(request, "news/article_detail.html", context)


@require_GET
def all_news(request: HttpRequest) -> HttpResponse:
    """All published articles with pagination — /novini/"""
    qs = (
        Article.objects.filter(is_published=True)
        .select_related("category")
        .order_by("-published_at")
    )
    paginator = Paginator(qs, 10)
    page_num = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_num)

    context = {
        "page_obj": page_obj,
        "breadcrumbs": [
            {"title": _("Головна"), "url": "/"},
            {"title": _("Новини"), "url": "/novini/"},
        ],
    }
    return render(request, "news/all_news.html", context)


def _static_page_for_category(path_clean: str) -> StaticPage | None:
    """StaticPage for an empty news category (section index pages)."""
    for variant in (f"/{path_clean}", f"/{path_clean}.html"):
        try:
            return StaticPage.objects.get(url_path=variant, is_published=True)
        except StaticPage.DoesNotExist:
            continue
    return None


def _build_breadcrumbs(category: Category | None, article: Article | None = None) -> list[dict]:
    crumbs: list[dict] = [{"title": _("Головна"), "url": "/"}]
    if article and is_fotoeksp_article(article):
        crumbs.append({"title": _("Фотовиставка"), "url": "/fotoekspozytsiya/"})
    elif category:
        crumbs.append({"title": category.title, "url": f"/{category.path}/"})
    return crumbs
