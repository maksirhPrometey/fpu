"""Fotoekspozytsiya page helpers."""
from __future__ import annotations

import re
from functools import lru_cache

from django.db.models import Q

from apps.core.media_utils import rewrite_joomla_body_html

_FOTOEKSP_PATH = "/fotoekspozytsiya"
_ARTICLE_ID_IN_HREF = re.compile(r"/(\d{5})-")
_INLINE_STYLE_RE = re.compile(r'\s+style="[^"]*"', re.IGNORECASE)

FOTOEKSP_TERRITORIAL_CATEGORY = "fotovystavka-2024"
FOTOEKSP_GALUZ_CATEGORY = "materiali"


def fotoeksp_albums_queryset():
    """Articles that belong to the fotoekspozytsiya exhibition."""
    from apps.news.models import Article

    joomla_ids = fotoeksp_article_joomla_ids()
    return (
        Article.objects.filter(
            Q(category__path=FOTOEKSP_TERRITORIAL_CATEGORY)
            | Q(category__path=FOTOEKSP_GALUZ_CATEGORY)
            | Q(joomla_id__in=joomla_ids)
        )
        .select_related("category")
        .distinct()
    )


def fotoeksp_section_label(article) -> str:
    """Human-readable section name for admin list."""
    if article.category and article.category.path == FOTOEKSP_GALUZ_CATEGORY:
        return "Галузеві профспілки"
    return "Територіальні об'єднання"


def get_fotoeksp_page():
    """Return the fotoekspozytsiya StaticPage, creating a stub if missing."""
    from apps.pages.models import FOTOEKSP_URL_PATH, StaticPage

    page, _ = StaticPage.objects.get_or_create(
        url_path=FOTOEKSP_URL_PATH,
        defaults={
            "title": "ФОТОВИСТАВКА",
            "is_published": True,
        },
    )
    return page


def fotoeksp_entries_for_page(page):
    """Published entries grouped by section."""
    from apps.pages.models import FotoekspEntry

    qs = (
        FotoekspEntry.objects.filter(page=page, is_published=True)
        .select_related("article", "article__category")
        .order_by("order", "pk")
    )
    return {
        FotoekspEntry.SECTION_TERRITORIAL: qs.filter(section=FotoekspEntry.SECTION_TERRITORIAL),
        FotoekspEntry.SECTION_GALUZ: qs.filter(section=FotoekspEntry.SECTION_GALUZ),
    }


def uses_structured_content(page) -> bool:
    from apps.pages.models import FotoekspEntry

    return FotoekspEntry.objects.filter(page=page).exists()


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    return " ".join(text.split())


def _local_image_from_src(src: str) -> str:
    if not src:
        return ""
    if "/joomla_images/" in src:
        return src.split("/joomla_images/", 1)[1]
    if src.startswith("/media/"):
        return src[len("/media/") :]
    return ""


def _parse_table_rows(table_html: str, section: str) -> list[dict]:
    rows = re.findall(r"<tr\b.*?</tr>", table_html, re.IGNORECASE | re.DOTALL)
    entries: list[dict] = []
    for row in rows[1:]:
        num_match = re.search(r">(\d+)\.", row)
        order = int(num_match.group(1)) if num_match else len(entries) + 1
        link_match = re.search(r'<a href=["\']([^"\']+)["\']', row, re.IGNORECASE)
        joomla_id = None
        if link_match:
            id_match = _ARTICLE_ID_IN_HREF.search(link_match.group(1))
            if id_match:
                joomla_id = int(id_match.group(1))
        title = _strip_html(row)
        title = re.sub(r"^\d+\.\s*", "", title).strip()
        if not title:
            continue
        entries.append(
            {
                "section": section,
                "order": order,
                "title": title,
                "joomla_id": joomla_id,
            }
        )
    return entries


def import_fotoeksp_from_html(html: str) -> dict:
    """Parse legacy Joomla HTML into settings fields and entry rows."""
    from apps.pages.models import FotoekspEntry

    settings: dict[str, str] = {}
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if img_match:
        settings["hero_image_local"] = _local_image_from_src(img_match.group(1))

    notice_match = re.search(
        r"color:\s*#ff0000[^>]*>([^<]+)",
        html,
        re.IGNORECASE,
    )
    if notice_match:
        settings["notice_text"] = _strip_html(notice_match.group(1))

    teritorial_date = re.search(
        r"ТЕРИТОРІАЛЬНІ[\s\S]{0,400}?<em[^>]*>([^<]+)</em>",
        html,
        re.IGNORECASE,
    )
    if teritorial_date:
        settings["teritorial_date_note"] = _strip_html(teritorial_date.group(1))

    galuz_date = re.search(
        r"ВСЕУКРАЇНСЬКІ[\s\S]{0,400}?<em[^>]*>([^<]+)</em>",
        html,
        re.IGNORECASE,
    )
    if galuz_date:
        settings["galuz_date_note"] = _strip_html(galuz_date.group(1))

    tables = re.findall(r"<table\b.*?</table>", html, re.IGNORECASE | re.DOTALL)
    entries: list[dict] = []
    if tables:
        entries.extend(
            _parse_table_rows(tables[0], FotoekspEntry.SECTION_TERRITORIAL)
        )
    if len(tables) > 1:
        entries.extend(_parse_table_rows(tables[1], FotoekspEntry.SECTION_GALUZ))

    return {"settings": settings, "entries": entries}


@lru_cache(maxsize=1)
def fotoeksp_article_joomla_ids() -> frozenset[int]:
    """Joomla article IDs linked from the fotoekspozytsiya index page."""
    from apps.pages.models import FotoekspEntry, StaticPage

    ids: set[int] = set()

    page = StaticPage.objects.filter(url_path=_FOTOEKSP_PATH).first()
    if page and FotoekspEntry.objects.filter(page=page).exists():
        for joomla_id in (
            FotoekspEntry.objects.filter(page=page, article__isnull=False)
            .values_list("article__joomla_id", flat=True)
        ):
            if joomla_id:
                ids.add(joomla_id)
    elif page and page.body:
        for href in re.findall(r'href=["\']([^"\']+)["\']', page.body):
            match = _ARTICLE_ID_IN_HREF.search(href)
            if match:
                ids.add(int(match.group(1)))

    # Broken relative Joomla link for Dnipropetrovsk oblast exhibition
    ids.add(25879)
    return frozenset(ids)


def is_fotoeksp_article(article) -> bool:
    """True when article belongs to the fotoekspozytsiya exhibition."""
    if not article or not article.joomla_id:
        return False
    if article.category and article.category.path == "fotovystavka-2024":
        return True
    return article.joomla_id in fotoeksp_article_joomla_ids()


def _strip_inline_styles(html: str, tags: tuple[str, ...]) -> str:
    for tag in tags:
        html = re.sub(
            rf"(<{tag}\b[^>]*)\s+style=\"[^\"]*\"",
            r"\1",
            html,
            flags=re.IGNORECASE,
        )
    return html


def _fix_joomla_table_head(html: str) -> str:
    """Move data rows out of thead — Joomla exports all rows inside thead."""
    def fix_one_table(match: re.Match[str]) -> str:
        table_html = match.group(0)
        if "<tbody" in table_html.lower():
            return table_html
        thead_match = re.search(r"<thead>(.*?)</thead>", table_html, re.IGNORECASE | re.DOTALL)
        if not thead_match:
            return table_html
        rows = re.findall(r"<tr\b.*?</tr>", thead_match.group(1), re.IGNORECASE | re.DOTALL)
        if len(rows) <= 1:
            return table_html
        header = rows[0]
        body = "".join(rows[1:])
        replacement = f"<thead>{header}</thead><tbody>{body}</tbody>"
        return table_html.replace(thead_match.group(0), replacement, 1)

    return re.sub(
        r'<table class="fotoeksp-table".*?</table>',
        fix_one_table,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )


def prepare_fotoeksp_html(html: str) -> str:
    """Normalize imported Joomla HTML for the fotoekspozytsiya layout."""
    if not html:
        return html

    html = rewrite_joomla_body_html(html)
    html = _strip_inline_styles(html, ("table", "thead", "tbody", "tr", "td", "th", "p", "span"))
    html = re.sub(r"<table\b", '<div class="fotoeksp-table-wrap"><table class="fotoeksp-table"', html)
    html = re.sub(r"</table>", "</table></div>", html)
    html = _fix_joomla_table_head(html)

    html = re.sub(
        r"<p>\s*(?:<span>\s*)?ТЕРИТОРІАЛЬНІ",
        '<p id="fotoeksp-teritorial">ТЕРИТОРІАЛЬНІ',
        html,
        count=1,
    )
    html = re.sub(
        r"<p>\s*(?:<span>\s*)?ВСЕУКРАЇНСЬКІ",
        '<p id="fotoeksp-galuz">ВСЕУКРАЇНСЬКІ',
        html,
        count=1,
    )
    return html
