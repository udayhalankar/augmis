import apiClient from "./apiClient";

export const repositorySyncApi = {
  syncRepository: async (repositoryId: string) => {
    const res = await apiClient.post(`/api/repositories/${repositoryId}/sync`);
    return res.data;
  },

  reindexRepository: async (repositoryId: string) => {
    const res = await apiClient.post(`/api/repositories/${repositoryId}/reindex`);
    return res.data;
  },

  getRepositoryIndexReport: async (repositoryId: string) => {
    const res = await apiClient.get(`/api/repositories/${repositoryId}/index-report`);
    return res.data;
  },

  getRepositoryContentReport: async (
    repositoryId: string,
    options?: { status?: string; page?: number; pageSize?: number }
  ) => {
    const res = await apiClient.get(`/api/repositories/${repositoryId}/content-report`, {
      params: {
        status: options?.status || "all",
        page: options?.page || 1,
        page_size: options?.pageSize || 4,
      },
    });
    return res.data;
  },

  getRepositoryFileContent: async (repositoryId: string, connectorFileId: string) => {
    const res = await apiClient.get(
      `/api/repositories/${repositoryId}/files/${connectorFileId}/content`,
      { responseType: "blob" }
    );
    return {
      blob: res.data,
      contentType: res.headers["content-type"],
    };
  },

  getStatus: async (repositoryId: string) => {
    const res = await apiClient.get(`/api/repositories/${repositoryId}/sync/status`);
    return res.data;
  },

  getHealth: async (repositoryId: string) => {
    const res = await apiClient.get(`/api/repositories/${repositoryId}/sync/health`);
    return res.data;
  },

  getHistory: async (repositoryId: string) => {
    const res = await apiClient.get(`/api/repositories/${repositoryId}/sync/history`);
    return res.data;
  },

  getFailures: async (repositoryId: string) => {
    const res = await apiClient.get(`/api/repositories/${repositoryId}/sync/failures`);
    return res.data;
  },

  retryFailure: async (repositoryId: string, failureId: string) => {
    const res = await apiClient.post(
      `/api/repositories/${repositoryId}/sync/failures/${failureId}/retry`
    );
    return res.data;
  },

  getConnectorCapabilities: async () => {
    const res = await apiClient.get("/api/repositories/connector-capabilities");
    return res.data;
  },

  getSyncLogs: async (repositoryId: string) => {
    const res = await apiClient.get(`/api/repositories/${repositoryId}/sync/logs`);
    return res.data;
  },

  testConnector: async (repositoryId: string) => {
    const res = await apiClient.post(`/api/repositories/${repositoryId}/connector/test`);
    return res.data;
  },

  discoverSharePointDrives: async (payload: {
    auth_method?: string;
    tenant_id: string;
    client_id: string;
    client_secret?: string;
    client_secret_env?: string;
    certificate_thumbprint?: string;
    certificate_private_key?: string;
    certificate_private_key_env?: string;
    certificate_private_key_path?: string;
    certificate_passphrase?: string;
    certificate_passphrase_env?: string;
    site_id: string;
  }) => {
    const res = await apiClient.post("/api/repositories/sharepoint/discover-drives", payload);
    return res.data;
  },

  resolveSharePointSite: async (payload: {
    auth_method?: string;
    tenant_id: string;
    client_id: string;
    client_secret?: string;
    client_secret_env?: string;
    certificate_thumbprint?: string;
    certificate_private_key?: string;
    certificate_private_key_env?: string;
    certificate_private_key_path?: string;
    certificate_passphrase?: string;
    certificate_passphrase_env?: string;
    hostname: string;
    site_path: string;
  }) => {
    const res = await apiClient.post("/api/repositories/sharepoint/resolve-site", payload);
    return res.data;
  },

  discoverSharePointSites: async (payload: Record<string, any>, search = "") => {
    const res = await apiClient.post(
      `/api/repositories/sharepoint/discover-sites?search=${encodeURIComponent(search)}`,
      payload
    );
    return res.data;
  },

  discoverSharePointFolders: async (payload: Record<string, any>, folderPath = "/") => {
    const res = await apiClient.post(
      `/api/repositories/sharepoint/discover-folders?folder_path=${encodeURIComponent(folderPath)}`,
      payload
    );
    return res.data;
  },

  validateSharePointConfig: async (payload: Record<string, any>) => {
    const res = await apiClient.post("/api/repositories/sharepoint/validate-config", payload);
    return res.data;
  },

  discoverSharedDriveRoots: async (basePath?: string) => {
    const res = await apiClient.get(
      `/api/repositories/sharedrive/discover-roots${
        basePath ? `?base_path=${encodeURIComponent(basePath)}` : ""
      }`
    );
    return res.data;
  },

  discoverSharedDriveFolders: async (rootPath: string, folderPath?: string) => {
    const query = new URLSearchParams({ root_path: rootPath });
    if (folderPath) {
      query.set("folder_path", folderPath);
    }

    const res = await apiClient.get(
      `/api/repositories/sharedrive/discover-folders?${query.toString()}`
    );
    return res.data;
  },

  resetSharePointDelta: async (repositoryId: string) => {
    const res = await apiClient.post(
      `/api/repositories/${repositoryId}/sharepoint/reset-delta`
    );
    return res.data;
  },

  updateSchedule: async (
    repositoryId: string,
    payload: { sync_enabled: boolean; sync_interval_minutes: number | null }
  ) => {
    const res = await apiClient.patch(
      `/api/repositories/${repositoryId}/sync/schedule`,
      payload
    );
    return res.data;
  },

  runDueSyncs: async () => {
    const res = await apiClient.post("/api/repositories/sync/run-due");
    return res.data;
  },

  cleanupSyncRecords: async () => {
    const res = await apiClient.post("/api/repositories/sync/cleanup");
    return res.data;
  },

  getSchedulerSettings: async () => {
    const res = await apiClient.get("/api/repositories/sync/scheduler/settings");
    return res.data;
  },

  updateSchedulerSettings: async (payload: {
    mode: "embedded" | "external" | "disabled";
    interval_minutes: number;
    timezone: string;
  }) => {
    const res = await apiClient.patch(
      "/api/repositories/sync/scheduler/settings",
      payload
    );
    return res.data;
  },

  getChunkingSettings: async () => {
    const res = await apiClient.get("/api/repositories/chunking/settings");
    return res.data;
  },

  updateChunkingSettings: async (payload: {
    max_chars: number;
    overlap_chars: number;
  }) => {
    const res = await apiClient.patch("/api/repositories/chunking/settings", payload);
    return res.data;
  },

  retryReadyFailures: async (repositoryId: string) => {
    const res = await apiClient.post(
      `/api/repositories/${repositoryId}/sync/retry-ready`
    );
    return res.data;
  },
};
