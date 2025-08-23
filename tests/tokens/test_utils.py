from tokens.utils import get_client_ip


def test_get_client_ip_prefers_forwarded_for(rf):
    request = rf.get("/")
    request.META["REMOTE_ADDR"] = "10.0.0.1"
    request.META["HTTP_X_FORWARDED_FOR"] = "1.2.3.4, 5.6.7.8"
    assert get_client_ip(request) == "1.2.3.4"


def test_get_client_ip_fallback_remote_addr(rf):
    request = rf.get("/")
    request.META["REMOTE_ADDR"] = "9.9.9.9"
    assert get_client_ip(request) == "9.9.9.9"

