import { useState } from "react";
import { Send, StopCircle, Paperclip } from "lucide-react";
import { useChatStore } from "@/stores/chatStore";
import { useNavigate, useParams } from "react-router-dom";

export function InputArea() {
  const [text, setText] = useState("");
  const { streaming, sendMessage, activeId, createSession } = useChatStore();
  const navigate = useNavigate();
  const { sessionId } = useParams();

  const handleSend = async () => {
    if (!text.trim() || streaming) return;
    const content = text; setText("");
    if (!activeId && !sessionId) {
      const id = await createSession();
      navigate(`/chat/${id}`);
    }
    await sendMessage(content);
  };

  return (
    <div className="p-3 border-t border-[#2a2d3a] shrink-0">
      {/* Attachment bar */}
      <div className="flex gap-3 items-center">
        <button className="text-[#8b8fa3] hover:text-[#e1e4ea] p-2" title="附件">
          <Paperclip size={18} />
        </button>
        <input value={text} onChange={(e) => setText(e.target.value)}
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
  );
}
