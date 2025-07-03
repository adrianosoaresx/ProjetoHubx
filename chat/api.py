from django.contrib.auth import get_user_model
from .models import Mensagem, Notificacao

User = get_user_model()


def get_user(pk: int):
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:  # pragma: no cover - simple fallback
        return None


def create_message(**kwargs):
    print("✅ Entrou em create_message com dados:")
    for k, v in kwargs.items():
        print(f"   {k}: {v}")
    """Create a chat message and return it."""
    return Mensagem.objects.create(**kwargs)


def notify_users(recipient_ids, remetente_id: int, message: Mensagem):
    """Create notifications for a list of recipients."""
    for uid in recipient_ids:
        Notificacao.objects.create(
            usuario_id=uid,
            remetente_id=remetente_id,
            mensagem=message,
        )
