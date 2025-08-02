from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from .forms import NovaConversaForm, NovaMensagemForm
from .models import ChatChannel, ChatMessage, ChatParticipant

User = get_user_model()


@login_required
def conversation_list(request):
    last_msg = ChatMessage.objects.filter(channel=OuterRef("pk")).order_by("-timestamp")
    qs = (
        ChatChannel.objects.filter(participants__user=request.user)
        .prefetch_related("participants")
        .annotate(
            last_message_text=Subquery(last_msg.values("conteudo")[:1]),
            last_message_at=Subquery(last_msg.values("timestamp")[:1]),
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
            conv = form.save(commit=False)
            conv.contexto_tipo = "privado"
            conv.save()
            ChatParticipant.objects.create(channel=conv, user=request.user, is_owner=True)
            for user in form.cleaned_data.get("participants"):
                ChatParticipant.objects.get_or_create(channel=conv, user=user)
            messages.success(request, _("Conversa criada com sucesso."))
            return redirect("chat:conversation_detail", channel_id=conv.pk)
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
    if request.method == "POST":
        form = NovaMensagemForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.channel = conversation
            msg.remetente = request.user
            msg.save()
            msg.lido_por.add(request.user)
            if request.headers.get("HX-Request"):
                return render(request, "chat/partials/message.html", {"m": msg})
            messages.success(request, _("Mensagem enviada."))
            return redirect("chat:conversation_detail", channel_id=channel_id)
        messages.error(request, _("Erro ao enviar mensagem."))
        if request.headers.get("HX-Request"):
            return HttpResponse(status=400)
        return redirect("chat:conversation_detail", channel_id=channel_id)
    else:
        form = NovaMensagemForm()
    mensagens = conversation.messages.select_related("remetente").prefetch_related("lido_por")
    return render(
        request,
        "chat/conversation_detail.html",
        {"conversation": conversation, "mensagens": mensagens, "form": form},
    )
