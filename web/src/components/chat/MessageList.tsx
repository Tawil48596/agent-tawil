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
    <div className="flex-1 space-y-6 overflow-y-auto bg-[radial-gradient(circle_at_50%_-12%,rgba(255,255,255,.045),transparent_34rem)] px-4 py-8 sm:px-6">
      {messages.length === 0 && !streaming && (
        <div className="mx-auto mt-[clamp(3rem,10vh,7rem)] max-w-2xl text-center">
          <div className="mx-auto mb-5 grid h-12 w-12 place-items-center rounded-xl border border-white/10 bg-[#1b1b1b] text-xl text-[#d4d4d8] shadow-xl shadow-black/20">✦</div>
          <h1 className="text-2xl font-medium tracking-[-0.025em] text-[#f4f4f5] sm:text-3xl">今天想让 Agent 完成什么？</h1>
          <p className="mt-3 text-sm leading-6 text-[#a3a3a3]">从具体目标开始。Agent 可以调用工具、检索知识，并在中断后继续工作。</p>
          <div className="mt-7 grid gap-2 text-left sm:grid-cols-3">
            {STARTERS.map((starter) => (
              <button
                type="button"
                key={starter}
                onClick={() => onSuggestion(starter)}
                className="min-h-20 rounded-xl border border-white/[0.08] bg-[#151515]/80 p-3 text-left text-xs leading-5 text-[#c4c4c8] transition hover:-translate-y-0.5 hover:border-white/20 hover:bg-[#1b1b1b] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50 motion-reduce:transform-none"
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
          <div className="w-full max-w-3xl px-1 py-3 text-sm">
            {streamContent ? <AssistantMessage content={streamContent} /> : <span className="animate-pulse text-[#737373]">思考中...</span>}
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
