"""Tests for fotoekspozytsiya admin section."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.news.models import Article, Category
from apps.pages.fotoekspozytsiya import fotoeksp_albums_queryset, get_fotoeksp_page
from apps.pages.models import FotoekspSettings, StaticPage


class FotoekspAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@test.local",
            password="testpass12345",
        )
        cls.cat = Category.objects.create(
            joomla_id=281,
            alias="fotovystavka-2024",
            title="Фотовиставка 2024",
            path="fotovystavka-2024",
        )
        cls.page = StaticPage.objects.create(
            url_path="/fotoekspozytsiya",
            title="ФОТОВИСТАВКА",
            body='<a href="/25888-donetska.html">Donetsk</a>',
            is_published=True,
        )
        cls.album = Article.objects.create(
            joomla_id=25888,
            title="04_Донецька",
            slug="04-donetska",
            category=cls.cat,
            body="<p>Photos</p>",
            is_published=True,
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.staff)

    def test_fotoeksp_page_redirects_to_edit(self):
        response = self.client.get(reverse("admin:pages_fotoeksppage_changelist"))
        page = get_fotoeksp_page()
        self.assertRedirects(
            response,
            reverse("admin:pages_fotoeksppage_change", args=[page.pk]),
        )

    def test_fotoeksp_page_form_includes_banner_fields(self):
        page = get_fotoeksp_page()
        FotoekspSettings.objects.update_or_create(
            pk=1,
            defaults={
                "eyebrow": "Експозиція 2025",
                "banner_title": "Фотовиставка",
                "banner_subtitle": "Опис",
            },
        )
        response = self.client.get(
            reverse("admin:pages_fotoeksppage_change", args=[page.pk])
        )
        self.assertContains(response, "Експозиція 2025")
        self.assertContains(response, "Банер (синя смуга зверху)")
        self.assertContains(response, "Територіальні")
        self.assertContains(response, "/fotoekspozytsiya/")

    def test_fotoeksp_page_form_saves_banner(self):
        settings = FotoekspSettings.load()
        settings.eyebrow = "Тест 2024"
        settings.banner_title = "Тестова виставка"
        settings.save()
        settings = FotoekspSettings.load()
        self.assertEqual(settings.eyebrow, "Тест 2024")
        self.assertEqual(settings.banner_title, "Тестова виставка")

    def test_fotoeksp_albums_queryset_includes_linked_album(self):
        qs = fotoeksp_albums_queryset()
        self.assertIn(self.album, qs)

    def test_fotoeksp_album_changelist_shows_album(self):
        response = self.client.get(reverse("admin:pages_fotoekspalbum_changelist"))
        self.assertContains(response, "04_Донецька")
        self.assertContains(response, "Сторінки з фото")

    def test_fotoeksp_album_edit_has_tinymce_body(self):
        response = self.client.get(
            reverse("admin:pages_fotoekspalbum_change", args=[self.album.pk])
        )
        self.assertContains(response, "Фото та текст")
        self.assertContains(response, "data-mce-conf")
        self.assertContains(response, "tinymce/tinymce.min.js")
        self.assertContains(response, "fpsuTinyMceUploadHandler")

    def test_fotoeksp_page_renders_settings_banner(self):
        FotoekspSettings.objects.update_or_create(
            pk=1,
            defaults={
                "eyebrow": "Тест 2024",
                "banner_title": "Тестова виставка",
                "banner_subtitle": "Тестовий опис",
            },
        )
        response = self.client.get("/fotoekspozytsiya/", follow=True)
        self.assertContains(response, "Тест 2024")
        self.assertContains(response, "Тестова виставка")
        self.assertContains(response, "Тестовий опис")
