"""Middleware fictício apenas para satisfazer referências do Django."""

from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse


class SilkyMiddleware:
    """Middleware pass-through que não altera a requisição."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)
