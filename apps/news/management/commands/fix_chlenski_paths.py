"""
Переносить категорії членських організацій на шляхи pro-fpu/chlenski-organizatsiji/*.

Під час імпорту Joomla статті потрапили в chlenski-organizatsiji/* замість
pro-fpu/chlenski-organizatsiji/*. Команда виправляє path і прибирає дублікати.

Usage:
    python manage.py fix_chlenski_paths
    python manage.py fix_chlenski_paths --dry-run
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.news.models import Article, Category
from apps.pages.models import StaticPage

_BASE = Path(__file__).resolve().parents[4]
_ARTICLES_TSV = _BASE / "tools" / "data" / "articles.tsv"
if not _ARTICLES_TSV.exists():
    _ARTICLES_TSV = _BASE / "tools" / "articles.tsv"

_MEMBER_ORG_PATHS: frozenset[str] = frozenset({
    "pro-fpu/chlenski-organizatsiji/vseukrajinski-galuzevi-profspilki",
    "pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok",
})

_EMPTY_STATIC_PREFIXES: tuple[str, ...] = (
    "/pro-fpu/chlenski-organizatsiji/vseukrajinski-galuzevi-profspilki",
    "/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok",
)

_PATH_UPDATES: dict[str, str] = {
    "chlenski-organizatsiji/vseukrajinski-galuzevi-profspilki": (
        "pro-fpu/chlenski-organizatsiji/vseukrajinski-galuzevi-profspilki"
    ),
    "chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok": (
        "pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok"
    ),
}

# Порожні дубльовані категорії з typo-path (повторний імпорт).
_PATHS_TO_REMOVE: tuple[str, ...] = (
    "pro-fpu/chlenski-organizatsiji/vseukrajinski-galuzevi-profspilky",
)

# Joomla ID статей-дублікатів (канонічні версії вже в основній категорії).
_DUPLICATE_JOOMLA_IDS: frozenset[int] = frozenset({20913})


class Command(BaseCommand):
    help = "Fix member organization category paths under pro-fpu/chlenski-organizatsiji/"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))

        with transaction.atomic():
            removed_articles = self._remove_duplicate_articles(dry_run)
            removed_cats = self._remove_empty_duplicate_categories(dry_run)
            updated = self._update_category_paths(dry_run)
            repaired_titles = self._repair_empty_titles(dry_run)
            removed_pages = self._remove_empty_static_pages(dry_run)

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {updated} paths updated, "
                f"{removed_articles} duplicate articles removed, "
                f"{removed_cats} empty categories removed, "
                f"{repaired_titles} titles repaired, "
                f"{removed_pages} empty static pages removed."
            )
        )

    def _remove_duplicate_articles(self, dry_run: bool) -> int:
        qs = Article.objects.filter(joomla_id__in=_DUPLICATE_JOOMLA_IDS)
        count = qs.count()
        for article in qs:
            self.stdout.write(f"  DELETE article joomla_id={article.joomla_id} ({article.title[:50]})")
        if not dry_run and count:
            qs.delete()
        return count

    def _remove_empty_duplicate_categories(self, dry_run: bool) -> int:
        removed = 0
        for path in _PATHS_TO_REMOVE:
            try:
                category = Category.objects.get(path=path)
            except Category.DoesNotExist:
                continue
            article_count = Article.objects.filter(category=category).count()
            if article_count:
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP delete {path} — still has {article_count} articles"
                    )
                )
                continue
            self.stdout.write(f"  DELETE category {path}")
            if not dry_run:
                category.delete()
            removed += 1
        return removed

    def _update_category_paths(self, dry_run: bool) -> int:
        updated = 0
        for old_path, new_path in _PATH_UPDATES.items():
            try:
                category = Category.objects.get(path=old_path)
            except Category.DoesNotExist:
                self.stdout.write(f"  SKIP {old_path} — not found")
                continue

            if Category.objects.filter(path=new_path).exclude(pk=category.pk).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP {old_path} → {new_path} — target path already taken"
                    )
                )
                continue

            self.stdout.write(f"  UPDATE {old_path} → {new_path} ({category.title})")
            if not dry_run:
                category.path = new_path
                category.save(update_fields=["path"])
            updated += 1
        return updated

    def _load_joomla_titles(self) -> dict[int, str]:
        titles: dict[int, str] = {}
        if not _ARTICLES_TSV.exists():
            return titles
        for line in _ARTICLES_TSV.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split("\t")
            if len(parts) < 6:
                continue
            try:
                jid = int(parts[0])
            except ValueError:
                continue
            title = parts[5].strip()
            if title:
                titles[jid] = title
        return titles

    def _repair_empty_titles(self, dry_run: bool) -> int:
        joomla_titles = self._load_joomla_titles()
        repaired = 0
        qs = (
            Article.objects.filter(category__path__in=_MEMBER_ORG_PATHS, title="")
            .select_related("category")
        )
        for article in qs:
            title = joomla_titles.get(article.joomla_id or -1, "")
            if not title:
                continue
            self.stdout.write(f"  TITLE joomla_id={article.joomla_id} → {title[:60]}")
            if not dry_run:
                article.title = title
                article.save(update_fields=["title"])
            repaired += 1
        return repaired

    def _remove_empty_static_pages(self, dry_run: bool) -> int:
        removed = 0
        for prefix in _EMPTY_STATIC_PREFIXES:
            for variant in (prefix, f"{prefix}.html"):
                try:
                    page = StaticPage.objects.get(url_path=variant)
                except StaticPage.DoesNotExist:
                    continue
                if page.body.strip():
                    continue
                self.stdout.write(f"  DELETE StaticPage {variant}")
                if not dry_run:
                    page.delete()
                removed += 1
        return removed
