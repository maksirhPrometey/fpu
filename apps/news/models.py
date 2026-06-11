"""News models — Category and Article, images stored in Cloudinary."""
from __future__ import annotations

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.media_utils import file_field_url, joomla_media_url


class Category(models.Model):
    """Joomla category mirror — one row per content category."""

    joomla_id = models.IntegerField(_("Joomla ID"), unique=True, null=True, blank=True)
    alias = models.SlugField(_("Alias"), max_length=400, unique=True, allow_unicode=True)
    title = models.CharField(_("Назва"), max_length=255)
    path = models.CharField(
        _("URL-шлях"),
        max_length=400,
        blank=True,
        help_text=_("Наприклад: materialy або pro-fpu/istoriya"),
    )
    meta_description = models.CharField(_("Meta description"), max_length=1024, blank=True)
    meta_keywords = models.CharField(_("Meta keywords"), max_length=1024, blank=True)
    is_active = models.BooleanField(_("Активна"), default=True)

    class Meta:
        verbose_name = _("Категорія")
        verbose_name_plural = _("Категорії")
        ordering = ("path", "title")
        indexes = [
            models.Index(fields=["path"]),
            models.Index(fields=["alias"]),
        ]

    def __str__(self) -> str:
        return self.title


class Article(models.Model):
    """News article — each article maps to a Joomla content item."""

    # Django-native fields
    title = models.CharField(_("Заголовок"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=400, unique=True, blank=True, allow_unicode=True)
    summary = models.CharField(_("Короткий опис"), max_length=500, blank=True)
    body = models.TextField(_("Повний текст"), blank=True)
    image = models.ImageField(_("Зображення"), upload_to="news/covers/", blank=True, null=True)
    local_image = models.CharField(
        _("Локальне зображення"),
        max_length=500,
        blank=True,
        help_text=_("Відносний шлях у media/joomla_images/, напр. images/foo.webp"),
    )
    published_at = models.DateTimeField(_("Дата публікації"), default=timezone.now)
    is_published = models.BooleanField(_("Опубліковано"), default=True)
    order = models.IntegerField(_("Ручний порядок"), default=0)

    # Joomla migration fields
    joomla_id = models.IntegerField(_("Joomla ID"), unique=True, null=True, blank=True, db_index=True)
    wp_post_id = models.IntegerField(_("WordPress ID"), unique=True, null=True, blank=True, db_index=True)
    is_spo = models.BooleanField(
        _("Новина СПО"),
        default=False,
        db_index=True,
        help_text=_("Якщо увімкнено — новина належить до розділу СПО і не показується у загальних новинах"),
    )
    source_url = models.URLField(_("Джерело (URL)"), max_length=500, blank=True)
    category = models.ForeignKey(
        Category,
        verbose_name=_("Категорія"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )

    # SEO fields (from Joomla metadesc/metakey + custom page title)
    meta_title = models.CharField(
        _("SEO заголовок (title)"),
        max_length=255,
        blank=True,
        help_text=_("Якщо порожньо — використовується поле Заголовок"),
    )
    meta_description = models.CharField(
        _("Meta description"),
        max_length=500,
        blank=True,
    )
    meta_keywords = models.CharField(
        _("Meta keywords"),
        max_length=500,
        blank=True,
    )

    class Meta:
        verbose_name = _("Новина")
        verbose_name_plural = _("Новини")
        ordering = ("-published_at", "-id")
        indexes = [
            models.Index(fields=["-published_at"]),
            models.Index(fields=["is_published"]),
            models.Index(fields=["joomla_id"]),
            models.Index(fields=["wp_post_id"]),
            models.Index(fields=["is_spo", "-published_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.title, allow_unicode=False) or "article"
            slug = base
            i = 2
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def effective_meta_title(self) -> str:
        return self.meta_title or self.title

    @property
    def display_date(self) -> str:
        return self.published_at.strftime("%d.%m.%Y")

    @property
    def display_date_ua(self) -> str:
        months = (
            "січня", "лютого", "березня", "квітня", "травня", "червня",
            "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
        )
        dt = self.published_at
        return f"{dt.day:02d} {months[dt.month - 1]} {dt.year}"

    @property
    def listing_excerpt(self) -> str:
        from apps.news.body_excerpt import listing_excerpt as extract_excerpt
        from apps.news.body_excerpt import sanitize_listing_text

        if self.summary:
            return sanitize_listing_text(self.summary)
        return extract_excerpt(self.body)

    @property
    def listing_image_url(self) -> str:
        """Intro image for blog-style category listings."""
        import os
        import re

        from django.conf import settings

        raw = self.image_url
        if not raw:
            return ""
        match = re.search(r"/images/([^/?#\"']+)", raw)
        if match:
            filename = match.group(1)
            local_path = os.path.join(settings.MEDIA_ROOT, "joomla_images", "images", filename)
            if os.path.isfile(local_path):
                return joomla_media_url(f"images/{filename}")
        return raw

    def get_listing_url(self, menu_path: str | None = None) -> str:
        if menu_path and self.joomla_id:
            return f"/{menu_path.strip('/')}/{self.joomla_id}-{self.slug}.html"
        return self.get_absolute_url()

    @property
    def image_url(self) -> str:
        if self.local_image:
            if self.local_image.startswith("spo/"):
                from django.conf import settings
                return f"{settings.MEDIA_URL.rstrip('/')}/{self.local_image.lstrip('/')}"
            return joomla_media_url(self.local_image)
        url = file_field_url(self.image)
        if url:
            return url
        if self.body:
            import re as _re
            m = _re.search(
                r'src="(/media/joomla_images/[^"]+)"',
                self.body,
            )
            if m:
                return m.group(1)
            m = _re.search(
                r'src="(https?://(?:www\.)?fpsu\.org\.ua/images/[^"]+)"',
                self.body,
            )
            if m:
                return m.group(1)
        return ""

    def get_absolute_url(self) -> str:
        """Return the canonical URL for this article."""
        if self.wp_post_id or self.is_spo:
            return f"/spo-ob-iednan-profspilok/novyny/{self.slug}/"
        if self.category and self.category.path:
            return f"/{self.category.path}/{self.joomla_id}-{self.slug}.html"
        if self.joomla_id:
            return f"/{self.joomla_id}-{self.slug}.html"
        return f"/news/{self.slug}/"


class SpoArticle(Article):
    """Proxy — новини розділу СПО (керуються окремо від загальних новин)."""

    class Meta:
        proxy = True
        verbose_name = _("Новина СПО")
        verbose_name_plural = _("Новини СПО")
