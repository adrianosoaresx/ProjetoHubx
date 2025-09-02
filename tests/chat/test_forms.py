from django.core.files.uploadedfile import SimpleUploadedFile

from chat.forms import NovaMensagemForm


def test_nova_mensagem_form_requires_content_or_file():
    form = NovaMensagemForm(data={"tipo": "text"}, files={})
    assert not form.is_valid()


def test_nova_mensagem_form_accepts_file_only():
    form = NovaMensagemForm(
        data={"tipo": "file"},
        files={"arquivo": SimpleUploadedFile("f.txt", b"data")},
    )
    assert form.is_valid()
