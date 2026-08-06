"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import { getAuditLogs } from "@/services/auditService";

const categories = ["ALL", "AUTH", "ADMIN", "REPOSITORY", "DOCUMENT", "AI"];

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [category, setCategory] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  async function loadLogs() {
    setLoading(true);

    const result = await getAuditLogs({
      event_category: category === "ALL" ? undefined : category,
      limit: 200,
    });

    if (result.success) {
      setLogs(result.data);
      setMessage(result.message || "");
    }

    setLoading(false);
  }

  useEffect(() => {
    loadLogs();
  }, [category]);

  if (loading) {
    return (
      <ModuleGuard moduleName="settings" permission="admin:settings">
        <Box sx={{ p: 4, display: "flex", alignItems: "center", gap: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading audit logs...</Typography>
        </Box>
      </ModuleGuard>
    );
  }

  return (
    <ModuleGuard moduleName="settings" permission="admin:settings">
      <OutletPage title="Audit Logs">
        <Box sx={{ mb: 3 }}>
          <Typography color="text.secondary">
            Governance trail for authentication, repositories, documents and AI usage.
          </Typography>
        </Box>

        {message && (
          <Alert severity="info" sx={{ mb: 3 }}>
            {message}
          </Alert>
        )}

        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            mb: 3,
          }}
        >
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 4 }}>
              <FormControl fullWidth>
                <InputLabel>Category</InputLabel>
                <Select
                  label="Category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  {categories.map((item) => (
                    <MenuItem key={item} value={item}>
                      {item}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </Paper>

        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          {logs.length === 0 ? (
            <Typography color="text.secondary">
              No audit logs available yet.
            </Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell>Event</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>Resource</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.audit_id} hover>
                    <TableCell sx={{ whiteSpace: "nowrap" }}>
                      {log.created_at ? new Date(log.created_at).toLocaleString() : "-"}
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={log.event_category} />
                    </TableCell>
                    <TableCell>
                      <Typography sx={{ fontWeight: 700 }}>{log.event_type}</Typography>
                    </TableCell>
                    <TableCell>{log.description || "-"}</TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {log.resource_type || "-"}
                      </Typography>
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
          )}
        </Paper>
      </OutletPage>
    </ModuleGuard>
  );
}

