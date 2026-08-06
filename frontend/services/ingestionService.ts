import apiClient from "./apiClient";

export async function uploadRepositoryDocument(
  repositoryId: string,
  file: File
) {
  const formData = new FormData();
  formData.append("repository_id", repositoryId);
  formData.append("file", file);

  const response = await apiClient.post("/api/ingestion/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function rebuildRepository(repositoryId: string) {
  const response = await apiClient.post("/api/ingestion/rebuild/repository", {
    repository_id: repositoryId,
  });

  return response.data;
}
