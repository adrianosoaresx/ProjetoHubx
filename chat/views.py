from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Subquery, UUIDField
from django.http import HttpResponse
import csv
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _

from .forms import NovaConversaForm
from .models import ChatChannel, ChatMessage, ChatModerationLog, ChatNotification
from .services import criar_canal

User = get_user_model()


@login_required
def conversation_list(request):
    last_msg = ChatMessage.objects.filter(channel=OuterRef("pk")).order_by("-created_at")
    unread = (
        ChatNotification.objects.filter(usuario=request.user, mensagem__channel=OuterRef("pk"), lido=False)
        .values("mensagem__channel")
        .annotate(cnt=Count("id"))
        .values("cnt")
    )
    qs = (
        ChatChannel.objects.filter(participants__user=request.user)
        .prefetch_related("participants")
        .annotate(
            last_message_text=Subquery(last_msg.values("conteudo")[:1]),
            last_message_at=Subquery(last_msg.values("created_at")[:1]),
            unread_count=Subquery(unread),
        )
        .distinct()
    )
    grupos = {
        "privado": qs.filter(contexto_tipo="privado"),
        "organizacao": qs.filter(contexto_tipo="organizacao"),
        "nucleo": qs.filter(contexto_tipo="nucleo"),
        "evento": qs.filter(contexto_tipo="evento"),
    }
    return render(
        request,
        "chat/conversation_list.html",
        {"grupos": grupos, "conversas": qs},
    )


@login_required
def nova_conversa(request):
    if request.method == "POST":
        form = NovaConversaForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            canal = criar_canal(
                criador=request.user,
                contexto_tipo=form.cleaned_data.get("contexto_tipo"),
                contexto_id=form.cleaned_data.get("contexto_id"),
                titulo=form.cleaned_data.get("titulo"),
                descricao=form.cleaned_data.get("descricao"),
                participantes=form.cleaned_data.get("participants") or [],
                imagem=form.cleaned_data.get("imagem"),
            )
            messages.success(request, _("Conversa criada com sucesso."))
            return redirect("chat:conversation_detail", channel_id=canal.pk)
        messages.error(request, _("Erro ao criar conversa."))
    else:
        form = NovaConversaForm(user=request.user)
    return render(request, "chat/conversation_form.html", {"form": form})


@login_required
def contextos(request):
    tipo = request.GET.get("contexto_tipo")
    options: list[tuple[str, str]] = []
    if tipo == "organizacao":
        org = getattr(request.user, "organizacao", None)
        if org:
            options = [(str(org.id), str(org))]
    elif tipo == "nucleo":
        from nucleos.models import Nucleo

        qs = Nucleo.objects.filter(
            participacoes__user=request.user,
            participacoes__status="ativo",
            participacoes__status_suspensao=False,
        ).values_list("id", "nome")
        options = [(str(pk), name) for pk, name in qs]
    elif tipo == "evento":
        from agenda.models import Evento

        qs = Evento.objects.filter(
            inscricoes__user=request.user,
            inscricoes__status="confirmada",
        ).values_list("id", "titulo")
        options = [(str(pk), title) for pk, title in qs]

    from django.utils.html import format_html_join

    html = format_html_join(
        "",
        '<option value="{}">{}</option>',
        ((pk, name) for pk, name in options),
    )
    return HttpResponse(html)


@login_required
def conversation_detail(request, channel_id):
    conversation = get_object_or_404(
        ChatChannel.objects.prefetch_related("messages__lido_por", "participants__user"),
        pk=channel_id,
        participants__user=request.user,
    )
    is_admin = conversation.participants.filter(user=request.user, is_admin=True).exists()
    is_owner = conversation.participants.filter(user=request.user, is_owner=True).exists()
    qs = conversation.messages.select_related("remetente").prefetch_related("lido_por")
    pinned = qs.filter(pinned_at__isnull=False)
    mensagens = qs.filter(pinned_at__isnull=True)
    from django.urls import reverse

    history_url = reverse("chat_api:chat-channel-messages-history", args=[conversation.id])
    return render(
        request,
        "chat/conversation_detail.html",
        {
            "conversation": conversation,
            "messages": mensagens,
            "pinned_messages": pinned,
            "is_admin": is_admin,
            "is_owner": is_owner,
            "history_url": history_url,
        },
    )


@login_required
def message_partial(request, message_id):
    message = get_object_or_404(ChatMessage.objects.select_related("remetente"), pk=message_id)
    is_admin = message.channel.participants.filter(user=request.user, is_admin=True).exists()
    return render(request, "chat/partials/message.html", {"m": message, "is_admin": is_admin})


@login_required
def historico_edicoes(request, channel_id, message_id):
    channel = get_object_or_404(ChatChannel, pk=channel_id, participants__user=request.user)
    message = get_object_or_404(ChatMessage, pk=message_id, channel=channel)
    is_admin = channel.participants.filter(user=request.user, is_admin=True).exists() or request.user.is_staff
    if not is_admin:
        return HttpResponse(status=403)
    logs = (
        ChatModerationLog.objects.filter(message=message, action="edit")
        .select_related("moderator")
        .order_by("-created_at")
    )
    inicio = request.GET.get("inicio")
    fim = request.GET.get("fim")
    if inicio:
        dt = parse_date(inicio)
        if dt:
            logs = logs.filter(created_at__date__gte=dt)
    if fim:
        dt = parse_date(fim)
        if dt:
            logs = logs.filter(created_at__date__lte=dt)
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=historico_edicoes.csv"
        writer = csv.writer(response)
        writer.writerow(["created_at", "moderator", "previous_content"])
        for log in logs:
            writer.writerow([log.created_at.isoformat(), log.moderator.username, log.previous_content])
        return response
    paginator = Paginator(logs, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "chat/historico_edicoes.html",
        {"channel": channel, "message": message, "logs": page},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def moderacao(request):
    msgs = (
        ChatMessage.objects.filter(flags__isnull=False)
        .annotate(flags_count=Count("flags"))
        .select_related("remetente", "channel")
    )
    return render(request, "chat/moderacao.html", {"mensagens": msgs})


@login_required
def exportar_modal(request, channel_id):
    channel = get_object_or_404(ChatChannel, pk=channel_id, participants__user=request.user)
    is_admin = channel.participants.filter(user=request.user, is_admin=True).exists()
    if not is_admin:
        return HttpResponse(status=403)
    return render(request, "chat/partials/export_modal.html", {"channel": channel})


@login_required
def modal_users(request):
    users = User.objects.exclude(pk=request.user.pk).order_by("username")
    return render(request, "chat/modal_user_list.html", {"users": users})


@login_required
def modal_room(request, user_id):
    if isinstance(User._meta.pk, UUIDField):
        other = get_object_or_404(User, pk=user_id)
    else:
        other = get_object_or_404(User, pk=user_id.int)
    channel = (
        ChatChannel.objects.filter(contexto_tipo="privado", participants__user=request.user)
        .filter(participants__user=other)
        .first()
    )
    if channel is None:
        channel = criar_canal(
            criador=request.user,
            contexto_tipo="privado",
            contexto_id=request.user.nucleo_id,
            titulo="",
            descricao="",
            participantes=[other],
        )
    messages = (
        channel.messages.select_related("remetente").order_by("-created_at")[:20]
    )
    messages = list(messages)[::-1]
    return render(
        request,
        "chat/modal_room.html",
        {"dest": other, "messages": messages},
    )
