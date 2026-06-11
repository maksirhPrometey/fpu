"""CMS static pages — mirrors Joomla menu/article pages."""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.news.models import Article


class StaticPage(models.Model):
    """A static content page sourced from Joomla menu or standalone article."""

    url_path = models.CharField(
        _("URL-шлях"),
        max_length=500,
        unique=True,
        help_text=_("Наприклад: /pro-fpu/istoriya-fpu або /276-cherhovyi-den.html"),
    )
    title = models.CharField(_("Заголовок"), max_length=255)
    meta_title = models.CharField(
        _("SEO заголовок"),
        max_length=255,
        blank=True,
        help_text=_("Якщо порожньо — використовується Заголовок"),
    )
    meta_description = models.CharField(_("Meta description"), max_length=500, blank=True)
    meta_keywords = models.CharField(_("Meta keywords"), max_length=500, blank=True)
    body = models.TextField(_("Вміст сторінки"), blank=True)
    is_published = models.BooleanField(_("Опублікована"), default=True)

    # Joomla reference
    joomla_id = models.IntegerField(_("Joomla menu/article ID"), null=True, blank=True)
    joomla_type = models.CharField(
        _("Тип Joomla"),
        max_length=50,
        blank=True,
        help_text=_("menu | article"),
    )

    class Meta:
        verbose_name = _("Статична сторінка")
        verbose_name_plural = _("Статичні сторінки")
        ordering = ("url_path",)
        indexes = [models.Index(fields=["url_path"])]

    def __str__(self) -> str:
        return f"{self.title} ({self.url_path})"

    def get_absolute_url(self) -> str:
        path = self.url_path
        if not path.endswith("/") and not path.endswith(".html"):
            path = path + "/"
        return path

    @property
    def effective_meta_title(self) -> str:
        return self.meta_title or self.title


class FotoekspSettings(models.Model):
    """Singleton — banner texts and labels for the fotoekspozytsiya page."""

    eyebrow = models.CharField(
        _("Підзаголовок банера"),
        max_length=100,
        default="Експозиція 2024",
        help_text=_("Невеликий рядок над заголовком, напр. «Експозиція 2024»"),
    )
    banner_title = models.CharField(
        _("Заголовок банера"),
        max_length=255,
        default="Фотовиставка",
    )
    banner_subtitle = models.TextField(
        _("Опис під банером"),
        blank=True,
        default=(
            "Федерація профспілок України — діяльність на захист "
            "незалежності країни та людини праці в умовах війни"
        ),
    )
    hero_image = models.ImageField(
        _("Зображення над списками"),
        upload_to="fotoeksp/",
        blank=True,
        null=True,
    )
    hero_image_local = models.CharField(
        _("Локальне зображення"),
        max_length=500,
        blank=True,
        help_text=_("Шлях у media/joomla_images/, напр. images/2024/March/foo.jpg"),
    )
    notice_text = models.CharField(
        _("Попередження"),
        max_length=255,
        blank=True,
        default="(УВАГА!!! Експозиція поповнюється)",
        help_text=_("Червоний рядок під заголовком на сторінці"),
    )
    teritorial_date_note = models.CharField(
        _("Дата для територіальних"),
        max_length=255,
        blank=True,
        default="(станом на березень 2024 р.)",
    )
    galuz_date_note = models.CharField(
        _("Дата для галузевих"),
        max_length=255,
        blank=True,
        default="(станом на березень 2024 р.)",
    )

    class Meta:
        verbose_name = _("Налаштування фотовиставки")
        verbose_name_plural = _("Налаштування фотовиставки")

    def __str__(self) -> str:
        return str(_("Фотовиставка — оформлення"))

    def save(self, *args, **kwargs) -> None:
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> FotoekspSettings:
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def hero_image_url(self) -> str:
        from apps.core.media_utils import file_field_url, joomla_media_url

        if self.hero_image_local:
            return joomla_media_url(self.hero_image_local)
        return file_field_url(self.hero_image)


class FotoekspEntry(models.Model):
    """One row in the fotoekspozytsiya organization table."""

    SECTION_TERRITORIAL = "teritorial"
    SECTION_GALUZ = "galuz"
    SECTION_CHOICES = (
        (SECTION_TERRITORIAL, _("Територіальні об'єднання")),
        (SECTION_GALUZ, _("Галузеві профспілки")),
    )

    page = models.ForeignKey(
        StaticPage,
        verbose_name=_("Сторінка"),
        on_delete=models.CASCADE,
        related_name="fotoeksp_entries",
    )
    section = models.CharField(_("Розділ"), max_length=20, choices=SECTION_CHOICES)
    order = models.PositiveIntegerField(_("№"), default=0)
    title = models.CharField(_("Назва організації"), max_length=500)
    article = models.ForeignKey(
        Article,
        verbose_name=_("Альбом"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fotoeksp_entries",
        help_text=_("Якщо обрано — назва стає посиланням на альбом з фото"),
    )
    is_published = models.BooleanField(_("Показувати"), default=True)

    class Meta:
        verbose_name = _("Рядок списку")
        verbose_name_plural = _("Рядки списку")
        ordering = ("section", "order", "pk")
        indexes = [
            models.Index(fields=["page", "section", "order"]),
        ]

    def __str__(self) -> str:
        return f"{self.order}. {self.title[:60]}"

    @property
    def has_link(self) -> bool:
        return bool(self.article_id and self.is_published)

    @property
    def url(self) -> str:
        if self.article_id:
            return self.article.get_absolute_url()
        return ""


class FotoekspTerritorialEntry(FotoekspEntry):
    """Proxy — territorial rows for admin inline."""

    class Meta:
        proxy = True
        verbose_name = _("Територіальне об'єднання")
        verbose_name_plural = _("Територіальні об'єднання")


class FotoekspGaluzEntry(FotoekspEntry):
    """Proxy — industry union rows for admin inline."""

    class Meta:
        proxy = True
        verbose_name = _("Галузева профспілка")
        verbose_name_plural = _("Галузеві профспілки")


FOTOEKSP_URL_PATH = "/fotoekspozytsiya"


class FotoekspPage(StaticPage):
    """Proxy — сторінка /fotoekspozytsiya/."""

    class Meta:
        proxy = True
        verbose_name = _("Фотовиставка")
        verbose_name_plural = _("Фотовиставка")


class FotoekspAlbum(Article):
    """Proxy — окремі сторінки організацій з фото."""

    class Meta:
        proxy = True
        verbose_name = _("Сторінка з фото")
        verbose_name_plural = _("Сторінки з фото")
