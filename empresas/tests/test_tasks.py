from empresas import tasks


def _fake_capture(monkeypatch):
    calls = []
    def fake_capture(exc):
        calls.append(exc)
    monkeypatch.setattr(tasks.sentry_sdk, "capture_exception", fake_capture)
    return calls


def test_validar_cnpj_async_capture_exception(monkeypatch):
    calls = _fake_capture(monkeypatch)

    def fake_validator(cnpj):
        raise tasks.CNPJValidationError("err")
    monkeypatch.setattr(tasks, "validar_cnpj", fake_validator)

    tasks.validar_cnpj_async.run("00000000000000")
    assert calls


def test_validar_cnpj_empresa_capture_exception(monkeypatch):
    calls = _fake_capture(monkeypatch)

    def fake_get(pk):
        raise tasks.Empresa.DoesNotExist
    monkeypatch.setattr(tasks.Empresa.objects, "get", fake_get)

    tasks.validar_cnpj_empresa.run("1")
    assert calls


def test_notificar_responsavel_capture_exception(monkeypatch):
    calls = _fake_capture(monkeypatch)

    def fake_select_related(*args, **kwargs):
        raise tasks.AvaliacaoEmpresa.DoesNotExist
    monkeypatch.setattr(tasks.AvaliacaoEmpresa.objects, "select_related", fake_select_related)

    tasks.notificar_responsavel.run("1")
    assert calls


def test_criar_post_empresa_capture_exception(monkeypatch):
    calls = _fake_capture(monkeypatch)

    def fake_select_related(*args, **kwargs):
        raise tasks.Empresa.DoesNotExist
    monkeypatch.setattr(tasks.Empresa.objects, "select_related", fake_select_related)

    tasks.criar_post_empresa.run("1")
    assert calls


def test_criar_post_avaliacao_capture_exception(monkeypatch):
    calls = _fake_capture(monkeypatch)

    def fake_select_related(*args, **kwargs):
        raise tasks.AvaliacaoEmpresa.DoesNotExist
    monkeypatch.setattr(tasks.AvaliacaoEmpresa.objects, "select_related", fake_select_related)

    tasks.criar_post_avaliacao.run("1")
    assert calls
