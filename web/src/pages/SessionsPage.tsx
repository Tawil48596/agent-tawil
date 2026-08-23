import { Clock3, MessageSquare, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { formatTime } from "@/lib/utils";
import { useChatStore } from "@/stores/chatStore";

export function SessionsPage() {
  const {
    sessions,
    activeId,
    selectSession,
    deleteSession,
  } = useChatStore();
  const navigate = useNavigate();

  const removeSession = async (
    sessionId: string,
  ) => {
    if (!window.confirm("删除这个对话？此操作无法撤销。")) return;
    await deleteSession(sessionId);
    if (activeId === sessionId) navigate("/");
  };

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="mb-6">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <MessageSquare size={20} /> 对话
        </h2>
        <p className="text-xs text-[#8b8fa3] mt-1">
          对话会自动保存在本机，重启后仍可继续。
        </p>
      </div>

      <div className="space-y-2 max-w-4xl">
        {sessions.map((session) => (
          <div key={session.id} className="group flex items-center gap-2 rounded-xl border border-[#2a2d3a] bg-[#1a1d27] p-2 transition hover:border-[#6c8cff]">
            <button type="button" onClick={() => { void selectSession(session.id); navigate(`/chat/${session.id}`); }} className="min-w-0 flex-1 p-2 text-left">
              <span className="block truncate text-sm font-medium">
                {session.title || "新对话"}
              </span>
              <span className="mt-1 flex items-center gap-2 text-xs text-[#8b8fa3]">
                <Clock3 size={12} aria-hidden="true" />
                {formatTime(session.updated_at || session.created_at)}
                {typeof session.message_count === "number" && (
                  <span>· {session.message_count} 条消息</span>
                )}
              </span>
            </button>
            <button
              type="button"
              aria-label={`删除对话 ${session.title || "新对话"}`}
              onClick={() => void removeSession(session.id)}
              className="opacity-60 group-hover:opacity-100 text-[#8b8fa3] hover:text-[#f87171] p-2 rounded-lg hover:bg-[#f87171]/10 transition"
            >
              <Trash2 size={15} />
            </button>
          </div>
        ))}
        {sessions.length === 0 && (
          <div className="border border-dashed border-[#2a2d3a] rounded-xl py-14 text-center text-sm text-[#8b8fa3]">
            还没有保存的对话
          </div>
        )}
      </div>
    </div>
  );
}
