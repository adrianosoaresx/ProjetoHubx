import pytest

from empresas.forms import EmpresaForm
from empresas.factories import EmpresaFactory
from empresas.models import Tag


@pytest.mark.django_db
def test_tags_are_assigned_from_ids():
    tag1 = Tag.objects.create(nome="Alpha")
    tag2 = Tag.objects.create(nome="Beta")
    empresa = EmpresaFactory()
    form = EmpresaForm(instance=empresa)
    data = dict(form.initial)
    data["tags"] = [tag1.id, tag2.id]
    form = EmpresaForm(data, instance=empresa)
    assert form.is_valid()
    form.save()
    assert set(empresa.tags.all()) == {tag1, tag2}
