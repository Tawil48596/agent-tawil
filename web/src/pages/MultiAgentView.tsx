import { useEffect, useState } from "react";
import { Bot, Play, Square, RefreshCw } from "lucide-react";

export function MultiAgentView() {
  const [plans, setPlans] = useState<any[]>([]);
  const [hitl, setHitl] = useState<any[]>([]);
  const [activePlan, setActivePlan] = useState<any>(null);

  const loadAll = async () => {
    try {
      const [tr, hr] = await Promise.all([
        fetch("/api/v1/agents/tasks").then(r => r.json()),
        fetch("/api/v1/agents/hitl/pending").then(r => r.json()),
      ]);
      setPlans(tr.plans || []);
      setHitl(hr.requests || []);
    } catch {}
  };

  useEffect(() => { loadAll(); const i = setInterval(loadAll, 5000); return () => clearInterval(i); }, []);

  const loadPlanDetail = async (id: string) => {
    try {
      const r = await fetch(`/api/v1/agents/tasks/${id}`);
      setActivePlan(await r.json());
    } catch {}
  };

  const hitlAction = async (reqId: string, action: string) => {
    await fetch(`/api/v1/agents/hitl/${reqId}/action`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action }),
    });
    loadAll();
  };

  const executePlan = async (id: string) => {
    await fetch(`/api/v1/agents/tasks/${id}/execute`, { method: "POST" });
    loadAll();
  };

  const cancelPlan = async (id: string) => {
    await fetch(`/api/v1/agents/tasks/${id}/cancel`, { method: "POST" });
    loadAll();
  };

  const retryPlan = async (id: string) => {
    await fetch(`/api/v1/agents/tasks/${id}/retry`, { method: "POST" });
    loadAll();
  };

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold flex items-center gap-2"><Bot size={20} /> 多智能体任务</h2>
        <button onClick={loadAll} className="text-[#8b8fa3] hover:text-[#e1e4ea] p-1"><RefreshCw size={18} /></button>
      </div>

      {/* HITL alerts */}
      {hitl.length > 0 && (
        <div className="mb-6 space-y-2">
          <h3 className="text-sm font-semibold text-[#fbbf24]">⏸️ 待审批 ({hitl.length})</h3>
          {hitl.map((r: any) => (
            <div key={r.id} className="bg-[#1a1d27] border border-[#fbbf24] rounded-xl p-4 flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold">{r.title}</div>
                <div className="text-xs text-[#8b8fa3]">{r.description}</div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => hitlAction(r.id, "approve")}
                  className="bg-[#4ade80] text-black px-4 py-2 rounded-lg text-sm font-medium">批准</button>
                <button onClick={() => hitlAction(r.id, "deny")}
                  className="bg-[#f87171] text-white px-4 py-2 rounded-lg text-sm font-medium">拒绝</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Task board */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {plans.map((p) => {
          const pct = Math.round((p.progress || 0) * 100);
          const color = p.status === "completed" ? "#4ade80" : p.status === "running" ? "#d4d4d8" : "#fbbf24";
          return (
            <div key={p.id}
              className="rounded-xl border border-[#303030] bg-[#171717] p-4 transition-colors hover:border-white/25 hover:bg-[#1b1b1b]">
              <button type="button" onClick={() => void loadPlanDetail(p.id)} className="w-full text-left">
                <span className="flex items-start justify-between">
                  <span>
                    <span className="block text-sm font-semibold">{p.title}</span>
                    <span className="mt-1 block text-xs text-[#8b8fa3]">{p.mode} · {p.completed}/{p.tasks} 完成</span>
                  </span>
                  <span className="text-2xl font-bold" style={{ color }}>{pct}%</span>
                </span>
                <span className="mt-3 block h-2 overflow-hidden rounded-full bg-[#2a2d3a]">
                  <span className="block h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
                </span>
              </button>
              <div className="flex gap-2 mt-3">
                {p.status !== "running" && p.status !== "completed" && (
                  <button type="button" onClick={() => void executePlan(p.id)}
                    className="flex items-center gap-1 rounded bg-[#f4f4f5] px-3 py-1 text-xs text-[#171717] hover:bg-white"><Play size={12} /> 执行</button>
                )}
                {p.status === "running" && (
                  <button type="button" onClick={() => void cancelPlan(p.id)}
                    className="text-xs bg-[#f87171] text-white px-3 py-1 rounded flex items-center gap-1"><Square size={12} /> 取消</button>
                )}
                {(p.status === "failed" || p.status === "cancelled") && (
                  <button type="button" onClick={() => void retryPlan(p.id)}
                    className="text-xs bg-[#fbbf24] text-black px-3 py-1 rounded flex items-center gap-1"><RefreshCw size={12} /> 重试</button>
                )}
              </div>
            </div>
          );
        })}
        {plans.length === 0 && <div className="col-span-2 text-center text-[#8b8fa3] py-12">暂无任务</div>}
      </div>

      {/* Active plan detail */}
      {activePlan && (
        <div className="mt-6 bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
          <h3 className="text-sm font-semibold mb-3">任务详情: {activePlan.title}</h3>
          <div className="space-y-2">
            {(activePlan.tasks || []).map((t: any) => (
              <div key={t.id} className="flex items-center gap-3 text-sm bg-[#0f1117] rounded-lg p-3">
                <span className={`w-2 h-2 rounded-full ${
                  t.status === "completed" ? "bg-[#4ade80]" : t.status === "running" ? "bg-[#d4d4d8] animate-pulse" :
                  t.status === "failed" ? "bg-[#f87171]" : "bg-[#8b8fa3]"
                }`} />
                <span className="flex-1">{t.goal?.slice(0, 80)}</span>
                <span className="text-xs text-[#8b8fa3]">{t.status} · {(t.progress || 0) * 100}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
