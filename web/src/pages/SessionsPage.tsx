import { useChatStore } from "@/stores/chatStore";
import { useNavigate } from "react-router-dom";
import { MessageSquare, Trash2 } from "lucide-react";
import { formatTime } from "@/lib/utils";

export function SessionsPage() {
  const { sessions, selectSession, loadSessions } = useChatStore();
  const navigate = useNavigate();

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-lg font-semibold flex items-center gap-2 mb-4"><MessageSquare size={20} /> 历史会话</h2>
      <div className="space-y-2">
        {sessions.map((s) => (
          <div key={s.id} onClick={() => { selectSession(s.id); navigate(`/chat/${s.id}`); }}
            className="bg-[#1a1d27] border border-[#2a2d3a] rounded-lg p-3 cursor-pointer hover:border-[#6c8cff] flex items-center justify-between">
            <div><div className="text-sm font-medium">{s.title || "未命名"}</div>
              <div className="text-xs text-[#8b8fa3]">{formatTime(s.created_at)} · {s.source}</div></div>
            <button onClick={(e) => { e.stopPropagation(); useChatStore.getState().loadSessions(); }}
              className="text-[#8b8fa3] hover:text-[#f87171] p-1"><Trash2 size={14} /></button>
          </div>
        ))}
      </div>
    </div>
  );
}
