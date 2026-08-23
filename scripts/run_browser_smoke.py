"""Browser smoke test for a running local Agent service."""

from __future__ import annotations

import argparse
import time
import urllib.request

from playwright.sync_api import Error, sync_playwright


def wait_until_ready(base_url: str, timeout: float) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(f"Service did not become healthy within {timeout}s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    wait_until_ready(base_url, args.timeout)

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Error:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(type(error).__name__))

        response = page.goto(base_url, wait_until="networkidle")
        if response is None or response.status != 200:
            raise RuntimeError("Home page did not return HTTP 200")
        if page.title() != "AI Agent Platform":
            raise RuntimeError(f"Unexpected page title: {page.title()}")

        response = page.goto(f"{base_url}/settings", wait_until="networkidle")
        if response is None or response.status != 200:
            raise RuntimeError("Settings page did not return HTTP 200")
        page.get_by_role("heading", name="设置").wait_for(timeout=5000)
        browser.close()

    if page_errors:
        raise RuntimeError(f"Browser page errors: {page_errors}")
    print("Browser smoke passed: health, home and settings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
