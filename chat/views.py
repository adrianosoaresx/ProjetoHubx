from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.conf import settings
import uuid

from .models import Mensagem, Notificacao


@login_required
def chat_index(request):
    users = (
        get_user_model()
        .objects.filter(nucleo=request.user.nucleo)
        .exclude(id=request.user.id)
    )
    return render(request, "chat/index.html", {"users": users})


@login_required
def chat_room(request, user_id):
    dest = get_object_or_404(get_user_model(), pk=user_id, nucleo=request.user.nucleo)
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        ext = file.name.split(".")[-1].lower()
        tipo = "file"
        if ext in ["jpg", "jpeg", "png"]:
            tipo = "image"
        elif ext in ["mp4"]:
            tipo = "video"
        filename = f"chat/{uuid.uuid4().hex}.{ext}"
        path = default_storage.save(filename, file)
        url = settings.MEDIA_URL + path
        return JsonResponse({"url": url, "tipo": tipo})

    messages = (
        Mensagem.objects.filter(
            remetente__in=[request.user, dest],
            destinatario__in=[request.user, dest],
        )
        .order_by("criado_em")
        .reverse()[:50]
    )
    if not messages:
        Notificacao.objects.create(
            usuario=dest,
            remetente=request.user,
            mensagem="Novo chat iniciado",
        )
    return render(
        request, "chat/room.html", {"dest": dest, "messages": reversed(list(messages))}
    )
