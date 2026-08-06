"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  FormControlLabel,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import ReplayIcon from "@mui/icons-material/Replay";
import SyncIcon from "@mui/icons-material/Sync";

import { repositorySyncApi } from "@/services/repositorySyncApi";


type RepositoryLike = {
  repository_id: string;
  repository_name: string;
  source_type: string;
};


const statusColor = (status?: string) => {
  if (status === "completed") return "success";
  if (status === "completed_with_errors") return "warning";
  if (status === "failed") return "error";
  if (status === "running") return "info";
  return "default";
};


export default function SyncStatusPanel({
  repository,
}: {
  repository: RepositoryLike | null;
}) {
  const [status, setStatus] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [failures, setFailures] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const [syncEnabled, setSyncEnabled] = useState(true);
  const [syncInterval, setSyncInterval] = useState("");

  const discoveryWarning =
    status?.sync_metadata?.discovery_warning?.message ||
    status?.sync_metadata?.warning?.message ||
    "";
  const warningMessage =
    status?.last_sync_status === "completed_with_errors"
      ? status?.last_sync_error || discoveryWarning
      : discoveryWarning;
  const errorMessage =
    status?.last_sync_status === "failed" ? status?.last_sync_error : "";

  const loadData = async () => {
    if (!repository?.repository_id) return;

    setLoading(true);
    setError("");

    try {
      const [statusRes, historyRes, failuresRes, healthRes] = await Promise.all([
        repositorySyncApi.getStatus(repository.repository_id),
        repositorySyncApi.getHistory(repository.repository_id),
        repositorySyncApi.getFailures(repository.repository_id),
        repositorySyncApi.getHealth(repository.repository_id),
      ]);

      setStatus(statusRes);
      setHealth(healthRes);
      setSyncEnabled(Boolean(statusRes.sync_enabled));
      setSyncInterval(statusRes.sync_interval_minutes || "");
      setHistory(historyRes);
      setFailures(failuresRes);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load sync data");
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    if (!repository?.repository_id) return;

    setSyncing(true);
    setError("");

    try {
      await repositorySyncApi.syncRepository(repository.repository_id);
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const handleTestConnection = async () => {
    if (!repository?.repository_id) return;

    setSyncing(true);
    setError("");

    try {
      const result = await repositorySyncApi.testConnector(repository.repository_id);

      if (!result.ok) {
        setError(result.message || "Connection test failed");
        return;
      }

      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Connection test failed");
    } finally {
      setSyncing(false);
    }
  };

  const handleRetry = async (failureId: string) => {
    if (!repository?.repository_id) return;

    setSyncing(true);
    setError("");

    try {
      await repositorySyncApi.retryFailure(repository.repository_id, failureId);
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Retry failed");
    } finally {
      setSyncing(false);
    }
  };

  const handleSaveSchedule = async () => {
    if (!repository?.repository_id) return;

    setSyncing(true);
    setError("");

    try {
      await repositorySyncApi.updateSchedule(repository.repository_id, {
        sync_enabled: syncEnabled,
        sync_interval_minutes: syncInterval ? Number(syncInterval) : null,
      });

      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to save schedule");
    } finally {
      setSyncing(false);
    }
  };

  const handleRetryReady = async () => {
    if (!repository?.repository_id) return;

    setSyncing(true);
    setError("");

    try {
      await repositorySyncApi.retryReadyFailures(repository.repository_id);
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Retry-ready processing failed");
    } finally {
      setSyncing(false);
    }
  };

  const handleResetSharePointDelta = async () => {
    if (!repository?.repository_id) return;

    setSyncing(true);
    setError("");

    try {
      await repositorySyncApi.resetSharePointDelta(repository.repository_id);
      await loadData();
    } catch (err: any) {
      setError(
        err?.response?.data?.detail || "Failed to reset SharePoint delta cursor"
      );
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [repository?.repository_id]);

  if (!repository) {
    return (
      <Alert severity="info">
        Select a repository to view sync status.
      </Alert>
    );
  }

  return (
    <Paper
      elevation={0}
      sx={{
        p: 3,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Stack spacing={2}>
        <Stack
          direction="row"
          sx={{ justifyContent: "space-between", alignItems: "center" }}
        >
          <Box>
            <Typography variant="h6" fontWeight={800}>
              Connector Sync Status
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {repository.repository_name} · {repository.source_type}
            </Typography>
          </Box>

          <Stack direction="row" spacing={1}>
            {repository?.source_type === "sharepoint" && (
              <Button
                variant="outlined"
                color="warning"
                onClick={handleResetSharePointDelta}
                disabled={syncing}
              >
                Reset Delta Cursor
              </Button>
            )}
            <Button
              variant="outlined"
              onClick={handleTestConnection}
              disabled={syncing}
            >
              Test Connection
            </Button>
            <Button
              variant="contained"
              startIcon={syncing ? <CircularProgress size={16} /> : <SyncIcon />}
              disabled={syncing}
              onClick={handleSync}
            >
              Run Sync
            </Button>
          </Stack>
        </Stack>

        {error && <Alert severity="error">{error}</Alert>}

        {loading ? (
          <CircularProgress size={24} />
        ) : (
          <>
            <Alert severity={health?.healthy ? "success" : "warning"}>
              Connector Health: {health?.healthy ? "Healthy" : "Needs Attention"}
            </Alert>

            <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap" }}>
              <Chip
                label={status?.last_sync_status || "Never synced"}
                color={statusColor(status?.last_sync_status)}
              />
              {repository?.source_type === "sharepoint" && (
                <Chip
                  label={
                    status?.sync_metadata?.sharepoint_delta_initialized
                      ? "Delta sync active"
                      : "Delta not initialized"
                  }
                  color={
                    status?.sync_metadata?.sharepoint_delta_initialized
                      ? "success"
                      : "warning"
                  }
                />
              )}
              <Chip
                label={`Last started: ${
                  status?.last_sync_started_at
                    ? new Date(status.last_sync_started_at).toLocaleString()
                    : "N/A"
                }`}
              />
              <Chip
                label={`Last completed: ${
                  status?.last_sync_completed_at
                    ? new Date(status.last_sync_completed_at).toLocaleString()
                    : "N/A"
                }`}
              />
            </Stack>

            {errorMessage && (
              <Alert severity="error">{errorMessage}</Alert>
            )}

            {warningMessage && (
              <Alert severity="warning">{warningMessage}</Alert>
            )}

            <Divider />

            <Typography variant="subtitle1" fontWeight={800}>
              Scheduled Sync Readiness
            </Typography>

            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={2}
              sx={{ alignItems: "center" }}
            >
              <FormControlLabel
                control={
                  <Switch
                    checked={syncEnabled}
                    onChange={(e) => setSyncEnabled(e.target.checked)}
                  />
                }
                label="Enable scheduled sync"
              />

              <TextField
                size="small"
                type="number"
                label="Interval minutes"
                value={syncInterval}
                onChange={(e) => setSyncInterval(e.target.value)}
                sx={{ width: 180 }}
              />

              <Button
                variant="outlined"
                onClick={handleSaveSchedule}
                disabled={syncing}
              >
                Save Schedule
              </Button>

              <Button
                variant="outlined"
                color="warning"
                startIcon={<ReplayIcon />}
                onClick={handleRetryReady}
                disabled={syncing}
              >
                Retry Ready Failures
              </Button>
            </Stack>

            <Divider />

            <Typography variant="subtitle1" fontWeight={800}>
              Sync History
            </Typography>

            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Status</TableCell>
                  <TableCell>Started</TableCell>
                  <TableCell>Processed</TableCell>
                  <TableCell>Skipped</TableCell>
                  <TableCell>Failed</TableCell>
                  <TableCell>Deleted</TableCell>
                  <TableCell>Chunks</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {history.map((run) => (
                  <TableRow key={run.id}>
                    <TableCell>
                      <Chip
                        size="small"
                        label={run.sync_status}
                        color={statusColor(run.sync_status)}
                      />
                    </TableCell>
                    <TableCell>
                      {run.sync_started_at
                        ? new Date(run.sync_started_at).toLocaleString()
                        : "N/A"}
                    </TableCell>
                    <TableCell>{run.files_processed}</TableCell>
                    <TableCell>{run.files_skipped}</TableCell>
                    <TableCell>{run.files_failed}</TableCell>
                    <TableCell>{run.files_deleted}</TableCell>
                    <TableCell>{run.chunks_created}</TableCell>
                  </TableRow>
                ))}

                {!history.length && (
                  <TableRow>
                    <TableCell colSpan={7}>
                      <Typography color="text.secondary">
                        No sync history yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>

            <Divider />

            <Typography variant="subtitle1" fontWeight={800}>
              Failed Files
            </Typography>

            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>File</TableCell>
                  <TableCell>Stage</TableCell>
                  <TableCell>Error</TableCell>
                  <TableCell>Retries</TableCell>
                  <TableCell align="right">Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {failures.map((failure) => (
                  <TableRow key={failure.id}>
                    <TableCell>
                      <Typography fontWeight={700}>
                        {failure.file_name || "Unknown file"}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {failure.file_path}
                      </Typography>
                    </TableCell>
                    <TableCell>{failure.failure_stage}</TableCell>
                    <TableCell>
                      <Typography variant="caption">
                        {failure.error_message}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {failure.retry_count}/{failure.max_retries}
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        startIcon={<ReplayIcon />}
                        onClick={() => handleRetry(failure.id)}
                        disabled={syncing || failure.retry_count >= failure.max_retries}
                      >
                        Retry
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}

                {!failures.length && (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography color="text.secondary">
                        No unresolved failed files.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </>
        )}
      </Stack>
    </Paper>
  );
}
