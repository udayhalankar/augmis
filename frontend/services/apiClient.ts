import axios from "axios";
import { API_BASE_URL } from "./apiBase";
import { reportFrontendLog } from "./clientLogService";
import { clearStoredSession, refreshSessionTokens } from "./sessionRefresh";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  // timeout: 20000,
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("infomentica_token");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (typeof window !== "undefined") {
      const status = error.response?.status;
      const requestId =
        error.response?.headers?.["x-request-id"] || error.response?.headers?.["X-Request-ID"];
      const method = String(error.config?.method || "GET").toUpperCase();
      const url = error.config?.url || "unknown";
      const detail =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.message ||
        "API request failed";

      void reportFrontendLog({
        message: `${method} ${url} failed: ${detail}`,
        category: "api_error",
        level: status && status >= 500 ? "ERROR" : "WARNING",
        route: `${window.location.pathname}${window.location.search}`,
        method,
        status_code: status,
        request_id: requestId,
        component: "api_client",
        is_critical: Boolean(status && status >= 500),
        stack: error.stack,
        metadata: {
          api_url: url,
          response_status: status,
          response_detail:
            typeof detail === "string" ? detail : JSON.stringify(detail),
        },
      });
    }

    if (
      typeof window !== "undefined" &&
      error.response &&
      error.response.status === 401 &&
      !error.config?._retry
    ) {
      if (localStorage.getItem("infomentica_refresh_token")) {
        try {
          error.config._retry = true;
          const refreshResult = await refreshSessionTokens();
          error.config.headers.Authorization = `Bearer ${refreshResult.access_token}`;
          return apiClient.request(error.config);
        } catch {
          // fall through to clear session
        }
      }

      clearStoredSession();
      window.location.href = "/login";
    }

    return Promise.reject(error);
  }
);

export default apiClient;
