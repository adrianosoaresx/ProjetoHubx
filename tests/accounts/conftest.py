import pytest


@pytest.fixture(autouse=True)
def celery_eager(settings, monkeypatch):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    monkeypatch.setattr("accounts.tasks.send_confirmation_email.delay", lambda *a, **k: None)
