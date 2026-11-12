"""Entry point for the packaged backend: binds the configured port (0 = any free one) and reports it.

The desktop shell reads the `FARMTWIN_PORT=<n>` line from stdout to know where the API lives.
"""

import socket

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((settings.host, settings.port))
    print(f"FARMTWIN_PORT={sock.getsockname()[1]}", flush=True)

    # import the app object directly, so a frozen build doesn't need to find it by name
    from app.main import app

    config = uvicorn.Config(app, log_level="info")
    uvicorn.Server(config).run(sockets=[sock])


if __name__ == "__main__":
    main()
