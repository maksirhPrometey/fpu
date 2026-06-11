"""Fetch and import all posts from spo.fpsu.org.ua/blog/ via WordPress REST API."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from django.utils.timezone import make_aware

_API_BASE = "https://spo.fpsu.org.ua/wp-json/wp/v2/posts"
_UA = "Mozilla/5.0 (compatible; FPSU-spo-blog-sync/1.0)"
_SPO_SITE = "https://spo.fpsu.org.ua"
_PER_PAGE = 100

_SPO_IMG_RE = re.compile(
    r'(?P<attr>src|href)="(?P<url>https?://spo\.fpsu\.org\.ua/wp-content/[^"]+)"',
    re.IGNORECASE,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class SpoBlogPost:
    wp_post_id: int
    title: str
    slug: str
    summary: str
    body: str
    published_at: Any
    source_url: str
    featured_image_url: str


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _plain(html: str) -> str:
    text = _HTML_TAG_RE.sub(" ", html or "")
    return unescape(re.sub(r"\s+", " ", text)).strip()


def _parse_post(raw: dict[str, Any]) -> SpoBlogPost:
    featured_url = ""
    embedded = raw.get("_embedded") or {}
    media_items = embedded.get("wp:featuredmedia") or []
    if media_items:
        featured_url = (media_items[0].get("source_url") or "").strip()

    published = parse_datetime(raw.get("date") or "")
    if published and published.tzinfo is None:
        published = make_aware(published)

    title = _plain(raw.get("title", {}).get("rendered", ""))
    excerpt = _plain(raw.get("excerpt", {}).get("rendered", ""))
    body = raw.get("content", {}).get("rendered", "") or ""

    slug = (raw.get("slug") or slugify(title, allow_unicode=False) or f"post-{raw['id']}").strip()

    return SpoBlogPost(
        wp_post_id=int(raw["id"]),
        title=title[:255],
        slug=slug[:400],
        summary=excerpt[:500],
        body=body,
        published_at=published,
        source_url=(raw.get("link") or "").strip(),
        featured_image_url=featured_url,
    )


def fetch_all_spo_blog_posts() -> list[SpoBlogPost]:
    """Return all published posts from spo.fpsu.org.ua (newest first)."""
    posts: list[SpoBlogPost] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({
            "per_page": _PER_PAGE,
            "page": page,
            "_embed": "wp:featuredmedia",
        })
        url = f"{_API_BASE}?{query}"
        try:
            batch = _fetch_json(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 400 and page > 1:
                break
            raise
        if not batch:
            break
        for raw in batch:
            posts.append(_parse_post(raw))
        if len(batch) < _PER_PAGE:
            break
        page += 1
    return posts


def _media_subpath(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    marker = "/wp-content/uploads/"
    idx = parsed.path.find(marker)
    if idx < 0:
        name = Path(parsed.path).name or "file.bin"
        return f"spo/misc/{name}"
    rel = parsed.path[idx + len(marker) :].lstrip("/")
    return f"spo/{rel}"


def download_spo_media(url: str, *, media_root: Path | None = None) -> str:
    """Download file to MEDIA_ROOT and return relative path (e.g. spo/2026/05/x.jpg)."""
    if not url:
        return ""
    root = media_root or Path(settings.MEDIA_ROOT)
    rel = _media_subpath(url)
    dest = root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 0:
        return rel

    parsed = urllib.parse.urlsplit(url)
    safe_path = urllib.parse.quote(parsed.path, safe="/%")
    safe_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, safe_path, parsed.query, parsed.fragment))
    request = urllib.request.Request(safe_url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        dest.write_bytes(response.read())
    return rel


def rewrite_spo_body_html(html: str, *, media_root: Path | None = None) -> str:
    """Download inline spo.fpsu.org.ua media and rewrite URLs to /media/spo/…"""
    if not html:
        return html

    def _replace(match: re.Match[str]) -> str:
        attr = match.group("attr")
        url = match.group("url")
        try:
            rel = download_spo_media(url, media_root=media_root)
        except (urllib.error.URLError, TimeoutError, OSError):
            return match.group(0)
        local = f"{settings.MEDIA_URL.rstrip('/')}/{rel}"
        return f'{attr}="{local}"'

    return _SPO_IMG_RE.sub(_replace, html)


def unique_article_slug(base_slug: str, wp_post_id: int) -> str:
    """Ensure slug is unique among Article rows."""
    from apps.news.models import Article

    slug = base_slug[:400] or f"spo-post-{wp_post_id}"
    if not Article.objects.filter(slug=slug).exclude(wp_post_id=wp_post_id).exists():
        return slug
    candidate = f"{slug}-{wp_post_id}"[:400]
    if not Article.objects.filter(slug=candidate).exclude(wp_post_id=wp_post_id).exists():
        return candidate
    return f"spo-{wp_post_id}"[:400]
