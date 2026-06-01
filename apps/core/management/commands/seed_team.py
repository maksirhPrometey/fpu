"""Seed / reset FPU leadership team members."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.core.models import TeamMember

TEAM = [
    {
        "full_name": "Бизов Сергій Сергійович",
        "role": "Голова ФПУ",
        "bio": "Очолює Федерацію профспілок України. Захищає трудові права, "
               "веде соціальний діалог та міжнародне співробітництво.",
        "order": 1,
    },
    {
        "full_name": "Москаленко Ігор Іванович",
        "role": "Заступник Голови ФПУ",
        "bio": "Координує правовий захист та колективно-договірне регулювання.",
        "order": 2,
    },
    {
        "full_name": "Драп'ятий Євген Михайлович",
        "role": "Заступник Голови ФПУ",
        "bio": "Відповідає за організаційну роботу та взаємодію з членськими організаціями.",
        "order": 3,
    },
    {
        "full_name": "Андреєв Василь Миколайович",
        "role": "Заступник Голови ФПУ",
        "bio": "Координує питання охорони праці, безпеки виробництва та соціального страхування.",
        "order": 4,
    },
]


class Command(BaseCommand):
    help = "Reset FPU team members to current leadership."

    def handle(self, *args, **options) -> None:
        TeamMember.objects.all().delete()
        for data in TEAM:
            TeamMember.objects.create(
                full_name=data["full_name"],
                role=data["role"],
                bio=data["bio"],
                order=data["order"],
                is_active=True,
            )
        self.stdout.write(self.style.SUCCESS(f"Done: {len(TEAM)} team members set."))
