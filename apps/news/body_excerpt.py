"""Extract Joomla-style listing text from article HTML bodies."""
from __future__ import annotations

import re
from html import unescape

_STRONG_RE = re.compile(r"<strong[^>]*>(.*?)</strong>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_PARTIAL_TAG_RE = re.compile(r"<[^>]*$")
_WS_RE = re.compile(r"\s+")


def _plain(html: str) -> str:
    text = _PARTIAL_TAG_RE.sub("", html or "")
    text = _TAG_RE.sub(" ", text)
    return unescape(_WS_RE.sub(" ", text)).strip()


def sanitize_listing_text(text: str, *, max_len: int = 480) -> str:
    """Plain text for blog listings — no HTML, safe truncation."""
    plain = _plain(text)
    if not plain:
        return ""
    if len(plain) <= max_len:
        return plain
    truncated = plain[: max_len - 1].rsplit(" ", 1)[0]
    return f"{truncated}…"


def listing_lead(body: str) -> str:
    """First question/heading — usually the first <strong> block."""
    match = _STRONG_RE.search(body or "")
    if match:
        lead = _plain(match.group(1))
        if lead:
            return lead
    plain = _plain(body)
    return plain[:200] if plain else ""


def listing_excerpt(body: str, *, max_len: int = 480) -> str:
    """Intro text for category blog view (question + start of answer)."""
    plain = _plain(body)
    if not plain:
        return ""

    lead = listing_lead(body)
    if lead and plain.startswith(lead):
        rest = plain[len(lead) :].strip()
        text = f"{lead} {rest}".strip() if rest else lead
    else:
        text = plain

    return sanitize_listing_text(text, max_len=max_len)
