import apiClient from "./apiClient";

export async function getDocumentControllerRecordsConfiguration(params: Record<string, any> = {}) {
  const response = await apiClient.get("/api/symployees/document-controller/configuration/records", {
    params,
  });
  return response.data;
}

export async function listDocumentControllerRecordsConfigurationDomain(
  domain: string,
  params: Record<string, any> = {}
) {
  const response = await apiClient.get(
    `/api/symployees/document-controller/configuration/records/${encodeURIComponent(domain)}`,
    { params }
  );
  return response.data;
}

export async function createDocumentControllerRecordsConfigurationRow(
  domain: string,
  payload: Record<string, any>
) {
  const response = await apiClient.post(
    `/api/symployees/document-controller/configuration/records/${encodeURIComponent(domain)}`,
    payload
  );
  return response.data;
}

export async function updateDocumentControllerRecordsConfigurationRow(
  domain: string,
  rowId: string,
  payload: Record<string, any>
) {
  const response = await apiClient.patch(
    `/api/symployees/document-controller/configuration/records/${encodeURIComponent(domain)}/${encodeURIComponent(rowId)}`,
    payload
  );
  return response.data;
}

export async function deleteDocumentControllerRecordsConfigurationRow(
  domain: string,
  rowId: string
) {
  const response = await apiClient.delete(
    `/api/symployees/document-controller/configuration/records/${encodeURIComponent(domain)}/${encodeURIComponent(rowId)}`
  );
  return response.data;
}
