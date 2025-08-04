import pytest
from accounts.models import LoginAttempt


@pytest.mark.django_db
def test_login_attempt_timestamp_and_soft_delete():
    attempt = LoginAttempt.objects.create(email="a@example.com", sucesso=False)
    assert attempt.created_at is not None and attempt.updated_at is not None
    attempt.delete()
    assert attempt.deleted and attempt.deleted_at is not None
