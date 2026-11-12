"""Lifecycle hooks for the desktop shell: a clean shutdown, and exiting if the shell dies.

On Windows a killed process can't clean up, so the shell asks the API to stop instead; the API
then stops llama-server before exiting. If the shell crashes, the parent watch does the same.
"""

import logging
import os
import secrets
import threading
import time

import psutil
from fastapi import APIRouter, Header

from app.ai.server import supervisor
from app.config import get_settings
from app.errors import AppError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["system"])


@router.post("/shutdown", status_code=202)
def shutdown(x_farmtwin_token: str = Header(default="")):
    expected = get_settings().shutdown_token
    # compare in constant time; without a configured token nobody can shut it down this way
    if not expected or not secrets.compare_digest(x_farmtwin_token, expected):
        raise AppError(403, "forbidden", "Not allowed.")
    threading.Thread(target=_exit, args=("shell asked",), daemon=True).start()
    return {"status": "stopping"}


def watch_parent() -> None:
    """Exits when the desktop shell that started the API is gone."""
    parent = get_settings().parent_pid
    if not parent:
        return

    def loop() -> None:
        while psutil.pid_exists(parent):
            time.sleep(2)
        _exit("shell is gone")

    threading.Thread(target=loop, daemon=True).start()


def _exit(reason: str) -> None:
    time.sleep(0.2)  # let the response go out first
    logger.info("stopping: %s", reason)
    supervisor.stop()
    os._exit(0)
