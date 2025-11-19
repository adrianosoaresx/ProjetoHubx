from __future__ import annotations

import re
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Q

from feed.models import Post
from feed.services.link_preview import LinkPreviewError, extract_link_preview

LINK_REGEX = re.compile(r"https?://[\w.-]+(?:\.[\w.-]+)*(?::\d+)?[^\s]*", re.IGNORECASE)


def _extract_first_url(content: str | None) -> str | None:
    if not content:
        return None
    match = LINK_REGEX.search(content)
    return match.group(0) if match else None


class Command(BaseCommand):
    help = "Populate Post.link_preview for existing posts."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--limit", type=int, default=100, help="Maximum number of posts to process.")
        parser.add_argument("--offset", type=int, default=0, help="Skip the first N posts that match the criteria.")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rebuild link previews even when a post already stores data.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only log the actions without persisting any change.",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ANN401 - command signature
        limit: int = options["limit"]
        offset: int = options["offset"]
        force: bool = options["force"]
        dry_run: bool = options["dry_run"]

        queryset = Post.objects.order_by("created_at")
        if not force:
            queryset = queryset.filter(Q(link_preview__isnull=True) | Q(link_preview={}))

        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[:limit]

        updated = 0
        skipped_missing_url = 0
        failed = 0

        for post in queryset:
            url = _extract_first_url(post.conteudo)
            if not url:
                skipped_missing_url += 1
                continue

            try:
                preview = extract_link_preview(url)
            except LinkPreviewError as exc:
                failed += 1
                self.stderr.write(
                    self.style.WARNING(f"Falha ao gerar preview para {post.pk}: {exc.__class__.__name__}")
                )
                continue

            payload = {
                "url": preview.url,
                "title": preview.title,
                "description": preview.description,
                "image": preview.image,
                "site_name": preview.site_name,
            }

            if dry_run:
                self.stdout.write(f"[dry-run] Atualizaria {post.pk} com {preview.url}")
            else:
                Post.objects.filter(pk=post.pk).update(link_preview=payload)
            updated += 1

        summary = (
            f"Pré-visualizações atualizadas: {updated}. Sem URL detectada: {skipped_missing_url}. "
            f"Falhas: {failed}."
        )
        self.stdout.write(self.style.SUCCESS(summary))
