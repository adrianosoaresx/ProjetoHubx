from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, OuterRef, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from .forms import NovaConversaForm, NovaMensagemForm
from .models import ChatChannel, ChatMessage, ChatNotification
from .services import criar_canal, enviar_mensagem

User = get_user_model()


@login_required
def conversation_list(request):
    last_msg = ChatMessage.objects.filter(channel=OuterRef("pk")).order_by("-timestamp")
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
            last_message_at=Subquery(last_msg.values("timestamp")[:1]),
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
def conversation_detail(request, channel_id):
    conversation = get_object_or_404(
        ChatChannel.objects.prefetch_related("messages__lido_por", "participants__user"),
        pk=channel_id,
        participants__user=request.user,
    )
    is_admin = conversation.participants.filter(user=request.user, is_admin=True).exists()
    is_owner = conversation.participants.filter(user=request.user, is_owner=True).exists()
    if request.method == "POST":
        form = NovaMensagemForm(request.POST, request.FILES)
        if form.is_valid():
            msg = enviar_mensagem(
                canal=conversation,
                remetente=request.user,
                tipo=form.cleaned_data.get("tipo", "text"),
                conteudo=form.cleaned_data.get("conteudo", ""),
                arquivo=form.cleaned_data.get("arquivo"),
            )
            msg.lido_por.add(request.user)
            if request.headers.get("HX-Request"):
                return render(
                    request,
                    "chat/partials/message.html",
                    {"m": msg, "is_admin": is_admin},
                )
            messages.success(request, _("Mensagem enviada."))
            return redirect("chat:conversation_detail", channel_id=channel_id)
        messages.error(request, _("Erro ao enviar mensagem."))
        if request.headers.get("HX-Request"):
            return HttpResponse(status=400)
        return redirect("chat:conversation_detail", channel_id=channel_id)
    else:
        form = NovaMensagemForm()
    qs = conversation.messages.select_related("remetente").prefetch_related("lido_por")
    pinned = qs.filter(pinned_at__isnull=False)
    mensagens = qs.filter(pinned_at__isnull=True)
    return render(
        request,
        "chat/conversation_detail.html",
        {
            "conversation": conversation,
            "messages": mensagens,
            "pinned_messages": pinned,
            "form": form,
            "is_admin": is_admin,
            "is_owner": is_owner,
        },
    )


@login_required
def message_partial(request, message_id):
    message = get_object_or_404(ChatMessage.objects.select_related("remetente"), pk=message_id)
    is_admin = message.channel.participants.filter(user=request.user, is_admin=True).exists()
    return render(request, "chat/partials/message.html", {"m": message, "is_admin": is_admin})
