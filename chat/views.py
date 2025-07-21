from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .forms import NovaConversaForm, NovaMensagemForm
from .models import ChatConversation, ChatParticipant

User = get_user_model()


@login_required
def conversation_list(request):
    qs = (
        ChatConversation.objects.filter(participants__user=request.user)
        .select_related("organizacao", "nucleo", "evento")
        .prefetch_related("participants")
        .distinct()
    )
    grupos = {
        "direta": qs.filter(tipo_conversa="direta"),
        "grupo": qs.filter(tipo_conversa="grupo"),
        "organizacao": qs.filter(tipo_conversa="organizacao"),
        "nucleo": qs.filter(tipo_conversa="nucleo"),
        "evento": qs.filter(tipo_conversa="evento"),
    }
    return render(request, "chat/conversation_list.html", {"grupos": grupos})


@login_required
def nova_conversa(request):
    if request.method == "POST":
        form = NovaConversaForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            conv = form.save(commit=False)
            if not conv.slug:
                conv.slug = slugify(conv.titulo or "conv")
            conv.save()
            ChatParticipant.objects.create(conversation=conv, user=request.user, is_owner=True)
            return redirect("chat:conversation_detail", slug=conv.slug)
    else:
        form = NovaConversaForm(user=request.user)
    return render(request, "chat/conversation_form.html", {"form": form})


@login_required
def conversation_detail(request, slug):
    conversation = get_object_or_404(
        ChatConversation.objects.prefetch_related("messages__lido_por", "participants__user"),
        slug=slug,
        participants__user=request.user,
    )
    if request.method == "POST":
        form = NovaMensagemForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.conversation = conversation
            msg.organizacao = conversation.organizacao
            msg.sender = request.user
            msg.save()
            msg.lido_por.add(request.user)
        return redirect("chat:conversation_detail", slug=slug)
    else:
        form = NovaMensagemForm()
    mensagens = conversation.messages.select_related("sender").prefetch_related("lido_por")
    return render(
        request,
        "chat/conversation_detail.html",
        {"conversation": conversation, "mensagens": mensagens, "form": form},
    )
