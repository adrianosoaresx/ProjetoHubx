from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Remove contas marcadas para exclusão há mais de 30 dias"

    def handle(self, *args, **options):
        User = get_user_model()
        limite = timezone.now() - timezone.timedelta(days=30)
        qs = User.objects.filter(deleted=True, deleted_at__lt=limite, exclusao_confirmada=True)
        count = 0
        for user in qs:
            user.delete(soft=False)
            count += 1
        self.stdout.write(f"{count} contas removidas")
