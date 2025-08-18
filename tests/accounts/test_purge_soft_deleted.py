from __future__ import annotations

import pytest
from django.utils import timezone

from accounts.models import User
from accounts.tasks import purge_soft_deleted


@pytest.mark.django_db
def test_purge_soft_deleted_respects_age():
    old = User.objects.create_user(email="old@example.com", username="old")
    old.delete()
    old.deleted_at = timezone.now() - timezone.timedelta(days=31)
    old.exclusao_confirmada = True
    old.save(update_fields=["deleted_at", "exclusao_confirmada"])

    recent = User.objects.create_user(email="new@example.com", username="new")
    recent.delete()
    recent.deleted_at = timezone.now() - timezone.timedelta(days=10)
    recent.exclusao_confirmada = True
    recent.save(update_fields=["deleted_at", "exclusao_confirmada"])

    purge_soft_deleted()

    assert not User.all_objects.filter(pk=old.pk).exists()
    assert User.all_objects.filter(pk=recent.pk).exists()


@pytest.mark.django_db
def test_purge_soft_deleted_idempotent():
    user = User.objects.create_user(email="tmp@example.com", username="tmp")
    user.delete()
    user.deleted_at = timezone.now() - timezone.timedelta(days=40)
    user.exclusao_confirmada = True
    user.save(update_fields=["deleted_at", "exclusao_confirmada"])

    purge_soft_deleted()
    purge_soft_deleted()

    assert not User.all_objects.filter(pk=user.pk).exists()


@pytest.mark.django_db
def test_purge_soft_deleted_chunking(mocker):
    for i in range(3):
        u = User.objects.create_user(email=f"c{i}@ex.com", username=f"c{i}")
        u.delete()
        u.deleted_at = timezone.now() - timezone.timedelta(days=40)
        u.exclusao_confirmada = True
        u.save(update_fields=["deleted_at", "exclusao_confirmada"])

    spy = mocker.spy(User.all_objects, "filter")
    purge_soft_deleted(batch_size=2)
    calls = [c for c in spy.call_args_list if c.kwargs.get("deleted")]
    assert len(calls) >= 2
