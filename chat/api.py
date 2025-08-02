from __future__ import annotations

from django.contrib.auth import get_user_model

from .models import ChatMessage, ChatNotification

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
    return ChatMessage.objects.create(**kwargs)


def notify_users(recipient_ids, message: ChatMessage) -> None:
    """Create notifications for a list of recipients."""
    for uid in recipient_ids:
        ChatNotification.objects.create(
            usuario_id=uid,
            mensagem=message,
        )


def add_reaction(message: ChatMessage, emoji: str) -> None:
    reactions = message.reactions
    reactions[emoji] = reactions.get(emoji, 0) + 1
    message.reactions = reactions
    message.save(update_fields=["reactions"])
