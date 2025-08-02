import pytest

from feed.api import PostSerializer


@pytest.mark.django_db
def test_serializer_requires_nucleo():
    ser = PostSerializer(data={"tipo_feed": "nucleo", "conteudo": "x"})
    assert not ser.is_valid()
    assert "nucleo" in ser.errors


@pytest.mark.django_db
def test_serializer_requires_evento():
    ser = PostSerializer(data={"tipo_feed": "evento", "conteudo": "x"})
    assert not ser.is_valid()
    assert "evento" in ser.errors
