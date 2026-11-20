"""Shared helpers for the unittest suite."""


def _origin_in_headers(headers) -> bool:
    if isinstance(headers, dict):
        return any(str(key).casefold() == "origin" for key in headers)
    if isinstance(headers, (list, tuple)):
        return any(str(key).casefold() == "origin" for key, _value in headers)
    return False


def make_client(application, origin="http://localhost"):
    """Test client that sends an Origin header with every request.

    The application rejects state-changing requests whose Origin/Referer is
    missing or cross-origin, so browser-facing tests must declare one. Pass
    ``origin=None`` to simulate a client that sends no Origin at all.
    """
    client = application.test_client()
    original_open = client.open

    def open_with_origin(*args, **kwargs):
        if origin is not None and not _origin_in_headers(kwargs.get("headers")):
            overrides = kwargs.setdefault("environ_overrides", {})
            overrides.setdefault("HTTP_ORIGIN", origin)
        return original_open(*args, **kwargs)

    client.open = open_with_origin
    return client
