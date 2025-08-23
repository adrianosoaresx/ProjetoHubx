import pytest

from configuracoes.serializers import ConfiguracaoContaSerializer

pytestmark = pytest.mark.django_db


def test_serializer_valid_data(admin_user):
    config = admin_user.configuracao
    data = {
        "receber_notificacoes_email": False,
        "frequencia_notificacoes_email": "diaria",
        "receber_notificacoes_whatsapp": True,
        "frequencia_notificacoes_whatsapp": "semanal",
        "receber_notificacoes_push": True,
        "frequencia_notificacoes_push": "imediata",
        "idioma": "en-US",
        "tema": "escuro",
        "hora_notificacao_diaria": "08:00:00",
        "hora_notificacao_semanal": "09:00:00",
        "dia_semana_notificacao": 1,
    }
    serializer = ConfiguracaoContaSerializer(instance=config, data=data)
    assert serializer.is_valid(), serializer.errors
    obj = serializer.save()
    config.refresh_from_db()
    assert obj == config
    assert config.receber_notificacoes_email is False
    assert config.frequencia_notificacoes_email == "imediata"
    assert config.frequencia_notificacoes_whatsapp == "semanal"


def test_serializer_requires_daily_time(admin_user):
    config = admin_user.configuracao
    serializer = ConfiguracaoContaSerializer(
        instance=config,
        data={"frequencia_notificacoes_email": "diaria"},
        partial=True,
    )
    assert not serializer.is_valid()
    assert "hora_notificacao_diaria" in serializer.errors


def test_serializer_requires_weekly_fields(admin_user):
    config = admin_user.configuracao
    serializer = ConfiguracaoContaSerializer(
        instance=config,
        data={"frequencia_notificacoes_push": "semanal"},
        partial=True,
    )
    assert not serializer.is_valid()
    assert "hora_notificacao_semanal" in serializer.errors
    assert "dia_semana_notificacao" in serializer.errors
