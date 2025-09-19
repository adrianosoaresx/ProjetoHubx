from celery.schedules import crontab
from django.conf import settings


def test_token_tasks_scheduled_daily():
    schedule_remover = settings.CELERY_BEAT_SCHEDULE["remover_logs_antigos"]
    assert schedule_remover["task"] == "tokens.tasks.remover_logs_antigos"
    assert isinstance(schedule_remover["schedule"], crontab)
    assert schedule_remover["schedule"].minute == {0}
    assert schedule_remover["schedule"].hour == {0}
