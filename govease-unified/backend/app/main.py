from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from threading import Thread
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router, v1_router
from backend.app.config import settings
from backend.app.errors import APIError
from backend.app.services.index_manager import index_manager


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialization = Thread(target=index_manager.initialize, name="index-initializer", daemon=True)
    initialization.start()
    yield
    # Let the daemon thread exit with the process instead of blocking
    # asyncio's default executor shutdown during dev reload/stop.


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix=settings.api_prefix)
app.include_router(v1_router, prefix=settings.api_v1_prefix)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    started_at = perf_counter()
    response = await call_next(request)
    elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-MS"] = str(elapsed_ms)
    response.headers["Server-Timing"] = f"app;dur={elapsed_ms}"
    logger.info(
        "http_timing request_id=%s method=%s path=%s status=%s total_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "request_id": request.state.request_id}},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INVALID_REQUEST",
                "message": "Dữ liệu yêu cầu không hợp lệ.",
                "request_id": request.state.request_id,
                "details": exc.errors(),
            }
        },
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "docs": "/docs", "health": "/api/v1/health"}
