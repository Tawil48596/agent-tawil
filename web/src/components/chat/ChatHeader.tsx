import { useChatStore } from "@/stores/chatStore";
import { GitBranch } from "lucide-react";

export function ChatHeader() {
  const { model, task, models, setModel, setTask, activeId } = useChatStore();

  return (
    <div className="h-12 border-b border-[#2a2d3a] flex items-center px-4 gap-3 shrink-0">
      <select value={model} onChange={(e) => setModel(e.target.value)}
        className="bg-[#1a1d27] text-sm border border-[#2a2d3a] rounded px-3 py-1.5 text-[#e1e4ea]">
        <option value="">自动路由</option>
        {models.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
      </select>
      <select value={task} onChange={(e) => setTask(e.target.value)}
        className="bg-[#1a1d27] text-sm border border-[#2a2d3a] rounded px-3 py-1.5 text-[#e1e4ea]">
        <option value="reasoning">推理</option>
        <option value="coding">编码</option>
        <option value="summarization">摘要</option>
      </select>
      <button className="text-xs text-[#8b8fa3] hover:text-[#e1e4ea] flex items-center gap-1 px-2 py-1 rounded border border-[#2a2d3a]">
        <GitBranch size={14} /> 分支
      </button>
      <span className="text-xs text-[#8b8fa3] ml-auto">会话: {activeId?.slice(0, 8)}</span>
    </div>
  );
}
