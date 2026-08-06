import apiClient from "./apiClient";

export async function getSymployees() {
  const response = await apiClient.get("/api/symployees");
  return response.data;
}

export async function getDocumentControllerOverview() {
  const response = await apiClient.get("/api/symployees/document-controller/overview");
  return response.data;
}

export async function getDocumentControllerPolicies() {
  const response = await apiClient.get("/api/symployees/document-controller/policies");
  return response.data;
}

export async function createDocumentControllerPolicy(payload: {
  policy_domain: string;
  policy_code: string;
  name: string;
  scope_type?: string;
  scope_ref?: string | null;
  config_json: Record<string, any>;
  is_default?: boolean;
  status?: string;
}) {
  const response = await apiClient.post("/api/symployees/document-controller/policies", payload);
  return response.data;
}

export async function bootstrapDocumentControllerPolicies() {
  const response = await apiClient.post(
    "/api/symployees/document-controller/policies/bootstrap-defaults"
  );
  return response.data;
}

export async function updateDocumentControllerPolicy(
  policyDomain: string,
  policyCode: string,
  payload: {
    name?: string;
    scope_type?: string;
    scope_ref?: string | null;
    config_json?: Record<string, any>;
    is_default?: boolean;
    status?: string;
  }
) {
  const response = await apiClient.patch(
    `/api/symployees/document-controller/policies/${encodeURIComponent(policyDomain)}/${encodeURIComponent(policyCode)}`,
    payload
  );
  return response.data;
}

export async function getDocumentControllerDocuments() {
  const response = await apiClient.get("/api/symployees/document-controller/documents");
  return response.data;
}

export async function getDocumentControllerDocumentDetail(identityId: string) {
  const response = await apiClient.get(
    `/api/symployees/document-controller/documents/${encodeURIComponent(identityId)}`
  );
  return response.data;
}

export async function openDocumentControllerDocumentFile(
  identityId: string,
  versionId?: string | null
) {
  const response = await apiClient.get(
    `/api/symployees/document-controller/documents/${encodeURIComponent(identityId)}/file`,
    {
      params: versionId ? { version_id: versionId } : undefined,
      responseType: "blob",
    }
  );
  const objectUrl = window.URL.createObjectURL(response.data);
  window.open(objectUrl, "_blank", "noopener,noreferrer");
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 60000);
}

export async function getDocumentControllerRecommendations() {
  const response = await apiClient.get("/api/symployees/document-controller/recommendations");
  return response.data;
}

export async function approveDocumentControllerRecommendation(
  recommendationId: string,
  payload: { comments?: string; effective_values?: Record<string, any> } = {}
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/recommendations/${encodeURIComponent(recommendationId)}/approve`,
    payload
  );
  return response.data;
}

export async function rejectDocumentControllerRecommendation(
  recommendationId: string,
  payload: { comments?: string; reason_code?: string } = {}
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/recommendations/${encodeURIComponent(recommendationId)}/reject`,
    payload
  );
  return response.data;
}

export async function overrideDocumentControllerRecommendation(
  recommendationId: string,
  payload: { reason_code: string; reason_text?: string; after_state?: Record<string, any> }
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/recommendations/${encodeURIComponent(recommendationId)}/override`,
    payload
  );
  return response.data;
}

export async function getDocumentControllerApprovals() {
  const response = await apiClient.get("/api/symployees/document-controller/approvals");
  return response.data;
}

export async function getDocumentControllerCommands() {
  const response = await apiClient.get("/api/symployees/document-controller/commands");
  return response.data;
}

export async function createDocumentControllerCommand(payload: {
  repository_id: string;
  agent_id?: string | null;
  identity_id: string;
  version_id?: string | null;
  command_type: string;
  payload: Record<string, any>;
  source_recommendation_id?: string | null;
}) {
  const response = await apiClient.post("/api/symployees/document-controller/commands", payload);
  return response.data;
}

export async function approveDocumentControllerCommand(
  commandId: string,
  payload: { comments?: string } = {}
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/commands/${encodeURIComponent(commandId)}/approve`,
    payload
  );
  return response.data;
}

export async function rejectDocumentControllerCommand(
  commandId: string,
  payload: { comments?: string } = {}
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/commands/${encodeURIComponent(commandId)}/reject`,
    payload
  );
  return response.data;
}

export async function dispatchDocumentControllerCommand(
  commandId: string,
  payload: { comments?: string } = {}
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/commands/${encodeURIComponent(commandId)}/dispatch`,
    payload
  );
  return response.data;
}

export async function acknowledgeDocumentControllerCommand(
  commandId: string,
  payload: { comments?: string } = {}
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/commands/${encodeURIComponent(commandId)}/acknowledge`,
    payload
  );
  return response.data;
}

export async function failDocumentControllerCommand(
  commandId: string,
  payload: { comments?: string; failure_reason?: string } = {}
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/commands/${encodeURIComponent(commandId)}/fail`,
    payload
  );
  return response.data;
}

export async function rollbackDocumentControllerCommand(
  commandId: string,
  payload: { comments?: string } = {}
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/commands/${encodeURIComponent(commandId)}/rollback`,
    payload
  );
  return response.data;
}

export async function getMasterDocumentRegister() {
  const response = await apiClient.get(
    "/api/symployees/document-controller/registers/master-document-register"
  );
  return response.data;
}
