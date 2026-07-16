"""Seguranca: JWT admin, embed token, rate limit em memoria e SSRF guard."""

import ipaddress
import secrets
import socket
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import bcrypt
import jwt

from app.config import get_settings

_settings = get_settings()
JWT_ALGORITHM = "HS256"


# --- Senha / JWT admin ---
def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(subject: str, role: str = "admin") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=_settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, _settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    # Levanta jwt.PyJWTError em assinatura/expiracao invalidas.
    return jwt.decode(token, _settings.jwt_secret, algorithms=[JWT_ALGORITHM])


def generate_embed_token() -> str:
    # Publico e escopado ao tutor; nao e segredo, mas deve ser imprevisivel.
    return secrets.token_urlsafe(24)


# --- Rate limit em memoria (janela deslizante por minuto) ---
class RateLimiter:
    # ponytail: em memoria, serve para MVP/1 instancia. Producao usa Redis/WAF (SECURITY.md).
    def __init__(self, limit_per_min: int) -> None:
        self.limit = limit_per_min
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window = self._hits.setdefault(key, [])
        # Descarta batidas com mais de 60s.
        window[:] = [t for t in window if now - t < 60]
        if len(window) >= self.limit:
            return False
        window.append(now)
        return True


chat_rate_limiter = RateLimiter(_settings.chat_rate_limit_per_min)
login_rate_limiter = RateLimiter(10)


# --- SSRF guard ---
class SSRFError(ValueError):
    """URL bloqueada por apontar para rede interna ou esquema invalido."""


def assert_safe_url(url: str) -> None:
    """Valida esquema http/https e bloqueia IPs privados/reservados/metadata."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFError("Esquema nao permitido (use http/https).")
    host = parsed.hostname
    if not host:
        raise SSRFError("Host ausente.")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise SSRFError("Host nao resolvido.") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        # Bloqueia loopback, link-local (inclui 169.254.169.254), privado e reservado.
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise SSRFError(f"IP nao permitido: {ip}")
