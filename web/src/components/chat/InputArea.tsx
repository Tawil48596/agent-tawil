import { useState } from "react";
import { Send, StopCircle, Paperclip } from "lucide-react";
import { useChatStore } from "@/stores/chatStore";

export function InputArea() {
  const [text, setText] = useState("");
  const streaming = useChatStore((s) => s.streaming);
  const sendMessage = useChatStore((s) => s.sendMessage);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || streaming) return;
    setText("");
    sendMessage(trimmed);
  };

  return (
    <div className="px-6 pb-5 pt-3 shrink-0">
      <div className="flex gap-3 items-center max-w-4xl mx-auto rounded-2xl border border-white/10 bg-[#18233b]/75 px-2 py-2 shadow-2xl shadow-black/10 focus-within:ring-2 focus-within:ring-[#7899ff]/35">
        <button className="text-[#9ca9c9] hover:text-white hover:bg-white/5 rounded-xl p-2 transition" title="附件">
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
        <button
          onClick={handleSend}
          disabled={streaming}
          className="bg-gradient-to-br from-[#86a4ff] to-[#765dff] hover:brightness-110 disabled:opacity-40 text-white rounded-xl px-4 py-3 shadow-lg shadow-[#6c8cff]/20 transition"
        >
          {streaming ? <StopCircle size={18} /> : <Send size={18} />}
        </button>
      </div>
    </div>
  );
}
