"""Tests for body excerpt extraction."""
from apps.news.body_excerpt import listing_excerpt, listing_lead, sanitize_listing_text


def test_listing_lead_from_strong():
    body = "<p><strong>Чи можна працювати?</strong> Відповідь так.</p>"
    assert listing_lead(body) == "Чи можна працювати?"


def test_listing_excerpt_includes_question_and_answer_start():
    body = (
        "<p><strong>З якого віку можна прийняти?</strong></p>"
        "<p>Відповідно до статті 187 КЗпП неповнолітні…</p>"
    )
    excerpt = listing_excerpt(body, max_len=200)
    assert "З якого віку" in excerpt
    assert "187 КЗпП" in excerpt


def test_sanitize_listing_text_strips_partial_html():
    dirty = "Текст уривка ... прирівнюються у правах до ... <div"
    assert sanitize_listing_text(dirty) == "Текст уривка ... прирівнюються у правах до ..."
