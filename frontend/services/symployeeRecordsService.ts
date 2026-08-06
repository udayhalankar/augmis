import apiClient from "./apiClient";

export async function getRecordDeclarations(params: Record<string, any> = {}) {
  const response = await apiClient.get("/api/symployees/document-controller/records/declarations", {
    params,
  });
  return response.data;
}

export async function updateRecordVitalStatus(payload: {
  identity_id: string;
  vital_status: "NON_VITAL" | "VITAL_CANDIDATE" | "VITAL" | "VITAL_UNDER_REVIEW";
  reason?: string;
  metadata_json?: Record<string, any>;
}) {
  const response = await apiClient.post(
    "/api/symployees/document-controller/records/vital-status",
    payload
  );
  return response.data;
}

export async function runRecordTimeEvaluation(payload: {
  identity_id?: string | null;
  version_id?: string | null;
  limit?: number;
  evaluation_reason?: string;
  metadata_json?: Record<string, any>;
}) {
  const response = await apiClient.post(
    "/api/symployees/document-controller/records/time-evaluation",
    payload
  );
  return response.data;
}

export async function runRetentionDispositionAutomation(payload: {
  identity_id?: string | null;
  version_id?: string | null;
  limit?: number;
  evaluation_reason?: string;
  auto_initiate_disposition?: boolean;
  auto_initiate_archive?: boolean;
  metadata_json?: Record<string, any>;
}) {
  const response = await apiClient.post(
    "/api/symployees/document-controller/records/retention-automation",
    payload
  );
  return response.data;
}

export async function getLegalHolds(params: Record<string, any> = {}) {
  const response = await apiClient.get("/api/symployees/document-controller/records/legal-holds", {
    params,
  });
  return response.data;
}

export async function getDispositionCases(params: Record<string, any> = {}) {
  const response = await apiClient.get("/api/symployees/document-controller/records/disposition", {
    params,
  });
  return response.data;
}

export async function approveDispositionCase(
  dispositionCaseId: string,
  payload: {
    approval_role: "RECORDS" | "LEGAL" | "BUSINESS_OWNER";
    comments?: string;
    metadata_json?: Record<string, any>;
  }
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/records/disposition/${dispositionCaseId}/approve`,
    payload
  );
  return response.data;
}

export async function executeDispositionCase(
  dispositionCaseId: string,
  payload: {
    execution_outcome: "DESTROY" | "ARCHIVE";
    reason?: string;
    evidence_json?: Record<string, any>;
    metadata_json?: Record<string, any>;
  }
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/records/disposition/${dispositionCaseId}/execute`,
    payload
  );
  return response.data;
}

export async function getArchiveTransfers(params: Record<string, any> = {}) {
  const response = await apiClient.get(
    "/api/symployees/document-controller/records/archive-transfers",
    {
      params,
    }
  );
  return response.data;
}

export async function completeArchiveTransfer(
  archiveTransferId: string,
  payload: {
    receipt_reference?: string | null;
    integrity_verified?: boolean | null;
    metadata_json?: Record<string, any>;
  }
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/records/archive-transfers/${archiveTransferId}/complete`,
    payload
  );
  return response.data;
}
