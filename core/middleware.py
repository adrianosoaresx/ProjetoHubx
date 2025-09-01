import time
from django.utils.deprecation import MiddlewareMixin

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
