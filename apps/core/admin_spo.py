"""SPO homepage admin — structured forms instead of raw JSON."""
from __future__ import annotations

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin

from apps.core.models import SpoHomeCache
from apps.core.spo_home_forms import (
    SpoGalleryFormSet,
    SpoPartnerFormSet,
    SpoVideoFormSet,
    gallery_to_initial,
    pack_gallery,
    pack_partners,
    pack_videos,
    partners_to_initial,
    videos_to_initial,
)


@admin.register(SpoHomeCache)
class SpoHomeCacheAdmin(ModelAdmin):
    change_form_template = "admin/core/spohomecache/change_form.html"

    readonly_fields = ("synced_at", "sync_controls", "spo_news_panel")

    fieldsets = (
        (None, {
            "fields": ("sync_controls", "synced_at"),
            "description": (
                "Блоки головної сторінки /spo-ob-iednan-profspilok/. "
                "Новини беруться з розділу «Новини СПО»; нижче — відео, галерея та партнери."
            ),
        }),
        ("Новини", {
            "fields": ("spo_news_panel",),
        }),
    )

    class Media:
        css = {"all": ("admin/css/spo_home_admin.css",)}

    def has_add_permission(self, request) -> bool:
        return not SpoHomeCache.objects.exists()

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SpoHomeCache.load()
        return HttpResponseRedirect(
            reverse("admin:core_spohomecache_change", args=[obj.pk])
        )

    def get_urls(self):
        custom = [
            path(
                "sync/",
                self.admin_site.admin_view(self.sync_now),
                name="core_spohomecache_sync",
            ),
        ]
        return custom + super().get_urls()

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id) or SpoHomeCache.load()

        if request.method == "POST":
            video_fs = SpoVideoFormSet(request.POST, prefix="videos")
            gallery_fs = SpoGalleryFormSet(request.POST, prefix="gallery")
            partner_fs = SpoPartnerFormSet(request.POST, prefix="partners")
            formsets = (video_fs, gallery_fs, partner_fs)

            if all(fs.is_valid() for fs in formsets):
                obj.videos = pack_videos(video_fs)
                obj.gallery = pack_gallery(gallery_fs)
                obj.partners = pack_partners(partner_fs)
                obj.save()
                self.message_user(request, "Блоки СПО збережено.", level=messages.SUCCESS)
                return HttpResponseRedirect(
                    reverse("admin:core_spohomecache_change", args=[obj.pk])
                )
        else:
            video_fs = SpoVideoFormSet(initial=videos_to_initial(obj.videos), prefix="videos")
            gallery_fs = SpoGalleryFormSet(initial=gallery_to_initial(obj.gallery), prefix="gallery")
            partner_fs = SpoPartnerFormSet(initial=partners_to_initial(obj.partners), prefix="partners")

        extra_context.update({
            "video_formset": video_fs,
            "gallery_formset": gallery_fs,
            "partner_formset": partner_fs,
            "spo_site_url": "/spo-ob-iednan-profspilok/",
        })
        return super().changeform_view(request, object_id, form_url, extra_context)

    def sync_now(self, request):
        from django.utils import timezone

        from apps.core.spo_live_sync import fetch_spo_homepage

        obj = SpoHomeCache.load()
        try:
            data = fetch_spo_homepage()
            obj.news = data["news"]
            obj.videos = data["videos"]
            obj.gallery = data["gallery"]
            obj.partners = data["partners"]
            obj.synced_at = timezone.now()
            obj.save()
            self.message_user(
                request,
                f"Синхронізовано: {len(obj.news)} новин, {len(obj.videos)} відео, "
                f"{len(obj.gallery)} фото, {len(obj.partners)} партнерів.",
                level=messages.SUCCESS,
            )
        except Exception as exc:  # noqa: BLE001
            self.message_user(
                request,
                f"Помилка синхронізації зі spo.fpsu.org.ua: {exc}",
                level=messages.ERROR,
            )
        return HttpResponseRedirect(
            reverse("admin:core_spohomecache_change", args=[obj.pk])
        )

    @admin.display(description="Синхронізація зі spo.fpsu.org.ua")
    def sync_controls(self, obj: SpoHomeCache) -> str:
        if not obj or not obj.pk:
            return "—"
        url = reverse("admin:core_spohomecache_sync")
        return mark_safe(
            '<a href="{url}" style="display:inline-block;background:#0284c7;color:#fff;'
            'padding:8px 14px;border-radius:8px;text-decoration:none;font-weight:500;">'
            "↻ Синхронізувати з spo.fpsu.org.ua</a>".format(url=url)
        )

    @admin.display(description="Новини на головній")
    def spo_news_panel(self, obj: SpoHomeCache) -> str:
        from apps.news.models import Article

        count = Article.objects.filter(is_spo=True, is_published=True).count()
        url = reverse("admin:news_spoarticle_changelist")
        style = (
            "display:flex;align-items:center;justify-content:space-between;"
            "padding:10px 14px;border-radius:8px;background:#1e293b;"
            "border:1px solid #334155;text-decoration:none;color:#e2e8f0;font-weight:500;"
        )
        return format_html(
            '<a href="{url}" style="{style}">'
            "<span>Новини СПО ({count} опублікованих)</span>"
            '<span style="color:#38bdf8;font-size:0.85rem;">Редагувати →</span>'
            "</a>",
            url=url,
            style=style,
            count=count,
        )
