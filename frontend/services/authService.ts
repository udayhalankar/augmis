import axios from "axios";
import apiClient from "./apiClient";
import { API_BASE_URL } from "./apiBase";

export async function loginUser(
  email: string,
  password: string,
  remember_me = true
) {
  const response = await axios.post(`${API_BASE_URL}/api/auth/login`, {
    email,
    password,
    remember_me,
  });

  return response.data;
}

export async function registerWorkspace(payload: {
  tenant_name: string;
  name: string;
  email: string;
  password: string;
  plan_id?: string;
}) {
  const response = await axios.post(`${API_BASE_URL}/api/auth/register`, payload);
  return response.data;
}

export async function refreshLogin(refresh_token: string) {
  const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
    refresh_token,
  });
  return response.data;
}

export async function getAuthCapabilities() {
  const response = await axios.get(`${API_BASE_URL}/api/auth/capabilities`);
  return response.data;
}

export async function requestPasswordResetOtp(email: string) {
  const response = await axios.post(
    `${API_BASE_URL}/api/auth/forgot-password/request-otp`,
    { email }
  );
  return response.data;
}

export async function requestPasswordResetLink(email: string) {
  const response = await axios.post(
    `${API_BASE_URL}/api/auth/forgot-password/request-link`,
    { email }
  );
  return response.data;
}

export async function resetPasswordWithOtp(payload: {
  challenge_id: string;
  otp: string;
  new_password: string;
}) {
  const response = await axios.post(
    `${API_BASE_URL}/api/auth/forgot-password/reset`,
    payload
  );
  return response.data;
}

export async function resetPasswordWithLink(payload: {
  token: string;
  new_password: string;
}) {
  const response = await axios.post(
    `${API_BASE_URL}/api/auth/forgot-password/reset-link`,
    payload
  );
  return response.data;
}

export async function getMySessions() {
  const response = await apiClient.get("/api/auth/sessions");
  return response.data;
}

export async function logoutSession() {
  const response = await apiClient.post("/api/auth/logout");
  return response.data;
}

export async function revokeSession(sessionId: string) {
  const response = await apiClient.post(`/api/auth/sessions/${sessionId}/revoke`);
  return response.data;
}

export async function logoutAllSessions() {
  const response = await apiClient.post("/api/auth/logout-all");
  return response.data;
}

export async function changePassword(payload: {
  current_password: string;
  new_password: string;
  revoke_other_sessions: boolean;
}) {
  const response = await apiClient.post("/api/auth/change-password", payload);
  return response.data;
}

export async function createUserInvite(payload: {
  email: string;
  role: string;
  allowed_modules: string[];
  permissions: string[];
  status: string;
}) {
  const response = await apiClient.post("/api/auth/invites", payload);
  return response.data;
}

export async function getInvite(token: string) {
  const response = await axios.get(`${API_BASE_URL}/api/auth/invites/${token}`);
  return response.data;
}

export async function acceptInvite(
  token: string,
  payload: { name: string; email: string; password: string }
) {
  const response = await axios.post(
    `${API_BASE_URL}/api/auth/invites/${token}/accept`,
    payload
  );
  return response.data;
}

export async function getAuthGovernance() {
  const response = await apiClient.get("/api/auth/governance");
  return response.data;
}

export async function updateAuthGovernance(payload: Record<string, any>) {
  const response = await apiClient.patch("/api/auth/governance", payload);
  return response.data;
}

export async function getMe(token: string) {
  const response = await axios.get(`${API_BASE_URL}/api/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
}

export async function getTenantUsers() {
  const response = await apiClient.get("/api/auth/users");
  return response.data;
}

export async function createTenantUser(payload: {
  name: string;
  email: string;
  password: string;
  role: string;
  status: string;
  allowed_modules: string[];
  permissions: string[];
}) {
  const response = await apiClient.post("/api/auth/users", payload);
  return response.data;
}

export async function updateTenantUser(
  userId: string,
  payload: {
    name: string;
    email: string;
    role: string;
    status: string;
    allowed_modules: string[];
    permissions: string[];
  }
) {
  const response = await apiClient.patch(`/api/auth/users/${userId}`, payload);
  return response.data;
}

export async function deleteTenantUser(userId: string) {
  const response = await apiClient.delete(`/api/auth/users/${userId}`);
  return response.data;
}
