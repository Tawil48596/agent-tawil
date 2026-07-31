import { useState, useEffect } from "react";
import { Settings as SettingsIcon, User, Cpu, Brain, Key, Save, Eye, EyeOff, Trash2, Plus, Globe, X } from "lucide-react";
import { useChatStore } from "@/stores/chatStore";

interface ProviderConfig {
  name: string;
  apiKey: string;
  baseUrl: string;
}

const DEFAULT_PROVIDERS: ProviderConfig[] = [
  { name: "openai", apiKey: "", baseUrl: "https://api.openai.com/v1" },
  { name: "anthropic", apiKey: "", baseUrl: "https://api.anthropic.com" },
  { name: "deepseek", apiKey: "", baseUrl: "https://api.deepseek.com/v1" },
];

export function Settings() {
  const [tab, setTab] = useState("profile");
  const [providers, setProviders] = useState<ProviderConfig[]>(() => {
    try {
      const saved = localStorage.getItem("ai-agent-providers");
      return saved ? JSON.parse(saved) : DEFAULT_PROVIDERS;
    } catch { return DEFAULT_PROVIDERS; }
  });
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [editValues, setEditValues] = useState<Record<string, { key: string; url: string }>>({});
  const [memories, setMemories] = useState<any[]>([]);
  const [theme, setTheme] = useState(() => localStorage.getItem("ai-agent-theme") || "dark");
  const [notice, setNotice] = useState("");
  const model = useChatStore((s) => s.model);
  const models = useChatStore((s) => s.models);
  const setModel = useChatStore((s) => s.setModel);
  const [newProvider, setNewProvider] = useState({ name: "", baseUrl: "" });
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => {
    fetch("/api/v1/memory").then(r => r.json()).then(d => setMemories(d.entries || [])).catch(() => {});
    // Init edit values from saved
    const ev: Record<string, { key: string; url: string }> = {};
    providers.forEach(p => { ev[p.name] = { key: p.apiKey, url: p.baseUrl }; });
    setEditValues(ev);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("ai-agent-theme", theme);
  }, [theme]);

  const getEditVal = (name: string, field: "key" | "url") => {
    if (editValues[name]?.[field] !== undefined) return editValues[name][field];
    const p = providers.find(x => x.name === name);
    return p ? (field === "key" ? p.apiKey : p.baseUrl) : "";
  };

  const setEditVal = (name: string, field: "key" | "url", value: string) => {
    setEditValues(prev => ({
      ...prev,
      [name]: { ...prev[name], [field]: value },
    }));
  };

  const saveProvider = (name: string) => {
    setProviders(prev => prev.map(p =>
      p.name === name ? { ...p, apiKey: editValues[name]?.key ?? p.apiKey, baseUrl: editValues[name]?.url ?? p.baseUrl } : p
    ));
    // Persist
    const updated = providers.map(p =>
      p.name === name ? { ...p, apiKey: editValues[name]?.key ?? p.apiKey, baseUrl: editValues[name]?.url ?? p.baseUrl } : p
    );
    localStorage.setItem("ai-agent-providers", JSON.stringify(updated));
    setNotice(`${name} 已保存在当前浏览器。服务端调用仍需配置对应环境变量并重启。`);
  };

  const addProvider = () => {
    if (!newProvider.name.trim() || !newProvider.baseUrl.trim()) return;
    const p: ProviderConfig = { name: newProvider.name.trim().toLowerCase(), apiKey: "", baseUrl: newProvider.baseUrl.trim() };
    const updated = [...providers, p];
    setProviders(updated);
    setEditValues(prev => ({ ...prev, [p.name]: { key: "", url: p.baseUrl } }));
    localStorage.setItem("ai-agent-providers", JSON.stringify(updated));
    setNewProvider({ name: "", baseUrl: "" });
    setShowAdd(false);
  };

  const removeProvider = (name: string) => {
    const updated = providers.filter(p => p.name !== name);
    setProviders(updated);
    localStorage.setItem("ai-agent-providers", JSON.stringify(updated));
  };

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-lg font-semibold flex items-center gap-2 mb-6"><SettingsIcon size={20} /> 设置</h2>

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
            <select value={model} onChange={(e) => { setModel(e.target.value); setNotice("默认模型已保存"); }}
              className="w-full bg-[#0f1117] border border-[#2a2d3a] rounded-lg px-4 py-2.5 text-sm text-[#e1e4ea]">
              <option value="">自动路由</option>
              {models.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
            </select>
          </div>
          {notice && <div className="rounded-lg border border-[#4ade80]/30 bg-[#12301d] px-4 py-2 text-xs text-[#86efac]">{notice}</div>}
        </div>
      )}

      {tab === "models" && (
        <div className="max-w-2xl space-y-4">
          <div className="rounded-lg border border-[#fbbf24]/30 bg-[#382b10] px-4 py-3 text-xs text-[#fde68a]">
            浏览器保存不会修改正在运行的服务。要让模型真正可用，请在服务端配置 OPENAI_API_KEY、ANTHROPIC_API_KEY 或 DEEPSEEK_API_KEY 后重启。
          </div>
          {notice && <div className="rounded-lg border border-[#4ade80]/30 bg-[#12301d] px-4 py-2 text-xs text-[#86efac]">{notice}</div>}
          {providers.map((p) => {
            const hasKey = !!(editValues[p.name]?.key ?? p.apiKey);
            const hasUrl = !!(editValues[p.name]?.url ?? p.baseUrl);
            return (
              <div key={p.name} className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold capitalize flex items-center gap-2">
                    <Globe size={16} /> {p.name}
                  </h3>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] px-2 py-0.5 rounded ${hasKey ? "bg-[#1a3a1a] text-[#4ade80]" : "bg-[#3d1515] text-[#f87171]"}`}>
                      {hasKey ? "已配置" : "未配置"}
                    </span>
                    {!DEFAULT_PROVIDERS.find(d => d.name === p.name) && (
                      <button onClick={() => removeProvider(p.name)} className="text-[#8b8fa3] hover:text-[#f87171]"><X size={14} /></button>
                    )}
                  </div>
                </div>

                {/* API URL */}
                <label className="text-xs text-[#8b8fa3] mb-1 block">API URL</label>
                <input
                  type="text"
                  value={getEditVal(p.name, "url")}
                  onChange={(e) => setEditVal(p.name, "url", e.target.value)}
                  placeholder="https://api.openai.com/v1"
                  className="w-full bg-[#0f1117] border border-[#2a2d3a] rounded-lg px-4 py-2.5 text-sm text-[#e1e4ea] outline-none focus:border-[#6c8cff] mb-3"
                />

                {/* API Key */}
                <label className="text-xs text-[#8b8fa3] mb-1 block">API Key</label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <input
                      type={showKeys[p.name] ? "text" : "password"}
                      value={getEditVal(p.name, "key")}
                      onChange={(e) => setEditVal(p.name, "key", e.target.value)}
                      placeholder="sk-..."
                      className="w-full bg-[#0f1117] border border-[#2a2d3a] rounded-lg pl-4 pr-10 py-2.5 text-sm text-[#e1e4ea] outline-none focus:border-[#6c8cff]"
                    />
                    <button onClick={() => setShowKeys(prev => ({ ...prev, [p.name]: !prev[p.name] }))}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-[#8b8fa3]">
                      {showKeys[p.name] ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  <button onClick={() => saveProvider(p.name)}
                    className="bg-[#6c8cff] text-white px-4 py-2 rounded-lg text-sm hover:opacity-90 flex items-center gap-1">
                    <Save size={16} /> 保存
                  </button>
                </div>
              </div>
            );
          })}

          {/* Add custom provider */}
          {showAdd ? (
            <div className="bg-[#1a1d27] border border-[#6c8cff] rounded-xl p-4">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Plus size={16} /> 自定义 Provider</h3>
              <input value={newProvider.name} onChange={(e) => setNewProvider(p => ({ ...p, name: e.target.value }))}
                placeholder="Provider 名称 (如 ollama, groq)" className="w-full bg-[#0f1117] border border-[#2a2d3a] rounded-lg px-4 py-2.5 text-sm mb-2 outline-none focus:border-[#6c8cff]" />
              <input value={newProvider.baseUrl} onChange={(e) => setNewProvider(p => ({ ...p, baseUrl: e.target.value }))}
                placeholder="API URL (如 http://localhost:11434/v1)" className="w-full bg-[#0f1117] border border-[#2a2d3a] rounded-lg px-4 py-2.5 text-sm mb-3 outline-none focus:border-[#6c8cff]" />
              <div className="flex gap-2">
                <button onClick={addProvider} className="bg-[#6c8cff] text-white px-4 py-2 rounded-lg text-sm">添加</button>
                <button onClick={() => setShowAdd(false)} className="bg-[#2a2d3a] text-[#e1e4ea] px-4 py-2 rounded-lg text-sm">取消</button>
              </div>
            </div>
          ) : (
            <button onClick={() => setShowAdd(true)}
              className="w-full border-2 border-dashed border-[#2a2d3a] rounded-xl p-4 text-sm text-[#8b8fa3] hover:border-[#6c8cff] hover:text-[#e1e4ea] flex items-center justify-center gap-2">
              <Plus size={16} /> 添加自定义 Provider
            </button>
          )}
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
          {memories.length === 0 && <p className="text-xs text-[#8b8fa3]">暂无长期记忆</p>}
        </div>
      )}
    </div>
  );
}
