import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from membros.templatetags import membros_extras
from accounts.models import UserType


class _UserStub:
    nucleos_consultoria = None
    nucleo = None
    user_type = ""
    is_associado = False


def test_usuario_badges_deduplica_promocao_nucleado_mantendo_badges_de_nucleos(monkeypatch):
    user = _UserStub()

    monkeypatch.setattr(
        membros_extras,
        "_active_participacoes_data",
        lambda _user: [
            {
                "promotion_label": "Nucleado",
                "nucleo_nome": "Núcleo A",
                "nucleo_id": 1,
                "is_coordenador": False,
            },
            {
                "promotion_label": "Nucleado",
                "nucleo_nome": "Núcleo B",
                "nucleo_id": 2,
                "is_coordenador": False,
            },
        ],
    )

    badges = membros_extras.usuario_badges(user)

    assert [badge["label"] for badge in badges] == ["Nucleado", "Núcleo A", "Núcleo B"]
    assert [badge["group"] for badge in badges] == ["promotion", "nucleus", "nucleus"]


def test_usuario_badges_coordenador_reutiliza_cor_do_nucleo(monkeypatch):
    user = _UserStub()

    monkeypatch.setattr(
        membros_extras,
        "_active_participacoes_data",
        lambda _user: [
            {
                "promotion_label": "Coordenador Geral",
                "nucleo_nome": "Núcleo A",
                "nucleo_id": 10,
                "is_coordenador": True,
            }
        ],
    )

    badges = membros_extras.usuario_badges(user)

    assert [badge["group"] for badge in badges] == ["promotion", "nucleus"]
    assert badges[0]["style"] == badges[1]["style"]
    assert badges[0]["style"] == membros_extras._nucleo_style(10)


def test_usuario_badges_coordenador_em_dois_nucleos_gera_cores_distintas(monkeypatch):
    user = _UserStub()

    monkeypatch.setattr(
        membros_extras,
        "_active_participacoes_data",
        lambda _user: [
            {
                "promotion_label": "Coordenador Geral",
                "nucleo_nome": "Núcleo A",
                "nucleo_id": 1,
                "is_coordenador": True,
            },
            {
                "promotion_label": "Coordenador Geral",
                "nucleo_nome": "Núcleo B",
                "nucleo_id": 2,
                "is_coordenador": True,
            },
        ],
    )

    badges = membros_extras.usuario_badges(user)

    assert [badge["group"] for badge in badges] == ["promotion", "nucleus", "promotion", "nucleus"]
    assert badges[0]["style"] == badges[1]["style"]
    assert badges[2]["style"] == badges[3]["style"]
    assert badges[0]["style"] != badges[2]["style"]


def test_nucleo_style_sem_nucleo_id_faz_fallback_para_estilo_coordenador():
    assert membros_extras._nucleo_style(None) == membros_extras.BADGE_STYLES["coordenador"]


def test_usuario_badges_admin_nao_mostra_promocao_ou_nucleo(monkeypatch):
    user = _UserStub()
    user.user_type = UserType.ADMIN.value

    monkeypatch.setattr(
        membros_extras,
        "_active_participacoes_data",
        lambda _user: [
            {
                "promotion_label": "Nucleado",
                "nucleo_nome": "Núcleo A",
                "nucleo_id": 1,
                "is_coordenador": False,
            }
        ],
    )

    assert membros_extras.usuario_badges(user) == []


def test_usuario_badges_operador_nao_mostra_promocao_ou_nucleo(monkeypatch):
    user = _UserStub()
    user.user_type = UserType.OPERADOR.value

    monkeypatch.setattr(
        membros_extras,
        "_active_participacoes_data",
        lambda _user: [
            {
                "promotion_label": "Coordenador",
                "nucleo_nome": "Núcleo B",
                "nucleo_id": 2,
                "is_coordenador": True,
            }
        ],
    )

    assert membros_extras.usuario_badges(user) == []
