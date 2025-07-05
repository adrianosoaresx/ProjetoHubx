from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid

from accounts.models import UserType, TokenAcesso


class Command(BaseCommand):
    help = "Corrige dados de usuários e tokens de acesso"

    def handle(self, *args, **options):
        User = get_user_model()

        # Garantir UserTypes padrao
        tipos_padrao = ["root", "admin", "gerente", "cliente"]
        tipos = {}
        for desc in tipos_padrao:
            tipo, _ = UserType.objects.get_or_create(descricao=desc)
            tipos[desc] = tipo
        self.stdout.write(f"UserTypes verificados: {', '.join(tipos_padrao)}")

        # Atribuir tipo CLIENTE para usuarios sem tipo
        qs_sem_tipo = User.objects.filter(tipo__isnull=True)
        count_users = qs_sem_tipo.count()
        if count_users:
            qs_sem_tipo.update(tipo=tipos["cliente"])
        self.stdout.write(f"Usuarios atualizados: {count_users}")

        # Ajustar tokens incompletos
        tokens = TokenAcesso.objects.all()
        updated_tokens = 0
        for token in tokens:
            changed = False
            if not token.tipo_destino:
                token.tipo_destino = TokenAcesso.Tipo.CLIENTE
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
        for desc in ["admin", "gerente", "cliente"]:
            TokenAcesso.objects.get_or_create(
                gerado_por=exemplo_user,
                tipo_destino=desc,
                defaults={"data_expiracao": timezone.now() + timedelta(days=30)},
            )
        self.stdout.write("Tokens de exemplo criados para admin, gerente e cliente")

