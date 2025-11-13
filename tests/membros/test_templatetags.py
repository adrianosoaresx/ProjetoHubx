import pytest

from accounts.factories import UserFactory
from accounts.models import UserType
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo

from membros.templatetags.membros_extras import usuario_badges, usuario_tipo_badge


@pytest.mark.django_db
class TestUsuarioTipoBadge:
    def test_returns_admin_badge_with_icon(self):
        user = UserFactory(user_type=UserType.ADMIN.value, organizacao=NucleoFactory().organizacao)
        user.nucleo = None
        user.save(update_fields=["nucleo"])

        badge = usuario_tipo_badge(user)

        assert badge is not None
        assert badge["label"] == UserType.ADMIN.label
        assert badge["icon"] == "shield-check"
        assert "#ef4444" in badge["style"]

    def test_detects_coordinator_from_associado_flags(self):
        nucleo = NucleoFactory()
        user = UserFactory(
            organizacao=nucleo.organizacao,
            is_associado=True,
            is_coordenador=True,
        )
        user.nucleo = nucleo
        user.save(update_fields=["nucleo", "is_associado", "is_coordenador"])

        badge = usuario_tipo_badge(user)

        assert badge is not None
        assert badge["label"] == UserType.COORDENADOR.label
        assert badge["icon"] == "flag"
        assert "#f97316" in badge["style"]


@pytest.mark.django_db
class TestUsuarioBadges:
    def test_includes_coordinator_badge_with_icon_and_nucleo(self):
        nucleo = NucleoFactory(nome="Núcleo Alfa")
        user = UserFactory(organizacao=nucleo.organizacao, is_associado=True)
        user.nucleo = None
        user.save(update_fields=["nucleo", "is_associado"])
        ParticipacaoNucleo.objects.create(
            user=user,
            nucleo=nucleo,
            status="ativo",
            papel="coordenador",
            papel_coordenador=ParticipacaoNucleo.PapelCoordenador.MARKETING,
        )

        badges = usuario_badges(user)

        assert any(
            badge["icon"] == "flag" and "Marketing" in badge["label"] and "Núcleo Alfa" in badge["label"]
            for badge in badges
        )

    def test_includes_consultor_badge_from_related_nucleo(self):
        nucleo = NucleoFactory()
        consultor = UserFactory(organizacao=nucleo.organizacao, user_type=UserType.CONSULTOR.value)
        consultor.nucleo = None
        consultor.save(update_fields=["nucleo"])
        nucleo.consultor = consultor
        nucleo.save(update_fields=["consultor"])

        badges = usuario_badges(consultor)

        assert any(badge["icon"] == "briefcase" and "Consultor" in badge["label"] for badge in badges)

    def test_fallback_to_associado_badge_has_icon(self):
        user = UserFactory(is_associado=True)
        user.nucleo = None
        user.save(update_fields=["nucleo", "is_associado"])

        badges = usuario_badges(user)

        assert badges
        assert badges[0]["icon"] == "id-card"
        assert "Associado" in badges[0]["label"]
        assert "#6366f1" in badges[0]["style"]

    def test_admin_excludes_nucleado_badges(self):
        nucleo = NucleoFactory()
        admin = UserFactory(organizacao=nucleo.organizacao, user_type=UserType.ADMIN.value)
        admin.nucleo = None
        admin.save(update_fields=["nucleo"])
        ParticipacaoNucleo.objects.create(user=admin, nucleo=nucleo, status="ativo")

        badges = usuario_badges(admin)

        assert all(badge["type"] != "nucleado" for badge in badges)
