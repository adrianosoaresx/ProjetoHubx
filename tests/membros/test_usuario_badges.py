import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from membros.templatetags import membros_extras


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
