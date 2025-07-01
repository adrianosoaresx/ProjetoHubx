from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404

from django.core.files.storage import default_storage
from django.conf import settings
from django.db.models import Q
import uuid


from django.contrib.auth import get_user_model
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
            | Q(destinatario__isnull=True, remetente__in=[request.user, dest])
        )
        .order_by("criado_em")
    )
    context = {
        "dest": dest,
        "messages": messages_qs,
    }
    return render(request, "chat/modal_room.html", context)
