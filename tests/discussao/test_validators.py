import clamd
import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from discussao.validators import validar_arquivo_discussao


def _mock_scan(monkeypatch, status):
    class FakeClamd:
        def scan_stream(self, data):
            return {"stream": (status, None)}

    monkeypatch.setattr(clamd, "ClamdUnixSocket", lambda: FakeClamd())


def test_scan_malicioso(monkeypatch):
    _mock_scan(monkeypatch, "FOUND")
    file = SimpleUploadedFile("x.png", b"data", content_type="image/png")
    with pytest.raises(ValidationError):
        validar_arquivo_discussao(file)


def test_scan_ok(monkeypatch):
    _mock_scan(monkeypatch, "OK")
    file = SimpleUploadedFile("x.png", b"data", content_type="image/png")
    validar_arquivo_discussao(file)
