import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { UserMessage } from "./UserMessage";
import { AssistantMessage } from "./AssistantMessage";
import { BranchIndicator } from "./BranchIndicator";

export function MessageList() {
  const { messages, streaming, streamContent } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streamContent]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-8 space-y-5 bg-[radial-gradient(circle_at_45%_-10%,rgba(108,140,255,.16),transparent_34%)]">
      {messages.length === 0 && !streaming && (
        <div className="text-center mt-24 max-w-lg mx-auto">
          <div className="text-5xl mb-5">✦</div>
          <div className="text-2xl font-semibold tracking-tight">从一个清晰的任务开始</div>
          <div className="text-sm text-[#9ca9c9] mt-3 leading-6">选择模型和任务类型，然后让 Agent 调用工具、检索知识并持续完成工作。</div>
          <div className="mt-7 flex justify-center gap-2 text-xs text-[#aebdff]"><span className="rounded-full bg-[#6c8cff]/15 px-3 py-1.5">模型路由</span><span className="rounded-full bg-[#6c8cff]/15 px-3 py-1.5">工具调用</span><span className="rounded-full bg-[#6c8cff]/15 px-3 py-1.5">SSE 流式输出</span></div>
        </div>
      )}
      {messages.map((msg) =>
        msg.role === "user" ? <UserMessage key={msg.id} message={msg} /> :
        msg.role === "assistant" ? <AssistantMessage key={msg.id} message={msg} /> :
        msg.role === "system" ? <BranchIndicator key={msg.id} message={msg} /> : null
      )}
      {streaming && (
        <div className="flex justify-start">
          <div className="max-w-[80%] px-4 py-3 rounded-xl text-sm border border-[#2a2d3a]">
            {streamContent ? <AssistantMessage content={streamContent} /> : <span className="text-[#8b8fa3] animate-pulse">思考中...</span>}
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
