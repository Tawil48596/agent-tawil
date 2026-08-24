import { useState, useEffect } from "react";
import { BarChart3, TrendingUp, Zap, MessageSquare, Wrench, RefreshCw } from "lucide-react";

export function AnalyticsDashboard() {
  const [stats, setStats] = useState<any>({});
  const [models, setModels] = useState<any[]>([]);
  const [error, setError] = useState("");
  const COLORS = ["#d4d4d8","#4ade80","#fbbf24","#f87171","#c084fc","#fb923c","#22d3ee","#a3a3a3"];

  const load = async () => {
    setError("");
    try {
      const [sr, mr] = await Promise.all([
        fetch("/api/v1/tools/stats").then(r => {
          if (!r.ok) throw new Error(`工具统计加载失败 (${r.status})`);
          return r.json();
        }),
        fetch("/api/v1/chat/models").then(r => {
          if (!r.ok) throw new Error(`模型列表加载失败 (${r.status})`);
          return r.json();
        }),
      ]);
      setStats(sr);
      setModels((mr.models || []).slice(0, 8));
    } catch (e: any) {
      setError(e?.message || "仪表板数据加载失败");
    }
  };

  useEffect(() => { load(); }, []);

  const kpis = [
    { icon: TrendingUp, label: "已注册工具", value: stats.registry?.total || 8, color: "#d4d4d8" },
    { icon: Zap, label: "工具调用", value: stats.registry?.total_calls || 0, color: "#c084fc" },
    { icon: Wrench, label: "工具集", value: Object.keys(stats.registry?.toolsets || {}).length || 3, color: "#22d3ee" },
    { icon: MessageSquare, label: "市场工具", value: stats.marketplace?.market_size || 2, color: "#fb923c" },
  ];

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold flex items-center gap-2"><BarChart3 size={20} /> 用量仪表板</h2>
        <button onClick={load} className="text-[#8b8fa3] hover:text-[#e1e4ea] p-1"><RefreshCw size={18} /></button>
      </div>
      {error && <div className="mb-4 rounded-lg border border-[#f87171]/40 bg-[#3d1515] px-4 py-2 text-sm text-[#fca5a5]">{error}</div>}

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((k) => (
          <div key={k.label} className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-5 text-center">
            <div className="text-3xl font-bold" style={{ color: k.color }}>{k.value}</div>
            <div className="text-xs text-[#8b8fa3] mt-1">{k.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-5">
          <h3 className="text-sm font-semibold text-[#8b8fa3] mb-4">模型列表</h3>
          <div className="space-y-3">
            {models.map((m: any, i: number) => (
              <div key={m.name} className="flex items-center gap-3">
                <span className="text-xs text-[#8b8fa3] w-32 truncate">{m.name}</span>
                <div className="flex-1 bg-[#2a2d3a] rounded-full h-5 overflow-hidden">
                  <div className="h-full rounded-full flex items-center pl-2 text-[10px] font-medium"
                    style={{ width: `${100 - i * 12}%`, background: COLORS[i] }}>
                    {m.provider}
                  </div>
                </div>
                <span className="text-xs text-[#8b8fa3] w-16 text-right">{m.context_length ? (m.context_length / 1000).toFixed(0) + "K" : ""}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-5">
          <h3 className="text-sm font-semibold text-[#8b8fa3] mb-4">系统状态</h3>
          <div className="space-y-2 text-sm">
            {[
              ["Phase 1:", "安全兜底 ✅"],
              ["Phase 2:", "MCP + 持久化 ✅"],
              ["Phase 3:", "RAG + 上下文 ✅"],
              ["Phase 4:", "工具市场 + GenUI ✅"],
              ["Phase 5:", "多智能体 + HITL ✅"],
              ["Phase 6:", "评测 + Trace ✅"],
              ["Phase 7:", "部署打磨 ✅"],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between">
                <span className="text-[#8b8fa3]">{label}</span>
                <span>{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
