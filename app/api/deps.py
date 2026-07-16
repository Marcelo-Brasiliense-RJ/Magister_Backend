"""Dependencias: sessao de DB e guarda de admin via JWT."""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.database import get_session  # noqa: F401 - reexport para as rotas

# auto_error=False para responder 401 (e nao 403) quando falta o header.
_bearer = HTTPBearer(auto_error=False)


def require_admin(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado.")
    try:
        payload = decode_access_token(cred.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido.") from exc
    if payload.get("role") != "admin":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sem permissao.")
    return payload
