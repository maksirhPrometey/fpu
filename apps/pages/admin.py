"""Pages admin — StaticPage with fieldsets and readonly Joomla fields."""
from __future__ import annotations

from urllib.parse import urlencode

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from apps.core.nav import NAV_SECTIONS
from apps.news import views_admin as news_views_admin
from apps.pages.menu_news import news_category_for_menu_path
from apps.pages.section_hubs import (
    page_content_links,
    render_admin_content_panel,
    uses_content_panel,
)

from .forms import StaticPageAdminForm
from .models import StaticPage

# Register fotoekspozytsiya admins (separate sidebar section via UNFOLD).
from . import admin_fotoeksp  # noqa: F401

_NEWS_CATEGORY_BODY_WARNING = (
    "⚠️ Ця сторінка відображає стрічку новин відповідної категорії. "
    "Поле «Вміст» НЕ показується відвідувачам — воно не має ефекту. "
    "Редагуйте лише Заголовок та SEO-поля."
)

def _section_choices() -> list[tuple[str, str]]:
    """Top-level site sections derived from the site navigation."""
    seen: dict[str, str] = {}
    for section in NAV_SECTIONS:
        segment = section["url"].strip("/").split("/")[0]
        if segment and segment not in seen:
            seen[segment] = str(section["label"])
    return list(seen.items())


def _is_news_category_page(url_path: str) -> bool:
    """Return True when this StaticPage URL is handled by the news category view."""
    clean = url_path.strip("/").removesuffix(".html")
    return bool(news_category_for_menu_path(clean))


class SiteSectionFilter(admin.SimpleListFilter):
    """Filter static pages by the top-level site section of their url_path."""

    title = "Розділ сайту"
    parameter_name = "section"

    def lookups(self, request, model_admin):
        choices = _section_choices()
        choices.append(("other", "Інші / окремі сторінки"))
        return choices

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        if value == "other":
            for segment, _label in _section_choices():
                queryset = queryset.exclude(url_path__startswith=f"/{segment}")
            return queryset
        return queryset.filter(url_path__startswith=f"/{value}")


class PageTypeFilter(admin.SimpleListFilter):
    """Filter by page display type — static body vs news-category feed."""

    title = "Тип відображення"
    parameter_name = "page_type"

    def lookups(self, request, model_admin):
        return [
            ("static", "Статична сторінка"),
            ("news_cat", "Список новин категорії"),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        from apps.pages.menu_news import MENU_TO_NEWS_CATEGORY
        news_url_paths = [f"/{k}" for k in MENU_TO_NEWS_CATEGORY]
        if value == "news_cat":
            q = queryset.none()
            for p in news_url_paths:
                q = q | queryset.filter(url_path__in=[p, p + "/", p + ".html"])
            return q
        if value == "static":
            for p in news_url_paths:
                queryset = queryset.exclude(url_path__in=[p, p + "/", p + ".html"])
            return queryset
        return queryset


@admin.register(StaticPage)
class StaticPageAdmin(ModelAdmin):
    form = StaticPageAdminForm
    view_on_site = True

    def get_urls(self):
        custom = [
            path(
                "go/",
                self.admin_site.admin_view(self.go_to_page),
                name="pages_staticpage_go",
            ),
            path(
                "upload-image/",
                self.admin_site.admin_view(news_views_admin.upload_image),
                name="pages_staticpage_upload_image",
            ),
        ]
        return custom + super().get_urls()

    def go_to_page(self, request):
        """Resolve ?path=<url_path> to its change form (prefilled add if missing)."""
        raw = (request.GET.get("path") or "").strip()
        if raw and not raw.startswith("/"):
            raw = f"/{raw}"
        candidate = raw.rstrip("/") or raw

        page = (
            StaticPage.objects.filter(url_path=candidate).first()
            or StaticPage.objects.filter(url_path=f"{candidate}.html").first()
            or StaticPage.objects.filter(url_path=f"{candidate}/").first()
        )
        if page:
            return HttpResponseRedirect(
                reverse("admin:pages_staticpage_change", args=[page.pk])
            )
        add_url = reverse("admin:pages_staticpage_add")
        query = urlencode({"url_path": candidate, "title": request.GET.get("title", "")})
        return HttpResponseRedirect(f"{add_url}?{query}")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and _is_news_category_page(obj.url_path):
            form.base_fields["body"].help_text = _NEWS_CATEGORY_BODY_WARNING
        return form

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and uses_content_panel(obj.url_path, obj.body):
            fields.append("related_pages_panel")
        return fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if obj and uses_content_panel(obj.url_path, obj.body):
            fieldsets = [fs for fs in fieldsets if fs[0] != "Вміст"]
            fieldsets.insert(
                1,
                (
                    "Контент",
                    {
                        "fields": ("related_pages_panel",),
                        "description": "Оберіть елемент для редагування його контенту.",
                    },
                ),
            )
        return fieldsets

    list_display = ("title", "url_path", "page_type_badge", "is_published", "joomla_type")
    list_filter = (SiteSectionFilter, PageTypeFilter, "is_published", "joomla_type")
    list_editable = ("is_published",)
    search_fields = ("title", "url_path", "body")
    ordering = ("url_path",)
    list_per_page = 100
    readonly_fields = ("joomla_id", "joomla_type")

    fieldsets = (
        (None, {
            "fields": ("url_path", "title", "is_published"),
            "description": (
                "URL-шлях має починатися з /. "
                "Сторінки-стрічки новин (Напрями діяльності тощо) — "
                "заголовок і SEO впливають на сайт, вміст — ні."
            ),
        }),
        ("Вміст", {
            "fields": ("body",),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description", "meta_keywords"),
            "classes": ("collapse",),
        }),
        ("Joomla (тільки читання)", {
            "fields": ("joomla_id", "joomla_type"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Контент")
    def related_pages_panel(self, obj: StaticPage) -> str:
        return render_admin_content_panel(page_content_links(obj.url_path, obj.body))

    @admin.display(description="Тип")
    def page_type_badge(self, obj: StaticPage) -> str:
        if _is_news_category_page(obj.url_path):
            return format_html(
                '<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;'
                'border-radius:999px;font-size:0.75rem;font-weight:600;">'
                "Список новин</span>"
            )
        return format_html(
            '<span style="background:#dcfce7;color:#166534;padding:2px 8px;'
            'border-radius:999px;font-size:0.75rem;font-weight:600;">'
            "Статична</span>"
        )
