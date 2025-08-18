from django.urls import reverse
from rest_framework.test import APIClient
from validate_docbr import CNPJ

from empresas.services.cnpj_adapter import CNPJServiceError


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_validar_cnpj_ok(monkeypatch, admin_user):
    cnpj = CNPJ().generate()
    client = _client(admin_user)
    monkeypatch.setattr("empresas.api.validate_cnpj_externo", lambda c: (True, "serpro"))
    url = reverse("empresas_api:empresa-validar-cnpj")
    resp = client.post(url, {"cnpj": cnpj}, format="json")
    data = resp.json()
    assert resp.status_code == 200
    assert data["valido_local"] is True
    assert data["valido_externo"] is True
    assert data["fonte"] == "serpro"


def test_validar_cnpj_invalido_local(monkeypatch, admin_user):
    called = []
    client = _client(admin_user)
    def fake(c):
        called.append(True)
        return True, "serpro"
    monkeypatch.setattr("empresas.api.validate_cnpj_externo", fake)
    url = reverse("empresas_api:empresa-validar-cnpj")
    resp = client.post(url, {"cnpj": "123"}, format="json")
    data = resp.json()
    assert resp.status_code == 200
    assert data["valido_local"] is False
    assert data["valido_externo"] is None
    assert not called


def test_validar_cnpj_externo_invalido(monkeypatch, admin_user):
    cnpj = CNPJ().generate()
    client = _client(admin_user)
    monkeypatch.setattr("empresas.api.validate_cnpj_externo", lambda c: (False, "serpro"))
    url = reverse("empresas_api:empresa-validar-cnpj")
    resp = client.post(url, {"cnpj": cnpj}, format="json")
    data = resp.json()
    assert resp.status_code == 200
    assert data["valido_local"] is True
    assert data["valido_externo"] is False


def test_validar_cnpj_servico_indisponivel(monkeypatch, admin_user):
    cnpj = CNPJ().generate()
    client = _client(admin_user)
    def boom(c):
        raise CNPJServiceError("fail")
    monkeypatch.setattr("empresas.api.validate_cnpj_externo", boom)
    url = reverse("empresas_api:empresa-validar-cnpj")
    resp = client.post(url, {"cnpj": cnpj}, format="json")
    assert resp.status_code == 503
