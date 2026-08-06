import apiClient from "./apiClient";

export async function getAuditLogs(params?: {
  event_category?: string;
  event_type?: string;
  request_id?: string;
  limit?: number;
}) {
  const response = await apiClient.get("/api/audit/logs", {
    params,
  });

  return response.data;
}
