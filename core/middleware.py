import time
from django.utils.deprecation import MiddlewareMixin
from django.utils.cache import add_never_cache_headers

from .metrics import ENDPOINT_LATENCY


class EndpointMetricsMiddleware(MiddlewareMixin):
    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration = time.monotonic() - start
        resolver = getattr(request, "resolver_match", None)
        endpoint = resolver.view_name if resolver else request.path
        ENDPOINT_LATENCY.labels(request.method, endpoint).observe(duration)
        return response


class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        add_never_cache_headers(response)
        return response
