"""Fix 0015: matched Article by local Django PK, which is NOT portable
across separate databases (dev / production each have their own
auto-incremented Article IDs). Re-link using joomla_id instead, which is
stable — it's the original content ID from the source Joomla export.
"""
from __future__ import annotations

from django.db import migrations

# full_name → Article.joomla_id (stable across all databases)
_NAME_TO_JOOMLA_ID = {
    "Бизов Сергій Сергійович": 138,
    "Москаленко Ігор Іванович": 139,
    "Драп'ятий Євген Михайлович": 140,
    "Андреєв Василь Миколайович": 137,
}


def link_articles(apps, schema_editor):
    TeamMember = apps.get_model("core", "TeamMember")
    Article = apps.get_model("news", "Article")

    for full_name, joomla_id in _NAME_TO_JOOMLA_ID.items():
        member = TeamMember.objects.filter(full_name=full_name).first()
        if not member:
            continue
        article = Article.objects.filter(joomla_id=joomla_id).first()
        member.detail_article = article
        member.save(update_fields=["detail_article"])


def unlink_articles(apps, schema_editor):
    TeamMember = apps.get_model("core", "TeamMember")
    TeamMember.objects.filter(full_name__in=_NAME_TO_JOOMLA_ID.keys()).update(
        detail_article=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_link_teammember_detail_articles"),
    ]

    operations = [
        migrations.RunPython(link_articles, unlink_articles),
    ]
