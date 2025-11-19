from celery.schedules import crontab
from django.conf import settings


def test_publicar_feed_noticias_agendado_diariamente():
    schedule = settings.CELERY_BEAT_SCHEDULE["publicar_feed_noticias_diario"]
    assert schedule["task"] == "organizacoes.tasks.publicar_feed_noticias_task"
    assert isinstance(schedule["schedule"], crontab)
    assert schedule["schedule"].minute == {0}
    assert schedule["schedule"].hour == {4}
