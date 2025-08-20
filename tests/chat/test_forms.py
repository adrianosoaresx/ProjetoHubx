from django.core.files.uploadedfile import SimpleUploadedFile

from chat.forms import NovaMensagemForm, NovaConversaForm
from nucleos.models import ParticipacaoNucleo


def test_nova_mensagem_form_requires_content_or_file():
    form = NovaMensagemForm(data={"tipo": "text"}, files={})
    assert not form.is_valid()


def test_nova_mensagem_form_accepts_file_only():
    form = NovaMensagemForm(
        data={"tipo": "file"},
        files={"arquivo": SimpleUploadedFile("f.txt", b"data")},
    )
    assert form.is_valid()


def test_nova_conversa_form_privado_valida_nucleo(admin_user, coordenador_user, nucleo):
    ParticipacaoNucleo.objects.create(user=admin_user, nucleo=nucleo, status="ativo")
    ParticipacaoNucleo.objects.create(
        user=coordenador_user, nucleo=nucleo, status="ativo"
    )
    data = {
        "contexto_tipo": "privado",
        "contexto_id": str(nucleo.id),
        "participants": [str(coordenador_user.id)],
    }
    form = NovaConversaForm(data=data, user=admin_user)
    assert form.is_valid()


def test_nova_conversa_form_privado_requer_pertencimento(
    admin_user, coordenador_user, associado_user, nucleo
):
    ParticipacaoNucleo.objects.create(user=admin_user, nucleo=nucleo, status="ativo")
    data = {
        "contexto_tipo": "privado",
        "contexto_id": str(nucleo.id),
        "participants": [str(associado_user.id)],
    }
    form = NovaConversaForm(data=data, user=admin_user)
    assert not form.is_valid()
