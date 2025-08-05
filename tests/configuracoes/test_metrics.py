from configuracoes import metrics


def test_latency_histogram_records():
    metrics.config_api_latency_seconds.clear()
    metrics.config_api_latency_seconds.labels(method="GET").observe(0.2)
    sample = metrics.config_api_latency_seconds.collect()[0]
    buckets = {float(s.labels['le']): s.value for s in sample.samples if s.name.endswith('_bucket')}
    assert buckets[0.25] >= 1
