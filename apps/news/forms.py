"""Admin forms for the news app."""
from __future__ import annotations

from django import forms

from .models import Article, SpoArticle
from .widgets import BodyEditorWidget


class ArticleAdminForm(forms.ModelForm):
    """ModelForm for Article with TinyMCE rich-text editor on the body field."""

    body = forms.CharField(
        widget=BodyEditorWidget(),
        required=False,
        label="Повний текст",
    )

    class Meta:
        model = Article
        fields = "__all__"


class SpoArticleAdminForm(forms.ModelForm):
    """ModelForm for SPO news with TinyMCE rich-text editor on the body field."""

    body = forms.CharField(
        widget=BodyEditorWidget(),
        required=False,
        label="Повний текст",
    )

    class Meta:
        model = SpoArticle
        fields = "__all__"
