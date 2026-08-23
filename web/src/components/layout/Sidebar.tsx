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
  X,
} from "lucide-react";

import { APP_VERSION } from "@/lib/constants";
import { cn, truncate } from "@/lib/utils";
import { useChatStore } from "@/stores/chatStore";
import { useUIStore } from "@/stores/uiStore";

export function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const {
    sessions,
    activeId,
    createSession,
    selectSession,
    deleteSession,
  } = useChatStore();

  const goTo = (path: string) => {
    navigate(path);
    setSidebarOpen(false);
  };

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
    <aside aria-label="主导航" className="h-full w-[17.5rem] bg-[#101729]/95 border-r border-white/10 flex flex-col shrink-0 backdrop-blur-xl">
      <div className="p-5 border-b border-white/10">
        <div className="flex items-center gap-2">
          <button type="button" className="flex min-w-0 flex-1 items-center gap-2 text-left" onClick={() => goTo("/")}>
            <span className="h-9 w-9 rounded-xl bg-gradient-to-br from-[#8aa7ff] to-[#7b5cff] flex items-center justify-center shadow-lg shadow-[#6c8cff]/20">
              <Sparkles size={17} aria-hidden="true" />
            </span>
            <span className="leading-tight">
              <span className="block text-sm font-semibold tracking-tight">Agent Studio</span>
              <span className="mt-0.5 block text-[10px] text-[#9ca9c9]">
                AI workspace · v{APP_VERSION}
              </span>
            </span>
          </button>
          <button
            type="button"
            aria-label="关闭导航"
            onClick={() => setSidebarOpen(false)}
            className="ml-auto grid h-9 w-9 place-items-center rounded-lg text-[#8f9dbc] hover:bg-white/5 hover:text-white lg:hidden"
          >
            <X size={17} aria-hidden="true" />
          </button>
        </div>
      </div>

      <button
        onClick={async () => {
          const id = await createSession();
          goTo(`/chat/${id}`);
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
            className={cn(
              "group mb-1 flex items-center rounded-lg text-sm text-[#9ca9c9] transition hover:bg-white/[0.06] hover:text-white",
              activeId === session.id &&
                "bg-[#6c8cff]/15 text-white ring-1 ring-[#8aa7ff]/20",
            )}
          >
            <button
              type="button"
              onClick={() => {
                selectSession(session.id);
                goTo(`/chat/${session.id}`);
              }}
              className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#8aa7ff]/70"
            >
              <MessageSquare size={14} className="shrink-0 opacity-70" />
              <span className="min-w-0 flex-1 truncate">
                {truncate(session.title || "新对话", 25)}
              </span>
            </button>
            <button
              type="button"
              aria-label={`删除对话 ${session.title || "新对话"}`}
              onClick={(event) => removeSession(event, session.id)}
              className="mr-2 p-1 text-[#7785a9] opacity-70 transition hover:text-[#f87171] focus:opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
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
          <button
            type="button"
            key={to}
            onClick={() => goTo(to)}
            className={cn(
              "flex w-full items-center gap-3 px-3 py-2.5 rounded-lg text-left text-sm text-[#9ca9c9] hover:bg-white/[0.06] hover:text-white transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8aa7ff]/70",
              location.pathname.startsWith(to) &&
                "text-[#aebdff] bg-[#6c8cff]/10",
            )}
          >
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>
    </aside>
  );
}
