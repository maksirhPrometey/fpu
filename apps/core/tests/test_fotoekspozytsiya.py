"""Tests for fotoekspozytsiya link and image rewriting."""
from django.test import TestCase

from apps.core.media_utils import rewrite_body_html_links, rewrite_joomla_body_html
from apps.news.models import Article, Category


class RewriteBodyHtmlLinksTests(TestCase):
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
            title="04_Донецька обласна рада",
            slug="04-donetska-oblasna-rada-profesiinykh-spilok",
            category=cls.cat,
            body="<p>test</p>",
            is_published=True,
        )

    def test_fpsu_link_rewritten_to_local_article_url(self):
        html = (
            '<a href="https://www.fpsu.org.ua/281-fotovystavka-2024/'
            '25888-04-donetska-oblasna-rada-profesiinykh-spilok.html">link</a>'
        )
        out = rewrite_body_html_links(html)
        self.assertIn(
            'href="/fotovystavka-2024/25888-04-donetska-oblasna-rada-profesiinykh-spilok.html"',
            out,
        )
        self.assertNotIn("fpsu.org.ua", out)

    def test_materialy_alias_rewritten(self):
        html = (
            '<a href="https://www.fpsu.org.ua/materialy/25867-01-federatsiia.html">x</a>'
        )
        cat = Category.objects.create(
            joomla_id=59,
            alias="materiali",
            title="Матеріали",
            path="materiali",
        )
        Article.objects.create(
            joomla_id=25867,
            title="01_Вінниця",
            slug="01-federatsiia",
            category=cat,
            body="",
            is_published=True,
        )
        out = rewrite_body_html_links(html)
        self.assertIn('href="/materiali/25867-01-federatsiia.html"', out)

    def test_joomla_body_combines_links_and_images(self):
        html = (
            '<img src="https://www.fpsu.org.ua/images/images/2024/March/lg.jpg">'
            '<a href="https://www.fpsu.org.ua/281-fotovystavka-2024/'
            '25888-04-donetska-oblasna-rada-profesiinykh-spilok.html">x</a>'
        )
        out = rewrite_joomla_body_html(html)
        self.assertIn("/media/joomla_images/", out)
        self.assertIn("/fotovystavka-2024/25888-", out)
