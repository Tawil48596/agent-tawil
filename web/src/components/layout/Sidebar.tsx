import { useLocation, useNavigate } from "react-router-dom";
import {
  BarChart3,
  BookOpen,
  Bot,
  History,
  MessageSquare,
  Plus,
  Settings,
  Sparkles,
  Trash2,
  Wrench,
} from "lucide-react";

import { cn, truncate } from "@/lib/utils";
import { useChatStore } from "@/stores/chatStore";

export function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    sessions,
    activeId,
    createSession,
    selectSession,
    deleteSession,
  } = useChatStore();

  const navItems = [
    { to: "/sessions", icon: History, label: "全部对话" },
    { to: "/tools", icon: Wrench, label: "工具" },
    { to: "/knowledge", icon: BookOpen, label: "知识库" },
    { to: "/agents", icon: Bot, label: "多智能体" },
    { to: "/analytics", icon: BarChart3, label: "用量" },
    { to: "/settings", icon: Settings, label: "设置" },
  ];

  const removeSession = async (
    event: React.MouseEvent,
    sessionId: string,
  ) => {
    event.stopPropagation();
    if (!window.confirm("删除这个对话？此操作无法撤销。")) return;
    await deleteSession(sessionId);
    if (activeId === sessionId) navigate("/");
  };

  return (
    <aside className="w-[17.5rem] bg-[#101729]/95 border-r border-white/10 flex flex-col shrink-0 backdrop-blur-xl">
      <div className="p-5 border-b border-white/10">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate("/")}>
          <span className="h-9 w-9 rounded-xl bg-gradient-to-br from-[#8aa7ff] to-[#7b5cff] flex items-center justify-center shadow-lg shadow-[#6c8cff]/20">
            <Sparkles size={17} />
          </span>
          <div className="leading-tight">
            <h1 className="text-sm font-semibold tracking-tight">Agent Studio</h1>
            <p className="text-[10px] text-[#9ca9c9] mt-0.5">AI workspace · v0.1.1</p>
          </div>
        </div>
      </div>

      <button
        onClick={async () => {
          const id = await createSession();
          navigate(`/chat/${id}`);
        }}
        className="mx-4 mt-4 py-3 bg-gradient-to-r from-[#7899ff] to-[#8068ff] hover:brightness-110 text-white rounded-xl text-sm font-semibold flex items-center justify-center gap-2 shadow-lg shadow-[#6c8cff]/20 transition"
      >
        <Plus size={16} /> 新对话
      </button>

      <div className="px-5 pt-5 text-[10px] tracking-[0.16em] text-[#7785a9] font-semibold">
        最近对话
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {sessions.slice(0, 12).map((session) => (
          <div
            key={session.id}
            onClick={() => {
              selectSession(session.id);
              navigate(`/chat/${session.id}`);
            }}
            className={cn(
              "group px-3 py-2.5 rounded-lg cursor-pointer text-sm mb-1 hover:bg-white/[0.06] text-[#9ca9c9] hover:text-white transition flex items-center gap-2",
              activeId === session.id &&
                "bg-[#6c8cff]/15 text-white ring-1 ring-[#8aa7ff]/20",
            )}
          >
            <MessageSquare size={14} className="shrink-0 opacity-70" />
            <span className="min-w-0 flex-1 truncate">
              {truncate(session.title || "新对话", 25)}
            </span>
            <button
              aria-label={`删除对话 ${session.title || "新对话"}`}
              onClick={(event) => removeSession(event, session.id)}
              className="opacity-0 group-hover:opacity-100 focus:opacity-100 text-[#7785a9] hover:text-[#f87171] p-1 rounded transition"
            >
              <Trash2 size={13} />
            </button>
          </div>
        ))}
        {sessions.length === 0 && (
          <p className="px-3 py-4 text-xs text-[#66718e]">还没有对话</p>
        )}
      </div>

      <div className="border-t border-white/10 p-3">
        {navItems.map(({ to, icon: Icon, label }) => (
          <div
            key={to}
            onClick={() => navigate(to)}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer text-sm text-[#9ca9c9] hover:bg-white/[0.06] hover:text-white transition",
              location.pathname.startsWith(to) &&
                "text-[#aebdff] bg-[#6c8cff]/10",
            )}
          >
            <Icon size={16} /> {label}
          </div>
        ))}
      </div>
    </aside>
  );
}
