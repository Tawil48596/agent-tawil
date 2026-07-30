import { useNavigate, useLocation } from "react-router-dom";
import { useChatStore } from "@/stores/chatStore";
import { MessageSquare, Wrench, BookOpen, Bot, BarChart3, Settings, Plus, Hash } from "lucide-react";
import { cn, truncate } from "@/lib/utils";

export function Sidebar() {
  const navigate = useNavigate();
  const loc = useLocation();
  const { sessions, activeId, createSession, selectSession } = useChatStore();

  const navItems = [
    { to: "/tools", icon: Wrench, label: "工具市场" },
    { to: "/knowledge", icon: BookOpen, label: "知识库" },
    { to: "/agents", icon: Bot, label: "多智能体" },
    { to: "/analytics", icon: BarChart3, label: "用量" },
    { to: "/settings", icon: Settings, label: "设置" },
  ];

  return (
    <div className="w-64 bg-[#1a1d27] border-r border-[#2a2d3a] flex flex-col shrink-0">
      <div className="p-4 border-b border-[#2a2d3a]">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate("/")}>
          <span className="text-lg">🤖</span>
          <div>
            <h1 className="text-sm font-semibold">AI Agent Platform</h1>
            <p className="text-[10px] text-[#8b8fa3]">v0.1.0</p>
          </div>
        </div>
      </div>
      <button onClick={async () => { const id = await createSession(); navigate(`/chat/${id}`); }}
        className="mx-3 mt-3 py-2.5 bg-[#6c8cff] hover:opacity-90 text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2">
        <Plus size={16} /> 新对话
      </button>
      <div className="flex-1 overflow-y-auto p-2 mt-2">
        {sessions.map((s) => (
          <div key={s.id}
            onClick={() => { selectSession(s.id); navigate(`/chat/${s.id}`); }}
            className={cn("px-3 py-2 rounded-md cursor-pointer text-sm mb-0.5 hover:bg-[#2a2d3a] text-[#8b8fa3] hover:text-[#e1e4ea]",
              activeId === s.id && "bg-[#2a2d3a] text-[#e1e4ea]")}>
            {truncate(s.title || "新对话", 25)}
          </div>
        ))}
      </div>
      <div className="border-t border-[#2a2d3a] p-3">
        {navItems.map(({ to, icon: Icon, label }) => (
          <div key={to} onClick={() => navigate(to)}
            className={cn("flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer text-sm text-[#8b8fa3] hover:bg-[#2a2d3a] hover:text-[#e1e4ea]",
              loc.pathname.startsWith(to) && "text-[#6c8cff] bg-[#1e2030]")}>
            <Icon size={16} /> {label}
          </div>
        ))}
      </div>
    </div>
  );
}
