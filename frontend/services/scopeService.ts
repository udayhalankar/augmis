import apiClient from "./apiClient";

type ScopeTrack = "augmis" | "symployee";

export async function getScopeTracker() {
  const response = await apiClient.get("/api/scope-tracker");
  return response.data;
}

export async function createPhase(payload: {
  title: string;
  description: string;
  status: string;
}, track: ScopeTrack) {
  const response = await apiClient.post("/api/scope-tracker/phases", payload, {
    params: { track },
  });
  return response.data;
}

export async function updatePhase(
  phaseId: string,
  payload: {
    title?: string;
    description?: string;
    status?: string;
  },
  track: ScopeTrack
) {
  const response = await apiClient.patch(
    `/api/scope-tracker/phases/${phaseId}`,
    payload,
    { params: { track } }
  );
  return response.data;
}

export async function deletePhase(phaseId: string, track: ScopeTrack) {
  const response = await apiClient.delete(`/api/scope-tracker/phases/${phaseId}`, {
    params: { track },
  });
  return response.data;
}

export async function createMilestone(
  phaseId: string,
  payload: {
    title: string;
    description: string;
    status: string;
  },
  track: ScopeTrack
) {
  const response = await apiClient.post(
    `/api/scope-tracker/phases/${phaseId}/milestones`,
    payload,
    { params: { track } }
  );
  return response.data;
}

export async function updateMilestone(
  phaseId: string,
  milestoneId: string,
  payload: {
    title?: string;
    description?: string;
    status?: string;
  },
  track: ScopeTrack
) {
  const response = await apiClient.patch(
    `/api/scope-tracker/phases/${phaseId}/milestones/${milestoneId}`,
    payload,
    { params: { track } }
  );
  return response.data;
}

export async function deleteMilestone(
  phaseId: string,
  milestoneId: string,
  track: ScopeTrack
) {
  const response = await apiClient.delete(
    `/api/scope-tracker/phases/${phaseId}/milestones/${milestoneId}`,
    { params: { track } }
  );
  return response.data;
}

export async function createScopeItem(
  phaseId: string,
  milestoneId: string,
  payload: {
    title: string;
    description: string;
    status: string;
    item_type: string;
    owner: string;
    due_date: string;
  },
  track: ScopeTrack
) {
  const response = await apiClient.post(
    `/api/scope-tracker/phases/${phaseId}/milestones/${milestoneId}/items`,
    payload,
    { params: { track } }
  );
  return response.data;
}

export async function updateScopeItem(
  phaseId: string,
  milestoneId: string,
  itemId: string,
  payload: {
    title?: string;
    description?: string;
    status?: string;
    item_type?: string;
    owner?: string;
    due_date?: string;
  },
  track: ScopeTrack
) {
  const response = await apiClient.patch(
    `/api/scope-tracker/phases/${phaseId}/milestones/${milestoneId}/items/${itemId}`,
    payload,
    { params: { track } }
  );
  return response.data;
}

export async function deleteScopeItem(
  phaseId: string,
  milestoneId: string,
  itemId: string,
  track: ScopeTrack
) {
  const response = await apiClient.delete(
    `/api/scope-tracker/phases/${phaseId}/milestones/${milestoneId}/items/${itemId}`,
    { params: { track } }
  );
  return response.data;
}
