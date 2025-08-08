from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.test import APIClient

from accounts.models import UserType
from audit.models import AuditLog
from audit.services import hash_ip, log_audit
from audit.tasks import cleanup_old_logs
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def organizacao():
    return OrganizacaoFactory()


@pytest.fixture
def root_user():
    User = get_user_model()
    return User.objects.create_user(
        username="root",
        email="root@example.com",
        password="pass",
        user_type=UserType.ROOT,
    )


@pytest.fixture
def admin_user(organizacao):
    User = get_user_model()
    return User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )


@pytest.fixture
def cliente_user():
    User = get_user_model()
    return User.objects.create_user(
        username="cliente",
        email="cliente@example.com",
        password="pass",
        user_type=UserType.CONVIDADO,
    )


def test_log_audit_creates_entry(root_user) -> None:
    log_audit(
        root_user,
        "EXPORT_CSV",
        "Dashboard",
        "1",
        hash_ip("127.0.0.1"),
        "SUCCESS",
        {"foo": "bar"},
    )
    assert AuditLog.objects.filter(action="EXPORT_CSV").count() == 1


def test_middleware_logs_success_and_failure(client, admin_user, cliente_user) -> None:
    client.force_login(admin_user)
    client.get(reverse("dashboard:admin"))
    assert AuditLog.objects.filter(user=admin_user, status="SUCCESS").exists()

    client.force_login(cliente_user)
    client.get(reverse("dashboard:admin"))
    assert AuditLog.objects.filter(user=cliente_user, status="FAILURE").exists()


def test_audit_api_permissions(api_client: APIClient, root_user, admin_user) -> None:
    api_client.force_authenticate(user=root_user)
    resp = api_client.get("/api/audit/logs/")
    assert resp.status_code == 200

    api_client.force_authenticate(user=admin_user)
    resp2 = api_client.get("/api/audit/logs/")
    assert resp2.status_code == 403


def test_cleanup_old_logs(root_user) -> None:
    with freeze_time(timezone.now() - timedelta(days=365 * 6)):
        log_audit(root_user, "OLD", "", "", "ip", "SUCCESS", {})
    with freeze_time(timezone.now() - timedelta(days=365 * 4)):
        log_audit(root_user, "NEW", "", "", "ip", "SUCCESS", {})

    cleanup_old_logs()

    assert AuditLog.all_objects.get(action="OLD").deleted is True
    assert AuditLog.objects.get(action="NEW").deleted is False
