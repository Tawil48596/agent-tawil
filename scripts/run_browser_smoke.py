"""Browser smoke test for a running local Agent service."""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Error, Page, Route, expect, sync_playwright


def install_chat_fixture(page: Page, base_url: str) -> None:
    """Keep browser chat tests deterministic and out of the local database."""
    sessions: list[dict] = []
    messages: dict[str, list[dict]] = {}
    approvals: dict[str, dict] = {}
    approval_polls: dict[str, int] = {}

    def handle(route: Route) -> None:
        request = route.request
        path = urlparse(request.url).path
        method = request.method

        if path == "/api/v1/chat/models":
            route.fulfill(json={"models": [], "available_models": []})
            return
        if path == "/api/v1/chat/sessions" and method == "GET":
            route.fulfill(json={"items": sessions, "total": len(sessions)})
            return
        if path == "/api/v1/chat/sessions" and method == "POST":
            session_id = f"browser-smoke-{len(sessions) + 1}"
            now = datetime.now(UTC).isoformat()
            session = {
                "id": session_id,
                "title": "新对话",
                "source": "browser-smoke",
                "created_at": now,
                "updated_at": now,
                "message_count": 0,
            }
            sessions.insert(0, session)
            messages[session_id] = []
            approvals[session_id] = {
                "id": f"approval-{session_id}",
                "session_id": session_id,
                "tool_name": "file_write",
                "command": "write browser-smoke.txt",
                "reason": "Browser approval fixture",
                "status": "pending",
                "created_at": time.time(),
                "timeout": 1 if session_id == "browser-smoke-2" else 300,
            }
            route.fulfill(json=session)
            return

        prefix = "/api/v1/chat/sessions/"
        if path.startswith(prefix) and method == "DELETE":
            session_id = path.removeprefix(prefix)
            sessions[:] = [item for item in sessions if item["id"] != session_id]
            messages.pop(session_id, None)
            route.fulfill(json={"ok": True})
            return
        if path.startswith(prefix) and path.endswith("/messages"):
            session_id = path.removeprefix(prefix).removesuffix("/messages")
            if method == "GET":
                route.fulfill(json={"items": messages.get(session_id, []), "total": 0})
                return
            body = request.post_data_json
            content = body["content"]
            session_messages = messages.setdefault(session_id, [])
            session_messages.extend(
                [
                    {"id": 1, "session_id": session_id, "role": "user", "content": content},
                    {
                        "id": 2,
                        "session_id": session_id,
                        "role": "assistant",
                        "content": "浏览器测试回复",
                    },
                ]
            )
            if sessions:
                sessions[0]["title"] = content
                sessions[0]["message_count"] = len(session_messages)
            done = {
                "type": "done",
                "content": "浏览器测试回复",
                "usage": {"input_tokens": 4, "output_tokens": 3, "total_tokens": 7},
                "session_usage": {
                    "input_tokens": 4,
                    "cached_input_tokens": 0,
                    "cache_write_input_tokens": 0,
                    "output_tokens": 3,
                    "reasoning_tokens": 0,
                    "total_tokens": 7,
                    "requests": 1,
                    "cache_hit_rate": 0,
                },
            }
            route.fulfill(
                content_type="text/event-stream",
                body=f"event: message\ndata: {json.dumps(done, ensure_ascii=False)}\n\n",
            )
            return

        route.fulfill(status=404, json={"detail": "Browser fixture route not found"})

    def handle_approval(route: Route) -> None:
        request = route.request
        parsed = urlparse(request.url)
        if request.method == "GET":
            session_id = parse_qs(parsed.query).get("session_id", [""])[0]
            item = approvals.get(session_id)
            if item and item["timeout"] == 1:
                approval_polls[session_id] = approval_polls.get(session_id, 0) + 1
                if approval_polls[session_id] >= 4:
                    approvals.pop(session_id)
                    item = None
            route.fulfill(json={"items": [item] if item else []})
            return
        approval_id = parsed.path.rsplit("/", maxsplit=1)[-1]
        session_id = next(
            (key for key, item in approvals.items() if item["id"] == approval_id),
            None,
        )
        if session_id is None:
            route.fulfill(status=404, json={"detail": "Pending approval not found"})
            return
        decision = request.post_data_json["decision"]
        approvals.pop(session_id)
        route.fulfill(json={"ok": True, "status": f"{decision}d"})

    page.route(f"{base_url}/api/v1/chat/**", handle)
    page.route(f"{base_url}/api/v1/security/tool-approvals**", handle_approval)


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
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    wait_until_ready(base_url, args.timeout)

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Error:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        install_chat_fixture(page, base_url)
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(type(error).__name__))

        response = page.goto(base_url, wait_until="networkidle")
        if response is None or response.status != 200:
            raise RuntimeError("Home page did not return HTTP 200")
        if page.title() != "AI Agent Platform":
            raise RuntimeError(f"Unexpected page title: {page.title()}")
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=args.screenshot, full_page=True)
        starter = page.get_by_role("button", name="分析这个项目的架构并给出改进顺序")
        starter.click()
        composer = page.get_by_role("textbox", name="发送给 Agent 的消息")
        expect(composer).to_be_focused()
        expect(composer).to_have_value("分析这个项目的架构并给出改进顺序")
        expect(page.get_by_role("button", name="发送消息")).to_be_enabled()

        composer.fill("验证浏览器会话主链路")
        page.get_by_role("button", name="发送消息").click()
        expect(page.get_by_text("验证浏览器会话主链路", exact=True)).to_be_visible()
        expect(page.get_by_text("浏览器测试回复", exact=True)).to_be_visible(timeout=10000)
        approval = page.get_by_role("heading", name="允许调用受保护工具？")
        expect(approval).to_be_visible()
        page.get_by_role("button", name="允许本次调用").click()
        expect(approval).to_be_hidden()

        delete_button = page.get_by_role("button", name="删除对话 验证浏览器会话主链路")
        expect(delete_button).to_be_visible()
        page.once("dialog", lambda dialog: dialog.accept())
        delete_button.click()
        expect(delete_button).to_be_hidden()
        expect(page.get_by_role("heading", name="今天想让 Agent 完成什么？")).to_be_visible()

        new_chat = page.get_by_role("button", name="新对话", exact=True).first
        new_chat.click()
        expect(approval).to_be_visible()
        page.get_by_role("button", name="拒绝", exact=True).click()
        expect(approval).to_be_hidden()

        new_chat.click()
        expect(approval).to_be_visible()
        expect(approval).to_be_hidden(timeout=5000)

        response = page.goto(f"{base_url}/settings", wait_until="networkidle")
        if response is None or response.status != 200:
            raise RuntimeError("Settings page did not return HTTP 200")
        page.get_by_role("heading", name="设置").wait_for(timeout=5000)
        page.get_by_label("界面主题").select_option("light")
        expect(page.locator("html")).to_have_attribute("data-theme", "light")

        mobile_page = browser.new_page(viewport={"width": 390, "height": 844})
        mobile_page.on("pageerror", lambda error: page_errors.append(type(error).__name__))
        response = mobile_page.goto(base_url, wait_until="networkidle")
        if response is None or response.status != 200:
            raise RuntimeError("Mobile home page did not return HTTP 200")
        mobile_page.get_by_role("button", name="打开导航").click()
        sidebar = mobile_page.get_by_role("complementary", name="主导航")
        expect(sidebar).to_be_visible()
        sidebar.get_by_role("button", name="关闭导航").click()
        expect(sidebar).to_be_hidden()
        browser.close()

    if page_errors:
        raise RuntimeError(f"Browser page errors: {page_errors}")
    print(
        "Browser smoke passed: health, session create/send/delete, approvals, "
        "starter/composer, settings/theme, mobile navigation"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
