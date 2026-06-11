"""News URL patterns — exact Joomla SEF URL compatibility.

Joomla URL structures preserved:
  /<cat_path>/<joomla_id>-<alias>.html   → article in category
  /<joomla_id>-<alias>.html              → article at root (no category path)
  /<cat_path>/                           → category listing
"""
from __future__ import annotations

from django.urls import re_path
from django.views.generic import RedirectView

from . import views

app_name = "news"

urlpatterns = [
    # Legacy Joomla SEF aliases → current category paths
    re_path(
        r"^materialy/(?P<joomla_id>\d+)-(?P<slug>[\w-]+)\.html$",
        RedirectView.as_view(url="/materiali/%(joomla_id)s-%(slug)s.html", permanent=True),
    ),
    re_path(
        r"^281-fotovystavka-2024/(?P<joomla_id>\d+)-(?P<slug>[\w-]+)\.html$",
        RedirectView.as_view(url="/fotovystavka-2024/%(joomla_id)s-%(slug)s.html", permanent=True),
    ),
    # Article inside a category path (one or more path segments)
    # e.g. /materialy/29093-vidbuvsia-xiii-forum.html
    # e.g. /pro-fpu/istoriya/123-some-article.html
    re_path(
        r"^(?P<cat_path>[\w-]+(?:/[\w-]+)*)/(?P<joomla_id>\d+)-(?P<slug>[\w-]+)\.html$",
        views.article_in_cat,
        name="article_in_cat",
    ),
    # Fallback for articles without a Joomla ID — /news/<slug>/
    re_path(
        r"^news/(?P<slug>[\w-]+)/$",
        views.article_by_slug,
        name="article_by_slug",
    ),
    # Category listing page
    # e.g. /materialy/
    re_path(
        r"^(?P<cat_path>[\w-]+(?:/[\w-]+)*)/$",
        views.category_list,
        name="category_list",
    ),
]
