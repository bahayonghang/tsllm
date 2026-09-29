"""Error envelope and the mapping from error codes to HTTP status codes."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from starlette.exceptions import HTTPException

from tsllm.errors import TsllmError

logger = logging.getLogger(__name__)

STATUS_BY_CODE: dict[str, int] = {
    "DATASET_NOT_FOUND": 404,
    "RUN_NOT_FOUND": 404,
    "TEMPLATE_NOT_FOUND": 404,
    "RESULT_NOT_FOUND": 404,
    "DATASET_NOT_INGESTED": 409,
    "INVALID_TRANSITION": 409,
    "VALIDATION_ERROR": 422,
    "CAPABILITY_UNSUPPORTED": 422,
    "DATASET_CONFIG_INVALID": 422,
    "CHANNEL_INVALID": 422,
    "TASK_CONFIG_INVALID": 422,
    "BACKBONE_LOAD_FAILED": 422,
    "NOT_IMPLEMENTED": 422,
}


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: Any = None


class ErrorOut(BaseModel):
    error: ErrorBody


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorOut} for status in (404, 409, 422, 500)
}


def error_response(status: int, code: str, message: str, detail: Any = None) -> JSONResponse:
    body = ErrorOut(error=ErrorBody(code=code, message=message, detail=detail))
    return JSONResponse(body.model_dump(mode="json"), status_code=status)


def _field_errors(errors: Any) -> list[dict[str, Any]]:
    # Keep field paths and messages; input values are not echoed.
    return [
        {"loc": list(error.get("loc", ())), "msg": error.get("msg", ""), "type": error.get("type")}
        for error in errors
    ]


async def _domain(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, TsllmError)
    return error_response(STATUS_BY_CODE.get(exc.code, 500), exc.code, str(exc))


async def _not_implemented(_: Request, exc: Exception) -> JSONResponse:
    return error_response(422, "NOT_IMPLEMENTED", str(exc))


async def _request_validation(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return error_response(
        422, "VALIDATION_ERROR", "request validation failed", _field_errors(exc.errors())
    )


async def _model_validation(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ValidationError)
    return error_response(
        422, "VALIDATION_ERROR", "configuration validation failed", _field_errors(exc.errors())
    )


async def _http(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    return error_response(exc.status_code, code, str(exc.detail))


async def _internal(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error for %s %s", request.method, request.url.path)
    return error_response(500, "INTERNAL_ERROR", "internal server error")


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(TsllmError, _domain)
    app.add_exception_handler(NotImplementedError, _not_implemented)
    app.add_exception_handler(RequestValidationError, _request_validation)
    app.add_exception_handler(ValidationError, _model_validation)
    app.add_exception_handler(HTTPException, _http)
    app.add_exception_handler(Exception, _internal)
