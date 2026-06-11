"""Tests for fotoeksp HTML import and structured rendering."""
from django.test import Client, TestCase

from apps.news.models import Article, Category
from apps.pages.fotoekspozytsiya import import_fotoeksp_from_html
from apps.pages.models import FotoekspEntry, FotoekspSettings, StaticPage


SAMPLE_BODY = """
<p><img src="/media/joomla_images/images/images/2024/March/220324/lg_220324_02.jpg" /></p>
<p><span style="color: #ff0000;">(УВАГА!!! Експозиція поповнюється)</span></p>
<p>ТЕРИТОРІАЛЬНІ ОБ'ЄДНАННЯ ПРОФСПІЛОК</p>
<p><em>(станом на березень 2024 р.)</em></p>
<table>
<tr><td>№</td><td>Назва</td></tr>
<tr><td>1.</td><td><a href="/fotovystavka-2024/25888-04-donetska.html">Донецька обласна рада</a></td></tr>
<tr><td>2.</td><td><span>Волинська область</span></td></tr>
</table>
<p>ВСЕУКРАЇНСЬКІ ГАЛУЗЕВІ ПРОФСПІЛКИ</p>
<p><em>(станом на квітень 2024 р.)</em></p>
<table>
<tr><td>№</td><td>Назва</td></tr>
<tr><td>1.</td><td><a href="/materiali/25900-test.html">Галузева профспілка</a></td></tr>
</table>
"""


class ImportFotoekspHtmlTests(TestCase):
    def test_parses_settings_and_entries(self):
        data = import_fotoeksp_from_html(SAMPLE_BODY)
        self.assertIn("images/images/2024/March/220324/lg_220324_02.jpg", data["settings"]["hero_image_local"])
        self.assertIn("УВАГА", data["settings"]["notice_text"])
        self.assertEqual(len(data["entries"]), 3)
        self.assertEqual(data["entries"][0]["section"], FotoekspEntry.SECTION_TERRITORIAL)
        self.assertEqual(data["entries"][0]["joomla_id"], 25888)
        self.assertIsNone(data["entries"][1]["joomla_id"])
        self.assertEqual(data["entries"][2]["section"], FotoekspEntry.SECTION_GALUZ)


class FotoekspStructuredRenderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = StaticPage.objects.create(
            url_path="/fotoekspozytsiya",
            title="ФОТОВИСТАВКА",
            body="legacy",
            is_published=True,
        )
        cls.cat = Category.objects.create(
            joomla_id=281,
            alias="fotovystavka-2024",
            title="Фотовиставка",
            path="fotovystavka-2024",
        )
        cls.article = Article.objects.create(
            joomla_id=25888,
            title="Донецька",
            slug="04-donetska",
            category=cls.cat,
            is_published=True,
        )
        FotoekspSettings.objects.update_or_create(
            pk=1,
            defaults={"notice_text": "Тестове попередження"},
        )
        FotoekspEntry.objects.create(
            page=cls.page,
            section=FotoekspEntry.SECTION_TERRITORIAL,
            order=1,
            title="Донецька обласна рада",
            article=cls.article,
        )
        FotoekspEntry.objects.create(
            page=cls.page,
            section=FotoekspEntry.SECTION_TERRITORIAL,
            order=2,
            title="Волинська область",
        )

    def test_renders_structured_lists(self):
        response = Client().get("/fotoekspozytsiya/", follow=True)
        self.assertContains(response, "Тестове попередження")
        self.assertContains(response, "Донецька обласна рада")
        self.assertContains(response, "Волинська область")
        self.assertContains(response, 'id="fotoeksp-teritorial"')
        self.assertContains(response, "/fotovystavka-2024/25888-04-donetska.html")
