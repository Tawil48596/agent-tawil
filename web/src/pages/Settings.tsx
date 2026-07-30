import { useState, useEffect } from "react";
import { Settings as SettingsIcon, User, Cpu, Brain, Key, Save, Eye, EyeOff, Trash2 } from "lucide-react";

export function Settings() {
  const [tab, setTab] = useState("profile");
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [memories, setMemories] = useState<any[]>([]);
  const [theme, setTheme] = useState("dark");

  useEffect(() => {
    fetch("/api/v1/memory").then(r => r.json()).then(d => setMemories(d.entries || [])).catch(() => {});
  }, []);

  const providers = ["openai", "anthropic", "deepseek"];
  const handleSaveKey = (p: string) => {
    setApiKeys(prev => ({ ...prev, [p]: keyInputs[p] || "" }));
  };

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-lg font-semibold flex items-center gap-2 mb-6"><SettingsIcon size={20} /> 设置</h2>

      {/* Tab nav */}
      <div className="flex gap-2 mb-6">
        {[
          { id: "profile", icon: User, label: "用户偏好" },
          { id: "models", icon: Cpu, label: "模型配置" },
          { id: "memory", icon: Brain, label: "记忆管理" },
        ].map(({ id, icon: Icon, label }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`px-4 py-2 rounded-lg text-sm flex items-center gap-2 ${
              tab === id ? "bg-[#6c8cff] text-white" : "bg-[#1a1d27] text-[#8b8fa3] border border-[#2a2d3a]"
            }`}>{<Icon size={16} />} {label}</button>
        ))}
      </div>

      {tab === "profile" && (
        <div className="max-w-lg space-y-4">
          <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
            <label className="text-sm font-medium block mb-2">界面主题</label>
            <select value={theme} onChange={(e) => setTheme(e.target.value)}
              className="w-full bg-[#0f1117] border border-[#2a2d3a] rounded-lg px-4 py-2.5 text-sm text-[#e1e4ea]">
              <option value="dark">暗色</option>
              <option value="light">亮色</option>
            </select>
          </div>
          <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
            <label className="text-sm font-medium block mb-2">默认模型</label>
            <select className="w-full bg-[#0f1117] border border-[#2a2d3a] rounded-lg px-4 py-2.5 text-sm text-[#e1e4ea]">
              <option>自动路由</option>
              <option>gpt-4o</option>
              <option>claude-sonnet-4</option>
              <option>deepseek-v4-pro</option>
            </select>
          </div>
        </div>
      )}

      {tab === "models" && (
        <div className="max-w-lg space-y-4">
          {providers.map((p) => (
            <div key={p} className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold capitalize flex items-center gap-2"><Key size={16} /> {p}</h3>
                <span className={`text-[10px] px-2 py-0.5 rounded ${apiKeys[p] ? "bg-[#1a3a1a] text-[#4ade80]" : "bg-[#3d1515] text-[#f87171]"}`}>
                  {apiKeys[p] ? "已配置" : "未配置"}
                </span>
              </div>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type={showKeys[p] ? "text" : "password"}
                    value={keyInputs[p] || apiKeys[p] || ""}
                    onChange={(e) => setKeyInputs(prev => ({ ...prev, [p]: e.target.value }))}
                    placeholder={`输入 ${p.toUpperCase()}_API_KEY`}
                    className="w-full bg-[#0f1117] border border-[#2a2d3a] rounded-lg pl-4 pr-10 py-2.5 text-sm text-[#e1e4ea] outline-none focus:border-[#6c8cff]"
                  />
                  <button onClick={() => setShowKeys(prev => ({ ...prev, [p]: !prev[p] }))}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-[#8b8fa3]">{showKeys[p] ? <EyeOff size={16} /> : <Eye size={16} />}</button>
                </div>
                <button onClick={() => handleSaveKey(p)}
                  className="bg-[#6c8cff] text-white px-4 py-2 rounded-lg text-sm hover:opacity-90"><Save size={16} /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "memory" && (
        <div className="max-w-lg space-y-2">
          <p className="text-xs text-[#8b8fa3] mb-3">{memories.length} 条长期记忆</p>
          {memories.map((m: any, i: number) => (
            <div key={m.id || i} className="bg-[#1a1d27] border border-[#2a2d3a] rounded-lg p-3 flex items-start justify-between gap-3">
              <div>
                <p className="text-sm">{m.content}</p>
                <p className="text-xs text-[#8b8fa3] mt-1">{m.type} · 重要性: {m.importance?.toFixed(1)}</p>
              </div>
              <button onClick={async () => {
                await fetch(`/api/v1/memory/${m.id}`, { method: "DELETE" });
                setMemories(prev => prev.filter(x => x.id !== m.id));
              }} className="text-[#8b8fa3] hover:text-[#f87171] p-1 shrink-0"><Trash2 size={14} /></button>
            </div>
          ))}
          {memories.length === 0 && <p className="text-xs text-[#8b8fa3]">暂无长期记忆。完成对话后将自动提取。</p>}
        </div>
      )}
    </div>
  );
}
