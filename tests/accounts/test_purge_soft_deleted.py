from __future__ import annotations

import pytest
from django.utils import timezone

from accounts.models import User
from accounts.tasks import purge_soft_deleted


def _create_deleted_user(**kwargs) -> User:
    return User.objects.create_user(
        email=f"{timezone.now().timestamp()}@example.com",
        username=str(timezone.now().timestamp()),
        password="x",
        deleted=True,
        deleted_at=timezone.now() - timezone.timedelta(days=31),
        exclusao_confirmada=True,
        **kwargs,
    )


@pytest.mark.django_db
def test_purge_removes_old_users():
    user = _create_deleted_user()
    purge_soft_deleted()
    assert not User.all_objects.filter(pk=user.pk).exists()


@pytest.mark.django_db
def test_purge_keeps_recent_users():
    user = User.objects.create_user(
        email="recent@example.com",
        username="recent",
        password="x",
        deleted=True,
        deleted_at=timezone.now() - timezone.timedelta(days=10),
        exclusao_confirmada=True,
    )
    purge_soft_deleted()
    assert User.all_objects.filter(pk=user.pk).exists()


@pytest.mark.django_db
def test_purge_idempotent():
    user = _create_deleted_user()
    purge_soft_deleted()
    purge_soft_deleted()
    assert not User.all_objects.filter(pk=user.pk).exists()


@pytest.mark.django_db
def test_purge_batches(mocker):
    users = [_create_deleted_user() for _ in range(3)]
    atomic = mocker.patch("accounts.tasks.transaction.atomic")
    purge_soft_deleted(batch_size=2)
    assert atomic.call_count >= 2
    for user in users:
        assert not User.all_objects.filter(pk=user.pk).exists()

