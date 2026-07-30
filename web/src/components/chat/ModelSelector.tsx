import { useChatStore } from "@/stores/chatStore";

export function ModelSelector() {
  const { model, models, setModel } = useChatStore();
  return (
    <select value={model} onChange={(e) => setModel(e.target.value)}
      className="bg-[#1a1d27] text-sm border border-[#2a2d3a] rounded px-3 py-1.5 text-[#e1e4ea]">
      <option value="">自动路由</option>
      {models.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
    </select>
  );
}
