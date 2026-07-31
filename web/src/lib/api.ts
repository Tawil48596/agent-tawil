const API = "/api/v1";

async function fetchJSON(url: string, options?: RequestInit) {
  const r = await fetch(url, { headers: { "Content-Type": "application/json", ...options?.headers }, ...options });
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  return r.json();
}

export const api = {
  // Chat
  createSession: (title: string) => fetchJSON(`${API}/chat/sessions`, { method: "POST", body: JSON.stringify({ title }) }),
  listSessions: () => fetchJSON(`${API}/chat/sessions`),
  getSession: (id: string) => fetchJSON(`${API}/chat/sessions/${id}`),
  deleteSession: (id: string) => fetchJSON(`${API}/chat/sessions/${id}`, { method: "DELETE" }),
  sendMessage: (
    sessionId: string,
    content: string,
    model?: string,
    taskType?: string,
    reasoningEffort?: string,
    tools?: string[],
  ) =>
    fetch(`${API}/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, model, task_type: taskType, reasoning_effort: reasoningEffort, tools }),
      headers: { "Content-Type": "application/json" },
    }),
  getMessages: (sessionId: string) => fetchJSON(`${API}/chat/sessions/${sessionId}/messages`),
  getModels: () => fetchJSON(`${API}/chat/models`),
  forkSession: (sessionId: string, atMessageId: number, title?: string) =>
    fetchJSON(`${API}/chat/sessions/${sessionId}/fork`, {
      method: "POST",
      body: JSON.stringify({ at_message_id: atMessageId, title }),
    }),
  // Tools
  listTools: () => fetchJSON(`${API}/tools`),
  getToolStats: () => fetchJSON(`${API}/tools/stats`),
  // Health
  health: () => fetchJSON("/health"),
};
