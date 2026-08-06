import apiClient from "./apiClient";

export async function getRepositories() {
  const response = await apiClient.get("/api/repositories");
  return response.data;
}

export async function getWorkAreas() {
  const response = await apiClient.get("/api/repositories/work-areas");
  return response.data;
}

export async function getIntelligencePatterns() {
  const response = await apiClient.get("/api/repositories/intelligence-patterns");
  return response.data;
}

export async function createIntelligencePattern(payload: {
  name: string;
  description: string;
  dashboard_type: string;
  tags_keywords: string[];
  summary_focus: string[];
  risk_rules: Array<Record<string, any>>;
  thresholds: Array<Record<string, any>>;
  required_specifics: string[];
  entities_to_extract: string[];
  summary_template: string;
  threshold_rules: Array<Record<string, any>>;
  fact_extractors: Array<Record<string, any>>;
  enabled_checks: string[];
}) {
  const response = await apiClient.post("/api/repositories/intelligence-patterns", payload);
  return response.data;
}

export async function updateIntelligencePattern(
  patternName: string,
  payload: {
    name: string;
    description: string;
    dashboard_type: string;
    tags_keywords: string[];
    summary_focus: string[];
    risk_rules: Array<Record<string, any>>;
    thresholds: Array<Record<string, any>>;
    required_specifics: string[];
    entities_to_extract: string[];
    summary_template: string;
    threshold_rules: Array<Record<string, any>>;
    fact_extractors: Array<Record<string, any>>;
    enabled_checks: string[];
  }
) {
  const response = await apiClient.patch(
    `/api/repositories/intelligence-patterns/${encodeURIComponent(patternName)}`,
    payload
  );
  return response.data;
}

export async function deleteIntelligencePattern(patternName: string) {
  const response = await apiClient.delete(
    `/api/repositories/intelligence-patterns/${encodeURIComponent(patternName)}`
  );
  return response.data;
}

export async function createWorkArea(payload: {
  name: string;
  description: string;
  intelligence_pattern: string;
  tags_keywords: string[];
  summary_focus: string[];
  risk_rules: Array<Record<string, any>>;
  thresholds: Array<Record<string, any>>;
  required_specifics: string[];
  entities_to_extract: string[];
  summary_template: string;
  threshold_rules: Array<Record<string, any>>;
  fact_extractors: Array<Record<string, any>>;
  dashboard_type: string;
  enabled_checks: string[];
}) {
  const response = await apiClient.post("/api/repositories/work-areas", payload);
  return response.data;
}

export async function updateWorkArea(
  workAreaName: string,
  payload: {
    name: string;
    description: string;
    intelligence_pattern: string;
    tags_keywords: string[];
    summary_focus: string[];
    risk_rules: Array<Record<string, any>>;
    thresholds: Array<Record<string, any>>;
    required_specifics: string[];
    entities_to_extract: string[];
    summary_template: string;
    threshold_rules: Array<Record<string, any>>;
    fact_extractors: Array<Record<string, any>>;
    dashboard_type: string;
    enabled_checks: string[];
  }
) {
  const response = await apiClient.patch(
    `/api/repositories/work-areas/${encodeURIComponent(workAreaName)}`,
    payload
  );
  return response.data;
}

export async function deleteWorkArea(workAreaName: string) {
  const response = await apiClient.delete(
    `/api/repositories/work-areas/${encodeURIComponent(workAreaName)}`
  );
  return response.data;
}

export async function createRepository(payload: {
  repository_name: string;
  source_type: string;
  business_area?: string;
  status: string;
  source_path?: string;
  connection_config?: Record<string, any>;
}) {
  const response = await apiClient.post("/api/repositories", payload);
  return response.data;
}

export async function getMyRepositoryAccess() {
  const response = await apiClient.get("/api/repositories/my-access");
  return response.data;
}

export async function getRepositoryAccess(repositoryId: string) {
  const response = await apiClient.get(
    `/api/repositories/${repositoryId}/access`
  );
  return response.data;
}

export async function grantRepositoryAccess(payload: {
  repository_id: string;
  user_id: string;
  can_read: boolean;
  can_ingest: boolean;
  can_admin: boolean;
  business_area?: string;
}) {
  const response = await apiClient.post("/api/repositories/access", payload);
  return response.data;
}

export async function updateRepositoryConnection(
  repositoryId: string,
  payload: {
    source_path?: string;
    business_area?: string;
    connection_config: Record<string, any>;
  }
) {
  const response = await apiClient.patch(
    `/api/repositories/${repositoryId}/connection`,
    payload
  );

  return response.data;
}

export async function syncRepository(repositoryId: string) {
  const response = await apiClient.post(`/api/repositories/${repositoryId}/sync`);
  return response.data;
}

export async function disconnectRepository(repositoryId: string) {
  const response = await apiClient.post(
    `/api/repositories/${repositoryId}/disconnect`
  );
  return response.data;
}

export async function deleteRepository(repositoryId: string) {
  const response = await apiClient.delete(`/api/repositories/${repositoryId}`);
  return response.data;
}
