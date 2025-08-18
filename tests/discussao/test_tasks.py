from __future__ import annotations

from discussao.models import RespostaDiscussao, TopicoDiscussao
from discussao.tasks import notificar_melhor_resposta, notificar_nova_resposta


def test_notificar_nova_resposta(monkeypatch, capfd, categoria, associado_user, admin_user, nucleado_user):
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
    out, _ = capfd.readouterr()
    assert out.count("notificar_nova_resposta_sucesso") == 2


def test_notificar_melhor_resposta(monkeypatch, capfd, categoria, associado_user, nucleado_user):
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
    out, _ = capfd.readouterr()
    assert "notificar_melhor_resposta_sucesso" in out


def test_notificar_melhor_resposta_log_falha(monkeypatch, capfd, categoria, associado_user, nucleado_user):
    topico = TopicoDiscussao.objects.create(
        categoria=categoria, titulo="T", conteudo="c", autor=associado_user, publico_alvo=0
    )
    resposta = RespostaDiscussao.objects.create(topico=topico, autor=nucleado_user, conteudo="b")

    def fake_enviar(user, codigo, ctx):
        raise ValueError("erro")

    monkeypatch.setattr("discussao.tasks.enviar_para_usuario", fake_enviar)
    notificar_melhor_resposta(resposta.id)
    out, _ = capfd.readouterr()
    assert "notificar_melhor_resposta_falha" in out
