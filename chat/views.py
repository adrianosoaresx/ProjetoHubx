import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import Mensagem

User = get_user_model()


@login_required
def modal_user_list(request):
    users = (
        get_user_model()
        .objects.filter(nucleo=request.user.nucleo)
        .exclude(id=request.user.id)
    )
    return render(request, "chat/modal_user_list.html", {"users": users})


@login_required
def modal_room(request, user_id):
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
        # Build an absolute URL so the client can access the file regardless of
        # the current location. This also ensures previously saved attachments
        # render correctly in the chat history.
        url = request.build_absolute_uri(settings.MEDIA_URL + path)
        return JsonResponse({"url": url, "tipo": tipo})
    messages_qs = (
        Mensagem.objects.filter(nucleo=request.user.nucleo)
        .filter(
            Q(remetente=request.user, destinatario=dest)
            | Q(remetente=dest, destinatario=request.user)
        )
        .select_related("remetente", "destinatario")
        .order_by("-criado_em")[:20]
    )

    # List of messages in chronological order from oldest to newest
    messages = list(messages_qs)[::-1]
    context = {
        "dest": dest,
        "messages": messages,
        "user": request.user,
    }
    return render(request, "chat/modal_room.html", context)


@login_required
def messages_history(request, user_id):
    """Return the last 50 messages in JSON format."""
    dest = get_object_or_404(User, pk=user_id, nucleo=request.user.nucleo)
    messages_qs = (
        Mensagem.objects.filter(nucleo=request.user.nucleo)
        .filter(
            Q(remetente=request.user, destinatario=dest)
            | Q(remetente=dest, destinatario=request.user)
        )
        .select_related("remetente")
        .order_by("-criado_em")[:50]
    )

    def _abs(url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return request.build_absolute_uri(
            settings.MEDIA_URL.rstrip("/") + "/" + url.lstrip("/")
        )

    messages = [
        {
            "remetente": m.remetente.username,
            "tipo": m.tipo,
            "conteudo": (
                _abs(m.conteudo) if m.tipo in {"image", "video", "file"} else m.conteudo
            ),
            "timestamp": m.criado_em.isoformat(),
        }
        for m in reversed(list(messages_qs))
    ]
    return JsonResponse({"messages": messages})
