import { ChangeEvent, useRef, useState } from "react";
import { RotateCcw, Send, StopCircle, Paperclip } from "lucide-react";
import { useChatStore } from "@/stores/chatStore";

export function InputArea() {
  const [text, setText] = useState("");
  const streaming = useChatStore((s) => s.streaming);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const stopStreaming = useChatStore((s) => s.stopStreaming);
  const retryLastMessage = useChatStore((s) => s.retryLastMessage);
  const interrupted = useChatStore((s) => s.interrupted);
  const fileRef = useRef<HTMLInputElement>(null);
  const [attachmentName, setAttachmentName] = useState("");

  const attachFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 1024 * 1024) {
      useChatStore.setState({ error: "附件不能超过 1 MB" });
      return;
    }
    try {
      const content = await file.text();
      setText((current) => `${current}${current ? "\n\n" : ""}附件：${file.name}\n\`\`\`\n${content}\n\`\`\``);
      setAttachmentName(file.name);
    } catch {
      useChatStore.setState({ error: "当前仅支持文本类附件" });
    }
  };

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || streaming) return;
    setText("");
    sendMessage(trimmed);
  };

  return (
    <div className="px-6 pb-5 pt-3 shrink-0">
      <div className="flex gap-3 items-center max-w-4xl mx-auto rounded-2xl border border-white/10 bg-[#18233b]/75 px-2 py-2 shadow-2xl shadow-black/10 focus-within:ring-2 focus-within:ring-[#7899ff]/35">
        <input ref={fileRef} type="file" className="hidden"
          accept=".txt,.md,.json,.yaml,.yml,.toml,.csv,.py,.js,.jsx,.ts,.tsx,.css,.html,.go,.rs,.java"
          onChange={attachFile} />
        <button onClick={() => fileRef.current?.click()} className="text-[#9ca9c9] hover:text-white hover:bg-white/5 rounded-xl p-2 transition" title={attachmentName || "添加文本附件"}>
          <Paperclip size={18} />
        </button>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="描述你希望 Agent 完成的工作…"
          className="flex-1 bg-transparent px-3 py-3 text-sm outline-none text-[#edf1ff] placeholder-[#8290b2]"
        />
        {interrupted && !streaming && (
          <button
            onClick={() => retryLastMessage()}
            className="text-[#a9b8db] hover:text-white rounded-xl px-3 py-3 hover:bg-white/5 transition flex items-center gap-2 text-xs"
            title="重新发送上一条消息"
          >
            <RotateCcw size={17} /> 重新发送
          </button>
        )}
        <button
          onClick={streaming ? stopStreaming : handleSend}
          disabled={!streaming && !text.trim()}
          title={streaming ? "停止生成" : "发送"}
          className="bg-gradient-to-br from-[#86a4ff] to-[#765dff] hover:brightness-110 disabled:opacity-40 text-white rounded-xl px-4 py-3 shadow-lg shadow-[#6c8cff]/20 transition"
        >
          {streaming ? <StopCircle size={18} /> : <Send size={18} />}
        </button>
      </div>
    </div>
  );
}
