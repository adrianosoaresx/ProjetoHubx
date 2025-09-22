import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import UserType
from tokens.models import TokenAcesso


class Command(BaseCommand):
    help = "Corrige dados de usuários e tokens de acesso"

    def handle(self, *args, **options):
        User = get_user_model()

        # Garantir campo user_type preenchido
        qs_sem_tipo = User.objects.filter(user_type__isnull=True)
        count_users = qs_sem_tipo.count()
        if count_users:
            qs_sem_tipo.update(user_type=UserType.ASSOCIADO)
        self.stdout.write(f"Usuarios atualizados: {count_users}")

        # Ajustar tokens incompletos
        tokens = TokenAcesso.objects.all()
        updated_tokens = 0
        for token in tokens:
            changed = False
            if not token.tipo_destino:
                token.tipo_destino = TokenAcesso.TipoUsuario.ASSOCIADO
                changed = True
            if not token.codigo:
                token.codigo = uuid.uuid4().hex
                changed = True
            if not token.data_expiracao:
                token.data_expiracao = timezone.now() + timedelta(days=30)
                changed = True
            if changed:
                token.save()
                updated_tokens += 1
        self.stdout.write(f"Tokens corrigidos: {updated_tokens}")

        # Criar tokens de exemplo para testes
        exemplo_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        for tipo in TokenAcesso.TipoUsuario.values:
            TokenAcesso.objects.get_or_create(
                gerado_por=exemplo_user,
                tipo_destino=tipo,
                defaults={"data_expiracao": timezone.now() + timedelta(days=30)},
            )
        self.stdout.write("Tokens de exemplo criados para os novos tipos suportados")
