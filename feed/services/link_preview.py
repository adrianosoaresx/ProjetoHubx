from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class LinkPreviewError(Exception):
    """Base error for link preview extraction."""


class MissingLinkPreviewURLError(LinkPreviewError):
    """Raised when the URL parameter is missing."""


class InvalidLinkPreviewURLError(LinkPreviewError):
    """Raised when the URL does not have a valid HTTP/HTTPS scheme."""


class LinkPreviewRequestError(LinkPreviewError):
    """Raised when the remote content cannot be retrieved."""


@dataclass(slots=True)
class LinkPreviewData:
    url: str
    title: str
    description: str
    image: Optional[str]
    site_name: str


def _extract_meta(soup: BeautifulSoup, *names: str) -> Optional[str]:
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag:
            content = tag.get("content") or tag.get("value")
            if content:
                return content.strip()
    return None


def extract_link_preview(url: str) -> LinkPreviewData:
    """Return metadata to build a link preview for ``url``."""

    target_url = (url or "").strip()
    parsed = urlparse(target_url)

    if not target_url:
        raise MissingLinkPreviewURLError()

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise InvalidLinkPreviewURLError()

    try:
        response = requests.get(
            target_url,
            timeout=5,
            headers={"User-Agent": "HubxLinkPreview/1.0"},
        )
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - exc info for debugging only
        raise LinkPreviewRequestError() from exc

    soup = BeautifulSoup(response.text, "html.parser")

    title = _extract_meta(soup, "og:title", "twitter:title") or (
        soup.title.string.strip() if soup.title and soup.title.string else None
    )
    description = _extract_meta(soup, "og:description", "twitter:description", "description") or ""
    image = _extract_meta(soup, "og:image", "twitter:image")
    site_name = _extract_meta(soup, "og:site_name") or parsed.netloc

    if image:
        image = urljoin(target_url, image)

    return LinkPreviewData(
        url=target_url,
        title=title or target_url,
        description=description,
        image=image,
        site_name=site_name,
    )
