import pytest
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from unittest.mock import patch

from django_ratelimit.exceptions import Ratelimited

from accounts.factories import UserFactory
from accounts.views import login_view

pytestmark = pytest.mark.django_db


@override_settings(DEBUG_PROPAGATE_EXCEPTIONS=True)
def test_login_ratelimit_blocks_authenticate():
    cache.clear()
    user = UserFactory(password="senha123")
    rf = RequestFactory()

    def build_request():
        req = rf.post("/login/", {"email": user.email, "password": "wrong"})
        req.user = AnonymousUser()
        req.META["REMOTE_ADDR"] = "1.1.1.1"
        SessionMiddleware(lambda r: None).process_request(req)
        req.session.save()
        MessageMiddleware(lambda r: None).process_request(req)
        return req

    with patch("accounts.views.render", return_value=HttpResponse("")), patch(
        "accounts.forms.authenticate"
    ) as mock_auth:
        for _ in range(5):
            resp = login_view(build_request())
            assert resp.status_code == 200
        assert mock_auth.call_count == 5
        with pytest.raises(Ratelimited):
            login_view(build_request())
        assert mock_auth.call_count == 5
