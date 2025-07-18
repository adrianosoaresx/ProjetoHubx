from django.db import migrations
from django.utils.text import slugify


def populate_slug(apps, schema_editor):
    Organizacao = apps.get_model("organizacoes", "Organizacao")
    for organizacao in Organizacao.objects.all():
        base_slug = slugify(organizacao.nome)
        slug = base_slug
        counter = 1
        while Organizacao.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        organizacao.slug = slug
        organizacao.save()


class Migration(migrations.Migration):

    dependencies = [
        ("organizacoes", "0001_initial")
    ]

    operations = [
        migrations.RunPython(populate_slug),
    ]
