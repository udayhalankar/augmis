import apiClient from "./apiClient";

export async function getPlans() {
  const response = await apiClient.get("/api/subscriptions/plans");
  return response.data;
}

export async function getMySubscription() {
  const response = await apiClient.get("/api/subscriptions/me");
  return response.data;
}

export async function updateUsage(payload: {
  documents_count?: number;
  storage_used_mb?: number;
  ai_tokens_used?: number;
}) {
  const response = await apiClient.patch("/api/subscriptions/usage", payload);
  return response.data;
}
