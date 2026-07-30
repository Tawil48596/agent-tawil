import { Settings as SettingsIcon, User, Cpu, Brain } from "lucide-react";

export function Settings() {
  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-lg font-semibold flex items-center gap-2 mb-6"><SettingsIcon size={20} /> 设置</h2>
      <div className="space-y-4 max-w-lg">
        <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
          <h3 className="text-sm font-semibold flex items-center gap-2"><User size={16} /> 用户偏好</h3>
          <p className="text-xs text-[#8b8fa3] mt-1">配置语言、时区、默认模型等偏好</p>
        </div>
        <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
          <h3 className="text-sm font-semibold flex items-center gap-2"><Cpu size={16} /> 模型配置</h3>
          <p className="text-xs text-[#8b8fa3] mt-1">管理 LLM Provider 和 API Key</p>
        </div>
        <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
          <h3 className="text-sm font-semibold flex items-center gap-2"><Brain size={16} /> 记忆管理</h3>
          <p className="text-xs text-[#8b8fa3] mt-1">查看和管理长期记忆</p>
        </div>
      </div>
    </div>
  );
}
