import apiClient from "./apiClient";

export type MigrationAgentRecord = {
  agent_id: string;
  tenant_id?: string | null;
  machine_name?: string | null;
  hostname?: string | null;
  platform?: string | null;
  version: string;
  root_path: string;
  status: string;
  pending_change_count: number;
  last_seen_at?: string | null;
  last_sync_at?: string | null;
  last_error?: string | null;
  metadata?: Record<string, any>;
  created_at?: string | null;
  modified_at?: string | null;
};

export type MigrationAgentActivityRecord = {
  activity_id: string;
  agent_id: string;
  tenant_id?: string | null;
  occurred_at?: string | null;
  event_type: string;
  root_path?: string | null;
  file_path?: string | null;
  file_name?: string | null;
  kind?: string | null;
  change_type?: string | null;
  item_count?: number | null;
  metadata?: Record<string, any>;
};

export async function getMigrationAgents(limit = 100) {
  const response = await apiClient.get<{
    success: boolean;
    data: {
      agents: MigrationAgentRecord[];
      activities: MigrationAgentActivityRecord[];
    };
  }>("/api/agents", {
    params: { limit },
  });
  return response.data;
}
