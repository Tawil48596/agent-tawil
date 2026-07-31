import { useChatStore } from "@/stores/chatStore";
import { GitBranch, Circle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useState } from "react";

export function ChatHeader() {
  const model = useChatStore((s) => s.model);
  const task = useChatStore((s) => s.task);
  const models = useChatStore((s) => s.models);
  const setModel = useChatStore((s) => s.setModel);
  const setTask = useChatStore((s) => s.setTask);
  const activeId = useChatStore((s) => s.activeId);
  const error = useChatStore((s) => s.error);
  const messages = useChatStore((s) => s.messages);
  const loadSessions = useChatStore((s) => s.loadSessions);
  const navigate = useNavigate();
  const [forking, setForking] = useState(false);

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
        {models.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
      </select>
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
      <span className="text-xs text-[#8f9dbc] ml-auto">
        {error ? <span className="text-[#f87171] mr-3 cursor-pointer" onClick={() => useChatStore.getState().clearError()} title="点击清除">{error.slice(0, 40)}</span> : null}
        会话: {activeId?.slice(0, 8)}
      </span>
    </header>
  );
}
