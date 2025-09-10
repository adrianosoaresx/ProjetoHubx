from __future__ import annotations

from django.core.management.base import BaseCommand

from accounts.tasks import purge_soft_deleted


class Command(BaseCommand):
    help = "Executa a purga de contas soft-deleted imediatamente"

    def handle(self, *args, **options):
        purge_soft_deleted()
        self.stdout.write(self.style.SUCCESS("Purga concluída"))
