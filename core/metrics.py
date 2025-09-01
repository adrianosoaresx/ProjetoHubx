from prometheus_client import Histogram

ENDPOINT_LATENCY = Histogram(
    "endpoint_latency_seconds",
    "Latency of HTTP requests by endpoint",
    ["method", "endpoint"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
