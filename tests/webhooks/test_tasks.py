import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from webhooks.models import WebhookEvent, WebhookSubscription
from webhooks.tasks import remover_eventos_antigos


@pytest.mark.django_db
def test_remover_eventos_antigos_deletes_only_old_delivered_events():
    User = get_user_model()
    user = User.objects.create_user(username="u", email="u@example.com")
    sub = WebhookSubscription.objects.create(user=user, url="http://example.com", secret="s")

    old_delivered = WebhookEvent.objects.create(
        subscription=sub,
        event="e",
        payload={},
        delivered=True,
        created_at=timezone.now() - timezone.timedelta(days=40),
    )
    recent_delivered = WebhookEvent.objects.create(subscription=sub, event="e", payload={}, delivered=True)
    old_pending = WebhookEvent.objects.create(
        subscription=sub,
        event="e",
        payload={},
        delivered=False,
        created_at=timezone.now() - timezone.timedelta(days=40),
    )

    removed = remover_eventos_antigos()

    assert removed == 1
    assert not WebhookEvent.objects.filter(id=old_delivered.id).exists()
    assert WebhookEvent.objects.filter(id=recent_delivered.id).exists()
    assert WebhookEvent.objects.filter(id=old_pending.id).exists()
