import pytest

from agenda.factories import EventoFactory
from agenda.models import FeedbackNota, InscricaoEvento

pytestmark = pytest.mark.django_db


def test_inscricao_nao_possui_campo_avaliacao():
    assert not any(f.name == "avaliacao" for f in InscricaoEvento._meta.get_fields())


def test_feedback_nota_mantem_avaliacao():
    evento = EventoFactory()
    user = evento.coordenador
    InscricaoEvento.objects.create(user=user, evento=evento)
    FeedbackNota.objects.create(evento=evento, usuario=user, nota=5)
    assert FeedbackNota.objects.filter(evento=evento, usuario=user, nota=5).exists()
