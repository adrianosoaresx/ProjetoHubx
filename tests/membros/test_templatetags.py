import pytest

from accounts.factories import UserFactory
from accounts.models import UserType
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo

from django.template import Context, Template

from membros.templatetags.membros_extras import rating_stars, usuario_badges, usuario_tipo_badge


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
        user.nucleo = None
        user.save(update_fields=["nucleo", "is_associado", "is_coordenador"])

        badge = usuario_tipo_badge(user)

        assert badge is not None
        assert badge["label"] == UserType.COORDENADOR.label
        assert badge["icon"] == "flag"
        assert "#f97316" in badge["style"]

    def test_coordinator_tipo_badge_hidden_when_nucleo_badge_present(self):
        nucleo = NucleoFactory()
        user = UserFactory(
            organizacao=nucleo.organizacao,
            is_associado=True,
            is_coordenador=True,
        )
        user.nucleo = nucleo
        user.save(update_fields=["nucleo", "is_associado", "is_coordenador"])
        ParticipacaoNucleo.objects.create(
            user=user,
            nucleo=nucleo,
            status="ativo",
            papel="coordenador",
            papel_coordenador=ParticipacaoNucleo.PapelCoordenador.COORDENADOR_GERAL,
        )

        tipo_badge = usuario_tipo_badge(user)
        badges = usuario_badges(user)

        assert tipo_badge is None
        assert any(badge["type"] == "coordenador" for badge in badges)
        assert not any(badge["type"] == "associado" for badge in badges)


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

    def test_consultor_tipo_badge_hidden_when_nucleo_badge_present(self):
        nucleo = NucleoFactory()
        consultor = UserFactory(
            organizacao=nucleo.organizacao,
            user_type=UserType.CONSULTOR.value,
        )
        consultor.nucleo = None
        consultor.save(update_fields=["nucleo", "user_type"])
        nucleo.consultor = consultor
        nucleo.save(update_fields=["consultor"])

        tipo_badge = usuario_tipo_badge(consultor)
        badges = usuario_badges(consultor)

        assert tipo_badge is None
        assert any(
            badge["type"] == "consultor" and nucleo.nome in badge["label"]
            for badge in badges
        )

    def test_fallback_to_associado_badge_has_icon(self):
        user = UserFactory(is_associado=True)
        user.nucleo = None
        user.save(update_fields=["nucleo", "is_associado"])

        badges = usuario_badges(user)

        assert badges
        assert badges[0]["icon"] == "id-card"
        assert "Associado" in badges[0]["label"]
        assert "#6366f1" in badges[0]["style"]

    def test_associado_badge_only_once_when_user_type_matches(self):
        user = UserFactory(is_associado=True, user_type=UserType.ASSOCIADO.value)
        user.nucleo = None
        user.save(update_fields=["nucleo", "is_associado", "user_type"])

        badges = usuario_badges(user)

        assert len(badges) == 1
        assert badges[0]["type"] == "associado"

    def test_associado_badge_only_once_without_flag(self):
        user = UserFactory(is_associado=False, user_type=UserType.ASSOCIADO.value)
        user.nucleo = None
        user.save(update_fields=["nucleo", "user_type"])

        badges = usuario_badges(user)

        assert len(badges) == 1
        assert badges[0]["type"] == "associado"

    def test_admin_excludes_nucleado_badges(self):
        nucleo = NucleoFactory()
        admin = UserFactory(organizacao=nucleo.organizacao, user_type=UserType.ADMIN.value)
        admin.nucleo = None
        admin.save(update_fields=["nucleo"])
        ParticipacaoNucleo.objects.create(user=admin, nucleo=nucleo, status="ativo")

        badges = usuario_badges(admin)

        assert all(badge["type"] != "nucleado" for badge in badges)


class TestRatingStars:
    @pytest.mark.parametrize(
        "rating,expected",
        [
            (5, ["full", "full", "full", "full", "full"]),
            (4.74, ["full", "full", "full", "full", "half"]),
            (3.26, ["full", "full", "full", "half", "empty"]),
            (2.24, ["full", "full", "empty", "empty", "empty"]),
            (0, ["empty", "empty", "empty", "empty", "empty"]),
            (None, ["empty", "empty", "empty", "empty", "empty"]),
            (7, ["full", "full", "full", "full", "full"]),
        ],
    )
    def test_returns_expected_star_states(self, rating, expected):
        assert rating_stars(rating) == expected

    def test_template_usage_renders_sequence(self):
        template = Template("""{% load membros_extras %}{% rating_stars value as stars %}{% for star in stars %}{{ star }} {% endfor %}""")

        result = template.render(Context({"value": 1.3}))

        assert result.strip() == "full half empty empty empty"
