import { useState, useEffect } from "react";
import { BookOpen, Upload, Plus, Trash2, Search } from "lucide-react";

export function KnowledgeBase() {
  const [kbs, setKbs] = useState<any[]>([]);
  const [activeKb, setActiveKb] = useState<string>("");
  const [docContent, setDocContent] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [status, setStatus] = useState("");

  useEffect(() => { loadKBs(); }, []);

  const loadKBs = async () => {
    try {
      const r = await fetch("/api/v1/rag/knowledge-bases");
      setKbs((await r.json()).knowledge_bases || []);
    } catch {}
  };

  const createKB = async () => {
    const name = prompt("知识库名称:");
    if (!name) return;
    await fetch("/api/v1/rag/knowledge-bases", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
    loadKBs();
  };

  const deleteKB = async (id: string) => {
    await fetch(`/api/v1/rag/knowledge-bases/${id}`, { method: "DELETE" });
    if (activeKb === id) setActiveKb("");
    loadKBs();
  };

  const indexDoc = async () => {
    if (!activeKb || !docContent.trim()) return;
    setStatus("索引中...");
    const r = await fetch(`/api/v1/rag/knowledge-bases/${activeKb}/documents`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: docContent, chunk_strategy: "fixed" }),
    });
    const d = await r.json();
    setStatus(`已索引 ${d.chunks_indexed || 0} 个 chunks`);
    setDocContent("");
    loadKBs();
  };

  const searchKB = async () => {
    if (!activeKb || !query.trim()) return;
    setStatus("检索中...");
    const r = await fetch("/api/v1/rag/query", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, knowledge_bases: [activeKb], top_k: 5 }),
    });
    const d = await r.json();
    setResults(d.results || []);
    setStatus(d.blocked ? "检索被守卫拦截（低置信度）" : `${d.results?.length || 0} 条结果`);
  };

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold flex items-center gap-2"><BookOpen size={20} /> 知识库</h2>
        <button onClick={createKB} className="bg-[#6c8cff] text-white px-4 py-2 rounded-lg text-sm flex items-center gap-1">
          <Plus size={16} /> 新建
        </button>
      </div>

      <div className="flex gap-4 h-[calc(100%-60px)]">
        {/* KB list */}
        <div className="w-64 shrink-0 space-y-2">
          {kbs.map((kb: any) => (
            <div key={kb.id} onClick={() => setActiveKb(kb.id)}
              className={`bg-[#1a1d27] border rounded-lg p-3 cursor-pointer flex justify-between items-center ${
                activeKb === kb.id ? "border-[#6c8cff]" : "border-[#2a2d3a]"
              }`}>
              <div><div className="text-sm font-medium">{kb.name}</div>
                <div className="text-xs text-[#8b8fa3]">{kb.description || "无描述"}</div></div>
              <button onClick={(e) => { e.stopPropagation(); deleteKB(kb.id); }}
                className="text-[#8b8fa3] hover:text-[#f87171]"><Trash2 size={14} /></button>
            </div>
          ))}
        </div>

        {/* Main area */}
        <div className="flex-1 space-y-4">
          {activeKb ? (
            <>
              <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
                <h3 className="text-sm font-medium mb-2">添加文档</h3>
                <textarea value={docContent} onChange={(e) => setDocContent(e.target.value)}
                  rows={6} placeholder="粘贴文档内容..."
                  className="w-full bg-[#0f1117] border border-[#2a2d3a] rounded-lg p-3 text-sm resize-none outline-none focus:border-[#6c8cff] text-[#e1e4ea]" />
                <button onClick={indexDoc}
                  className="mt-2 bg-[#6c8cff] text-white px-4 py-2 rounded-lg text-sm flex items-center gap-1">
                  <Upload size={16} /> 索引文档
                </button>
              </div>

              <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
                <h3 className="text-sm font-medium mb-2">检索测试</h3>
                <div className="flex gap-2">
                  <input value={query} onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && searchKB()}
                    placeholder="输入查询..." className="flex-1 bg-[#0f1117] border border-[#2a2d3a] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6c8cff]" />
                  <button onClick={searchKB} className="bg-[#6c8cff] text-white px-4 py-2 rounded-lg text-sm"><Search size={16} /></button>
                </div>
                {status && <p className="text-xs text-[#8b8fa3] mt-2">{status}</p>}
                {results.map((r: any, i: number) => (
                  <div key={i} className="mt-2 bg-[#0f1117] border border-[#2a2d3a] rounded-lg p-3">
                    <p className="text-xs text-[#8b8fa3]">相关度: {(r.score || 0).toFixed(2)} · {r.source}</p>
                    <p className="text-sm mt-1">{r.content?.slice(0, 300)}</p>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-center text-[#8b8fa3] mt-24">选择一个知识库或创建新的</div>
          )}
        </div>
      </div>
    </div>
  );
}
