import { useState, useEffect } from "react";
import { Settings as SettingsIcon, User, Cpu, Brain, Save, Eye, EyeOff, Trash2, Globe } from "lucide-react";
import { useChatStore } from "@/stores/chatStore";

interface ProviderConfig {
  name: string;
  apiKey: string;
  baseUrl: string;
  configured: boolean;
}

const DEFAULT_PROVIDERS: ProviderConfig[] = [
  { name: "openai", apiKey: "", baseUrl: "https://api.openai.com/v1", configured: false },
  { name: "anthropic", apiKey: "", baseUrl: "https://api.anthropic.com", configured: false },
  { name: "deepseek", apiKey: "", baseUrl: "https://api.deepseek.com/v1", configured: false },
];

export function Settings() {
  const [tab, setTab] = useState("profile");
  const [providers, setProviders] = useState<ProviderConfig[]>(DEFAULT_PROVIDERS);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [editValues, setEditValues] = useState<Record<string, { key: string; url: string }>>({});
  const [memories, setMemories] = useState<any[]>([]);
  const [theme, setTheme] = useState(() => localStorage.getItem("ai-agent-theme") || "dark");
  const [notice, setNotice] = useState("");
  const model = useChatStore((s) => s.model);
  const models = useChatStore((s) => s.models);
  const setModel = useChatStore((s) => s.setModel);
  const refreshChat = useChatStore((s) => s.init);

  useEffect(() => {
    fetch("/api/v1/memory").then(r => r.json()).then(d => setMemories(d.entries || [])).catch(() => {});
    fetch("/api/v1/runtime/providers")
      .then(async r => {
        if (!r.ok) throw new Error(await r.text());
        return r.json();
      })
      .then(data => {
        const statuses = new Map((data.providers || []).map((p: any) => [p.name, p]));
        setProviders(DEFAULT_PROVIDERS.map(provider => {
          const status: any = statuses.get(provider.name);
          return {
            ...provider,
            baseUrl: status?.base_url || provider.baseUrl,
            configured: !!status?.configured,
          };
        }));
      })
      .catch((e) => setNotice(`无法读取服务端配置：${e.message}`));
  }, []);

  useEffect(() => {
    const ev: Record<string, { key: string; url: string }> = {};
    providers.forEach(p => { ev[p.name] = { key: "", url: p.baseUrl }; });
    setEditValues(ev);
  }, [providers]);

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

  const saveProvider = async (name: string) => {
    const apiKey = editValues[name]?.key?.trim() || "";
    const baseUrl = editValues[name]?.url?.trim() || "";
    if (!apiKey) {
      setNotice(`请输入 ${name} API Key`);
      return;
    }
    setNotice("正在应用配置…");
    try {
      const response = await fetch(`/api/v1/runtime/providers/${name}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey, base_url: baseUrl }),
      });
      if (!response.ok) throw new Error(await response.text());
      setProviders(prev => prev.map(p =>
        p.name === name ? { ...p, configured: true, baseUrl } : p
      ));
      setEditValues(prev => ({ ...prev, [name]: { key: "", url: baseUrl } }));
      await refreshChat();
      setNotice(`${name} 已在当前服务中启用，无需重启。密钥不会返回浏览器或写入仓库。`);
    } catch (e: any) {
      setNotice(`配置失败：${e?.message || e}`);
    }
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
            在这里保存后会立即更新本机服务，无需重启。密钥仅保存在当前服务进程内存中，服务重启后需要重新填写。
          </div>
          {notice && <div className="rounded-lg border border-[#4ade80]/30 bg-[#12301d] px-4 py-2 text-xs text-[#86efac]">{notice}</div>}
          {providers.map((p) => {
            const hasKey = p.configured;
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

        </div>
      )}

      {tab === "memory" && (
        <div className="max-w-2xl space-y-3">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h3 className="text-sm font-semibold">记忆</h3>
              <p className="text-xs text-[#8b8fa3] mt-1">
                这里只保存 Agent 可跨对话使用的长期信息；普通聊天记录在“全部对话”中管理。
              </p>
            </div>
            {memories.length > 0 && (
              <button
                onClick={async () => {
                  if (!window.confirm("清空全部长期记忆？此操作无法撤销。")) return;
                  await fetch("/api/v1/memory", { method: "DELETE" });
                  setMemories([]);
                }}
                className="text-xs text-[#f87171] border border-[#f87171]/30 hover:bg-[#f87171]/10 px-3 py-2 rounded-lg shrink-0"
              >
                清空记忆
              </button>
            )}
          </div>
          <p className="text-xs text-[#8b8fa3]">{memories.length} 条长期记忆</p>
          {memories.map((m: any, i: number) => (
            <div key={m.id || i} className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm">{m.content}</p>
                <p className="text-xs text-[#8b8fa3] mt-2">
                  {m.type} · 重要性 {Number(m.importance ?? 0.5).toFixed(1)}
                  {m.source ? ` · ${m.source}` : ""}
                  {m.project_id && m.project_id !== "default" ? ` · 项目 ${m.project_id}` : ""}
                </p>
              </div>
              <button onClick={async () => {
                await fetch(`/api/v1/memory/${m.id}`, { method: "DELETE" });
                setMemories(prev => prev.filter(x => x.id !== m.id));
              }} aria-label="删除记忆" className="text-[#8b8fa3] hover:text-[#f87171] p-2 shrink-0"><Trash2 size={14} /></button>
            </div>
          ))}
          {memories.length === 0 && (
            <div className="border border-dashed border-[#2a2d3a] rounded-xl py-10 text-center text-xs text-[#8b8fa3]">
              暂无长期记忆
            </div>
          )}
        </div>
      )}
    </div>
  );
}
