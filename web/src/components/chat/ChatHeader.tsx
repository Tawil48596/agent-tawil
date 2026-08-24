import { useChatStore } from "@/stores/chatStore";
import { GitBranch, Circle, Wrench } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useState } from "react";

export function ChatHeader() {
  const model = useChatStore((s) => s.model);
  const task = useChatStore((s) => s.task);
  const models = useChatStore((s) => s.models);
  const setModel = useChatStore((s) => s.setModel);
  const setTask = useChatStore((s) => s.setTask);
  const reasoningEffort = useChatStore((s) => s.reasoningEffort);
  const setReasoningEffort = useChatStore((s) => s.setReasoningEffort);
  const toolsEnabled = useChatStore((s) => s.toolsEnabled);
  const setToolsEnabled = useChatStore((s) => s.setToolsEnabled);
  const tools = useChatStore((s) => s.tools);
  const dangerousToolsEnabled = useChatStore((s) => s.dangerousToolsEnabled);
  const toggleDangerousTool = useChatStore((s) => s.toggleDangerousTool);
  const activeId = useChatStore((s) => s.activeId);
  const error = useChatStore((s) => s.error);
  const messages = useChatStore((s) => s.messages);
  const loadSessions = useChatStore((s) => s.loadSessions);
  const lastUsage = useChatStore((s) => s.lastUsage);
  const sessionUsage = useChatStore((s) => s.sessionUsage);
  const navigate = useNavigate();
  const [forking, setForking] = useState(false);
  const formatTokens = (value = 0) => value >= 1000 ? `${(value / 1000).toFixed(1)}K` : String(value);

  const forkSession = async () => {
    if (!activeId || messages.length === 0 || forking) return;
    setForking(true);
    try {
      const lastMessageId = Number(messages[messages.length - 1].id);
      const result = await api.forkSession(activeId, lastMessageId);
      if (!result.branch_id) throw new Error(result.error || "无法创建分支");
      await loadSessions();
      navigate(`/chat/${result.branch_id}`);
    } catch (e: any) {
      useChatStore.setState({ error: e?.message || "无法创建分支" });
    } finally {
      setForking(false);
    }
  };

  return (
    <header className="relative flex min-h-14 shrink-0 flex-wrap items-center gap-2 border-b border-white/[0.07] bg-[#111111]/80 px-3 py-2.5 pl-16 backdrop-blur-xl sm:px-4 sm:pl-16 lg:px-5 2xl:flex-nowrap">
      <div className="mr-2 hidden 2xl:block">
        <div className="text-sm font-medium">工作台</div>
        <div className="mt-0.5 flex items-center gap-1 text-[11px] text-[#737373]"><Circle size={7} className="fill-[#63d6a3] text-[#63d6a3]" /> 系统已就绪</div>
      </div>
      <select value={model} onChange={(e) => setModel(e.target.value)}
        aria-label="选择模型"
        className="min-w-36 flex-1 rounded-lg border border-white/10 bg-[#1b1b1b] px-3 py-2 text-xs text-[#e4e4e7] outline-none transition hover:border-white/20 focus:border-white/25 focus:ring-2 focus:ring-white/10 sm:flex-none sm:text-sm">
        <option value="">自动路由</option>
        {models.map((m) => (
          <option key={m.name} value={m.name}>
            {m.provider ? `${m.provider} · ` : ""}{m.name}
          </option>
        ))}
      </select>
      <select value={reasoningEffort} onChange={(e) => setReasoningEffort(e.target.value)}
        title="控制支持该参数的模型所使用的思考强度"
        aria-label="选择思考强度"
        className="rounded-lg border border-white/10 bg-[#1b1b1b] px-3 py-2 text-xs text-[#e4e4e7] outline-none transition hover:border-white/20 focus:border-white/25 focus:ring-2 focus:ring-white/10 sm:text-sm">
        <option value="auto">思考：自动</option>
        <option value="low">思考：低</option>
        <option value="medium">思考：中</option>
        <option value="high">思考：高</option>
      </select>
      <button
        type="button"
        onClick={() => setToolsEnabled(!toolsEnabled)}
        title={toolsEnabled ? `已开放 ${tools.filter((tool) => !tool.is_dangerous).length} 个安全工具` : "工具调用已关闭"}
        className={`text-xs flex items-center gap-1 px-3 py-2 rounded-lg border transition ${
          toolsEnabled
            ? "border-[#63d6a3]/40 bg-[#16352f] text-[#8ff0c4]"
            : "border-white/10 text-[#a3a3a3] hover:bg-white/5 hover:text-white"
        }`}
      >
        <Wrench size={14} /> 工具{toolsEnabled ? "开启" : "关闭"}
      </button>
      {toolsEnabled && tools.some((tool) => tool.is_dangerous) && (
        <details className="relative">
          <summary className="cursor-pointer list-none rounded-lg border border-[#fbbf24]/30 px-3 py-2 text-xs text-[#fde68a] focus:outline-none focus:ring-2 focus:ring-white/30">
            受保护工具 {dangerousToolsEnabled.length || ""}
          </summary>
          <fieldset className="absolute left-0 top-[calc(100%+8px)] z-50 w-72 rounded-xl border border-[#fbbf24]/30 bg-[#171717] p-3 shadow-2xl shadow-black/40">
            <legend className="px-1 text-xs font-semibold text-[#fde68a]">每次调用仍需批准</legend>
            {tools.filter((tool) => tool.is_dangerous).map((tool) => (
              <label key={tool.name} className="mt-2 flex min-h-9 cursor-pointer items-center gap-2 rounded-lg px-2 text-xs text-[#e4e4e7] hover:bg-white/5">
                <input
                  type="checkbox"
                  checked={dangerousToolsEnabled.includes(tool.name)}
                  onChange={() => toggleDangerousTool(tool.name)}
                  className="h-4 w-4 accent-[#fbbf24]"
                />
                <span className="min-w-0 truncate">{tool.name}</span>
              </label>
            ))}
          </fieldset>
        </details>
      )}
      <select value={task} onChange={(e) => setTask(e.target.value)} aria-label="选择任务类型"
        className="hidden rounded-lg border border-white/10 bg-[#1b1b1b] px-3 py-2 text-sm text-[#e4e4e7] outline-none transition hover:border-white/20 focus:ring-2 focus:ring-white/10 xl:block">
        <option value="reasoning">推理</option>
        <option value="coding">编码</option>
        <option value="summarization">摘要</option>
      </select>
      <button onClick={forkSession} disabled={!activeId || messages.length === 0 || forking}
        title={!activeId || messages.length === 0 ? "发送消息后才能创建分支" : "从最新消息创建分支"}
        className="flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-xs text-[#a3a3a3] transition hover:bg-white/5 hover:text-white disabled:cursor-not-allowed disabled:opacity-40">
        <GitBranch size={14} /> <span className="hidden sm:inline">{forking ? "创建中…" : "分支"}</span>
      </button>
      <div
        className="ml-auto hidden items-center gap-2 rounded-lg border border-white/[0.08] bg-[#171717] px-3 py-1.5 text-[11px] text-[#a3a3a3] xl:flex"
        title={sessionUsage ? [
          `请求：${sessionUsage.requests}`,
          `输入：${sessionUsage.input_tokens}`,
          `缓存命中：${sessionUsage.cached_input_tokens}`,
          `缓存写入：${sessionUsage.cache_write_input_tokens}`,
          `输出：${sessionUsage.output_tokens}`,
          `推理：${sessionUsage.reasoning_tokens}`,
          `总计：${sessionUsage.total_tokens}`,
          `缓存命中率：${((sessionUsage.cache_hit_rate || 0) * 100).toFixed(1)}%`,
        ].join("\n") : "发送消息后显示 Token 用量"}
      >
        <span>本轮 <b className="text-[#e4e4e7]">{formatTokens(lastUsage?.total_tokens)}</b></span>
        <span>缓存 <b className="text-[#8ff0c4]">{formatTokens(lastUsage?.cached_input_tokens)}</b></span>
        <span>会话 <b className="text-[#d4d4d8]">{formatTokens(sessionUsage?.total_tokens)}</b></span>
      </div>
      <span className="ml-auto text-xs text-[#737373]">
        {error ? <span className="text-[#f87171] mr-3">调用失败</span> : null}
        会话: {activeId?.slice(0, 8)}
      </span>
      {error && (
        <div className="absolute right-4 top-[calc(100%+8px)] z-50 w-[min(680px,calc(100vw-2rem))] rounded-xl border border-[#f87171]/40 bg-[#241315] p-4 shadow-2xl shadow-black/40">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="text-xs font-semibold text-[#fca5a5] mb-1">模型调用失败</div>
              <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-[#fecaca] font-sans">{error}</pre>
            </div>
            <button
              type="button"
              onClick={() => useChatStore.getState().clearError()}
              className="shrink-0 rounded-md border border-[#f87171]/30 px-2 py-1 text-[11px] text-[#fca5a5] hover:bg-white/5"
            >
              关闭
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
