"""Structured admin forms for SpoHomeCache JSON blocks."""
from __future__ import annotations

from django import forms
from django.forms import formset_factory

from apps.core.youtube import extract_youtube_id, youtube_embed_url, youtube_watch_url


class SpoVideoItemForm(forms.Form):
    title = forms.CharField(
        label="Назва відео",
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Наприклад: Вебінар з трудового законодавства"}),
    )
    youtube_url = forms.URLField(
        label="Посилання YouTube",
        required=False,
        widget=forms.URLInput(attrs={"placeholder": "https://www.youtube.com/watch?v=..."}),
    )


class SpoGalleryItemForm(forms.Form):
    image_url = forms.URLField(
        label="Зображення (URL)",
        required=False,
        widget=forms.URLInput(attrs={"placeholder": "https://..."}),
    )
    link = forms.URLField(
        label="Посилання (куди веде фото)",
        required=False,
        widget=forms.URLInput(attrs={"placeholder": "https://..."}),
    )


class SpoPartnerItemForm(forms.Form):
    image_url = forms.URLField(
        label="Логотип (URL)",
        required=False,
        widget=forms.URLInput(attrs={"placeholder": "https://..."}),
    )
    alt = forms.CharField(
        label="Підпис / назва",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Назва організації"}),
    )


SpoVideoFormSet = formset_factory(SpoVideoItemForm, extra=1, can_delete=True)
SpoGalleryFormSet = formset_factory(SpoGalleryItemForm, extra=1, can_delete=True)
SpoPartnerFormSet = formset_factory(SpoPartnerItemForm, extra=1, can_delete=True)


def _skip_row(data: dict) -> bool:
    return not any(str(v).strip() for k, v in data.items() if k != "DELETE")


def videos_to_initial(videos: list) -> list[dict]:
    rows = []
    for item in videos or []:
        rows.append({
            "title": item.get("title", ""),
            "youtube_url": item.get("watch_url") or item.get("embed_url", ""),
        })
    return rows or [{}]


def gallery_to_initial(gallery: list) -> list[dict]:
    rows = []
    for item in gallery or []:
        rows.append({
            "image_url": item.get("image_url", ""),
            "link": item.get("link", ""),
        })
    return rows or [{}]


def partners_to_initial(partners: list) -> list[dict]:
    rows = []
    for item in partners or []:
        rows.append({
            "image_url": item.get("image_url", ""),
            "alt": item.get("alt", ""),
        })
    return rows or [{}]


def pack_videos(formset: SpoVideoFormSet) -> list[dict]:
    result: list[dict] = []
    for form in formset:
        if not form.cleaned_data or form.cleaned_data.get("DELETE"):
            continue
        if _skip_row(form.cleaned_data):
            continue
        video_id = extract_youtube_id(form.cleaned_data.get("youtube_url", ""))
        if not video_id:
            continue
        result.append({
            "title": form.cleaned_data.get("title", "").strip(),
            "embed_url": youtube_embed_url(video_id),
            "watch_url": youtube_watch_url(video_id),
        })
    return result


def pack_gallery(formset: SpoGalleryFormSet) -> list[dict]:
    result: list[dict] = []
    for form in formset:
        if not form.cleaned_data or form.cleaned_data.get("DELETE"):
            continue
        if _skip_row(form.cleaned_data):
            continue
        image_url = form.cleaned_data.get("image_url", "").strip()
        if not image_url:
            continue
        result.append({
            "image_url": image_url,
            "link": form.cleaned_data.get("link", "").strip(),
        })
    return result


def pack_partners(formset: SpoPartnerFormSet) -> list[dict]:
    result: list[dict] = []
    for form in formset:
        if not form.cleaned_data or form.cleaned_data.get("DELETE"):
            continue
        if _skip_row(form.cleaned_data):
            continue
        image_url = form.cleaned_data.get("image_url", "").strip()
        if not image_url:
            continue
        result.append({
            "image_url": image_url,
            "alt": form.cleaned_data.get("alt", "").strip(),
        })
    return result
