"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import { repositorySyncApi } from "@/services/repositorySyncApi";


const statusColor = (status?: string) => {
  if (status === "indexed") return "success";
  if (status === "updated") return "info";
  if (status === "new") return "primary";
  if (status === "unchanged") return "default";
  if (status === "failed") return "error";
  if (status === "deleted") return "warning";
  if (status === "skipped_duplicate") return "secondary";
  return "default";
};


export default function SyncLogsTable({
  repository,
}: {
  repository: { repository_id: string } | null;
}) {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadLogs = async () => {
    if (!repository?.repository_id) return;

    setLoading(true);
    setError("");

    try {
      const data = await repositorySyncApi.getSyncLogs(repository.repository_id);
      setLogs(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load sync logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [repository?.repository_id]);

  if (!repository) return null;

  return (
    <Paper
      elevation={0}
      sx={{
        p: 3,
        mt: 3,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Stack spacing={2}>
        <Box>
          <Typography variant="h6" fontWeight={800}>
            Connector File Sync Logs
          </Typography>
          <Typography variant="body2" color="text.secondary">
            File-level sync registry, versions, deletes, and indexing status.
          </Typography>
        </Box>

        {error && <Alert severity="error">{error}</Alert>}

        {loading ? (
          <CircularProgress size={24} />
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>File</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Version</TableCell>
                <TableCell>Deleted</TableCell>
                <TableCell>Modified</TableCell>
                <TableCell>Last Synced</TableCell>
                <TableCell>Retries</TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {logs.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>
                    <Typography fontWeight={700}>{row.file_name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {row.file_path}
                    </Typography>
                  </TableCell>

                  <TableCell>
                    <Chip
                      size="small"
                      label={row.sync_status}
                      color={statusColor(row.sync_status)}
                    />
                  </TableCell>

                  <TableCell>v{row.version_number}</TableCell>

                  <TableCell>
                    {row.is_deleted ? (
                      <Chip size="small" label="Deleted" color="warning" />
                    ) : (
                      <Chip size="small" label="Active" color="success" />
                    )}
                  </TableCell>

                  <TableCell>
                    {row.source_modified_at
                      ? new Date(row.source_modified_at).toLocaleString()
                      : "N/A"}
                  </TableCell>

                  <TableCell>
                    {row.last_synced_at
                      ? new Date(row.last_synced_at).toLocaleString()
                      : "N/A"}
                  </TableCell>

                  <TableCell>{row.retry_count}</TableCell>
                </TableRow>
              ))}

              {!logs.length && (
                <TableRow>
                  <TableCell colSpan={7}>
                    <Typography color="text.secondary">
                      No connector file logs yet.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </Stack>
    </Paper>
  );
}
