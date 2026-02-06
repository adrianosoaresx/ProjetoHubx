from django.db import migrations


LANGUAGE_ALIASES = {
    "en-us": "en",
    "es-es": "es",
    "pt-br": "pt-br",
}


def normalize_idioma_codes(apps, schema_editor):
    ConfiguracaoConta = apps.get_model("configuracoes", "ConfiguracaoConta")

    for config in ConfiguracaoConta.objects.all().only("id", "idioma"):
        current = (config.idioma or "").replace("_", "-").lower()
        normalized = LANGUAGE_ALIASES.get(current, current)
        if normalized and normalized != config.idioma:
            ConfiguracaoConta.objects.filter(pk=config.pk).update(idioma=normalized)


def reverse_normalize_idioma_codes(apps, schema_editor):
    ConfiguracaoConta = apps.get_model("configuracoes", "ConfiguracaoConta")
    reverse_aliases = {
        "en": "en-US",
        "es": "es-ES",
        "pt-br": "pt-BR",
    }

    for config in ConfiguracaoConta.objects.all().only("id", "idioma"):
        current = (config.idioma or "").replace("_", "-").lower()
        legacy = reverse_aliases.get(current)
        if legacy and legacy != config.idioma:
            ConfiguracaoConta.objects.filter(pk=config.pk).update(idioma=legacy)


class Migration(migrations.Migration):

    dependencies = [
        ("configuracoes", "0011_alter_configuracaoconta_idioma"),
    ]

    operations = [
        migrations.RunPython(normalize_idioma_codes, reverse_normalize_idioma_codes),
    ]
