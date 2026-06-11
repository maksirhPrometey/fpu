"""Tests for fotoekspozytsiya HTML preparation."""
from django.test import TestCase

from apps.pages.fotoekspozytsiya import prepare_fotoeksp_html


class PrepareFotoekspHtmlTests(TestCase):
    def test_wraps_table_and_strips_inline_styles(self):
        html = (
            '<p style="text-align:center;"><img src="/x.jpg"></p>'
            '<table style="width:900px;"><tr><td style="border:1px solid #000;">1</td></tr></table>'
        )
        out = prepare_fotoeksp_html(html)
        self.assertIn('class="fotoeksp-table-wrap"', out)
        self.assertIn('class="fotoeksp-table"', out)
        self.assertNotIn('style="width:900px;"', out)
        self.assertNotIn('style="border:1px solid #000;"', out)

    def test_injects_section_anchors(self):
        html = "<p><span>ТЕРИТОРІАЛЬНІ ОБ'ЄДНАННЯ</span></p><table></table><p><span>ВСЕУКРАЇНСЬКІ</span></p>"
        out = prepare_fotoeksp_html(html)
        self.assertIn('id="fotoeksp-teritorial"', out)
        self.assertIn('id="fotoeksp-galuz"', out)

    def test_moves_data_rows_from_thead_to_tbody(self):
        html = (
            "<table><thead>"
            "<tr><td>№</td><td>Name</td></tr>"
            "<tr><td>1.</td><td><a href='/x.html'>One</a></td></tr>"
            "<tr><td>2.</td><td>Two</td></tr>"
            "</thead></table>"
        )
        out = prepare_fotoeksp_html(html)
        self.assertIn("<tbody>", out)
        self.assertIn("<thead><tr><td>№</td><td>Name</td></tr></thead>", out)
        self.assertIn("<tr><td>1.</td><td><a href='/x.html'>One</a></td></tr>", out)
