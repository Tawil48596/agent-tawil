import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { run as runAxe } from "axe-core";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import App from "./App";

function apiPayload(url: string) {
  if (url.endsWith("/chat/models")) return { available_models: [], models: [] };
  if (url.endsWith("/tools")) return { tools: [] };
  if (url.endsWith("/chat/sessions")) return { items: [] };
  throw new Error(`Unexpected request: ${url}`);
}

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    return new Response(JSON.stringify(apiPayload(url)), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }));
});

test("a task starter fills and focuses the composer", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><App /></MemoryRouter>);

  const starter = await screen.findByRole("button", {
    name: "分析这个项目的架构并给出改进顺序",
  });
  await user.click(starter);

  const composer = screen.getByRole("textbox", { name: "发送给 Agent 的消息" });
  expect(composer).toHaveValue("分析这个项目的架构并给出改进顺序");
  expect(composer).toHaveFocus();
  expect(screen.getByRole("button", { name: "发送消息" })).toBeEnabled();
});

test("the empty chat screen has no detectable accessibility violations", async () => {
  const { container } = render(<MemoryRouter><App /></MemoryRouter>);
  await screen.findByRole("heading", { name: "今天想让 Agent 完成什么？" });

  const results = await runAxe(container, {
    rules: { "color-contrast": { enabled: false } },
  });
  expect(results.violations).toEqual([]);
});

test("an interrupted message can be retried without duplicating user text", async () => {
  const requests: Array<Record<string, unknown>> = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = init?.method || "GET";
    if (url.endsWith("/chat/models")) {
      return Response.json({ available_models: [], models: [] });
    }
    if (url.endsWith("/tools")) return Response.json({ tools: [] });
    if (url.endsWith("/chat/sessions") && method === "GET") {
      return Response.json({ items: [] });
    }
    if (url.endsWith("/chat/sessions") && method === "POST") {
      return Response.json({
        id: "retry-session",
        title: "新对话",
        source: "test",
        created_at: "2026-08-23T00:00:00Z",
        updated_at: "2026-08-23T00:00:00Z",
      });
    }
    if (url.endsWith("/chat/sessions/retry-session/messages") && method === "POST") {
      requests.push(JSON.parse(String(init?.body)));
      if (requests.length === 1) {
        return await new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        });
      }
      return new Response(
        `data: ${JSON.stringify({ type: "done", content: "恢复后的回复" })}\n\n`,
        { status: 200, headers: { "Content-Type": "text/event-stream" } },
      );
    }
    throw new Error(`Unexpected request: ${method} ${url}`);
  }));

  const user = userEvent.setup();
  render(<MemoryRouter><App /></MemoryRouter>);
  const composer = await screen.findByRole("textbox", { name: "发送给 Agent 的消息" });
  await user.type(composer, "可恢复任务");
  await user.click(screen.getByRole("button", { name: "发送消息" }));
  await user.click(await screen.findByRole("button", { name: "停止生成" }));
  await user.click(await screen.findByRole("button", { name: "重新发送" }));

  expect(await screen.findByText("恢复后的回复")).toBeInTheDocument();
  expect(screen.getAllByText("可恢复任务")).toHaveLength(1);
  expect(requests.map((request) => request.retry)).toEqual([false, true]);
});
