"""Link current TeamMember records to their legacy biography articles.

Restores click-through behaviour that existed when «Керівництво ФПУ» was
rendered from the old Joomla news category (each person had a full article
with biography). The dedicated /pro-fpu/kerivnitstvo-fpu/ page now uses the
curated TeamMember list, so we re-attach the same articles explicitly.
"""
from __future__ import annotations

from django.db import migrations

# full_name → Article PK (matched by exact title/name lookup, see chat history
# for how these were identified).
_NAME_TO_ARTICLE_PK = {
    "Бизов Сергій Сергійович": 27866,
    "Москаленко Ігор Іванович": 27867,
    "Драп'ятий Євген Михайлович": 27868,
    "Андреєв Василь Миколайович": 27865,
}


def link_articles(apps, schema_editor):
    TeamMember = apps.get_model("core", "TeamMember")
    Article = apps.get_model("news", "Article")

    for full_name, pk in _NAME_TO_ARTICLE_PK.items():
        member = TeamMember.objects.filter(full_name=full_name).first()
        if not member:
            continue
        article = Article.objects.filter(pk=pk).first()
        if not article:
            continue
        member.detail_article = article
        member.save(update_fields=["detail_article"])


def unlink_articles(apps, schema_editor):
    TeamMember = apps.get_model("core", "TeamMember")
    TeamMember.objects.filter(full_name__in=_NAME_TO_ARTICLE_PK.keys()).update(
        detail_article=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_teammember_detail_article"),
    ]

    operations = [
        migrations.RunPython(link_articles, unlink_articles),
    ]
