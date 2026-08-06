import apiClient from "./apiClient";

export async function getEscalationDashboard(options?: { includeRecords?: boolean }) {
  const includeRecords = options?.includeRecords ?? true;
  const response = await apiClient.get(
    includeRecords ? "/api/escalations/dashboard" : "/api/escalations/dashboard/summary",
    includeRecords
      ? {
          params: {
            include_records: true,
          },
        }
      : undefined
  );
  return response.data;
}
