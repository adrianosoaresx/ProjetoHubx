import pytest

from accounts.factories import UserFactory
from eventos.factories import EventoFactory
from eventos.models import BriefingEvento
from eventos.tasks import notificar_briefing_status


@pytest.mark.django_db
def test_notificar_briefing_status_envia_notificacoes(monkeypatch):
    evento = EventoFactory()
    briefing = BriefingEvento.objects.create(
        evento=evento,
        objetivos="obj",
        publico_alvo="pub",
        requisitos_tecnicos="req",
    )
    extra_user = UserFactory()
    chamados = []

    def fake_enviar(user, codigo, ctx):
        chamados.append((user, codigo, ctx))

    monkeypatch.setattr("eventos.tasks.enviar_para_usuario", fake_enviar)
    notificar_briefing_status(briefing.id, "aprovado", [extra_user.id], "msg")

    usuarios_notificados = {u for u, _, _ in chamados}
    assert usuarios_notificados == {evento.coordenador, extra_user}
    for _, codigo, ctx in chamados:
        assert codigo == "eventos_briefing_status"
        assert ctx["status"] == "aprovado"
        assert ctx["mensagem"] == "msg"
