import { useState, useRef, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useChatStore } from "@/stores/chatStore";
import { Send, StopCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { ToolCallCard } from "@/components/chat/ToolCallCard";

export function ChatView() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { messages, streaming, streamContent, model, task, models, setModel, setTask, sendMessage, selectSession, activeId, createSession } = useChatStore();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sessionId && sessionId !== activeId) selectSession(sessionId);
  }, [sessionId]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streamContent]);

  const handleSend = async () => {
    if (!input.trim() || streaming) return;
    const text = input; setInput("");
    if (!activeId && !sessionId) {
      const id = await createSession();
      navigate(`/chat/${id}`);
      await sendMessage(text);
    } else {
      await sendMessage(text);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
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
        <span className="text-xs text-[#8b8fa3] ml-auto">会话: {activeId?.slice(0,8)}</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && !streaming && (
          <div className="text-center mt-24">
            <div className="text-5xl mb-4">🤖</div>
            <div className="text-lg font-semibold">AI Agent Platform</div>
            <div className="text-sm text-[#8b8fa3] mt-2">输入消息开始对话 · 支持模型切换 · GitHub搜索</div>
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}>
            <div className={cn("max-w-[80%] px-4 py-3 rounded-xl text-sm leading-relaxed",
              msg.role === "user" ? "bg-[#1a1d27]" : "bg-transparent border border-[#2a2d3a]")}>
              {msg.role === "user" ? <p>{msg.content}</p> : <MarkdownRenderer content={msg.content} />}
              {msg.tool_calls?.map((tc, i) => <ToolCallCard key={i} call={tc} />)}
            </div>
          </div>
        ))}
        {streaming && (
          <div className="flex justify-start">
            <div className="max-w-[80%] px-4 py-3 rounded-xl text-sm border border-[#2a2d3a]">
              {streamContent ? <MarkdownRenderer content={streamContent} /> : <span className="text-[#8b8fa3] animate-pulse">思考中...</span>}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-[#2a2d3a] shrink-0">
        <div className="flex gap-3">
          <input value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="输入消息... (Enter 发送)"
            className="flex-1 bg-[#1a1d27] border border-[#2a2d3a] rounded-xl px-4 py-3 text-sm outline-none focus:border-[#6c8cff] text-[#e1e4ea] placeholder-[#8b8fa3]"
          />
          <button onClick={handleSend} disabled={streaming}
            className="bg-[#6c8cff] hover:opacity-90 disabled:opacity-40 text-white rounded-xl px-4 py-3">
            {streaming ? <StopCircle size={18} /> : <Send size={18} />}
          </button>
        </div>
      </div>
    </div>
  );
}
