import { useChatStore } from "@/stores/chatStore";
import { Wrench, Brain, BookOpen } from "lucide-react";

export function ContextPanel() {
  const tools = useChatStore((s) => s.tools);

  return (
    <div className="w-72 bg-[#1a1d27] border-l border-[#2a2d3a] overflow-y-auto p-4 shrink-0">
      <div className="mb-6">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#8b8fa3] mb-3 flex items-center gap-1">
          <Brain size={14} /> 上下文
        </h3>
        <p className="text-xs text-[#8b8fa3]">暂无记忆召回</p>
      </div>
      <div className="mb-6">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#8b8fa3] mb-3 flex items-center gap-1">
          <BookOpen size={14} /> RAG 来源
        </h3>
        <p className="text-xs text-[#8b8fa3]">暂无检索来源</p>
      </div>
      <div>
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#8b8fa3] mb-3 flex items-center gap-1">
          <Wrench size={14} /> 活跃工具 ({tools.length})
        </h3>
        {tools.slice(0, 10).map((t) => (
          <div key={t.name} className="text-xs py-1.5 px-2 rounded mb-1 hover:bg-[#2a2d3a]">
            <span className="text-[#e1e4ea] font-medium">{t.name}</span>
            <span className="text-[#8b8fa3] ml-2">{t.description?.slice(0, 30)}</span>
            {t.is_dangerous && <span className="ml-1 text-[#f87171] text-[10px]">危险</span>}
          </div>
        ))}
        {tools.length === 0 && <p className="text-xs text-[#8b8fa3]">加载中...</p>}
      </div>
    </div>
  );
}
