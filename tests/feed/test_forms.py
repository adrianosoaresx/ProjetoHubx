import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from feed.forms import CommentForm, PostForm


@pytest.mark.django_db
def test_postform_media_validation(nucleado_user):
    pdf = SimpleUploadedFile("a.pdf", b"data", content_type="application/pdf")
    img = SimpleUploadedFile("a.png", b"data", content_type="image/png")
    form = PostForm(
        data={"tipo_feed": "global", "conteudo": ""},
        files={"image": img, "pdf": pdf},
        user=nucleado_user,
    )
    assert not form.is_valid()
    assert form.errors.get("image") is not None


@pytest.mark.django_db
def test_postform_content_required(nucleado_user):
    form = PostForm(data={"tipo_feed": "global"}, user=nucleado_user)
    assert not form.is_valid()
    assert "Informe um conteúdo ou selecione uma mídia." in form.non_field_errors()[0]


@pytest.mark.django_db
def test_postform_nucleo_required(nucleado_user):
    form = PostForm(data={"tipo_feed": "nucleo", "conteudo": "x"}, user=nucleado_user)
    assert not form.is_valid()
    assert "Selecione o núcleo." in form.errors.get("nucleo", [])


@pytest.mark.django_db
def test_postform_nucleo_membership(admin_user, nucleo):
    form = PostForm(data={"tipo_feed": "nucleo", "nucleo": nucleo.id, "conteudo": "x"}, user=admin_user)
    assert not form.is_valid()
    msg = form.errors.get("nucleo")[0]
    assert "faça uma escolha válida" in msg.lower()


@pytest.mark.django_db
def test_postform_evento_required(nucleado_user):
    form = PostForm(data={"tipo_feed": "evento", "conteudo": "x"}, user=nucleado_user)
    assert not form.is_valid()
    assert "Selecione o evento." in form.errors.get("evento", [])


@pytest.mark.django_db
def test_commentform_text_required():
    form = CommentForm(data={})
    assert not form.is_valid()
    assert "texto" in form.errors
