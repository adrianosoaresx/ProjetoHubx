import pytest

from empresas.forms import EmpresaForm
from empresas.factories import EmpresaFactory
from empresas.models import Tag


@pytest.mark.django_db
def test_tags_are_sanitized():
    empresa = EmpresaFactory()
    form = EmpresaForm(instance=empresa)
    data = form.initial
    data["tags_field"] = "Tag<script>, outro!@#"
    form = EmpresaForm(data, instance=empresa)
    assert form.is_valid()
    form.save()
    assert Tag.objects.filter(nome="Tagscript").exists()
    assert Tag.objects.filter(nome="outro").exists()
