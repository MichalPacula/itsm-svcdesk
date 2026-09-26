# ai-generated: 90% - Claude Code wrote this module; reviewed and accepted as-is
"""Shared {"error": {"code", "message"}} body construction and exception handlers (API.md sec7)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from metrics import MetricsError


class NotFoundError(Exception):
    """Raised for an unknown ticket id; mapped to 404 (FR-024)."""

    def __init__(self, message: str = "not found") -> None:
        self.message = message
        super().__init__(message)


class InvalidTransitionError(Exception):
    """Raised for a state-machine transition that is not allowed; mapped to 409 (FR-008)."""

    def __init__(self, message: str = "invalid transition") -> None:
        self.message = message
        super().__init__(message)


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        parts = [f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()]
        message = "; ".join(parts) if parts else "validation failed"
        return JSONResponse(status_code=422, content=error_body("validation", message))

    @app.exception_handler(NotFoundError)
    async def _not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content=error_body("not_found", exc.message))

    @app.exception_handler(InvalidTransitionError)
    async def _invalid_transition_handler(request: Request, exc: InvalidTransitionError) -> JSONResponse:
        return JSONResponse(status_code=409, content=error_body("invalid_transition", exc.message))

    @app.exception_handler(MetricsError)
    async def _metrics_error_handler(request: Request, exc: MetricsError) -> JSONResponse:
        return JSONResponse(status_code=422, content=error_body("validation", str(exc)))

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            content = detail
        else:
            code = "not_found" if exc.status_code == 404 else "http_error"
            content = error_body(code, str(detail))
        return JSONResponse(status_code=exc.status_code, content=content)
