from __future__ import annotations

from django.db import migrations
from django.db.models import Prefetch, Q


def assign_organization_from_tokens(apps, schema_editor):  # noqa: ARG001
    User = apps.get_model("accounts", "User")
    TokenAcesso = apps.get_model("tokens", "TokenAcesso")
    ConviteNucleo = apps.get_model("nucleos", "ConviteNucleo")

    convidados_sem_org = User.objects.filter(
        user_type="convidado", organizacao__isnull=True
    ).select_related("nucleo__organizacao")

    token_base_qs = TokenAcesso.objects.filter(
        usuario__isnull=True,
        tipo_destino="convidado",
    ).order_by("-created_at")

    convite_nucleo_prefetch = Prefetch(
        "convites_nucleo",
        queryset=ConviteNucleo.objects.select_related("nucleo__organizacao").order_by(
            "-created_at"
        ),
    )

    for user in convidados_sem_org.iterator():
        if getattr(user, "nucleo", None) and user.nucleo.organizacao_id:
            user.organizacao_id = user.nucleo.organizacao_id
            user.save(update_fields=["organizacao", "updated_at"])
            continue

        email = (user.email or "").strip()
        token_qs = token_base_qs
        if email:
            token_qs = token_qs.filter(
                Q(convites_nucleo__email__iexact=email)
                | Q(pre_registros_convite__email__iexact=email)
            )

        token = (
            token_qs.select_related("organizacao")
            .prefetch_related(convite_nucleo_prefetch)
            .first()
        )

        if not token:
            continue

        convite_nucleo = next(iter(token.convites_nucleo.all()), None)
        if convite_nucleo and convite_nucleo.nucleo_id:
            organizacao_id = convite_nucleo.nucleo.organizacao_id
        else:
            organizacao_id = token.organizacao_id

        if organizacao_id:
            user.organizacao_id = organizacao_id
            user.save(update_fields=["organizacao", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0023_accounttoken_status"),
        ("tokens", "0020_totpdevice_base32_secrets"),
        ("nucleos", "0013_nucleomidia"),
        ("eventos", "0034_preregistroconvite"),  # garante que pre_registros_convite exista
    ]

    operations = [
        migrations.RunPython(assign_organization_from_tokens, migrations.RunPython.noop),
    ]
