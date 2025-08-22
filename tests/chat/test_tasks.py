import importlib
import sys
from datetime import timedelta
from unittest.mock import Mock
import types

import pytest
from django.core.files.storage import default_storage
from django.utils import timezone

from chat.models import RelatorioChatExport
from chat.services import criar_canal, enviar_mensagem
from chat.tasks import exportar_historico_chat, limpar_exports_antigos

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("module_path", ["chat.tasks", "chat.api_views"])
def test_scan_file_logs_exception(monkeypatch, module_path):
    class DummySocket:
        def scan(self, path):  # pragma: no cover - test stub
            raise RuntimeError("fail")

    dummy_module = types.SimpleNamespace(ClamdNetworkSocket=DummySocket)
    monkeypatch.setitem(sys.modules, "clamd", dummy_module)

    captured = Mock()
    monkeypatch.setattr(f"{module_path}.sentry_sdk.capture_exception", captured)

    mod = importlib.import_module(module_path)
    assert mod._scan_file("/tmp/test") is False
    assert captured.call_count == 1


def test_exportar_historico_chat_gera_arquivo(media_root, admin_user, coordenador_user):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=None,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    enviar_mensagem(canal, admin_user, "text", conteudo="oi")
    rel = RelatorioChatExport.objects.create(
        channel=canal,
        formato="json",
        gerado_por=admin_user,
        status="gerando",
    )
    url = exportar_historico_chat(str(canal.id), "json", relatorio_id=str(rel.id))
    rel.refresh_from_db()
    assert rel.status == "concluido"
    assert rel.arquivo_url == url
    assert rel.arquivo_path


def test_exportar_historico_chat_com_filtro(media_root, admin_user, coordenador_user):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=None,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    enviar_mensagem(canal, admin_user, "text", conteudo="oi")
    enviar_mensagem(canal, admin_user, "image", conteudo="https://exemplo.com/img.png")
    rel = RelatorioChatExport.objects.create(
        channel=canal, formato="json", gerado_por=admin_user, status="gerando"
    )
    exportar_historico_chat(
        str(canal.id),
        "json",
        tipos=["image"],
        relatorio_id=str(rel.id),
    )
    import json, os
    from django.conf import settings

    file_path = os.path.join(settings.MEDIA_ROOT, f"chat_exports/{canal.id}.json")
    with open(file_path) as f:
        data = json.load(f)
    assert len(data) == 1 and data[0]["tipo"] == "image"


def test_limpar_exports_antigos_remove_arquivos(media_root, admin_user, coordenador_user):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=None,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    enviar_mensagem(canal, admin_user, "text", conteudo="oi")
    rel_old = RelatorioChatExport.objects.create(
        channel=canal, formato="json", gerado_por=admin_user, status="gerando"
    )
    exportar_historico_chat(str(canal.id), "json", relatorio_id=str(rel_old.id))
    rel_old.refresh_from_db()
    RelatorioChatExport.objects.filter(id=rel_old.id).update(
        created_at=timezone.now() - timedelta(days=31)
    )

    rel_new = RelatorioChatExport.objects.create(
        channel=canal, formato="csv", gerado_por=admin_user, status="gerando"
    )
    exportar_historico_chat(str(canal.id), "csv", relatorio_id=str(rel_new.id))
    rel_new.refresh_from_db()

    assert default_storage.exists(rel_old.arquivo_path)
    assert default_storage.exists(rel_new.arquivo_path)

    limpar_exports_antigos()

    assert not default_storage.exists(rel_old.arquivo_path)
    assert default_storage.exists(rel_new.arquivo_path)
    assert not RelatorioChatExport.objects.filter(id=rel_old.id).exists()
    assert RelatorioChatExport.objects.filter(id=rel_new.id).exists()
