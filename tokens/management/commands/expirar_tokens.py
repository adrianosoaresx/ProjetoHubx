from django.core.management.base import BaseCommand
from django.utils import timezone
from tokens.models import TokenAcesso, CodigoAutenticacao

class Command(BaseCommand):
    help = "Marca tokens e códigos expirados como expirados."

    def handle(self, *args, **kwargs):
        agora = timezone.now()

        tokens_expirados = TokenAcesso.objects.filter(
            data_expiracao__lt=agora,
            estado=TokenAcesso.Estado.NOVO
        )
        tokens_expirados.update(estado=TokenAcesso.Estado.EXPIRADO)

        codigos_expirados = CodigoAutenticacao.objects.filter(
            expira_em__lt=agora,
            verificado=False
        )
        codigos_expirados.update(verificado=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"{tokens_expirados.count()} tokens e {codigos_expirados.count()} códigos expirados marcados como expirados."
            )
        )
