"""Tests for fotoekspozytsiya article detection."""
from django.test import TestCase

from apps.news.models import Article, Category
from apps.pages.fotoekspozytsiya import is_fotoeksp_article


class FotoekspArticleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(
            joomla_id=281,
            alias="fotovystavka-2024",
            title="Фотовиставка 2024",
            path="fotovystavka-2024",
        )
        cls.article = Article.objects.create(
            joomla_id=25888,
            title="04_Донецька",
            slug="04-donetska",
            category=cls.cat,
            body="",
            is_published=True,
        )

    def test_fotovystavka_category_is_fotoeksp(self):
        self.assertTrue(is_fotoeksp_article(self.article))

    def test_unrelated_article_is_not_fotoeksp(self):
        other = Article.objects.create(
            joomla_id=99999,
            title="Other",
            slug="other",
            body="",
            is_published=True,
        )
        self.assertFalse(is_fotoeksp_article(other))
