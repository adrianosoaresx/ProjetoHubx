import pytest

from chat.models import RelatorioChatExport
from chat.services import criar_canal, enviar_mensagem
from chat.tasks import exportar_historico_chat

pytestmark = pytest.mark.django_db


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
