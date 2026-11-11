"""Logging setup: key=value lines to stderr and a rotating file in the data folder, plus a request id per call."""

import logging
import time
import uuid
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request

from app.config import get_settings

request_id: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


def setup_logging() -> None:
    settings = get_settings()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s level=%(levelname)s logger=%(name)s rid=%(request_id)s %(message)s")
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        RotatingFileHandler(settings.logs_dir / "api.log", maxBytes=2_000_000, backupCount=3),
    ]
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in handlers:
        h.setFormatter(fmt)
        h.addFilter(_RequestIdFilter())
        root.addHandler(h)


def install_request_logging(app: FastAPI) -> None:
    log = logging.getLogger("app.request")

    @app.middleware("http")
    async def _log_requests(request: Request, call_next):
        token = request_id.set(uuid.uuid4().hex[:8])
        started = time.perf_counter()
        try:
            response = await call_next(request)
            ms = int((time.perf_counter() - started) * 1000)
            log.info(
                "method=%s path=%s status=%s ms=%s",
                request.method,
                request.url.path,
                response.status_code,
                ms,
            )
            response.headers["x-request-id"] = request_id.get()
            return response
        finally:
            request_id.reset(token)
