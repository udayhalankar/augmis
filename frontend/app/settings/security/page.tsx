"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  FormControlLabel,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import { useAuth } from "@/context/AuthContext";
import { getAuditLogs } from "@/services/auditService";
import { getMySessions, revokeSession } from "@/services/authService";

export default function SecuritySettingsPage() {
  const { user, changePassword, logoutAllSessions } = useAuth();
  const [sessions, setSessions] = useState<any[]>([]);
  const [authEvents, setAuthEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    confirmPassword: "",
    revoke_other_sessions: true,
  });

  async function loadSecurityData() {
    setLoading(true);
    try {
      const [sessionsResult, logsResult] = await Promise.all([
        getMySessions(),
        getAuditLogs({ event_category: "AUTH", limit: 20 }),
      ]);
      setSessions(sessionsResult.data || []);
      setAuthEvents(logsResult.data || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSecurityData();
  }, []);

  async function handleChangePassword(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (form.new_password !== form.confirmPassword) {
      setError("New password and confirm password must match.");
      return;
    }
    setSaving(true);
    try {
      await changePassword({
        current_password: form.current_password,
        new_password: form.new_password,
        revoke_other_sessions: form.revoke_other_sessions,
      });
      setMessage("Password changed successfully.");
      setForm({
        current_password: "",
        new_password: "",
        confirmPassword: "",
        revoke_other_sessions: true,
      });
      await loadSecurityData();
    } catch (changeError: any) {
      setError(
        changeError?.response?.data?.detail || "Unable to change password."
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleRevokeSession(sessionId: string) {
    setError("");
    setMessage("");
    try {
      await revokeSession(sessionId);
      setMessage("Session revoked successfully.");
      await loadSecurityData();
    } catch (sessionError: any) {
      setError(
        sessionError?.response?.data?.detail || "Unable to revoke session."
      );
    }
  }

  async function handleLogoutAllSessions() {
    setError("");
    setMessage("");
    setSaving(true);
    try {
      await logoutAllSessions();
    } catch (sessionError: any) {
      setError(
        sessionError?.response?.data?.detail || "Unable to log out all sessions."
      );
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <ModuleGuard moduleName="settings" permission="admin:settings">
        <Box sx={{ p: 4, display: "flex", alignItems: "center", gap: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading security settings...</Typography>
        </Box>
      </ModuleGuard>
    );
  }

  return (
    <ModuleGuard moduleName="settings" permission="admin:settings">
      <OutletPage
        title="Security Settings"
        actions={
          <Button variant="outlined" color="error" onClick={() => void handleLogoutAllSessions()}>
            Logout All Devices
          </Button>
        }
      >
        {message ? <Alert severity="success" sx={{ mb: 3 }}>{message}</Alert> : null}
        {error ? <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert> : null}

        <Grid container spacing={2.5}>
          <Grid size={{ xs: 12, lg: 4 }}>
            <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider", height: "100%" }}>
              <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                Profile Summary
              </Typography>
              <Stack spacing={1}>
                <Typography>
                  <strong>Name:</strong> {user?.name || "-"}
                </Typography>
                <Typography>
                  <strong>Email:</strong> {user?.email || "-"}
                </Typography>
                <Typography>
                  <strong>Role:</strong> {user?.role || "-"}
                </Typography>
                <Typography>
                  <strong>Tenant:</strong> {user?.tenant_name || "-"}
                </Typography>
              </Stack>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, lg: 8 }}>
            <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider", height: "100%" }}>
              <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                Session Posture
              </Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>
                Review remembered-device usage, revoke stale sessions, and enforce tenant password rotation from one place.
              </Typography>
              <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
                <Chip size="small" label={`${sessions.length} active session(s)`} />
                <Chip size="small" label={`${authEvents.length} recent auth events`} variant="outlined" />
              </Stack>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, lg: 5 }}>
            <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
              <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                Change Password
              </Typography>
              <Box component="form" onSubmit={handleChangePassword}>
                <TextField
                  fullWidth
                  type="password"
                  label="Current Password"
                  value={form.current_password}
                  onChange={(event) =>
                    setForm({ ...form, current_password: event.target.value })
                  }
                  sx={{ mb: 2 }}
                />
                <TextField
                  fullWidth
                  type="password"
                  label="New Password"
                  value={form.new_password}
                  onChange={(event) =>
                    setForm({ ...form, new_password: event.target.value })
                  }
                  sx={{ mb: 2 }}
                />
                <TextField
                  fullWidth
                  type="password"
                  label="Confirm New Password"
                  value={form.confirmPassword}
                  onChange={(event) =>
                    setForm({ ...form, confirmPassword: event.target.value })
                  }
                  sx={{ mb: 2 }}
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={form.revoke_other_sessions}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          revoke_other_sessions: event.target.checked,
                        })
                      }
                    />
                  }
                  label="Revoke other active sessions after password change"
                  sx={{ mb: 2 }}
                />
                <Button fullWidth type="submit" variant="contained" disabled={saving}>
                  {saving ? <CircularProgress size={22} /> : "Update Password"}
                </Button>
              </Box>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, lg: 7 }}>
            <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider", height: "100%" }}>
              <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                Active Sessions
              </Typography>
              {sessions.length === 0 ? (
                <Typography color="text.secondary">No active sessions found.</Typography>
              ) : (
                <Stack spacing={1.25}>
                  {sessions.map((session) => (
                    <Paper
                      key={session.session_id}
                      elevation={0}
                      sx={{
                        p: 2,
                        borderRadius: 2,
                        border: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Stack
                        direction={{ xs: "column", md: "row" }}
                        spacing={1.5}
                        sx={{ justifyContent: "space-between" }}
                      >
                        <Box>
                          <Typography sx={{ fontWeight: 700 }}>
                            {session.user_agent || "Unknown device"}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {session.ip_address || "Unknown IP"} • Last seen{" "}
                            {session.last_seen_at
                              ? new Date(session.last_seen_at).toLocaleString()
                              : "-"}
                          </Typography>
                          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                            <Chip size="small" label={session.session_id} />
                            <Chip
                              size="small"
                              label={session.remember_me ? "Remembered" : "Standard"}
                              variant="outlined"
                            />
                          </Stack>
                        </Box>
                        <Box>
                          <Button
                            variant="outlined"
                            color="error"
                            onClick={() => void handleRevokeSession(session.session_id)}
                          >
                            Revoke
                          </Button>
                        </Box>
                      </Stack>
                    </Paper>
                  ))}
                </Stack>
              )}
            </Paper>
          </Grid>

          <Grid size={{ xs: 12 }}>
            <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
              <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                Recent Authentication Events
              </Typography>
              {authEvents.length === 0 ? (
                <Typography color="text.secondary">No authentication events available yet.</Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Time</TableCell>
                      <TableCell>Event</TableCell>
                      <TableCell>Description</TableCell>
                      <TableCell>Resource</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {authEvents.map((log) => (
                      <TableRow key={log.audit_id} hover>
                        <TableCell sx={{ whiteSpace: "nowrap" }}>
                          {log.created_at ? new Date(log.created_at).toLocaleString() : "-"}
                        </TableCell>
                        <TableCell>
                          <Chip size="small" label={log.event_type} />
                        </TableCell>
                        <TableCell>{log.description || "-"}</TableCell>
                        <TableCell>{log.resource_type || "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Paper>
          </Grid>
        </Grid>
      </OutletPage>
    </ModuleGuard>
  );
}

