import logging
import time

logger = logging.getLogger(__name__)


class DashboardTimingMiddleware:
    """Middleware to log dashboard view response times."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        if request.path.startswith("/dashboard"):
            duration = (time.perf_counter() - start) * 1000
            logger.info("dashboard.request_time", extra={"duration_ms": duration})
        return response
