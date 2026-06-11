"""Documents URL patterns."""
from __future__ import annotations

from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "documents"

urlpatterns = [
    path("dokumenti-fpu", RedirectView.as_view(url="/documents/", permanent=True)),
    path("dokumenti-fpu/", views.legacy_index, name="legacy_document_index"),
    path("dokumenti-fpu/<slug:legacy_slug>/", views.legacy_category, name="legacy_document_category"),
    path("documents/", views.document_index, name="document_index"),
    path("documents/<slug:slug>/", views.category_detail, name="category_detail"),
]
