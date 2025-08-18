from empresas.factories import EmpresaFactory
from empresas.tasks import validar_cnpj_empresa


def test_task_retry_and_update(monkeypatch):
    empresa = EmpresaFactory(validado_em=None, fonte_validacao="")
    calls = {"n": 0}

    def fake_adapter(cnpj):
        calls["n"] += 1
        if calls["n"] < 3:
            raise Exception("boom")
        return True, "brasilapi"

    captured = []
    monkeypatch.setattr("empresas.tasks.validate_cnpj_externo", fake_adapter)
    monkeypatch.setattr("sentry_sdk.capture_exception", lambda exc: captured.append(str(exc)))

    validar_cnpj_empresa.delay(str(empresa.id))
    empresa.refresh_from_db()
    assert calls["n"] == 3
    assert empresa.validado_em is not None
    assert empresa.fonte_validacao == "brasilapi"
    assert len(captured) == 2
