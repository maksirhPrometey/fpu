"""Fetch and parse spo.fpsu.org.ua homepage blocks."""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from html import unescape
from typing import Any

from apps.core.youtube import extract_youtube_id, youtube_embed_url, youtube_watch_url

_BASE = "https://spo.fpsu.org.ua/"
_UA = "Mozilla/5.0 (compatible; FPSU-mirror-sync/1.0)"


def _fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def _plain(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return unescape(re.sub(r"\s+", " ", text)).strip()


def fetch_spo_homepage() -> dict[str, list[dict[str, Any]]]:
    """Return news, videos, gallery, partners from the live SPO homepage."""
    html = _fetch(_BASE)

    news: list[dict[str, Any]] = []
    for article in re.findall(r'<article id="post-\d+".*?</article>', html, re.DOTALL):
        date_match = re.search(r'entry-time">([^<]+)', article)
        title_match = re.search(
            r'entry-header">\s*<a href="([^"]+)"[^>]*>(.*?)</a>',
            article,
            re.DOTALL,
        )
        excerpt_match = re.search(r'class="entry-text">\s*(.*?)\s*</div>', article, re.DOTALL)
        img_match = re.search(r'<img[^>]+src="([^"]+)"', article)
        if not title_match:
            continue
        news.append({
            "date": date_match.group(1).strip() if date_match else "",
            "url": title_match.group(1).strip(),
            "title": _plain(title_match.group(2)),
            "excerpt": _plain(excerpt_match.group(1))[:500] if excerpt_match else "",
            "image_url": img_match.group(1).strip() if img_match else "",
        })

    videos: list[dict[str, Any]] = []
    for match in re.finditer(
        r'<iframe[^>]+src="(https://www\.youtube\.com/embed/[^"]+)"[^>]*title="([^"]*)"',
        html,
    ):
        video_id = extract_youtube_id(match.group(1))
        if not video_id:
            continue
        videos.append({
            "embed_url": youtube_embed_url(video_id),
            "watch_url": youtube_watch_url(video_id),
            "title": unescape(match.group(2).strip()),
        })

    gallery: list[dict[str, Any]] = []
    gallery_start = html.find("Фотогалерея")
    gallery_end = html.find('id="logos"', gallery_start if gallery_start >= 0 else 0)
    if gallery_start >= 0 and gallery_end > gallery_start:
        gallery_block = html[gallery_start:gallery_end]
        for match in re.finditer(
            r'<a[^>]+href="([^"]+)"[^>]*>\s*<img[^>]+src="([^"]+)"',
            gallery_block,
        ):
            gallery.append({
                "link": match.group(1).strip(),
                "image_url": match.group(2).strip(),
            })

    partners: list[dict[str, Any]] = []
    logos_match = re.search(r'id="logos".*?</section>', html, re.DOTALL)
    if logos_match:
        for match in re.finditer(r'<img src="([^"]+)" alt="([^"]*)"', logos_match.group(0)):
            partners.append({
                "image_url": match.group(1).strip(),
                "alt": unescape(match.group(2).strip()),
            })

    return {
        "news": news[:10],
        "videos": videos[:6],
        "gallery": gallery[:12],
        "partners": partners[:12],
    }
