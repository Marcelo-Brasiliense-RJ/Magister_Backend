import pytest

from app.core import security
from app.core.security import SSRFError, assert_safe_url


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/x",  # esquema invalido
        "file:///etc/passwd",  # esquema invalido
        "http://169.254.169.254/latest/meta-data/",  # metadata de cloud
        "http://127.0.0.1:8000/",  # loopback
        "http://10.0.0.5/",  # privado
        "http://192.168.1.1/",  # privado
    ],
)
def test_blocks_unsafe(url):
    with pytest.raises(SSRFError):
        assert_safe_url(url)


def test_allows_public_host(monkeypatch):
    # Evita DNS real: simula host publico resolvendo para IP publico.
    monkeypatch.setattr(
        security.socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    assert_safe_url("https://example.com/page")  # nao levanta
