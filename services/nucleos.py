from django.contrib.auth import get_user_model

from nucleos.models import ParticipacaoNucleo

User = get_user_model()


def user_belongs_to_nucleo(user: User, nucleo_id: str) -> tuple[bool, str, bool]:
    """Return (participa, "papel:status", suspenso) for given user and núcleo."""
    try:
        part = ParticipacaoNucleo.objects.get(user=user, nucleo_id=nucleo_id)
    except ParticipacaoNucleo.DoesNotExist:
        return False, "", False
    return True, f"{part.papel}:{part.status}", part.status_suspensao
