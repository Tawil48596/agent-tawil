import { useEffect, useState } from "react";
import { Bot, Play, Square } from "lucide-react";

export function MultiAgentView() {
  const [plans, setPlans] = useState<any[]>([]);

  useEffect(() => {
    fetch("/api/v1/agents/tasks").then((r) => r.json()).then((d) => setPlans(d.plans || [])).catch(() => {});
  }, []);

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-lg font-semibold flex items-center gap-2 mb-6"><Bot size={20} /> 多智能体任务</h2>
      {plans.length === 0 && <p className="text-sm text-[#8b8fa3]">暂无任务 — 在对话中使用多智能体功能创建</p>}
      <div className="space-y-3">
        {plans.map((p) => {
          const pct = Math.round((p.progress || 0) * 100);
          const color = p.status === "completed" ? "#4ade80" : p.status === "running" ? "#6c8cff" : "#8b8fa3";
          return (
            <div key={p.id} className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-sm">{p.title}</h3>
                  <p className="text-xs text-[#8b8fa3]">{p.mode} · {p.completed || 0}/{p.tasks} 完成 · {p.status}</p>
                </div>
                <span className="text-2xl font-bold" style={{ color }}>{pct}%</span>
              </div>
              <div className="mt-3 bg-[#2a2d3a] rounded-full h-2 overflow-hidden">
                <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
