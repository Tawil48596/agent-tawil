import { useState, useEffect, useRef, DragEvent } from "react";
import { BookOpen, Upload, Plus, Trash2, Search, FileText, X } from "lucide-react";

export function KnowledgeBase() {
  const [kbs, setKbs] = useState<any[]>([]);
  const [activeKb, setActiveKb] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [status, setStatus] = useState("");
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [uploads, setUploads] = useState<{ id: string; name: string; chunks: number; size: string; strategy?: string }[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { loadKBs(); }, []);

  const loadKBs = async () => {
    try { setKbs((await (await fetch("/api/v1/rag/knowledge-bases")).json()).knowledge_bases || []); } catch {}
  };

  const loadDocuments = async (kbId: string) => {
    try {
      const data = await (await fetch(`/api/v1/rag/knowledge-bases/${kbId}/documents`)).json();
      setUploads((data.documents || []).map((document: any) => ({
        id: document.id,
        name: document.name || document.source,
        chunks: document.chunk_count || 0,
        size: formatSize(document.size_bytes || 0),
        strategy: document.chunk_strategy,
      })));
    } catch {
      setUploads([]);
    }
  };

  const createKB = async () => {
    const name = prompt("知识库名称:");
    if (!name) return;
    await fetch("/api/v1/rag/knowledge-bases", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
    loadKBs();
  };

  const deleteKB = async (id: string) => {
    await fetch(`/api/v1/rag/knowledge-bases/${id}`, { method: "DELETE" });
    if (activeKb === id) { setActiveKb(""); setUploads([]); }
    loadKBs();
  };

  const uploadFile = async (file: File) => {
    if (!activeKb) return;
    setUploading(true); setStatus(`上传中: ${file.name}`);
    try {
      const form = new FormData(); form.append("file", file);
      const r = await fetch(`/api/v1/rag/knowledge-bases/${activeKb}/upload`, { method: "POST", body: form });
      const d = await r.json();
      await loadDocuments(activeKb);
      setStatus(`已索引: ${file.name} (${d.chunks_indexed || 0} chunks)`);
      loadKBs();
    } catch (e: any) { setStatus(`上传失败: ${e.message}`); }
    setUploading(false);
  };

  const deleteDocument = async (documentId: string) => {
    if (!activeKb) return;
    await fetch(`/api/v1/rag/knowledge-bases/${activeKb}/documents/${documentId}`, { method: "DELETE" });
    await loadDocuments(activeKb);
    setResults([]);
    setStatus("文档及其检索索引已删除");
    loadKBs();
  };

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault(); setDragOver(false);
    for (const file of Array.from(e.dataTransfer.files)) await uploadFile(file);
  };

  const searchKB = async () => {
    if (!activeKb || !query.trim()) return;
    setStatus("检索中...");
    const r = await fetch("/api/v1/rag/query", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, knowledge_bases: [activeKb], top_k: 5 }) });
    const d = await r.json();
    setResults(d.results || []);
    setStatus(d.blocked ? "检索被守卫拦截" : `${d.results?.length || 0} 条结果`);
  };

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold flex items-center gap-2"><BookOpen size={20} /> 知识库</h2>
        <button onClick={createKB} className="bg-[#6c8cff] text-white px-4 py-2 rounded-lg text-sm flex items-center gap-1"><Plus size={16} /> 新建</button>
      </div>

      <div className="flex gap-4 h-[calc(100%-60px)]">
        <div className="w-64 shrink-0 space-y-2">
          {kbs.map((kb: any) => (
            <div key={kb.id} onClick={() => { setActiveKb(kb.id); loadDocuments(kb.id); setResults([]); }}
              className={`bg-[#1a1d27] border rounded-lg p-3 cursor-pointer flex justify-between items-center ${activeKb === kb.id ? "border-[#6c8cff]" : "border-[#2a2d3a]"}`}>
              <div><div className="text-sm font-medium">{kb.name}</div><div className="text-xs text-[#8b8fa3]">{kb.description || "无描述"}</div></div>
              <button onClick={(e) => { e.stopPropagation(); deleteKB(kb.id); }} className="text-[#8b8fa3] hover:text-[#f87171]"><Trash2 size={14} /></button>
            </div>
          ))}
        </div>

        <div className="flex-1 space-y-4">
          {activeKb ? (
            <>
              {/* Upload area */}
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
                  dragOver ? "border-[#6c8cff] bg-[#1e2030]" : "border-[#2a2d3a] hover:border-[#8b8fa3]"
                }`}
                onClick={() => fileRef.current?.click()}
              >
                <input ref={fileRef} type="file" multiple className="hidden"
                  accept=".pdf,.md,.txt,.py,.js,.ts,.go,.rs,.java,.json,.yaml,.toml,.html,.css"
                  onChange={(e) => { for (const f of Array.from(e.target.files || [])) uploadFile(f); e.target.value = ""; }}
                />
                <Upload size={36} className="mx-auto mb-3 text-[#8b8fa3]" />
                <p className="text-sm">{uploading ? "上传中..." : "拖拽文件到此处 或 点击选择"}</p>
                <p className="text-xs text-[#8b8fa3] mt-1">支持 PDF · Markdown · TXT · Python · JS/TS · Go · 更多</p>
              </div>

              {/* Upload history */}
              {uploads.length > 0 && (
                <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
                  <h3 className="text-sm font-medium mb-2">已上传文件</h3>
                  {uploads.map((u, i) => (
                    <div key={u.id || i} className="flex items-center justify-between text-sm py-1">
                      <span className="flex items-center gap-2"><FileText size={14} className="text-[#8b8fa3]" /> {u.name}</span>
                      <span className="flex items-center gap-2 text-xs text-[#8b8fa3]">
                        {u.size} · {u.chunks} chunks
                        <button
                          onClick={() => deleteDocument(u.id)}
                          aria-label={`删除文档 ${u.name}`}
                          className="p-1 hover:text-[#f87171]"
                        >
                          <Trash2 size={13} />
                        </button>
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Search */}
              <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
                <h3 className="text-sm font-medium mb-2">检索测试</h3>
                <div className="flex gap-2">
                  <input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && searchKB()}
                    placeholder="输入查询..." className="flex-1 bg-[#0f1117] border border-[#2a2d3a] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6c8cff]" />
                  <button onClick={searchKB} className="bg-[#6c8cff] text-white px-4 py-2 rounded-lg text-sm"><Search size={16} /></button>
                </div>
                {status && <p className="text-xs text-[#8b8fa3] mt-2">{status}</p>}
                {results.map((r: any, i: number) => (
                  <div key={i} className="mt-2 bg-[#0f1117] border border-[#2a2d3a] rounded-lg p-3">
                    <p className="text-xs text-[#8b8fa3]">
                      [{i + 1}] 相关度: {(r.score || 0).toFixed(2)} · {r.source}
                      {r.chunk_index !== undefined && r.chunk_index !== null ? ` · 分块 ${r.chunk_index + 1}` : ""}
                    </p>
                    <p className="text-sm mt-1">{r.content?.slice(0, 400)}</p>
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

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}
