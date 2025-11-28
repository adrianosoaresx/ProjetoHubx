from __future__ import annotations

import logging
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Iterable, List, Optional
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone
from sentry_sdk import capture_exception

from accounts.models import UserType
from feed.models import Post, Tag
from feed.services import _upload_media
from feed.services.link_preview import LinkPreviewData, LinkPreviewError, extract_link_preview
from feed.tasks import POSTS_CREATED, notify_new_post
from organizacoes.models import Organizacao, OrganizacaoFeedSync

logger = logging.getLogger(__name__)
_FEED_LOCK_TIMEOUT = 60 * 10  # evita execuções duplicadas próximas (10 minutos)

try:  # feedparser >= 6.0
    from feedparser.util import mktime_tz as _mktime_tz
except Exception:  # pragma: no cover - import guard
    try:  # noqa: WPS440 - fallback import
        from email.utils import mktime_tz as _mktime_tz
    except Exception:  # pragma: no cover - import guard
        _mktime_tz = None


@dataclass(slots=True)
class NormalizedFeedItem:
    external_id: str
    link: str
    title: str
    summary: str
    published_at: Optional[datetime]


def _strip_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(" ", strip=True)


def _normalize_entry(entry: object) -> Optional[NormalizedFeedItem]:
    external_id = getattr(entry, "id", None) or getattr(entry, "guid", None) or getattr(entry, "link", None)
    link = getattr(entry, "link", None) or ""
    if not external_id or not link:
        return None

    title = _strip_html(getattr(entry, "title", ""))
    summary = _strip_html(getattr(entry, "summary", "")) or _strip_html(getattr(entry, "description", ""))

    published_raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
    published_at: Optional[datetime]
    published_parsed = getattr(entry, "published_parsed", None)
    if published_parsed:
        try:
            if _mktime_tz:
                timestamp = _mktime_tz(published_parsed)
                published_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            elif published_raw:
                published_at = parsedate_to_datetime(published_raw)
            else:
                published_at = datetime(*published_parsed[:6], tzinfo=timezone.utc)
            if timezone.is_naive(published_at):
                published_at = timezone.make_aware(published_at, timezone=timezone.utc)
        except Exception:
            published_at = None
    elif published_raw:
        try:
            published_at = parsedate_to_datetime(published_raw)
            if timezone.is_naive(published_at):
                published_at = timezone.make_aware(published_at, timezone=timezone.utc)
        except Exception:
            published_at = None
    else:
        published_at = None

    return NormalizedFeedItem(
        external_id=str(external_id),
        link=str(link),
        title=title.strip(),
        summary=summary.strip(),
        published_at=published_at,
    )


def _select_author(organizacao: Organizacao):
    User = get_user_model()
    return (
        User.objects.filter(
            organizacao=organizacao,
            is_active=True,
            user_type__in=[UserType.ADMIN, UserType.ROOT],
        )
        .order_by("created_at")
        .first()
    )


def _truncate_content(title: str, summary: str, link: str, limit: int = 500) -> str:
    base_parts = [part for part in [title, summary] if part]
    base_text = "\n\n".join(base_parts)

    if link:
        candidate = f"{base_text}\n\n{link}" if base_text else link
    else:
        candidate = base_text

    if len(candidate) <= limit:
        return candidate

    link_extra = len(link) + (2 if base_text and link else 0)
    available = max(limit - link_extra, 0)
    shortened = textwrap.shorten(base_text, width=max(available, 10), placeholder="...") if base_text else ""
    if link:
        return f"{shortened}\n\n{link}" if shortened else link[:limit]
    return shortened[:limit]


def _maybe_download_image(preview: LinkPreviewData) -> Optional[str]:
    if not preview.image:
        return None
    try:
        response = requests.get(preview.image, timeout=5)
        response.raise_for_status()
    except requests.RequestException:
        logger.warning("Não foi possível baixar imagem do preview", exc_info=True)
        return None

    parsed = urlparse(preview.image)
    filename = (parsed.path.rsplit("/", 1)[-1] or "image").split("?")[0] or "image"
    content_type = response.headers.get("Content-Type") or ""

    try:
        upload = SimpleUploadedFile(filename, response.content, content_type=content_type)
        key = _upload_media(upload)
        if isinstance(key, (list, tuple)):
            return key[0]
        return key
    except Exception:
        logger.warning("Falha ao enviar imagem do preview", exc_info=True)
        return None


def _create_post(
    organizacao: Organizacao,
    author,
    item: NormalizedFeedItem,
    tipo_feed: str = "global",
) -> Optional[Post]:
    try:
        preview = extract_link_preview(item.link)
    except LinkPreviewError:
        preview = LinkPreviewData(url=item.link, title=item.title or item.link, description=item.summary, image=None, site_name="")
    except Exception:
        logger.warning("Erro inesperado ao extrair link preview", exc_info=True)
        preview = LinkPreviewData(url=item.link, title=item.title or item.link, description=item.summary, image=None, site_name="")

    conteudo = _truncate_content(item.title, item.summary, item.link)
    post = Post(
        autor=author,
        organizacao=organizacao,
        tipo_feed=tipo_feed,
        conteudo=conteudo,
        link_preview=asdict(preview),
    )

    image_key = _maybe_download_image(preview)
    if image_key:
        post.image = image_key

    post.full_clean()
    post.save()

    tag, _ = Tag.objects.get_or_create(nome="notícias")
    post.tags.add(tag)

    OrganizacaoFeedSync.objects.create(
        organizacao=organizacao,
        external_id=item.external_id,
        title=item.title,
        link=item.link,
        published_at=item.published_at,
    )

    POSTS_CREATED.inc()
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        notify_new_post(post.id)
    else:
        notify_new_post.delay(post.id)

    return post


def publicar_feed_da_organizacao(
    organizacao: Organizacao, *, max_items: int = 3, tipo_feed: str = "global"
) -> List[Post]:
    if not organizacao.feed_noticias or organizacao.inativa:
        return []

    author = _select_author(organizacao)
    if not author:
        logger.warning("Nenhum autor encontrado para publicar feed", extra={"organizacao": str(organizacao.id)})
        return []

    parsed = feedparser.parse(organizacao.feed_noticias)
    entries: Iterable[NormalizedFeedItem] = filter(None, (_normalize_entry(entry) for entry in parsed.entries))
    sorted_entries = sorted(entries, key=lambda item: item.published_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    limited_entries = sorted_entries[:max_items]

    external_ids = [item.external_id for item in limited_entries]
    existing_ids = set(
        OrganizacaoFeedSync.objects.filter(organizacao=organizacao, external_id__in=external_ids).values_list("external_id", flat=True)
    )

    created_posts: List[Post] = []
    for item in limited_entries:
        if item.external_id in existing_ids:
            continue
        try:
            with transaction.atomic():
                post = _create_post(organizacao, author, item, tipo_feed=tipo_feed)
        except Exception:
            logger.exception("Erro ao publicar item do feed", extra={"organizacao": str(organizacao.id), "external_id": item.external_id})
            continue
        if post:
            created_posts.append(post)

    return created_posts


def publicar_feed_noticias(max_items: int = 3, tipo_feed: str = "global") -> List[Post]:
    created: List[Post] = []
    orgs = Organizacao.objects.filter(feed_noticias__isnull=False).exclude(feed_noticias="").filter(inativa=False)

    for org in orgs:
        lock_key = f"organizacoes:feed_noticias:{org.pk}"
        if not cache.add(lock_key, True, timeout=_FEED_LOCK_TIMEOUT):
            logger.info("Feed de notícias já em processamento", extra={"organizacao": str(org.id)})
            continue
        try:
            created_posts = publicar_feed_da_organizacao(org, max_items=max_items, tipo_feed=tipo_feed)
        except Exception as exc:
            logger.exception("Erro ao processar feed de notícias", extra={"organizacao": str(org.id)})
            capture_exception(exc)
        else:
            created.extend(created_posts)
            logger.info(
                "Feed de notícias processado",
                extra={"organizacao": str(org.id), "posts_criados": len(created_posts)},
            )
        finally:
            cache.delete(lock_key)

    return created
