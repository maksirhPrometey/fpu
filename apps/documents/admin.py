"""Documents admin — DocumentCategory with inline, Document with fieldsets."""
from __future__ import annotations

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from unfold.admin import ModelAdmin, TabularInline

from .models import Document, DocumentCategory


class DocumentInline(TabularInline):
    model = Document
    extra = 0
    fields = ("title", "file", "file_url", "file_type", "published_at", "order", "is_published")
    show_change_link = True


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(ModelAdmin):
    list_display = ("title", "slug", "get_doc_count", "order")
    list_editable = ("order",)
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    inlines = [DocumentInline]
    list_per_page = 50

    def get_urls(self):
        custom = [
            path(
                "go/",
                self.admin_site.admin_view(self.go_to_category),
                name="documents_documentcategory_go",
            ),
        ]
        return custom + super().get_urls()

    def go_to_category(self, request):
        """Resolve ?slug=<slug> to its change form (changelist if missing)."""
        slug = (request.GET.get("slug") or "").strip().strip("/")
        category = DocumentCategory.objects.filter(slug=slug).first()
        if category:
            return HttpResponseRedirect(
                reverse("admin:documents_documentcategory_change", args=[category.pk])
            )
        return HttpResponseRedirect(
            reverse("admin:documents_documentcategory_changelist")
        )

    fieldsets = (
        (None, {
            "fields": ("title", "slug", "description", "order"),
        }),
    )

    @admin.display(description="Документів")
    def get_doc_count(self, obj: DocumentCategory) -> int:
        return obj.documents.filter(is_published=True).count()


@admin.register(Document)
class DocumentAdmin(ModelAdmin):
    list_display = ("title", "category", "file_type", "published_at", "order", "is_published")
    list_filter = ("category", "file_type", "is_published")
    list_editable = ("order", "is_published")
    search_fields = ("title", "description")
    date_hierarchy = "published_at"
    list_select_related = ("category",)
    list_per_page = 50

    fieldsets = (
        (None, {
            "fields": ("title", "category", "published_at", "is_published", "order"),
        }),
        ("Файл", {
            "fields": ("file", "file_url", "file_type"),
        }),
        ("Додатково", {
            "fields": ("description",),
            "classes": ("collapse",),
        }),
    )
