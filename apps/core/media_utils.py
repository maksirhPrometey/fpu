"""Helpers for building local media URLs."""
from __future__ import annotations

import re

from django.conf import settings

_STYLE_ATTR_RE = re.compile(r"""\sstyle=(["'])[^"']*\1""", re.IGNORECASE)
_EMPTY_PARAGRAPH_RE = re.compile(r"<p>\s*(?:&nbsp;|\u00a0|\s)*</p>", re.IGNORECASE)
_SPAN_TAG_RE = re.compile(r"<span(?:\s[^>]*)?>(.*?)</span>", re.IGNORECASE | re.DOTALL)
_BOLD_TAG_RE = re.compile(r"<b>(.*?)</b>", re.IGNORECASE | re.DOTALL)
_TRAILING_BR_RE = re.compile(r"<br\s*/?>\s*(?=</p>)", re.IGNORECASE)
_PDF_LABEL_RE = re.compile(r"\s*\(у\s*pdf\)", re.IGNORECASE)
_EMPTY_LINK_PARAGRAPH_RE = re.compile(
    r"<p>\s*<a[^>]*>\s*(?:<br\s*/?>\s*)*</a>\s*</p>",
    re.IGNORECASE,
)

_FPSU_IMAGES_RE = re.compile(
    r'(?P<attr>src|href)=["\']https?://(?:www\.)?fpsu\.org\.ua/images/',
    re.IGNORECASE,
)
_REL_IMAGES_RE = re.compile(
    r'(?P<attr>src|href)=["\']/images/',
)
_BARE_IMAGES_RE = re.compile(
    r'(?P<attr>src|href)=["\']images/',
)

_FPSU_HREF_RE = re.compile(
    r'href=(["\'])https?://(?:www\.)?fpsu\.org\.ua(/[^"\']*)\1',
    re.IGNORECASE,
)
_ARTICLE_PATH_ID_RE = re.compile(r"/(\d+)-[\w-]+\.html$")

_LEGACY_CAT_PATHS = {
    "materialy": "materiali",
    "281-fotovystavka-2024": "fotovystavka-2024",
}

_BROKEN_RELATIVE_HREFS = {
    "03_Дніпропетровське%20обласне%20об'єднання%20профспілок": 25879,
}


def _media_images_base() -> str:
    return f"{settings.MEDIA_URL.rstrip('/')}/joomla_images/images/"


def joomla_media_url(relative: str) -> str:
    """Return /media/joomla_images/… for a relative Joomla image path."""
    if not relative:
        return ""
    rel = relative.strip().lstrip("/")
    if rel.startswith("media/"):
        rel = rel[len("media/") :]
    if not rel.startswith("joomla_images/"):
        rel = f"joomla_images/{rel}"
    return f"{settings.MEDIA_URL.rstrip('/')}/{rel}"


def file_field_url(field) -> str:
    """Safe URL for a FileField/ImageField (empty string on missing file)."""
    if not field:
        return ""
    try:
        return field.url
    except Exception:
        return ""


def rewrite_body_html_images(html: str) -> str:
    """Rewrite Joomla image URLs in HTML bodies to local /media/joomla_images/ paths."""
    if not html:
        return html
    base = _media_images_base()
    html = _FPSU_IMAGES_RE.sub(rf'\g<attr>="{base}', html)
    html = _REL_IMAGES_RE.sub(rf'\g<attr>="{base}', html)
    html = _BARE_IMAGES_RE.sub(rf'\g<attr>="{base}', html)
    return html


def _article_url_for_joomla_id(jid: int, cache: dict[int, str]) -> str:
    if jid not in cache:
        from apps.news.models import Article

        article = Article.objects.filter(joomla_id=jid, is_published=True).first()
        cache[jid] = article.get_absolute_url() if article else ""
    return cache[jid]


def _rewrite_legacy_path(path: str) -> str:
    for old, new in _LEGACY_CAT_PATHS.items():
        prefix = f"/{old}/"
        if path.startswith(prefix):
            return f"/{new}/{path[len(prefix):]}"
    return path


def rewrite_body_html_links(html: str) -> str:
    """Rewrite fpsu.org.ua article links to local Django URLs."""
    if not html:
        return html

    id_cache: dict[int, str] = {}

    def _replace_fpsu_href(match: re.Match[str]) -> str:
        quote, path = match.group(1), match.group(2)
        id_match = _ARTICLE_PATH_ID_RE.search(path)
        if id_match:
            local_url = _article_url_for_joomla_id(int(id_match.group(1)), id_cache)
            if local_url:
                return f"href={quote}{local_url}{quote}"
        return f"href={quote}{_rewrite_legacy_path(path)}{quote}"

    html = _FPSU_HREF_RE.sub(_replace_fpsu_href, html)

    for broken_href, jid in _BROKEN_RELATIVE_HREFS.items():
        local_url = _article_url_for_joomla_id(jid, id_cache)
        if local_url:
            html = html.replace(f'href="{broken_href}"', f'href="{local_url}"')

    return html


def normalize_legacy_body_html(html: str) -> str:
    """Strip Joomla inline styles and redundant wrappers from imported HTML."""
    if not html:
        return html
    html = _STYLE_ATTR_RE.sub("", html)
    prev = None
    while prev != html:
        prev = html
        html = _SPAN_TAG_RE.sub(r"\1", html)
    html = _EMPTY_PARAGRAPH_RE.sub("", html)
    html = _EMPTY_LINK_PARAGRAPH_RE.sub("", html)
    html = _BOLD_TAG_RE.sub(r"\1", html)
    html = _TRAILING_BR_RE.sub("", html)
    html = _PDF_LABEL_RE.sub("", html)
    return html.strip()


def rewrite_joomla_body_html(html: str) -> str:
    """Rewrite Joomla image and internal article links for local site."""
    html = normalize_legacy_body_html(html)
    html = rewrite_body_html_links(html)
    return rewrite_body_html_images(html)
