from __future__ import annotations

from discussao.models import RespostaDiscussao, TopicoDiscussao
from discussao.tasks import notificar_melhor_resposta, notificar_nova_resposta


def test_notificar_nova_resposta(monkeypatch, categoria, associado_user, admin_user, nucleado_user):
    topico = TopicoDiscussao.objects.create(
        categoria=categoria, titulo="T", conteudo="c", autor=associado_user, publico_alvo=0
    )
    RespostaDiscussao.objects.create(topico=topico, autor=admin_user, conteudo="a")
    resposta = RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="b")
    chamados = []

    def fake_enviar(user, codigo, ctx):
        chamados.append(user)

    monkeypatch.setattr("discussao.tasks.enviar_para_usuario", fake_enviar)
    notificar_nova_resposta(resposta.id)
    assert associado_user in chamados and admin_user in chamados and nucleado_user not in chamados


def test_notificar_melhor_resposta(monkeypatch, categoria, associado_user, nucleado_user):
    topico = TopicoDiscussao.objects.create(
        categoria=categoria, titulo="T", conteudo="c", autor=associado_user, publico_alvo=0
    )
    resposta = RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="b")
    chamados = []

    def fake_enviar(user, codigo, ctx):
        chamados.append((user, codigo))

    monkeypatch.setattr("discussao.tasks.enviar_para_usuario", fake_enviar)
    notificar_melhor_resposta(resposta.id)
    assert chamados == [(nucleado_user, "discussao_melhor_resposta")]
