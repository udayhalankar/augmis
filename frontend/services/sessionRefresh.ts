"use client";

import axios from "axios";

import { API_BASE_URL } from "./apiBase";

const SESSION_REFRESH_EVENT = "infomentica:session-refreshed";

type RefreshPayload = {
  access_token: string;
  refresh_token: string;
  user: Record<string, unknown>;
};

let refreshInFlight: Promise<RefreshPayload> | null = null;

function persistSession(payload: RefreshPayload) {
  localStorage.setItem("infomentica_token", payload.access_token);
  localStorage.setItem("infomentica_refresh_token", payload.refresh_token);
  localStorage.setItem("infomentica_user", JSON.stringify(payload.user));
  localStorage.setItem("infomentica_last_refresh_at", String(Date.now()));
  window.dispatchEvent(new CustomEvent(SESSION_REFRESH_EVENT, { detail: payload }));
}

export function clearStoredSession() {
  localStorage.removeItem("infomentica_token");
  localStorage.removeItem("infomentica_refresh_token");
  localStorage.removeItem("infomentica_user");
  localStorage.removeItem("infomentica_last_refresh_at");
}

export function sessionRefreshEventName() {
  return SESSION_REFRESH_EVENT;
}

export async function refreshSessionTokens() {
  if (typeof window === "undefined") {
    throw new Error("Session refresh is only available in the browser.");
  }
  if (refreshInFlight) {
    return refreshInFlight;
  }
  const refreshToken = localStorage.getItem("infomentica_refresh_token");
  if (!refreshToken) {
    throw new Error("Refresh token is missing.");
  }
  refreshInFlight = axios
    .post(`${API_BASE_URL}/api/auth/refresh`, {
      refresh_token: refreshToken,
    })
    .then((response) => {
      const payload = response.data as RefreshPayload;
      persistSession(payload);
      return payload;
    })
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}
