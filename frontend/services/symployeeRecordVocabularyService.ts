import apiClient from "./apiClient";

export async function getRecordVocabulary() {
  const response = await apiClient.get("/api/symployees/document-controller/records/vocabulary");
  return response.data;
}
