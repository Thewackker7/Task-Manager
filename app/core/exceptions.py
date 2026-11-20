"""Custom errors and handlers that turn every error into one consistent JSON shape:

{"error": {"code": "SOME_CODE", "message": "Human readable text"}}
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected, business-level errors."""

    status_code = 500
    code = "INTERNAL_ERROR"
    message = "Something went wrong."

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        self.message = message or self.message
        self.headers = headers
        super().__init__(self.message)


class EmailAlreadyRegisteredError(AppError):
    status_code = 409
    code = "EMAIL_ALREADY_REGISTERED"
    message = "An account with this email already exists."


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "INVALID_CREDENTIALS"
    # Deliberately identical for "unknown email" and "wrong password".
    message = "Incorrect email or password."

    def __init__(self, message: str | None = None):
        super().__init__(message, headers={"WWW-Authenticate": "Bearer"})


class NotAuthenticatedError(AppError):
    status_code = 401
    code = "NOT_AUTHENTICATED"
    message = "Not authenticated."

    def __init__(self, message: str | None = None):
        super().__init__(message, headers={"WWW-Authenticate": "Bearer"})


class InactiveUserError(AppError):
    status_code = 403
    code = "INACTIVE_USER"
    message = "This account is disabled."


def _error_response(
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
    details: list[dict] | None = None,
) -> JSONResponse:
    body: dict = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Only expose where the problem is and what is wrong. We intentionally do NOT
        # include the submitted value ("input"), which could be a password.
        details = [
            {
                "field": ".".join(
                    str(part) for part in err["loc"] if part not in ("body", "query")
                ),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return _error_response(422, "VALIDATION_ERROR", "Invalid request data.", details=details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Covers framework-raised errors such as 404 (no such route) and 405.
        return _error_response(
            exc.status_code, f"HTTP_{exc.status_code}", str(exc.detail), dict(exc.headers or {})
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Log the full traceback for us, send the client nothing revealing.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")
