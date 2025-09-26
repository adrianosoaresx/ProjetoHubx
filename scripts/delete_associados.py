"""Script para remover definitivamente usuários associados e seus relacionamentos.

Este utilitário inicializa o ambiente Django, localiza todos os usuários que
possuem ``is_associado=True`` (incluindo nucleados e coordenadores) e realiza a
exclusão definitiva desses registros junto de todas as relações relevantes em
outros aplicativos do sistema. Todos os modelos que utilizam ``SoftDeleteModel``
possuem uma chamada explícita para ``hard_delete`` garantindo que os dados sejam
removidos do banco de dados em vez de apenas marcados como deletados.

Para executar:

```
python scripts/delete_associados.py
```

O script imprime um resumo das remoções enquanto executa.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import django


def setup_django() -> None:
    """Configura o ambiente Django para que o ORM possa ser utilizado."""

    base_dir = Path(__file__).resolve().parents[1]
    if str(base_dir) not in sys.path:
        sys.path.append(str(base_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
    django.setup()


def hard_delete_queryset(queryset, description: str) -> int:
    """Realiza ``hard_delete`` em todos os objetos do *queryset* informado."""

    total = 0
    for obj in queryset.iterator():
        if hasattr(obj, "hard_delete"):
            obj.hard_delete()
        else:
            obj.delete()
        total += 1
    if total:
        print(f"    - {description}: {total}")
    return total


def purge_evento(evento) -> None:
    """Remove o evento e todos os relacionamentos associados."""

    from eventos.models import EventoLog, FeedbackNota, InscricaoEvento, ParceriaEvento

    print(f"  Removendo evento {evento.pk} ({evento.titulo})")
    hard_delete_queryset(InscricaoEvento.all_objects.filter(evento=evento), "inscrições")
    hard_delete_queryset(FeedbackNota.all_objects.filter(evento=evento), "feedbacks")
    hard_delete_queryset(ParceriaEvento.all_objects.filter(evento=evento), "parcerias")
    hard_delete_queryset(EventoLog.all_objects.filter(evento=evento), "logs")
    evento.delete(soft=False)


def purge_user(user) -> None:
    """Remove relacionamentos derivados do usuário antes de excluí-lo."""

    from accounts.models import AccountToken, SecurityEvent, UserMedia
    from configuracoes.models import ConfiguracaoConta, ConfiguracaoContaLog
    from eventos.models import Evento, FeedbackNota, InscricaoEvento
    from feed.models import Bookmark, Comment, Flag, Post, PostView, Reacao
    from nucleos.models import CoordenadorSuplente, ParticipacaoNucleo
    from notificacoes.models import (
        HistoricoNotificacao,
        NotificationLog,
        PushSubscription,
        UserNotificationPreference,
    )
    from tokens.models import (
        CodigoAutenticacao,
        TOTPDevice,
        TokenAcesso,
    )
    from webhooks.models import WebhookSubscription

    print(f"Processando usuário {user.pk} ({user.email})")

    # Remove vínculos sociais antes da exclusão definitiva
    user.connections.clear()
    user.followers.clear()
    user.following.clear()

    hard_delete_queryset(UserMedia.all_objects.filter(user=user), "mídias do usuário")
    hard_delete_queryset(AccountToken.all_objects.filter(usuario=user), "tokens de conta")
    hard_delete_queryset(SecurityEvent.all_objects.filter(usuario=user), "eventos de segurança")
    hard_delete_queryset(TokenAcesso.all_objects.filter(usuario=user), "tokens recebidos")
    hard_delete_queryset(TokenAcesso.all_objects.filter(gerado_por=user), "tokens gerados")
    hard_delete_queryset(CodigoAutenticacao.all_objects.filter(usuario=user), "códigos de autenticação")
    hard_delete_queryset(TOTPDevice.all_objects.filter(usuario=user), "dispositivos TOTP")

    hard_delete_queryset(ParticipacaoNucleo.all_objects.filter(user=user), "participações em núcleos")
    hard_delete_queryset(CoordenadorSuplente.all_objects.filter(usuario=user), "coordenações suplentes")

    hard_delete_queryset(InscricaoEvento.all_objects.filter(user=user), "inscrições em eventos")
    hard_delete_queryset(FeedbackNota.all_objects.filter(usuario=user), "feedbacks enviados")

    hard_delete_queryset(PushSubscription.all_objects.filter(user=user), "inscrições push")
    UserNotificationPreference.objects.filter(user=user).delete()
    HistoricoNotificacao.objects.filter(user=user).delete()
    NotificationLog.objects.filter(user=user).delete()

    hard_delete_queryset(ConfiguracaoConta.all_objects.filter(user=user), "configurações de conta")
    ConfiguracaoContaLog.objects.filter(user=user).delete()

    hard_delete_queryset(WebhookSubscription.all_objects.filter(user=user), "webhooks")

    PostView.objects.filter(user=user).delete()
    hard_delete_queryset(Bookmark.all_objects.filter(user=user), "bookmarks criados")
    hard_delete_queryset(Comment.all_objects.filter(user=user), "comentários criados")
    hard_delete_queryset(Flag.all_objects.filter(user=user), "denúncias criadas")
    hard_delete_queryset(Reacao.all_objects.filter(user=user), "reações criadas")

    user_posts = Post.all_objects.filter(autor=user)
    post_ids = list(user_posts.values_list("id", flat=True))
    if post_ids:
        hard_delete_queryset(Comment.all_objects.filter(post_id__in=post_ids), "comentários em posts do usuário")
        hard_delete_queryset(Flag.all_objects.filter(post_id__in=post_ids), "denúncias em posts do usuário")
        hard_delete_queryset(Bookmark.all_objects.filter(post_id__in=post_ids), "bookmarks em posts do usuário")
        hard_delete_queryset(Reacao.all_objects.filter(post_id__in=post_ids), "reações em posts do usuário")
        PostView.objects.filter(post_id__in=post_ids).delete()
        hard_delete_queryset(user_posts, "posts do usuário")

    eventos_coordenados = Evento.all_objects.filter(coordenador=user)
    for evento in eventos_coordenados.iterator():
        purge_evento(evento)


def main() -> None:
    setup_django()

    from django.contrib.auth import get_user_model
    from django.db import transaction

    User = get_user_model()

    associados = User.all_objects.filter(is_associado=True)
    total = associados.count()
    print(f"Usuários associados encontrados: {total}")

    if total == 0:
        return

    with transaction.atomic():
        for index, user in enumerate(associados.iterator(), start=1):
            print(f"[{index}/{total}] Iniciando remoção definitiva")
            purge_user(user)
            user.delete(soft=False)
            print(f"Usuário {user.pk} removido definitivamente.\n")

    print("Processo concluído com sucesso.")


if __name__ == "__main__":
    main()

