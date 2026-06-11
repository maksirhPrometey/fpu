"""News admin — Category and Article with image previews."""
from __future__ import annotations

from django.contrib import admin
from django.urls import path
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from apps.pages.section_hubs import (
    article_content_links,
    article_uses_content_panel,
    render_admin_content_panel,
)

from . import views_admin
from .forms import ArticleAdminForm, SpoArticleAdminForm
from .models import Article, Category, SpoArticle


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("title", "path", "article_count", "joomla_id", "is_active")
    list_filter = ("is_active",)
    list_editable = ("is_active",)
    search_fields = ("title", "alias", "path")
    ordering = ("path",)
    list_per_page = 50

    fieldsets = (
        (None, {
            "fields": ("title", "alias", "path", "is_active"),
        }),
        ("SEO", {
            "fields": ("meta_description", "meta_keywords"),
            "classes": ("collapse",),
        }),
        ("Joomla", {
            "fields": ("joomla_id",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Статей")
    def article_count(self, obj: Category) -> int:
        return obj.articles.filter(is_published=True).count()


@admin.register(Article)
class ArticleAdmin(ModelAdmin):
    form = ArticleAdminForm

    def get_urls(self):
        custom = [
            path(
                "upload-image/",
                self.admin_site.admin_view(views_admin.upload_image),
                name="news_article_upload_image",
            ),
        ]
        return custom + super().get_urls()

    def get_queryset(self, request):
        """Загальні новини — без новин розділу СПО (вони редагуються окремо)."""
        return super().get_queryset(request).filter(is_spo=False)

    list_display = (
        "get_cover_preview",
        "title",
        "category",
        "published_at",
        "is_published",
    )
    list_filter = (
        "is_published",
        ("published_at", admin.DateFieldListFilter),
        "category",
    )
    list_editable = ("is_published",)
    search_fields = ("title", "summary", "joomla_id")
    date_hierarchy = "published_at"
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-published_at",)
    autocomplete_fields = ("category",)
    list_per_page = 50
    list_select_related = ("category",)
    readonly_fields = ("joomla_id", "wp_post_id", "source_url", "get_cover_preview_large")

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and article_uses_content_panel(obj):
            fields.append("related_content_panel")
        return fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if obj and article_uses_content_panel(obj):
            fieldsets = [fs for fs in fieldsets if fs[0] != "Вміст"]
            fieldsets.insert(
                1,
                (
                    "Контент",
                    {
                        "fields": ("related_content_panel",),
                        "description": "Оберіть елемент для редагування його контенту.",
                    },
                ),
            )
        return fieldsets

    fieldsets = (
        (None, {
            "fields": ("title", "slug", "category", "published_at", "is_published"),
        }),
        ("Вміст", {
            "fields": ("summary", "body"),
        }),
        ("Зображення", {
            "fields": ("get_cover_preview_large", "image", "local_image"),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description", "meta_keywords"),
            "classes": ("collapse",),
        }),
        ("Джерело / Joomla (тільки читання)", {
            "fields": ("source_url", "joomla_id", "wp_post_id"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Контент")
    def related_content_panel(self, obj: Article) -> str:
        return render_admin_content_panel(article_content_links(obj))

    @admin.display(description="")
    def get_cover_preview(self, obj: Article) -> str:
        url = obj.image_url
        if not url:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height:44px;width:66px;object-fit:cover;border-radius:4px;" />',
            url,
        )

    @admin.display(description="Поточне зображення")
    def get_cover_preview_large(self, obj: Article) -> str:
        url = obj.image_url
        if not url:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="max-height:200px;max-width:100%;border-radius:8px;" />',
            url,
        )


@admin.register(SpoArticle)
class SpoArticleAdmin(ModelAdmin):
    """Новини розділу СПО — окремо від загальних новин."""

    form = SpoArticleAdminForm

    def get_urls(self):
        custom = [
            path(
                "upload-image/",
                self.admin_site.admin_view(views_admin.upload_image),
                name="news_spoarticle_upload_image",
            ),
        ]
        return custom + super().get_urls()

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_spo=True)

    def save_model(self, request, obj, form, change) -> None:
        obj.is_spo = True
        super().save_model(request, obj, form, change)

    list_display = (
        "get_cover_preview",
        "title",
        "published_at",
        "is_published",
    )
    list_filter = (
        "is_published",
        ("published_at", admin.DateFieldListFilter),
    )
    list_editable = ("is_published",)
    search_fields = ("title", "summary", "body")
    date_hierarchy = "published_at"
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-published_at",)
    list_per_page = 50
    readonly_fields = ("wp_post_id", "source_url", "get_cover_preview_large")

    fieldsets = (
        (None, {
            "fields": ("title", "slug", "published_at", "is_published"),
            "description": "Новини відображаються в розділі /spo-ob-iednan-profspilok/novyny/.",
        }),
        ("Вміст", {
            "fields": ("summary", "body"),
        }),
        ("Зображення", {
            "fields": ("get_cover_preview_large", "image", "local_image"),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description", "meta_keywords"),
            "classes": ("collapse",),
        }),
        ("Джерело / WordPress (тільки читання)", {
            "fields": ("source_url", "wp_post_id"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="")
    def get_cover_preview(self, obj: SpoArticle) -> str:
        url = obj.image_url
        if not url:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height:44px;width:66px;object-fit:cover;border-radius:4px;" />',
            url,
        )

    @admin.display(description="Поточне зображення")
    def get_cover_preview_large(self, obj: SpoArticle) -> str:
        url = obj.image_url
        if not url:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="max-height:200px;max-width:100%;border-radius:8px;" />',
            url,
        )
