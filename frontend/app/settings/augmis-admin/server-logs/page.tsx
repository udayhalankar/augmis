"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import ErrorOutlineOutlinedIcon from "@mui/icons-material/ErrorOutlineOutlined";

import AccessDenied from "@/components/auth/AccessDenied";
import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import { useAuth } from "@/context/AuthContext";
import { API_BASE_URL } from "@/services/apiBase";
import { getAuditLogs } from "@/services/auditService";
import {
  getServerLogs,
  getServerLogsExportUrl,
  markServerLogCritical,
  type ServerLogEntry,
} from "@/services/platformService";

type AuditLogEntry = {
  audit_id: string;
  created_at?: string | null;
  request_id?: string | null;
  event_category?: string | null;
  event_type?: string | null;
  description?: string | null;
  resource_type?: string | null;
  resource_id?: string | null;
};

type LogFilterState = {
  q: string;
  level: string;
  route: string;
  user: string;
  repository_id: string;
  business_area: string;
  request_id: string;
  start_at: string;
  end_at: string;
  critical_only: boolean;
};

const defaultFilters: LogFilterState = {
  q: "",
  level: "",
  route: "",
  user: "",
  repository_id: "",
  business_area: "",
  request_id: "",
  start_at: "",
  end_at: "",
  critical_only: false,
};

const auditCategories = ["", "AUTH", "ADMIN", "REPOSITORY", "DOCUMENT", "AI", "SETTINGS"];

function toDateTimeLocalValue(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

function downloadBlob(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function getLogErrorMessage(error: unknown) {
  if (typeof error === "object" && error !== null) {
    const candidate = error as {
      message?: string;
      response?: { data?: { detail?: string } };
    };
    return candidate.response?.data?.detail || candidate.message || "Failed to load logs.";
  }
  return "Failed to load logs.";
}

function LogTable({
  logs,
  onToggleCritical,
}: {
  logs: ServerLogEntry[];
  onToggleCritical: (log: ServerLogEntry) => Promise<void>;
}) {
  if (logs.length === 0) {
    return <Typography color="text.secondary">No log entries available for the current filters.</Typography>;
  }

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Time</TableCell>
          <TableCell>Level</TableCell>
          <TableCell>Message</TableCell>
          <TableCell>Correlation</TableCell>
          <TableCell>Context</TableCell>
          <TableCell align="right">Actions</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {logs.map((log) => (
          <TableRow key={log.log_id} hover>
            <TableCell sx={{ whiteSpace: "nowrap", verticalAlign: "top" }}>
              {log.occurred_at ? new Date(log.occurred_at).toLocaleString() : "-"}
            </TableCell>
            <TableCell sx={{ verticalAlign: "top" }}>
              <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                <Chip
                  size="small"
                  label={log.level}
                  color={
                    log.level === "ERROR"
                      ? "error"
                      : log.level === "WARNING"
                        ? "warning"
                        : "default"
                  }
                />
                {log.is_critical && (
                  <Chip
                    size="small"
                    color="error"
                    icon={<ErrorOutlineOutlinedIcon />}
                    label="Critical"
                  />
                )}
              </Stack>
            </TableCell>
            <TableCell sx={{ minWidth: 360, verticalAlign: "top" }}>
              <Typography sx={{ fontWeight: 700 }}>{log.message}</Typography>
              {log.exception && (
                <Typography
                  variant="caption"
                  color="error.main"
                  sx={{ display: "block", mt: 1, whiteSpace: "pre-wrap", wordBreak: "break-word" }}
                >
                  {log.exception}
                </Typography>
              )}
              {log.stack && (
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block", mt: 1, whiteSpace: "pre-wrap", wordBreak: "break-word" }}
                >
                  {log.stack}
                </Typography>
              )}
            </TableCell>
            <TableCell sx={{ verticalAlign: "top" }}>
              <Stack spacing={0.75}>
                <Typography variant="body2">
                  <strong>Request ID:</strong> {log.request_id || "-"}
                </Typography>
                <Typography variant="body2">
                  <strong>User:</strong> {log.user_email || log.user_id || "-"}
                </Typography>
                <Typography variant="body2">
                  <strong>Status:</strong> {log.status_code ?? "-"}
                </Typography>
              </Stack>
            </TableCell>
            <TableCell sx={{ verticalAlign: "top" }}>
              <Stack spacing={0.75}>
                <Typography variant="body2">
                  <strong>Route:</strong> {log.route || "-"}
                </Typography>
                <Typography variant="body2">
                  <strong>Repo:</strong> {log.repository_id || "-"}
                </Typography>
                <Typography variant="body2">
                  <strong>Business Area:</strong> {log.business_area || "-"}
                </Typography>
                <Typography variant="body2">
                  <strong>Component:</strong> {log.component || log.logger || "-"}
                </Typography>
              </Stack>
            </TableCell>
            <TableCell align="right" sx={{ verticalAlign: "top" }}>
              <Button size="small" onClick={() => void onToggleCritical(log)}>
                {log.is_critical ? "Unmark Critical" : "Mark Critical"}
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export default function ServerLogsPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [auditMessage, setAuditMessage] = useState("");
  const [filters, setFilters] = useState<LogFilterState>(defaultFilters);
  const [appliedFilters, setAppliedFilters] = useState<LogFilterState>(defaultFilters);
  const [auditCategory, setAuditCategory] = useState("");
  const [auditRequestId, setAuditRequestId] = useState("");
  const [backendLogs, setBackendLogs] = useState<ServerLogEntry[]>([]);
  const [frontendLogs, setFrontendLogs] = useState<ServerLogEntry[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);

  async function loadData(
    nextFilters = appliedFilters,
    nextAuditFilters?: { category?: string; requestId?: string }
  ) {
    setErrorMessage("");
    try {
      const [backendResult, frontendResult, auditResult] = await Promise.all([
        getServerLogs({
          source: "backend",
          ...nextFilters,
          limit: 250,
        }),
        getServerLogs({
          source: "frontend",
          ...nextFilters,
          limit: 250,
        }),
        getAuditLogs({
          event_category: (nextAuditFilters?.category ?? auditCategory) || undefined,
          request_id: (nextAuditFilters?.requestId ?? auditRequestId) || undefined,
          limit: 200,
        }),
      ]);

      if (backendResult.success) {
        setBackendLogs(backendResult.data);
      }
      if (frontendResult.success) {
        setFrontendLogs(frontendResult.data);
      }
      if (auditResult.success) {
        setAuditLogs(auditResult.data || []);
        setAuditMessage(auditResult.message || "");
      }
    } catch (error: unknown) {
      setErrorMessage(getLogErrorMessage(error));
    }
  }

  useEffect(() => {
    let mounted = true;

    async function run() {
      setLoading(true);
      await loadData(defaultFilters);
      if (mounted) {
        setLoading(false);
      }
    }

    void run();
    return () => {
      mounted = false;
    };
  }, []);

  const activeLogs = useMemo(() => {
    if (activeTab === 0) {
      return backendLogs;
    }
    if (activeTab === 1) {
      return frontendLogs;
    }
    return [];
  }, [activeTab, backendLogs, frontendLogs]);

  async function exportCsv() {
    const token = window.localStorage.getItem("infomentica_token");
    if (!token) {
      return;
    }
    const source = activeTab === 0 ? "backend" : activeTab === 1 ? "frontend" : undefined;
    const response = await fetch(
      `${API_BASE_URL}${getServerLogsExportUrl({
        source,
        ...appliedFilters,
        limit: 1000,
      })}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    const content = await response.text();
    downloadBlob(
      `augmis-${source || "server"}-logs.csv`,
      content,
      "text/csv;charset=utf-8"
    );
  }

  function exportJson() {
    const rows = activeTab === 2 ? auditLogs : activeLogs;
    downloadBlob(
      `augmis-${activeTab === 0 ? "backend" : activeTab === 1 ? "frontend" : "audit"}-logs.json`,
      JSON.stringify(rows, null, 2),
      "application/json;charset=utf-8"
    );
  }

  async function toggleCritical(log: ServerLogEntry) {
    const result = await markServerLogCritical(log.log_id, !log.is_critical);
    if (!result.success) {
      return;
    }
    await loadData(appliedFilters);
  }

  if (loading) {
    return (
      <ModuleGuard moduleName="settings" permission="admin:settings">
        <Box sx={{ p: 4, display: "flex", alignItems: "center", gap: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading server logs...</Typography>
        </Box>
      </ModuleGuard>
    );
  }

  return (
    <ModuleGuard moduleName="settings" permission="admin:settings">
      {user?.role !== "SUPER_ADMIN" ? (
        <AccessDenied />
      ) : (
        <OutletPage
          title="Server Logs"
          actions={
            <Stack direction="row" spacing={1}>
              <Button
                variant="outlined"
                startIcon={<DownloadOutlinedIcon />}
                onClick={() => void exportCsv()}
                disabled={activeTab === 2}
              >
                Export CSV
              </Button>
              <Button variant="outlined" startIcon={<DownloadOutlinedIcon />} onClick={exportJson}>
                Export JSON
              </Button>
              <Button
                variant="contained"
                startIcon={<RefreshOutlinedIcon />}
                onClick={async () => {
                  setRefreshing(true);
                  await loadData(appliedFilters);
                  setRefreshing(false);
                }}
                disabled={refreshing}
              >
                {refreshing ? "Refreshing..." : "Refresh"}
              </Button>
            </Stack>
          }
        >
          <Stack spacing={3}>
            <Alert severity="info">
              Runtime app logs now persist in the database with a 30-day retention window, request IDs,
              route/user/repository filters, and critical incident marking. Audit logs remain DB-backed as
              before.
            </Alert>

            {errorMessage && <Alert severity="error">{errorMessage}</Alert>}
            {auditMessage && activeTab === 2 && <Alert severity="info">{auditMessage}</Alert>}

            <Paper
              elevation={0}
              sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}
            >
              <Tabs value={activeTab} onChange={(_, value) => setActiveTab(value)} sx={{ mb: 2 }}>
                <Tab label={`Backend App Logs (${backendLogs.length})`} />
                <Tab label={`Frontend Errors (${frontendLogs.length})`} />
                <Tab label={`Audit Logs (${auditLogs.length})`} />
              </Tabs>

              {activeTab !== 2 ? (
                <Stack spacing={2} sx={{ mb: 3 }}>
                  <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                    <TextField
                      label="Search"
                      value={filters.q}
                      onChange={(event) => setFilters((prev) => ({ ...prev, q: event.target.value }))}
                      fullWidth
                    />
                    <TextField
                      label="Level"
                      value={filters.level}
                      onChange={(event) => setFilters((prev) => ({ ...prev, level: event.target.value.toUpperCase() }))}
                    />
                    <TextField
                      label="Route"
                      value={filters.route}
                      onChange={(event) => setFilters((prev) => ({ ...prev, route: event.target.value }))}
                    />
                    <TextField
                      label="User"
                      value={filters.user}
                      onChange={(event) => setFilters((prev) => ({ ...prev, user: event.target.value }))}
                    />
                  </Stack>

                  <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                    <TextField
                      label="Repository ID"
                      value={filters.repository_id}
                      onChange={(event) =>
                        setFilters((prev) => ({ ...prev, repository_id: event.target.value }))
                      }
                    />
                    <TextField
                      label="Business Area"
                      value={filters.business_area}
                      onChange={(event) =>
                        setFilters((prev) => ({ ...prev, business_area: event.target.value }))
                      }
                    />
                    <TextField
                      label="Request ID"
                      value={filters.request_id}
                      onChange={(event) =>
                        setFilters((prev) => ({ ...prev, request_id: event.target.value }))
                      }
                    />
                    <TextField
                      type="datetime-local"
                      label="From"
                      value={filters.start_at}
                      onChange={(event) => setFilters((prev) => ({ ...prev, start_at: event.target.value }))}
                      InputLabelProps={{ shrink: true }}
                    />
                    <TextField
                      type="datetime-local"
                      label="To"
                      value={filters.end_at}
                      onChange={(event) => setFilters((prev) => ({ ...prev, end_at: event.target.value }))}
                      InputLabelProps={{ shrink: true }}
                    />
                  </Stack>

                  <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ alignItems: { md: "center" } }}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={filters.critical_only}
                          onChange={(event) =>
                            setFilters((prev) => ({ ...prev, critical_only: event.target.checked }))
                          }
                        />
                      }
                      label="Critical only"
                    />
                    <Stack direction="row" spacing={1}>
                      <Button
                        variant="contained"
                        onClick={async () => {
                          setAppliedFilters(filters);
                          await loadData(filters);
                        }}
                      >
                        Apply Filters
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={async () => {
                          setFilters(defaultFilters);
                          setAppliedFilters(defaultFilters);
                          await loadData(defaultFilters);
                        }}
                      >
                        Reset
                      </Button>
                    </Stack>
                  </Stack>
                </Stack>
              ) : (
                <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 3 }}>
                  <TextField
                    select
                    label="Audit Category"
                    value={auditCategory}
                    onChange={(event) => setAuditCategory(event.target.value)}
                    sx={{ minWidth: 220 }}
                  >
                    {auditCategories.map((category) => (
                      <MenuItem key={category} value={category}>
                        {category || "ALL"}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    label="Request ID"
                    value={auditRequestId}
                    onChange={(event) => setAuditRequestId(event.target.value)}
                    sx={{ minWidth: 260 }}
                  />
                  <Stack direction="row" spacing={1}>
                    <Button
                      variant="contained"
                      onClick={async () => {
                        await loadData(appliedFilters, {
                          category: auditCategory,
                          requestId: auditRequestId,
                        });
                      }}
                    >
                      Apply Filters
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={async () => {
                        setAuditCategory("");
                        setAuditRequestId("");
                        await loadData(appliedFilters, {
                          category: "",
                          requestId: "",
                        });
                      }}
                    >
                      Reset
                    </Button>
                  </Stack>
                </Stack>
              )}

              <Box sx={{ overflowX: "auto" }}>
                {activeTab === 2 ? (
                  auditLogs.length === 0 ? (
                    <Typography color="text.secondary">No audit logs available for the current filters.</Typography>
                  ) : (
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Time</TableCell>
                          <TableCell>Category</TableCell>
                          <TableCell>Event</TableCell>
                          <TableCell>Request ID</TableCell>
                          <TableCell>Description</TableCell>
                          <TableCell>Resource</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {auditLogs.map((log) => (
                          <TableRow key={log.audit_id} hover>
                            <TableCell sx={{ whiteSpace: "nowrap", verticalAlign: "top" }}>
                              {log.created_at ? new Date(log.created_at).toLocaleString() : "-"}
                            </TableCell>
                            <TableCell sx={{ verticalAlign: "top" }}>
                              <Chip size="small" label={log.event_category || "-"} />
                            </TableCell>
                            <TableCell sx={{ verticalAlign: "top" }}>
                              <Typography sx={{ fontWeight: 700 }}>{log.event_type || "-"}</Typography>
                            </TableCell>
                            <TableCell sx={{ verticalAlign: "top" }}>{log.request_id || "-"}</TableCell>
                            <TableCell sx={{ verticalAlign: "top" }}>{log.description || "-"}</TableCell>
                            <TableCell sx={{ verticalAlign: "top" }}>
                              <Typography variant="body2">{log.resource_type || "-"}</Typography>
                              {log.resource_id && (
                                <Typography variant="caption" color="text.secondary">
                                  {log.resource_id}
                                </Typography>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )
                ) : (
                  <LogTable logs={activeLogs} onToggleCritical={toggleCritical} />
                )}
              </Box>
            </Paper>

            {(appliedFilters.start_at || appliedFilters.end_at) && activeTab !== 2 && (
              <Typography variant="caption" color="text.secondary">
                Active date range:
                {" "}
                {appliedFilters.start_at ? toDateTimeLocalValue(appliedFilters.start_at) : "Any"}
                {" "}to{" "}
                {appliedFilters.end_at ? toDateTimeLocalValue(appliedFilters.end_at) : "Any"}
              </Typography>
            )}
          </Stack>
        </OutletPage>
      )}
    </ModuleGuard>
  );
}

