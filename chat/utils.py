from __future__ import annotations


def _scan_file(path: str) -> bool:  # pragma: no cover - depends on external service
    try:
        import clamd  # type: ignore

        cd = clamd.ClamdNetworkSocket()
        result = cd.scan(path)
        if result:
            return any(status == "FOUND" for _, (status, _) in result.items())
    except Exception:
        return False
    return False
