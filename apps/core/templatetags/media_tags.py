"""Template filters for local Joomla media paths."""
from __future__ import annotations

from django import template
from django.utils.safestring import SafeString, mark_safe

from apps.core.media_utils import rewrite_joomla_body_html
from apps.pages.fotoekspozytsiya import prepare_fotoeksp_html

register = template.Library()


@register.simple_tag
def article_listing_url(article, menu_path: str) -> str:
    """Article URL under menu path (Joomla blog layout)."""
    return article.get_listing_url(menu_path)


@register.filter(name="local_media_body")
def local_media_body(html: str) -> SafeString:
    """Rewrite fpsu.org.ua links and images in HTML for local site."""
    return mark_safe(rewrite_joomla_body_html(html or ""))


@register.filter(name="fotoeksp_body")
def fotoeksp_body(html: str) -> SafeString:
    """Prepare fotoekspozytsiya page HTML (links, images, tables)."""
    return mark_safe(prepare_fotoeksp_html(html or ""))
