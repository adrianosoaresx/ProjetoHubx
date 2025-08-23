from __future__ import annotations

import sentry_sdk


def _scan_file(path: str) -> bool:  # pragma: no cover - depends on external service
    try:
        import clamd  # type: ignore

        cd = clamd.ClamdNetworkSocket()
        result = cd.scan(path)
        if result:
            return any(status == "FOUND" for _, (status, _) in result.items())
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        return False
    return False
