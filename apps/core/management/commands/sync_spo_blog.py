"""Import all SPO blog posts from spo.fpsu.org.ua into Article."""
from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.spo_blog_sync import (
    download_spo_media,
    fetch_all_spo_blog_posts,
    rewrite_spo_body_html,
    unique_article_slug,
)
from apps.news.models import Article, Category

SPO_WP_CATEGORY_PATH = "spo-wp-novyny"


class Command(BaseCommand):
    help = "Import all blog posts from spo.fpsu.org.ua into local Article records"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Do not download featured/inline images",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        skip_images: bool = options["skip_images"]

        posts = fetch_all_spo_blog_posts()
        self.stdout.write(f"Fetched {len(posts)} posts from spo.fpsu.org.ua/blog/")

        if dry_run:
            for post in posts[:5]:
                date = post.published_at.strftime("%d.%m.%Y") if post.published_at else "?"
                self.stdout.write(f"  [{post.wp_post_id}] {date} {post.title[:60]}")
            if len(posts) > 5:
                self.stdout.write(f"  … and {len(posts) - 5} more")
            return

        category, _ = Category.objects.get_or_create(
            alias=SPO_WP_CATEGORY_PATH,
            defaults={
                "title": "Новини СПО",
                "path": SPO_WP_CATEGORY_PATH,
                "is_active": True,
            },
        )

        created = updated = 0
        with transaction.atomic():
            for post in posts:
                slug = unique_article_slug(post.slug, post.wp_post_id)
                body = post.body
                local_image = ""

                if not skip_images:
                    body = rewrite_spo_body_html(body)
                    if post.featured_image_url:
                        try:
                            local_image = download_spo_media(post.featured_image_url)
                        except Exception:
                            local_image = ""

                defaults = {
                    "title": post.title,
                    "slug": slug,
                    "summary": post.summary,
                    "body": body,
                    "published_at": post.published_at or timezone.now(),
                    "is_published": True,
                    "is_spo": True,
                    "category": category,
                    "source_url": post.source_url,
                    "local_image": local_image,
                }
                _article, was_created = Article.objects.update_or_create(
                    wp_post_id=post.wp_post_id,
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

            synced_ids = {post.wp_post_id for post in posts}
            hidden = (
                Article.objects.filter(category=category, wp_post_id__isnull=False)
                .exclude(wp_post_id__in=synced_ids)
                .update(is_published=False)
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Synced SPO blog: {created} created, {updated} updated, {hidden} hidden."
            )
        )
