"""Tests for Joomla media URL rewriting in HTML bodies."""
from django.test import SimpleTestCase

from apps.core.media_utils import (
    normalize_legacy_body_html,
    rewrite_body_html_images,
)


class RewriteBodyHtmlImagesTests(SimpleTestCase):
    def test_fpsu_absolute_url(self):
        html = (
            '<img src="https://www.fpsu.org.ua/images/images/2024/March/'
            '220324/lg_220324_02.jpg" alt="test">'
        )
        out = rewrite_body_html_images(html)
        self.assertIn(
            'src="/media/joomla_images/images/images/2024/March/220324/lg_220324_02.jpg"',
            out,
        )

    def test_relative_images_path(self):
        html = '<a href="/images/stories/foo.jpg">link</a>'
        out = rewrite_body_html_images(html)
        self.assertIn('href="/media/joomla_images/images/stories/foo.jpg"', out)

    def test_empty_html(self):
        self.assertEqual(rewrite_body_html_images(""), "")


class NormalizeLegacyBodyHtmlTests(SimpleTestCase):
    def test_strips_inline_styles_and_span_wrappers(self):
        html = (
            '<p><span style="font-family: arial; font-size: large;">'
            '<a href="/foo.pdf"><b>Статут ФПУ</b> (у pdf)</a></span></p>'
        )
        out = normalize_legacy_body_html(html)
        self.assertNotIn("style=", out)
        self.assertNotIn("<span", out)
        self.assertIn("Статут ФПУ", out)
        self.assertIn('href="/foo.pdf"', out)
        self.assertNotIn("(у pdf)", out)

    def test_removes_empty_nbsp_paragraphs(self):
        html = "<p>&nbsp;</p><p>Text</p>"
        out = normalize_legacy_body_html(html)
        self.assertNotIn("&nbsp;", out)
        self.assertIn("<p>Text</p>", out)

    def test_strips_single_quoted_styles(self):
        html = "<p><span style='font-size: 13.5pt;'>Link</span></p>"
        out = normalize_legacy_body_html(html)
        self.assertNotIn("style=", out)
        self.assertIn("Link", out)

    def test_removes_empty_link_paragraphs(self):
        html = '<p><a href="https://example.com"><br /></a></p><p><a href="/x">Real</a></p>'
        out = normalize_legacy_body_html(html)
        self.assertNotIn("<br", out)
        self.assertEqual(out.count("<p>"), 1)


class RewriteJoomlaBodyHtmlTests(SimpleTestCase):
    def test_combined_normalization_and_image_rewrite(self):
        html = (
            '<p><span style="font-size: large;">'
            '<a href="https://www.fpsu.org.ua/images/doc.pdf">Doc</a></span></p>'
        )
        out = rewrite_body_html_images(normalize_legacy_body_html(html))
        self.assertNotIn("style=", out)
        self.assertIn("/media/joomla_images/", out)
