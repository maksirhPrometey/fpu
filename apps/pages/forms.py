"""Admin forms for the pages app."""
from __future__ import annotations

from django import forms

from apps.news.widgets import BodyEditorWidget

from .models import FotoekspAlbum, FotoekspPage, FotoekspSettings, StaticPage


class StaticPageAdminForm(forms.ModelForm):
    """ModelForm for StaticPage with TinyMCE rich-text editor on the body field."""

    body = forms.CharField(
        widget=BodyEditorWidget(),
        required=False,
        label="Вміст сторінки",
    )

    class Meta:
        model = StaticPage
        fields = "__all__"


class FotoekspPageAdminForm(forms.ModelForm):
    """Unified form for /fotoekspozytsiya/ — banner + page intro fields."""

    eyebrow = forms.CharField(
        label="Рядок над заголовком",
        max_length=100,
        help_text="Наприклад: «Експозиція 2024»",
    )
    banner_title = forms.CharField(
        label="Заголовок банера",
        max_length=255,
    )
    banner_subtitle = forms.CharField(
        label="Опис під заголовком",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
    )
    hero_image = forms.ImageField(
        label="Зображення над списками",
        required=False,
    )
    hero_image_local = forms.CharField(
        label="Шлях до локального зображення",
        required=False,
        help_text="Якщо файл уже в media/joomla_images/ — вкажіть відносний шлях",
    )
    notice_text = forms.CharField(
        label="Попередження (червоний рядок)",
        max_length=255,
        required=False,
    )
    teritorial_date_note = forms.CharField(
        label="Підпис дати — територіальні",
        max_length=255,
        required=False,
    )
    galuz_date_note = forms.CharField(
        label="Підпис дати — галузеві",
        max_length=255,
        required=False,
    )

    class Meta:
        model = FotoekspPage
        fields = (
            "eyebrow",
            "banner_title",
            "banner_subtitle",
            "hero_image",
            "hero_image_local",
            "notice_text",
            "teritorial_date_note",
            "galuz_date_note",
            "is_published",
            "meta_title",
            "meta_description",
            "meta_keywords",
        )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        settings = FotoekspSettings.load()
        if not self.is_bound:
            self.fields["eyebrow"].initial = settings.eyebrow
            self.fields["banner_title"].initial = settings.banner_title
            self.fields["banner_subtitle"].initial = settings.banner_subtitle
            self.fields["hero_image_local"].initial = settings.hero_image_local
            self.fields["notice_text"].initial = settings.notice_text
            self.fields["teritorial_date_note"].initial = settings.teritorial_date_note
            self.fields["galuz_date_note"].initial = settings.galuz_date_note

    def save(self, commit: bool = True):
        page = super().save(commit=commit)
        settings = FotoekspSettings.load()
        settings.eyebrow = self.cleaned_data["eyebrow"]
        settings.banner_title = self.cleaned_data["banner_title"]
        settings.banner_subtitle = self.cleaned_data["banner_subtitle"]
        settings.notice_text = self.cleaned_data["notice_text"]
        settings.teritorial_date_note = self.cleaned_data["teritorial_date_note"]
        settings.galuz_date_note = self.cleaned_data["galuz_date_note"]
        settings.hero_image_local = self.cleaned_data["hero_image_local"]
        hero_file = self.cleaned_data.get("hero_image")
        if hero_file:
            settings.hero_image = hero_file
        settings.save()
        return page


class FotoekspAlbumAdminForm(forms.ModelForm):
    """TinyMCE editor for fotoeksp album pages."""

    body = forms.CharField(
        widget=BodyEditorWidget(),
        required=False,
        label="Фото та текст",
        help_text="Вставляйте фото через кнопку зображення в редакторі.",
    )

    class Meta:
        model = FotoekspAlbum
        fields = "__all__"
