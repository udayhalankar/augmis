import apiClient from "./apiClient";

export async function getDocumentLifecycleHistory(identityId: string) {
  const response = await apiClient.get(
    `/api/symployees/document-controller/lifecycle/${encodeURIComponent(identityId)}`
  );
  return response.data;
}

export async function getLifecycleEvents(params: Record<string, any> = {}) {
  const response = await apiClient.get("/api/symployees/document-controller/lifecycle-events", {
    params,
  });
  return response.data;
}
