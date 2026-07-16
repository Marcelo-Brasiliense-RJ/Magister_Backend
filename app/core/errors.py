"""Handler global de erro: nunca vaza stack trace na resposta."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import logger


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exc(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Detalhe so no log; resposta generica para nao vazar interno.
        logger.error("unhandled error at %s: %s", request.url.path, exc, exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Erro interno."})
