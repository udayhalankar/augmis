"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined";
import DnsOutlinedIcon from "@mui/icons-material/DnsOutlined";
import MonitorHeartOutlinedIcon from "@mui/icons-material/MonitorHeartOutlined";
import FolderSpecialOutlinedIcon from "@mui/icons-material/FolderSpecialOutlined";

import AccessDenied from "@/components/auth/AccessDenied";
import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import { useAuth } from "@/context/AuthContext";
import {
  getMigrationAgents,
  type MigrationAgentActivityRecord,
  type MigrationAgentRecord,
} from "@/services/agentService";

function MetricCard({
  title,
  value,
  subtitle,
  icon,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
}) {
  return (
    <Card sx={{ height: "100%", border: "1px solid", borderColor: "divider" }}>
      <CardContent>
        <Stack direction="row" sx={{ justifyContent: "space-between", gap: 2 }}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              {title}
            </Typography>
            <Typography variant="h5" sx={{ mt: 1, fontWeight: 800 }}>
              {value}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
              {subtitle}
            </Typography>
          </Box>
          <Box sx={{ color: "primary.main", "& svg": { fontSize: 28 } }}>{icon}</Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

function formatDate(value?: string | null) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export default function MigrationAgentsPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [agents, setAgents] = useState<MigrationAgentRecord[]>([]);
  const [activities, setActivities] = useState<MigrationAgentActivityRecord[]>([]);

  async function loadData() {
    setError("");
    const result = await getMigrationAgents(100);
    setAgents(result.data.agents);
    setActivities(result.data.activities);
  }

  useEffect(() => {
    let mounted = true;

    async function run() {
      setLoading(true);
      try {
        await loadData();
      } catch (err: any) {
        if (mounted) {
          setError(err?.response?.data?.detail || err?.message || "Unable to load migration agents.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void run();
    return () => {
      mounted = false;
    };
  }, []);

  const metrics = useMemo(() => {
    const activeAgents = agents.filter((agent) => agent.status === "running" || agent.status === "RUNNING");
    const recentActivities = activities.filter((activity) => activity.event_type === "file_change");
    const distinctRoots = new Set(agents.map((agent) => agent.root_path).filter(Boolean));
    return {
      totalAgents: agents.length,
      activeAgents: activeAgents.length,
      recentActivities: recentActivities.length,
      distinctRoots: distinctRoots.size,
    };
  }, [agents, activities]);

  if (loading) {
    return (
      <ModuleGuard moduleName="settings" permission="admin:settings">
        <Box sx={{ p: 4, display: "flex", alignItems: "center", gap: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading migration agents...</Typography>
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
          title="Migration Agents"
          actions={
            <Button
              variant="contained"
              startIcon={<RefreshOutlinedIcon />}
              onClick={async () => {
                setRefreshing(true);
                try {
                  await loadData();
                } catch (err: any) {
                  setError(err?.response?.data?.detail || err?.message || "Unable to refresh migration agents.");
                } finally {
                  setRefreshing(false);
                }
              }}
              disabled={refreshing}
            >
              {refreshing ? "Refreshing..." : "Refresh"}
            </Button>
          }
        >
          <Stack spacing={3}>
            <Alert severity="info">
              This view combines local migration-agent registrations, heartbeat posture, watched root paths, and recent synced file activity.
            </Alert>

            {error ? <Alert severity="error">{error}</Alert> : null}

            <Grid container spacing={2.5}>
              <Grid size={{ xs: 12, md: 3 }}>
                <MetricCard
                  title="Registered Agents"
                  value={String(metrics.totalAgents)}
                  subtitle="Machines known to the backend"
                  icon={<DnsOutlinedIcon />}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <MetricCard
                  title="Active Agents"
                  value={String(metrics.activeAgents)}
                  subtitle="Agents reporting a running state"
                  icon={<MonitorHeartOutlinedIcon />}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <MetricCard
                  title="Recent File Events"
                  value={String(metrics.recentActivities)}
                  subtitle="Recent create/modify/delete events"
                  icon={<FolderSpecialOutlinedIcon />}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <MetricCard
                  title="Watched Roots"
                  value={String(metrics.distinctRoots)}
                  subtitle="Distinct local root paths"
                  icon={<DnsOutlinedIcon />}
                />
              </Grid>
            </Grid>

            <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 800 }}>
                Agents
              </Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Status</TableCell>
                      <TableCell>Agent</TableCell>
                      <TableCell>Machine</TableCell>
                      <TableCell>Root Path</TableCell>
                      <TableCell>Last Heartbeat</TableCell>
                      <TableCell>Last Sync</TableCell>
                      <TableCell>Pending</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {agents.map((agent) => (
                      <TableRow key={agent.agent_id} hover>
                        <TableCell>
                          <Chip
                            size="small"
                            label={agent.status}
                            color={
                              String(agent.status).toLowerCase().includes("run")
                                ? "success"
                                : String(agent.status).toLowerCase().includes("fail")
                                  ? "error"
                                  : "default"
                            }
                          />
                        </TableCell>
                        <TableCell>
                          <Typography sx={{ fontWeight: 700 }}>{agent.agent_id}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            Tenant: {agent.tenant_id || "-"}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography>{agent.machine_name || agent.hostname || "-"}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {agent.platform || agent.version}
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ maxWidth: 320 }}>
                          <Typography sx={{ wordBreak: "break-word" }}>{agent.root_path}</Typography>
                        </TableCell>
                        <TableCell>{formatDate(agent.last_seen_at)}</TableCell>
                        <TableCell>{formatDate(agent.last_sync_at)}</TableCell>
                        <TableCell>{agent.pending_change_count ?? 0}</TableCell>
                      </TableRow>
                    ))}
                    {agents.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7}>
                          <Typography color="text.secondary">No migration agents have reported yet.</Typography>
                        </TableCell>
                      </TableRow>
                    ) : null}
                  </TableBody>
                </Table>
              </Box>
            </Paper>

            <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 800 }}>
                Recent Activity
              </Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Time</TableCell>
                      <TableCell>Event</TableCell>
                      <TableCell>Agent</TableCell>
                      <TableCell>File</TableCell>
                      <TableCell>Change</TableCell>
                      <TableCell>Details</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {activities.map((activity) => (
                      <TableRow key={activity.activity_id} hover>
                        <TableCell sx={{ whiteSpace: "nowrap" }}>{formatDate(activity.occurred_at)}</TableCell>
                        <TableCell>
                          <Chip size="small" label={activity.event_type} variant="outlined" />
                        </TableCell>
                        <TableCell sx={{ maxWidth: 220 }}>
                          <Typography sx={{ wordBreak: "break-word" }}>{activity.agent_id}</Typography>
                        </TableCell>
                        <TableCell sx={{ maxWidth: 320 }}>
                          <Typography sx={{ wordBreak: "break-word" }}>
                            {activity.file_name || activity.file_path || activity.root_path || "-"}
                          </Typography>
                        </TableCell>
                        <TableCell>{activity.change_type || "-"}</TableCell>
                        <TableCell>
                          {activity.item_count != null ? `count=${activity.item_count}` : "-"}
                        </TableCell>
                      </TableRow>
                    ))}
                    {activities.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6}>
                          <Typography color="text.secondary">No recent migration-agent activity available.</Typography>
                        </TableCell>
                      </TableRow>
                    ) : null}
                  </TableBody>
                </Table>
              </Box>
            </Paper>
          </Stack>
        </OutletPage>
      )}
    </ModuleGuard>
  );
}

