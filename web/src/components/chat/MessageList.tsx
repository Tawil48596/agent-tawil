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
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      {messages.length === 0 && !streaming && (
        <div className="text-center mt-24">
          <div className="text-5xl mb-4">🤖</div>
          <div className="text-lg font-semibold">AI Agent Platform</div>
          <div className="text-sm text-[#8b8fa3] mt-2">输入消息开始对话 · 支持模型切换 · GitHub搜索</div>
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
