import apiClient from "./apiClient";

export async function getBusinessAreaCatalog() {
  const response = await apiClient.get("/api/repositories/business-areas");
  return response.data;
}

export async function getBusinessAreaDetail(businessArea: string) {
  const response = await apiClient.get(
    `/api/repositories/business-areas/${encodeURIComponent(businessArea)}`
  );
  return response.data;
}

export async function getBusinessAreaDashboard(
  businessArea: string,
  options?: { includeRecords?: boolean }
) {
  const includeRecords = options?.includeRecords ?? true;
  const response = await apiClient.get(
    `/api/repositories/business-areas/${encodeURIComponent(businessArea)}/dashboard`,
    {
      params: {
        include_records: includeRecords,
      },
    }
  );
  return response.data;
}
