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
    <header className="h-16 border-b border-white/10 flex items-center px-6 gap-3 shrink-0 bg-[#121a2d]/70 backdrop-blur-xl">
      <div className="mr-2 hidden lg:block">
        <div className="text-sm font-semibold">工作台</div>
        <div className="text-[11px] text-[#8f9dbc] mt-0.5 flex items-center gap-1"><Circle size={7} className="fill-[#63d6a3] text-[#63d6a3]" /> 系统已就绪</div>
      </div>
      <select value={model} onChange={(e) => setModel(e.target.value)}
        className="bg-[#18233b] text-sm border border-white/10 rounded-lg px-3 py-2 text-[#e1e4ea] focus:outline-none focus:ring-2 focus:ring-[#7899ff]/40">
        <option value="">自动路由</option>
        {models.map((m) => (
          <option key={m.name} value={m.name}>
            {m.provider ? `${m.provider} · ` : ""}{m.name}
          </option>
        ))}
      </select>
      <select value={reasoningEffort} onChange={(e) => setReasoningEffort(e.target.value)}
        title="控制支持该参数的模型所使用的思考强度"
        className="bg-[#18233b] text-sm border border-white/10 rounded-lg px-3 py-2 text-[#e1e4ea] focus:outline-none focus:ring-2 focus:ring-[#7899ff]/40">
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
            : "border-white/10 text-[#9ca9c9] hover:bg-white/5"
        }`}
      >
        <Wrench size={14} /> 工具{toolsEnabled ? "开启" : "关闭"}
      </button>
      <select value={task} onChange={(e) => setTask(e.target.value)}
        className="bg-[#18233b] text-sm border border-white/10 rounded-lg px-3 py-2 text-[#e1e4ea] focus:outline-none focus:ring-2 focus:ring-[#7899ff]/40">
        <option value="reasoning">推理</option>
        <option value="coding">编码</option>
        <option value="summarization">摘要</option>
      </select>
      <button onClick={forkSession} disabled={!activeId || messages.length === 0 || forking}
        title={!activeId || messages.length === 0 ? "发送消息后才能创建分支" : "从最新消息创建分支"}
        className="text-xs text-[#9ca9c9] hover:text-white flex items-center gap-1 px-3 py-2 rounded-lg border border-white/10 hover:bg-white/5 transition disabled:opacity-40 disabled:cursor-not-allowed">
        <GitBranch size={14} /> {forking ? "创建中…" : "分支"}
      </button>
      <div
        className="ml-auto hidden xl:flex items-center gap-2 rounded-lg border border-white/10 bg-[#10182a] px-3 py-1.5 text-[11px] text-[#9cacca]"
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
        <span>本轮 <b className="text-[#dce5ff]">{formatTokens(lastUsage?.total_tokens)}</b></span>
        <span>缓存 <b className="text-[#8ff0c4]">{formatTokens(lastUsage?.cached_input_tokens)}</b></span>
        <span>会话 <b className="text-[#aebfff]">{formatTokens(sessionUsage?.total_tokens)}</b></span>
      </div>
      <span className="text-xs text-[#8f9dbc]">
        {error ? <span className="text-[#f87171] mr-3 cursor-pointer" onClick={() => useChatStore.getState().clearError()} title="点击清除">{error.slice(0, 40)}</span> : null}
        会话: {activeId?.slice(0, 8)}
      </span>
    </header>
  );
}
