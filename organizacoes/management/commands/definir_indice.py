from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError

from organizacoes.models import Organizacao


class Command(BaseCommand):
    help = "Define o índice de reajuste para uma organização"

    def add_arguments(self, parser):
        parser.add_argument("slug", help="Slug da organização")
        parser.add_argument("indice", type=float, help="Índice (ex: 0.1 para 10%% de reajuste)")

    def handle(self, *args, **options):
        slug = options["slug"]
        indice = Decimal(str(options["indice"]))
        try:
            org = Organizacao.objects.get(slug=slug)
        except Organizacao.DoesNotExist as exc:
            raise CommandError("Organização não encontrada") from exc
        org.indice_reajuste = indice
        org.save(update_fields=["indice_reajuste"])
        self.stdout.write(self.style.SUCCESS(f"Índice {indice} definido para {org.nome}"))
