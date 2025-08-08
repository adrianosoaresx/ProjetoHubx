# Performance Tuning

This document outlines the strategies used to optimize ProjetoHubx and the results observed.

## Query Optimization
- Heavy views use `select_related` and `prefetch_related` to reduce database roundtrips.
- Slow queries are indexed based on logs from production monitoring.

## Celery Configuration
- `CELERYD_CONCURRENCY` is tuned to match available CPU cores.
- `CELERY_BEAT_SCHEDULE` groups periodic tasks to balance load.

## Load Testing
- Locust scripts simulate spikes of post creation and reading.
- During tests, p95 and p99 latency stayed under 200 ms after database and worker adjustments.

Further improvements can be tracked in future sprints.
