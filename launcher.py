"""Desktop-friendly launcher for local Windows deployments."""

from __future__ import annotations

import socket
import threading
import time
import urllib.request
import webbrowser

import uvicorn

from app import create_app, load_config, setup_logging

HOST = "127.0.0.1"
PORT = 8010
APP_URL = f"http://{HOST}:{PORT}/"
HEALTH_URL = f"{APP_URL}health"


def _port_is_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((HOST, PORT)) == 0


def _open_when_ready() -> None:
    for _ in range(90):
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(APP_URL)
                    return
        except OSError:
            time.sleep(0.5)


def main() -> None:
    if _port_is_open():
        print(f"服务已在运行，正在打开 {APP_URL}")
        webbrowser.open(APP_URL)
        return

    config = load_config()
    setup_logging(config)
    threading.Thread(target=_open_when_ready, daemon=True).start()

    print(f"正在启动 AI Agent Platform：{APP_URL}")
    print("关闭此窗口或按 Ctrl+C 可停止服务。")
    uvicorn.run(create_app(config), host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
