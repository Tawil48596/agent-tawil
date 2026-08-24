import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { Menu } from "lucide-react";
import { useChatStore } from "@/stores/chatStore";
import { useUIStore } from "@/stores/uiStore";
import { Sidebar } from "@/components/layout/Sidebar";
import { ContextPanel } from "@/components/layout/ContextPanel";
import { ChatView } from "@/pages/ChatView";
import { ToolMarket } from "@/pages/ToolMarket";
import { ToolDetail } from "@/pages/ToolDetail";
import { KnowledgeBase } from "@/pages/KnowledgeBase";
import { MultiAgentView } from "@/pages/MultiAgentView";
import { AnalyticsDashboard } from "@/pages/AnalyticsDashboard";
import { SessionsPage } from "@/pages/SessionsPage";
import { Settings } from "@/pages/Settings";

export default function App() {
  const init = useChatStore((s) => s.init);
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  useEffect(() => { void init(); }, [init]);

  return (
    <div className="app-shell h-[100dvh] flex overflow-hidden text-[#f4f4f5]">
      <button
        type="button"
        aria-label="打开导航"
        aria-expanded={sidebarOpen}
        onClick={toggleSidebar}
        className="fixed left-3 top-3 z-40 grid h-10 w-10 place-items-center rounded-xl border border-white/10 bg-[#1b1b1b]/95 text-[#e4e4e7] shadow-xl backdrop-blur-xl transition hover:bg-[#252525] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60 lg:hidden"
      >
        <Menu size={19} aria-hidden="true" />
      </button>
      <div className={`fixed inset-y-0 left-0 z-50 transition-transform duration-200 lg:static lg:visible lg:pointer-events-auto lg:translate-x-0 ${sidebarOpen ? "visible translate-x-0" : "invisible -translate-x-full pointer-events-none"}`}>
        <Sidebar />
      </div>
      {sidebarOpen && (
        <button
          type="button"
          aria-label="关闭导航"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden"
        />
      )}
      <main className="flex-1 flex flex-col min-w-0 min-h-0">
        <Routes>
          <Route path="/" element={<ChatView />} />
          <Route path="/chat/:sessionId" element={<ChatView />} />
          <Route path="/sessions" element={<SessionsPage />} />
          <Route path="/tools" element={<ToolMarket />} />
          <Route path="/tools/:toolName" element={<ToolDetail />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
          <Route path="/knowledge/:kbId" element={<KnowledgeBase />} />
          <Route path="/agents" element={<MultiAgentView />} />
          <Route path="/agents/:taskId" element={<MultiAgentView />} />
          <Route path="/analytics" element={<AnalyticsDashboard />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/settings/:section" element={<Settings />} />
        </Routes>
      </main>
      <ContextPanel />
    </div>
  );
}
