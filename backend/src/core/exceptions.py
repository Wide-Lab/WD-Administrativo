from typing import Any


class AppError(Exception):
    """Base class para erros da aplicação."""

    status_code = 400
    code = "app_error"
    message = "An application error occurred."

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> None:

        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "Resource not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "Resource conflict."


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    message = "Invalid credentials."


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
    message = "You do not have permission to perform this action."


class GoneError(AppError):
    status_code = 410
    code = "gone"
    message = "Resource no longer available."


class PayloadTooLargeError(AppError):
    """O corpo veio grande demais — 413.

    Separado do 422 de propósito: "o arquivo passou do teto" é uma resposta que o cliente
    conserta reduzindo o arquivo, e "os bytes não são uma imagem" é outra. Um 422 pros dois
    faria a tela mandar tirar outra foto quando o problema era o tamanho."""

    status_code = 413
    code = "payload_too_large"
    message = "Payload too large."


class UnsupportedMediaTypeError(AppError):
    """O `content-type` não está na lista — 415.

    Também distinto do 422: o formato foi entendido e recusado, e não é o conteúdo que está
    corrompido."""

    status_code = 415
    code = "unsupported_media_type"
    message = "Unsupported media type."


class TooManyRequestsError(AppError):
    status_code = 429
    code = "too_many_requests"
    message = "Too many requests."


class ValidationAppError(AppError):
    status_code = 422
    code = "validation_error"
    message = "Validation error."


class PersistenceError(AppError):
    status_code = 500
    code = "persistence_error"
    message = "A persistence error occurred while processing your request."
