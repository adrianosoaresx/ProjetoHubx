import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from discussao.forms import (
    CategoriaDiscussaoForm,
    RespostaDiscussaoForm,
    TopicoDiscussaoForm,
)
from discussao.models import CategoriaDiscussao, TopicoDiscussao
from nucleos.models import Nucleo

pytestmark = pytest.mark.django_db


def test_categoria_form_fields():
    form = CategoriaDiscussaoForm()
    assert list(form.fields) == [
        "nome",
        "descricao",
        "organizacao",
        "nucleo",
        "evento",
        "icone",
    ]


@pytest.mark.xfail(reason="Modelo permite duplicados quando núcleo/evento são nulos")
def test_categoria_form_unique_together(organizacao):
    CategoriaDiscussao.objects.create(nome="Cat", organizacao=organizacao)
    form = CategoriaDiscussaoForm(data={"nome": "Cat", "organizacao": organizacao.pk})
    assert not form.is_valid()


def test_topico_form_validation(categoria, admin_user, nucleo, evento):
    TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="Repetido",
        conteudo="c",
        autor=admin_user,
        publico_alvo=0,
    )
    form = TopicoDiscussaoForm(
        data={
            "categoria": categoria.pk,
            "titulo": "Repetido",
            "conteudo": "c",
            "publico_alvo": 0,
            "tags": "",
        }
    )
    assert not form.is_valid()
    cat_nucleo = CategoriaDiscussao.objects.create(nome="N", organizacao=categoria.organizacao, nucleo=nucleo)
    form2 = TopicoDiscussaoForm(
        data={
            "categoria": cat_nucleo.pk,
            "titulo": "Ok",
            "conteudo": "c",
            "publico_alvo": 0,
            "nucleo": nucleo.pk,
            "tags": "",
        }
    )
    assert form2.is_valid()
    outro = Nucleo.objects.create(nome="Outro", slug="outro", organizacao=categoria.organizacao)
    form3 = TopicoDiscussaoForm(
        data={
            "categoria": cat_nucleo.pk,
            "titulo": "Err",
            "conteudo": "c",
            "publico_alvo": 0,
            "nucleo": outro.pk,
        }
    )
    assert not form3.is_valid()
    form4 = TopicoDiscussaoForm(
        data={
            "categoria": categoria.pk,
            "titulo": "x",
            "conteudo": "c",
            "publico_alvo": 3,
        }
    )
    assert not form4.is_valid()


def test_resposta_form_fields():
    form = RespostaDiscussaoForm()
    assert list(form.fields) == ["conteudo", "arquivo", "reply_to", "motivo_edicao"]
    form = RespostaDiscussaoForm(data={"conteudo": ""})
    assert not form.is_valid()


def test_resposta_form_valid_upload():
    file = SimpleUploadedFile("a.png", b"data", content_type="image/png")
    form = RespostaDiscussaoForm(data={"conteudo": "ok"}, files={"arquivo": file})
    assert form.is_valid()


def test_resposta_form_invalid_upload():
    file = SimpleUploadedFile("a.exe", b"data", content_type="application/octet-stream")
    form = RespostaDiscussaoForm(data={"conteudo": "ok"}, files={"arquivo": file})
    assert not form.is_valid()
