export interface SessionDetail {
  id: string; title: string; source: string; profile?: string;
  parent_id?: string; created_at: string; updated_at: string;
  metadata?: Record<string, any>;
}
