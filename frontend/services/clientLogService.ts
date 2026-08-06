"use client";

import { API_BASE_URL } from "./apiBase";

const RECENT_LOG_WINDOW_MS = 5000;
const recentEvents = new Map<string, number>();

export type FrontendLogPayload = {
  message: string;
  category: string;
  level?: string;
  route?: string;
  method?: string;
  status_code?: number;
  request_id?: string;
  stack?: string | null;
  repository_id?: string;
  business_area?: string;
  component?: string;
  is_critical?: boolean;
  metadata?: Record<string, unknown>;
};

export function getCurrentBrowserRoute() {
  if (typeof window === "undefined") {
    return "";
  }

  return `${window.location.pathname}${window.location.search}`;
}

export async function reportFrontendLog(payload: FrontendLogPayload) {
  if (typeof window === "undefined") {
    return;
  }

  const token = window.localStorage.getItem("infomentica_token");
  if (!token) {
    return;
  }

  const route = payload.route || getCurrentBrowserRoute();
  const signature = [
    payload.category,
    route,
    payload.message,
    payload.stack || "",
    payload.request_id || "",
  ].join("|");
  const now = Date.now();
  const lastSeen = recentEvents.get(signature);
  if (lastSeen && now - lastSeen < RECENT_LOG_WINDOW_MS) {
    return;
  }
  recentEvents.set(signature, now);

  if (recentEvents.size > 200) {
    for (const [key, value] of recentEvents.entries()) {
      if (now - value > RECENT_LOG_WINDOW_MS) {
        recentEvents.delete(key);
      }
    }
  }

  try {
    await fetch(`${API_BASE_URL}/api/platform/frontend-logs`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        ...payload,
        route,
        user_agent: window.navigator.userAgent,
      }),
      keepalive: true,
    });
  } catch {
    // Avoid recursive client logging.
  }
}
