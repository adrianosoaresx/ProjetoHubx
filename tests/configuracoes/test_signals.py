from __future__ import annotations

from unittest.mock import Mock

import pytest

from configuracoes.models import ConfiguracaoConta


@pytest.mark.django_db
def test_log_changes_channel_error(monkeypatch, admin_user):
    class DummyLayer:
        async def group_send(self, *args, **kwargs):
            raise Exception("boom")

    monkeypatch.setattr("configuracoes.signals.get_channel_layer", lambda: DummyLayer())
    captured = Mock()
    monkeypatch.setattr("configuracoes.signals.sentry_sdk.capture_exception", captured)

    config = ConfiguracaoConta.objects.get(user=admin_user)
    config.idioma = "en-US"
    config.save()

    assert captured.call_count == 1
