import uuid

import pytest
from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.apps import apps as global_apps


@pytest.mark.django_db(transaction=True)
def test_conversation_migrates_to_channel():
    executor = MigrationExecutor(connection)
    # Create a user before migrating backwards
    FinalUser = global_apps.get_model(settings.AUTH_USER_MODEL.split(".")[0], settings.AUTH_USER_MODEL.split(".")[1])
    final_user = FinalUser.objects.create(username="u", email="u@example.com")

    # Migrate to state before channels
    executor.migrate([
        ("chat", "0008_alter_chatmessage_options_remove_chatmessage_sender_and_more"),
    ])
    apps = executor.loader.project_state([
        ("chat", "0008_alter_chatmessage_options_remove_chatmessage_sender_and_more"),
    ]).apps

    User = apps.get_model(settings.AUTH_USER_MODEL.split(".")[0], settings.AUTH_USER_MODEL.split(".")[1])
    ChatConversation = apps.get_model("chat", "ChatConversation")
    ChatMessage = apps.get_model("chat", "ChatMessage")
    ChatParticipant = apps.get_model("chat", "ChatParticipant")

    user = User.objects.get(pk=final_user.pk)
    conv = ChatConversation.objects.create(
        titulo="t", slug="t", tipo_conversa="direta"
    )
    ChatParticipant.objects.create(conversation=conv, user=user)
    ChatMessage.objects.create(conversation=conv, remetente=user, tipo="text", conteudo="hi")

    # Run migrations forward to latest
    executor.loader.build_graph()
    executor.migrate([
        ("chat", "0012_remove_chatparticipant_conversation_and_more"),
    ])
    new_apps = executor.loader.project_state([
        ("chat", "0012_remove_chatparticipant_conversation_and_more"),
    ]).apps
    ChatMessage = new_apps.get_model("chat", "ChatMessage")
    ChatParticipant = new_apps.get_model("chat", "ChatParticipant")
    ChatChannel = new_apps.get_model("chat", "ChatChannel")

    assert ChatChannel.objects.count() == 1
    assert not ChatMessage.objects.filter(channel__isnull=True).exists()
    assert not ChatParticipant.objects.filter(channel__isnull=True).exists()
    assert not ChatMessage.objects.filter(channel_id=uuid.UUID("00000000-0000-0000-0000-000000000000")).exists()
