import sys
import types

from chat.utils import _scan_file

def test_scan_file_infected(monkeypatch):
    fake = types.SimpleNamespace(
        ClamdNetworkSocket=lambda: types.SimpleNamespace(
            scan=lambda path: {path: ("FOUND", "virus")}
        )
    )
    monkeypatch.setitem(sys.modules, "clamd", fake)
    assert _scan_file("dummy") is True


def test_scan_file_clean(monkeypatch):
    fake = types.SimpleNamespace(
        ClamdNetworkSocket=lambda: types.SimpleNamespace(
            scan=lambda path: {path: ("OK", None)}
        )
    )
    monkeypatch.setitem(sys.modules, "clamd", fake)
    assert _scan_file("dummy") is False


def test_scan_file_error(monkeypatch):
    class DummySocket:
        def __init__(self):
            raise RuntimeError("fail")

    fake = types.SimpleNamespace(ClamdNetworkSocket=DummySocket)
    monkeypatch.setitem(sys.modules, "clamd", fake)
    assert _scan_file("dummy") is False
