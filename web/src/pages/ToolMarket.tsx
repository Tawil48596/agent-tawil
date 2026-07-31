import { useChatStore } from "@/stores/chatStore";
import { Wrench, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export function ToolMarket() {
  const tools = useChatStore((s) => s.tools);
  const [q, setQ] = useState("");
  const navigate = useNavigate();

  const filtered = tools.filter((t) => t.name.includes(q.toLowerCase()) || t.description?.includes(q));

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="flex items-center gap-4 mb-6">
        <h2 className="text-lg font-semibold flex items-center gap-2"><Wrench size={20} /> 工具市场</h2>
        <div className="flex-1 max-w-md relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8b8fa3]" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索工具..."
            className="w-full bg-[#1a1d27] border border-[#2a2d3a] rounded-lg pl-10 pr-4 py-2 text-sm outline-none focus:border-[#6c8cff]" />
        </div>
        <span className="text-xs text-[#8b8fa3]">{filtered.length} 个工具</span>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((t) => (
          <button key={t.name} type="button" onClick={() => navigate(`/tools/${encodeURIComponent(t.name)}`)}
            className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4 hover:border-[#6c8cff] transition-colors text-left focus:outline-none focus:ring-2 focus:ring-[#6c8cff]/50">
            <h3 className="font-semibold text-sm">{t.name}</h3>
            <p className="text-xs text-[#8b8fa3] mt-1">{t.description}</p>
            <div className="flex gap-1 mt-2 flex-wrap">
              {t.tags?.map((tag) => <span key={tag} className="text-[10px] bg-[#2a2d3a] px-2 py-0.5 rounded">{tag}</span>)}
              {t.is_dangerous && <span className="text-[10px] bg-[#3d1515] text-[#f87171] px-2 py-0.5 rounded">危险</span>}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
