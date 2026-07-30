import { BookOpen, Upload } from "lucide-react";

export function KnowledgeBase() {
  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-lg font-semibold flex items-center gap-2 mb-6"><BookOpen size={20} /> 知识库</h2>
      <div className="border-2 border-dashed border-[#2a2d3a] rounded-xl p-12 text-center">
        <Upload size={32} className="mx-auto mb-3 text-[#8b8fa3]" />
        <p className="text-sm text-[#8b8fa3]">拖拽文档到此处上传</p>
        <p className="text-xs text-[#8b8fa3] mt-1">支持 PDF · Markdown · 代码文件</p>
        <button className="mt-4 bg-[#6c8cff] text-white px-4 py-2 rounded-lg text-sm hover:opacity-90">
          创建知识库
        </button>
      </div>
      <div className="mt-6">
        <h3 className="text-sm font-semibold mb-3 text-[#8b8fa3]">知识库列表</h3>
        <p className="text-xs text-[#8b8fa3]">暂无知识库</p>
      </div>
    </div>
  );
}
