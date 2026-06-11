"""Admin for /fotoekspozytsiya/ — one entry point for the whole page."""
from __future__ import annotations

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline

from apps.news import views_admin as news_views_admin
from apps.pages.fotoekspozytsiya import (
    FOTOEKSP_GALUZ_CATEGORY,
    FOTOEKSP_TERRITORIAL_CATEGORY,
    fotoeksp_albums_queryset,
    fotoeksp_section_label,
    get_fotoeksp_page,
)
from apps.pages.forms import FotoekspAlbumAdminForm, FotoekspPageAdminForm
from apps.pages.models import (
    FotoekspAlbum,
    FotoekspEntry,
    FotoekspGaluzEntry,
    FotoekspPage,
    FotoekspSettings,
    FotoekspTerritorialEntry,
)


class FotoekspSectionFilter(admin.SimpleListFilter):
    title = "Розділ виставки"
    parameter_name = "fotoeksp_section"

    def lookups(self, request, model_admin):
        return (
            ("teritorial", "Територіальні об'єднання"),
            ("galuz", "Галузеві профспілки"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "galuz":
            return queryset.filter(category__path=FOTOEKSP_GALUZ_CATEGORY)
        if value == "teritorial":
            return queryset.filter(category__path=FOTOEKSP_TERRITORIAL_CATEGORY)
        return queryset


class BaseFotoekspEntryInline(TabularInline):
    extra = 1
    fields = ("order", "title", "article", "edit_album_link", "is_published")
    readonly_fields = ("edit_album_link",)
    autocomplete_fields = ("article",)
    ordering = ("order",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "article":
            kwargs["queryset"] = fotoeksp_albums_queryset()
            kwargs["label"] = "Сторінка з фото"
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Редагувати")
    def edit_album_link(self, obj: FotoekspEntry) -> str:
        if not obj or not obj.article_id:
            return "—"
        url = reverse("admin:pages_fotoekspalbum_change", args=[obj.article_id])
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Фото →</a>',
            url,
        )


class FotoekspTerritorialInline(BaseFotoekspEntryInline):
    model = FotoekspTerritorialEntry
    verbose_name = "організацію"
    verbose_name_plural = "Територіальні об'єднання"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(section=FotoekspEntry.SECTION_TERRITORIAL)

    def get_formset(self, request, obj=None, **kwargs):
        base_formset = super().get_formset(request, obj, **kwargs)
        section = FotoekspEntry.SECTION_TERRITORIAL

        class SectionFormSet(base_formset):
            def save_new(self, form, commit=True):
                instance = super().save_new(form, commit=False)
                instance.section = section
                if commit:
                    instance.save()
                return instance

        return SectionFormSet


class FotoekspGaluzInline(BaseFotoekspEntryInline):
    model = FotoekspGaluzEntry
    verbose_name = "організацію"
    verbose_name_plural = "Галузеві профспілки"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(section=FotoekspEntry.SECTION_GALUZ)

    def get_formset(self, request, obj=None, **kwargs):
        base_formset = super().get_formset(request, obj, **kwargs)
        section = FotoekspEntry.SECTION_GALUZ

        class SectionFormSet(base_formset):
            def save_new(self, form, commit=True):
                instance = super().save_new(form, commit=False)
                instance.section = section
                if commit:
                    instance.save()
                return instance

        return SectionFormSet


@admin.register(FotoekspPage)
class FotoekspPageAdmin(ModelAdmin):
    form = FotoekspPageAdminForm
    inlines = (FotoekspTerritorialInline, FotoekspGaluzInline)

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def get_queryset(self, request):
        page = get_fotoeksp_page()
        return super().get_queryset(request).filter(pk=page.pk)

    def changelist_view(self, request, extra_context=None):
        page = get_fotoeksp_page()
        return HttpResponseRedirect(
            reverse("admin:pages_fotoeksppage_change", args=[page.pk])
        )

    def save_model(self, request, obj, form, change) -> None:
        super().save_model(request, obj, form, change)
        from apps.pages.fotoekspozytsiya import fotoeksp_article_joomla_ids

        fotoeksp_article_joomla_ids.cache_clear()

    def save_related(self, request, form, formsets, change) -> None:
        super().save_related(request, form, formsets, change)
        from apps.pages.fotoekspozytsiya import fotoeksp_article_joomla_ids

        fotoeksp_article_joomla_ids.cache_clear()

    readonly_fields = ("view_on_site_link", "albums_admin_link", "hero_image_preview")

    fieldsets = (
        (None, {
            "fields": ("view_on_site_link", "albums_admin_link", "is_published"),
            "description": "Сторінка на сайті: /fotoekspozytsiya/",
        }),
        ("Банер (синя смуга зверху)", {
            "fields": ("eyebrow", "banner_title", "banner_subtitle"),
        }),
        ("Блок над таблицями", {
            "fields": (
                "hero_image_preview",
                "hero_image",
                "hero_image_local",
                "notice_text",
                "teritorial_date_note",
                "galuz_date_note",
            ),
            "description": (
                "Зображення та підписи перед списками організацій. "
                "Списки редагуйте в таблицях нижче."
            ),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description", "meta_keywords"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Сторінка на сайті")
    def view_on_site_link(self, obj: FotoekspPage) -> str:
        return mark_safe(
            '<a href="/fotoekspozytsiya/" target="_blank" rel="noopener">'
            "Відкрити /fotoekspozytsiya/ ↗</a>"
        )

    @admin.display(description="Сторінки з фото")
    def albums_admin_link(self, obj: FotoekspPage) -> str:
        url = reverse("admin:pages_fotoekspalbum_changelist")
        return format_html(
            '<a href="{}">Редагувати сторінки організацій з фото →</a>',
            url,
        )

    @admin.display(description="Поточне зображення")
    def hero_image_preview(self, obj: FotoekspPage) -> str:
        settings = FotoekspSettings.load()
        url = settings.hero_image_url
        if not url:
            return "—"
        return format_html(
            '<img src="{}" alt="" '
            'style="max-height:180px;max-width:100%;border-radius:8px;" />',
            url,
        )


@admin.register(FotoekspAlbum)
class FotoekspAlbumAdmin(ModelAdmin):
    """Окремі сторінки організацій — галереї фото фотовиставки."""

    form = FotoekspAlbumAdminForm

    def get_urls(self):
        custom = [
            path(
                "upload-image/",
                self.admin_site.admin_view(news_views_admin.upload_image),
                name="pages_fotoekspalbum_upload_image",
            ),
        ]
        return custom + super().get_urls()

    list_display = (
        "get_cover_preview",
        "title",
        "get_section",
        "is_published",
        "order",
    )
    list_display_links = ("title",)
    list_filter = (FotoekspSectionFilter, "is_published")
    list_editable = ("is_published", "order")
    search_fields = ("title", "summary", "joomla_id")
    ordering = ("order", "title")
    list_per_page = 50
    list_select_related = ("category",)
    readonly_fields = ("joomla_id", "get_cover_preview_large", "view_on_site_link")
    autocomplete_fields = ("category",)
    prepopulated_fields = {"slug": ("title",)}

    fieldsets = (
        (None, {
            "fields": ("view_on_site_link", "title", "is_published", "order"),
            "description": (
                "Сторінка з фото організації — відкривається зі списку на "
                "/fotoekspozytsiya/."
            ),
        }),
        ("Фото та текст", {
            "fields": ("summary", "body"),
        }),
        ("Обкладинка (перше фото в списках)", {
            "fields": ("get_cover_preview_large", "image", "local_image"),
        }),
        ("Додатково", {
            "fields": ("slug", "category", "published_at"),
            "classes": ("collapse",),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description", "meta_keywords"),
            "classes": ("collapse",),
        }),
        ("Joomla (тільки читання)", {
            "fields": ("joomla_id",),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        return fotoeksp_albums_queryset()

    def save_model(self, request, obj, form, change) -> None:
        if not change and not obj.category_id:
            from apps.news.models import Category

            default_cat = Category.objects.filter(path=FOTOEKSP_TERRITORIAL_CATEGORY).first()
            if default_cat:
                obj.category = default_cat
        super().save_model(request, obj, form, change)

    @admin.display(description="Розділ")
    def get_section(self, obj: FotoekspAlbum) -> str:
        return fotoeksp_section_label(obj)

    @admin.display(description="")
    def get_cover_preview(self, obj: FotoekspAlbum) -> str:
        url = obj.image_url
        if not url:
            return "—"
        return format_html(
            '<img src="{}" alt="" '
            'style="height:44px;width:66px;object-fit:cover;border-radius:4px;" />',
            url,
        )

    @admin.display(description="Поточне зображення")
    def get_cover_preview_large(self, obj: FotoekspAlbum) -> str:
        url = obj.image_url
        if not url:
            return "—"
        return format_html(
            '<img src="{}" alt="" '
            'style="max-height:200px;max-width:100%;border-radius:8px;" />',
            url,
        )

    @admin.display(description="Переглянути")
    def view_on_site_link(self, obj: FotoekspAlbum) -> str:
        if not obj.pk:
            return "—"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Відкрити альбом на сайті ↗</a>',
            obj.get_absolute_url(),
        )
