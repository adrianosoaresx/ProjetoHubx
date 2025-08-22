from celery.schedules import crontab
from django.conf import settings


def test_webhook_cleanup_scheduled_daily():
    schedule = settings.CELERY_BEAT_SCHEDULE["remover_eventos_antigos"]
    assert schedule["task"] == "webhooks.tasks.remover_eventos_antigos"
    assert isinstance(schedule["schedule"], crontab)
    assert schedule["schedule"].minute == {0}
    assert schedule["schedule"].hour == {0}
