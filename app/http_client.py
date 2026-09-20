from __future__ import annotations

import ssl
from urllib.request import Request, urlopen

import truststore


_SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def open_url(request: Request, timeout: int):
    """Open HTTPS URLs using the Windows system certificate store."""
    return urlopen(request, timeout=timeout, context=_SSL_CONTEXT)
