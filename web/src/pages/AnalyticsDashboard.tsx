import { BarChart3, TrendingUp, DollarSign, Zap } from "lucide-react";

export function AnalyticsDashboard() {
  const kpis = [
    { icon: TrendingUp, label: "今日 Token", value: "0", color: "#6c8cff" },
    { icon: DollarSign, label: "今日成本", value: "$0", color: "#4ade80" },
    { icon: Zap, label: "请求数", value: "0", color: "#c084fc" },
    { icon: BarChart3, label: "活跃会话", value: "0", color: "#fb923c" },
  ];

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-lg font-semibold flex items-center gap-2 mb-6"><BarChart3 size={20} /> 用量仪表板</h2>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {kpis.map((k) => (
          <div key={k.label} className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-5 text-center">
            <div className="text-3xl font-bold" style={{ color: k.color }}>{k.value}</div>
            <div className="text-xs text-[#8b8fa3] mt-1">{k.label}</div>
          </div>
        ))}
      </div>
      <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-6">
        <h3 className="text-sm font-semibold text-[#8b8fa3] mb-4">模型用量</h3>
        <p className="text-xs text-[#8b8fa3]">发送对话后将自动记录用量数据</p>
      </div>
    </div>
  );
}
