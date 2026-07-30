import { useEffect } from "react";
import { Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { useChatStore } from "@/stores/chatStore";
import { Sidebar } from "@/components/layout/Sidebar";
import { ContextPanel } from "@/components/layout/ContextPanel";
import { ChatView } from "@/pages/ChatView";
import { ToolMarket } from "@/pages/ToolMarket";
import { KnowledgeBase } from "@/pages/KnowledgeBase";
import { MultiAgentView } from "@/pages/MultiAgentView";
import { AnalyticsDashboard } from "@/pages/AnalyticsDashboard";
import { Settings } from "@/pages/Settings";

export default function App() {
  const init = useChatStore((s) => s.init);
  useEffect(() => { init(); }, []);

  return (
    <div className="h-screen flex bg-[#0f1117] text-[#e1e4ea] overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Routes>
          <Route path="/" element={<ChatView />} />
          <Route path="/chat/:sessionId" element={<ChatView />} />
          <Route path="/tools" element={<ToolMarket />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
          <Route path="/agents" element={<MultiAgentView />} />
          <Route path="/analytics" element={<AnalyticsDashboard />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
      <ContextPanel />
    </div>
  );
}
