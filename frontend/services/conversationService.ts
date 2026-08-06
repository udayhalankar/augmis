import apiClient from "./apiClient";

export async function createConversation(title = "New Conversation") {
  const response = await apiClient.post("/api/conversations", {
    title,
  });

  return response.data;
}

export async function getConversations() {
  const response = await apiClient.get("/api/conversations");
  return response.data;
}

export async function getConversation(sessionId: string) {
  const response = await apiClient.get(`/api/conversations/${sessionId}`);
  return response.data;
}

export async function addConversationMessage(
  sessionId: string,
  role: "user" | "assistant",
  content: string,
  sources: any[] = []
) {
  const response = await apiClient.post(
    `/api/conversations/${sessionId}/messages`,
    {
      role,
      content,
      sources,
    }
  );

  return response.data;
}

export async function deleteConversation(sessionId: string) {
  const response = await apiClient.delete(`/api/conversations/${sessionId}`);
  return response.data;
}

export async function clearConversations() {
  const response = await apiClient.delete("/api/conversations");
  return response.data;
}
