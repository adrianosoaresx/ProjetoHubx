import pytest
from django.urls import reverse

from chat.models import TrendingTopic
from chat.services import criar_canal, enviar_mensagem
from chat.tasks import calcular_trending_topics

pytestmark = pytest.mark.django_db


def test_calcular_trending_topics_endpoint(admin_user, coordenador_user, client):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=None,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    enviar_mensagem(canal, admin_user, "text", conteudo="legal legal inovador")
    enviar_mensagem(canal, coordenador_user, "text", conteudo="mundo legal")

    calcular_trending_topics(str(canal.id), dias=30)

    topics = list(TrendingTopic.objects.filter(canal=canal))
    assert any(t.palavra == "legal" and t.frequencia == 3 for t in topics)

    client.force_login(admin_user)
    url = reverse("chat_api:chat-trending")
    resp = client.get(url, {"canal": canal.id, "dias": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["palavra"] == "legal"
    assert data[0]["frequencia"] == 3
