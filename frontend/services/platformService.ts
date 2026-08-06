import apiClient from "./apiClient";

export type PlatformHealthResponse = {
  ok: boolean;
  service: string;
  version: string;
  model: string;
  embedding_model: string;
  datasource?: {
    configured_path?: string | null;
    exists?: boolean;
    status?: string;
    error?: string | null;
    deprecated?: boolean;
    message?: string | null;
  };
  ocr?: {
    available?: boolean;
    status?: string;
    error?: string | null;
    tesseract_cmd?: string | null;
    configured_tesseract_cmd?: string | null;
    pytesseract_installed?: boolean;
    pypdfium2_installed?: boolean;
  };
  openai?: {
    available?: boolean;
    status?: string;
    error?: string | null;
    model?: string;
    embedding_model?: string;
    api_key_configured?: boolean;
    sdk_version?: string | null;
  };
  database?: {
    available?: boolean;
    status?: string;
    error?: string | null;
    engine?: string;
    driver?: string;
    host?: string | null;
    database?: string | null;
    pgvector_enabled?: boolean;
  };
  security?: {
    email_provider?: string;
    smtp_host_configured?: boolean;
    smtp_from_email?: string | null;
    google_login_enabled?: boolean;
    mfa_enabled?: boolean;
    self_registration_enabled?: boolean;
    invite_onboarding_enabled?: boolean;
    reset_link_enabled?: boolean;
    capabilities?: Record<string, any>;
  };
  platform_diagnostics?: {
    python_version?: string;
    runtime_platform?: string;
    vector_backend?: string;
    scheduler?: {
      mode?: string;
      enabled?: boolean;
      interval_minutes?: number;
      timezone?: string;
    };
    libraries?: Record<string, string | null>;
    config?: {
      restart_required?: boolean;
      deprecated?: Record<string, any>;
    };
  };
};

export type PlatformConfigField = {
  key: string;
  label: string;
  is_secret: boolean;
  restart_required: boolean;
  pending_restart: boolean;
  applies_live: boolean;
  configured: boolean;
  value?: string | null;
  masked_value?: string | null;
  live_value?: string | null;
  has_override: boolean;
};

export type PlatformConfigResponse = {
  fields: PlatformConfigField[];
  restart_required: boolean;
  deprecated?: {
    datasource_path?: {
      key: string;
      label: string;
      configured: boolean;
      message: string;
      can_remove_from_env: boolean;
    };
  };
};

export type ServerLogEntry = {
  log_id: string;
  occurred_at: string;
  source: "backend" | "frontend";
  level: string;
  logger?: string;
  message: string;
  exception?: string;
  category?: string;
  route?: string | null;
  method?: string | null;
  status_code?: number | null;
  request_id?: string | null;
  repository_id?: string | null;
  business_area?: string | null;
  component?: string | null;
  is_critical?: boolean;
  user_agent?: string | null;
  stack?: string | null;
  tenant_id?: string | null;
  user_id?: string | null;
  user_email?: string | null;
  metadata?: Record<string, any>;
};

export async function getPlatformHealth() {
  const response = await apiClient.get<PlatformHealthResponse>("/api/health");
  return response.data;
}

export async function getPlatformConfig() {
  const response = await apiClient.get<{ success: boolean; data: PlatformConfigResponse }>("/api/platform/config");
  return response.data;
}

export async function updatePlatformConfig(payload: {
  openai_api_key?: string;
  openai_model?: string;
  openai_embedding_model?: string;
  database_url?: string;
  ocr_tesseract_cmd?: string;
}) {
  const response = await apiClient.patch<{ success: boolean; data: PlatformConfigResponse }>(
    "/api/platform/config",
    payload
  );
  return response.data;
}

export async function testOpenAIConfig() {
  const response = await apiClient.post<{
    success: boolean;
    data: {
      chat_model: string;
      embedding_model: string;
      chat_test: boolean;
      embedding_test: boolean;
      message: string;
    };
  }>("/api/platform/test/openai");
  return response.data;
}

export async function testDatabaseConfig() {
  const response = await apiClient.post<{
    success: boolean;
    data: {
      driver?: string;
      host?: string | null;
      database?: string | null;
      pgvector_enabled?: boolean;
      message: string;
    };
  }>("/api/platform/test/database");
  return response.data;
}

export async function getServerLogs(params?: {
  source?: "backend" | "frontend";
  level?: string;
  q?: string;
  route?: string;
  user?: string;
  repository_id?: string;
  business_area?: string;
  request_id?: string;
  category?: string;
  critical_only?: boolean;
  start_at?: string;
  end_at?: string;
  limit?: number;
}) {
  const response = await apiClient.get<{ success: boolean; data: ServerLogEntry[] }>(
    "/api/platform/server-logs",
    {
      params,
    }
  );
  return response.data;
}

export function getServerLogsExportUrl(params?: {
  source?: "backend" | "frontend";
  level?: string;
  q?: string;
  route?: string;
  user?: string;
  repository_id?: string;
  business_area?: string;
  request_id?: string;
  category?: string;
  critical_only?: boolean;
  start_at?: string;
  end_at?: string;
  limit?: number;
}) {
  const searchParams = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  return `/api/platform/server-logs/export?${searchParams.toString()}`;
}

export async function markServerLogCritical(logId: string, isCritical: boolean) {
  const response = await apiClient.patch<{ success: boolean; data: ServerLogEntry }>(
    `/api/platform/server-logs/${logId}/critical`,
    undefined,
    {
      params: {
        is_critical: isCritical,
      },
    }
  );
  return response.data;
}
