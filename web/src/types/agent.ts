export interface SubAgent {
  id: string; goal: string; status: string; progress: number;
  result?: string; error?: string; agent_id?: string;
}

export interface OrchestrationPlan {
  id: string; title: string; mode: string; status: string;
  tasks: number; completed: number; progress?: number;
  tasks_detail?: SubAgent[];
}

export interface HITLRequest {
  id: string; type: string; title: string; description: string;
  proposed_action: Record<string, any>; agent_state: Record<string, any>;
  created_at: number; timeout: number;
}
