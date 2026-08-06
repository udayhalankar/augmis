import apiClient from "./apiClient";

export async function getTransmittals(params: Record<string, any> = {}) {
  const response = await apiClient.get("/api/symployees/document-controller/transmittals", {
    params,
  });
  return response.data;
}

export async function getCorrespondence(params: Record<string, any> = {}) {
  const response = await apiClient.get("/api/symployees/document-controller/correspondence", {
    params,
  });
  return response.data;
}

export async function getAcknowledgements(params: Record<string, any> = {}) {
  const response = await apiClient.get(
    "/api/symployees/document-controller/transmittals/acknowledgements",
    { params }
  );
  return response.data;
}
