import { useChatStore } from "@/stores/chatStore";
import { Wrench, Brain, BookOpen } from "lucide-react";

export function ContextPanel() {
  const tools = useChatStore((s) => s.tools);

  return (
    <aside aria-label="当前上下文" className="hidden w-72 shrink-0 overflow-y-auto border-l border-white/[0.07] bg-[#111111]/90 p-4 2xl:block">
      <div className="mb-6">
        <h2 className="mb-3 flex items-center gap-1 text-[11px] font-medium uppercase tracking-wider text-[#a1a1aa]">
          <Brain size={14} aria-hidden="true" /> 上下文
        </h2>
        <p className="text-xs text-[#737373]">暂无记忆召回</p>
      </div>
      <div className="mb-6">
        <h2 className="mb-3 flex items-center gap-1 text-[11px] font-medium uppercase tracking-wider text-[#a1a1aa]">
          <BookOpen size={14} aria-hidden="true" /> RAG 来源
        </h2>
        <p className="text-xs text-[#737373]">暂无检索来源</p>
      </div>
      <div>
        <h2 className="mb-3 flex items-center gap-1 text-[11px] font-medium uppercase tracking-wider text-[#a1a1aa]">
          <Wrench size={14} aria-hidden="true" /> 活跃工具 ({tools.length})
        </h2>
        {tools.slice(0, 10).map((t) => (
          <div key={t.name} className="mb-1 rounded-lg px-2 py-2 text-xs hover:bg-white/[0.05]">
            <span className="font-medium text-[#e4e4e7]">{t.name}</span>
            <span className="ml-2 text-[#737373]">{t.description?.slice(0, 30)}</span>
            {t.is_dangerous && <span className="ml-1 text-[#f87171] text-[10px]">危险</span>}
          </div>
        ))}
        {tools.length === 0 && <p className="text-xs text-[#737373]">加载中...</p>}
      </div>
    </aside>
  );
}
