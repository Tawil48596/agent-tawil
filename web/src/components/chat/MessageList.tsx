import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { UserMessage } from "./UserMessage";
import { AssistantMessage } from "./AssistantMessage";
import { BranchIndicator } from "./BranchIndicator";

const STARTERS = [
  "分析这个项目的架构并给出改进顺序",
  "搜索资料并整理一份带来源的研究摘要",
  "检查代码问题，先说明风险再提出修改方案",
];

export function MessageList({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  const { messages, streaming, streamContent } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    bottomRef.current?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth" });
  }, [messages, streamContent]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-8 space-y-5 bg-[radial-gradient(circle_at_45%_-10%,rgba(108,140,255,.16),transparent_34%)]">
      {messages.length === 0 && !streaming && (
        <div className="mt-[clamp(3rem,10vh,7rem)] max-w-2xl mx-auto text-center">
          <div className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl border border-[#8aa7ff]/25 bg-[#6c8cff]/10 text-2xl text-[#b8c5ff] shadow-xl shadow-[#6c8cff]/10">✦</div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">今天想让 Agent 完成什么？</h1>
          <p className="text-sm text-[#9ca9c9] mt-3 leading-6">从具体目标开始。Agent 可以调用工具、检索知识，并在中断后继续工作。</p>
          <div className="mt-7 grid gap-2 text-left sm:grid-cols-3">
            {STARTERS.map((starter) => (
              <button
                type="button"
                key={starter}
                onClick={() => onSuggestion(starter)}
                className="min-h-20 rounded-xl border border-white/10 bg-[#121a2d]/65 p-3 text-left text-xs leading-5 text-[#bdc9e8] transition hover:-translate-y-0.5 hover:border-[#8aa7ff]/35 hover:bg-[#18233b] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8aa7ff] motion-reduce:transform-none"
              >
                {starter}
              </button>
            ))}
          </div>
        </div>
      )}
      {messages.map((msg) =>
        msg.role === "user" ? <UserMessage key={msg.id} message={msg} /> :
        msg.role === "assistant" ? <AssistantMessage key={msg.id} message={msg} /> :
        msg.role === "system" ? <BranchIndicator key={msg.id} message={msg} /> : null
      )}
      {streaming && (
        <div className="flex justify-start" role="status" aria-live="polite">
          <div className="max-w-[80%] px-4 py-3 rounded-xl text-sm border border-[#2a2d3a]">
            {streamContent ? <AssistantMessage content={streamContent} /> : <span className="text-[#8b8fa3] animate-pulse">思考中...</span>}
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
