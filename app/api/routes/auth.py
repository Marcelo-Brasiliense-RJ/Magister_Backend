"""Login do admin unico (credencial no .env) -> JWT curto."""

from fastapi import APIRouter, HTTPException, Request, status

from app.config import get_settings
from app.core.security import create_access_token, login_rate_limiter, verify_password
from app.schemas.chat import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
_settings = get_settings()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request) -> TokenResponse:
    ip = request.client.host if request.client else "unknown"
    if not login_rate_limiter.allow(ip):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Muitas tentativas.")
    # Mensagem generica: nao distingue usuario inexistente de senha errada.
    ok = body.username == _settings.admin_username and verify_password(
        body.password, _settings.admin_password_hash
    )
    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais invalidas.")
    return TokenResponse(access_token=create_access_token(body.username))
