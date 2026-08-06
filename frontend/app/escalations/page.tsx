"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  MenuItem,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import PendingActionsOutlinedIcon from "@mui/icons-material/PendingActionsOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import GppBadOutlinedIcon from "@mui/icons-material/GppBadOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import TimelapseOutlinedIcon from "@mui/icons-material/TimelapseOutlined";
import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import {
  WorkAreaChartCard,
  WorkAreaChartType,
  WorkAreaChartTypeSelector,
  WorkAreaFlexibleSeries,
  WorkAreaInsightsCard,
  WorkAreaMetricStrip,
  WorkAreaRegisterCard,
} from "@/components/work-area/WorkAreaIntelligence";
import { getEscalationDashboard } from "@/services/escalationService";

const severityColor: Record<string, "success" | "warning" | "error" | "default"> = {
  Low: "success",
  Medium: "warning",
  High: "error",
  Critical: "error",
};

const statusColor: Record<string, "success" | "warning" | "error" | "default"> = {
  Open: "warning",
  "In Review": "warning",
  Escalated: "error",
  Closed: "success",
};

export default function EscalationsPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [registerLoading, setRegisterLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusChartType, setStatusChartType] = useState<WorkAreaChartType>("bar");
  const [severityChartType, setSeverityChartType] = useState<WorkAreaChartType>("donut");
  const [sourceChartType, setSourceChartType] = useState<WorkAreaChartType>("bar");
  const [agingChartType, setAgingChartType] = useState<WorkAreaChartType>("bar");
  const [hotspotChartType, setHotspotChartType] = useState<WorkAreaChartType>("horizontalBar");
  const [ownerChartType, setOwnerChartType] = useState<WorkAreaChartType>("horizontalBar");
  const [registerSearch, setRegisterSearch] = useState("");
  const [agingFilter, setAgingFilter] = useState("all");
  const [departmentFilter, setDepartmentFilter] = useState("all");
  const [ownerFilter, setOwnerFilter] = useState("all");
  const [registerPage, setRegisterPage] = useState(0);
  const [activeBottomTab, setActiveBottomTab] = useState<"insights" | "register">("insights");

  useEffect(() => {
    let active = true;

    async function loadEscalationDashboard() {
      setLoading(true);
      setRegisterLoading(true);

      try {
        const summaryResponse = await getEscalationDashboard({ includeRecords: false });
        if (!active) return;

        setData(summaryResponse);
        setError(null);
        setLoading(false);

        const detailResponse = await getEscalationDashboard({ includeRecords: true });
        if (!active) return;

        const detailPayload = detailResponse;
        setData((current: any) => ({
          ...(current || detailPayload),
          data: {
            ...((current && current.data) || detailPayload.data || {}),
            ...(detailPayload.data || {}),
          },
        }));
      } catch (err: any) {
        if (!active) return;
        setError(
          err?.response?.data?.detail ||
            err?.message ||
            "Unable to load escalation dashboard."
        );
      } finally {
        if (active) {
          setLoading(false);
          setRegisterLoading(false);
        }
      }
    }

    void loadEscalationDashboard();

    return () => {
      active = false;
    };
  }, []);

  const safeData = data?.data ?? data ?? {
    kpis: {
      total_escalations: 0,
      active_escalations: 0,
      critical: 0,
      sla_breached: 0,
      overdue: 0,
      avg_aging: 0,
    },
    status_distribution: [],
    severity_distribution: [],
    source_distribution: [],
    aging_analysis: [],
    department_hotspots: [],
    owner_load: [],
    impact_by_department: [],
    sla_breach_by_department: [],
    insights: [],
    escalations: [],
  };

  const kpis = safeData.kpis;
  const registerCount = safeData.register_count ?? safeData.escalations.length;
  const departmentOptions = useMemo<string[]>(
    () => {
      const values = safeData.escalations
        .map((item: any) => item.department)
        .filter((value: any): value is string => Boolean(value));
      return [...new Set<string>(values)].sort();
    },
    [safeData.escalations]
  );
  const ownerOptions = useMemo<string[]>(
    () => {
      const values = safeData.escalations
        .map((item: any) => item.owner)
        .filter((value: any): value is string => Boolean(value));
      return [...new Set<string>(values)].sort();
    },
    [safeData.escalations]
  );
  const filteredEscalations = useMemo(() => {
    const query = registerSearch.trim().toLowerCase();
    return safeData.escalations.filter((item: any) => {
      const matchesSearch =
        !query ||
        [
          item.escalation_id,
          item.source_module,
          item.source_id,
          item.title,
          item.escalation_reason,
          item.description,
          item.department,
          item.owner,
          item.status,
          item.severity,
        ]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(query));

      const agingDays = Number(item.aging_days ?? 0);
      const matchesAging =
        agingFilter === "all" ||
        (agingFilter === "0-5" && agingDays >= 0 && agingDays <= 5) ||
        (agingFilter === "6-10" && agingDays >= 6 && agingDays <= 10) ||
        (agingFilter === "11-20" && agingDays >= 11 && agingDays <= 20) ||
        (agingFilter === "21+" && agingDays >= 21);

      const matchesDepartment =
        departmentFilter === "all" || item.department === departmentFilter;
      const matchesOwner = ownerFilter === "all" || item.owner === ownerFilter;

      return matchesSearch && matchesAging && matchesDepartment && matchesOwner;
    });
  }, [agingFilter, departmentFilter, ownerFilter, registerSearch, safeData.escalations]);

  useEffect(() => {
    setRegisterPage(0);
  }, [agingFilter, departmentFilter, ownerFilter, registerSearch]);

  const registerPageSize = 5;
  const registerPageCount = Math.max(1, Math.ceil(filteredEscalations.length / registerPageSize));
  const safeRegisterPage = Math.min(registerPage, registerPageCount - 1);
  const registerStart = safeRegisterPage * registerPageSize;
  const pagedEscalations = filteredEscalations.slice(
    registerStart,
    registerStart + registerPageSize
  );

  if (loading) {
    return (
      <ModuleGuard moduleName="escalations" permission="escalation:read">
        <OutletPage title="Escalation Intelligence">
          <Box sx={{ p: 4, display: "flex", alignItems: "center", gap: 2 }}>
            <CircularProgress size={24} />
            <Typography>Loading Escalation Intelligence...</Typography>
          </Box>
        </OutletPage>
      </ModuleGuard>
    );
  }

  if (error) {
    return (
      <ModuleGuard moduleName="escalations" permission="escalation:read">
        <OutletPage title="Escalation Intelligence">
          <Alert severity="error">{error}</Alert>
        </OutletPage>
      </ModuleGuard>
    );
  }

  const escalationMetrics = [
    {
      title: "Total Escalations",
      value: kpis.total_escalations,
      subtitle: "Generated records",
      icon: <ReportProblemOutlinedIcon />,
      accent: "#2563eb",
    },
    {
      title: "Active",
      value: kpis.active_escalations,
      subtitle: "Open / Escalated",
      icon: <PendingActionsOutlinedIcon />,
      accent: "#14b8a6",
    },
    {
      title: "Critical",
      value: kpis.critical,
      subtitle: "Critical severity",
      icon: <WarningAmberOutlinedIcon />,
      accent: "#ef4444",
    },
    {
      title: "SLA Breached",
      value: kpis.sla_breached,
      subtitle: "Rule breached",
      icon: <GppBadOutlinedIcon />,
      accent: "#f59e0b",
    },
    {
      title: "Overdue",
      value: kpis.overdue,
      subtitle: "More than 20 days",
      icon: <ScheduleOutlinedIcon />,
      accent: "#8b5cf6",
    },
    {
      title: "Avg Aging",
      value: `${kpis.avg_aging}d`,
      subtitle: "Average age",
      icon: <TimelapseOutlinedIcon />,
      accent: "#0f766e",
    },
  ];

  return (
    <ModuleGuard moduleName="escalations" permission="escalation:read">
      <OutletPage
        title="Escalation Intelligence"
        actions={
          <Tabs
            value={activeBottomTab}
            onChange={(_, value) => setActiveBottomTab(value)}
            sx={{
              minHeight: 0,
              "& .MuiTab-root": {
                minHeight: 0,
                py: 0.75,
                px: 1.5,
                textTransform: "none",
              },
            }}
          >
            <Tab value="insights" label="AI Escalation Insights" />
            <Tab value="register" label="Escalation Register" />
          </Tabs>
        }
      >
        <WorkAreaMetricStrip metrics={escalationMetrics} />

        <Grid container spacing={2.5} sx={{ mt: 1 }}>
          <Grid size={{ xs: 12, md: 6 }}>
            <WorkAreaChartCard
              title="Escalation Status Distribution"
              subtitle="Current business escalation mix across open, review, escalated, and closed cases."
              actions={
                <WorkAreaChartTypeSelector value={statusChartType} onChange={setStatusChartType} />
              }
            >
              <WorkAreaFlexibleSeries
                data={safeData.status_distribution || []}
                type={statusChartType}
                color="#2563eb"
              />
            </WorkAreaChartCard>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <WorkAreaChartCard
              title="Severity Distribution"
              subtitle="Severity balance across low, medium, high, and critical escalations."
              actions={
                <WorkAreaChartTypeSelector value={severityChartType} onChange={setSeverityChartType} />
              }
            >
              <WorkAreaFlexibleSeries
                data={safeData.severity_distribution || []}
                type={severityChartType}
                color="#ef4444"
              />
            </WorkAreaChartCard>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <WorkAreaChartCard
              title="Source Module Distribution"
              subtitle="Where business escalation pressure is originating across configured business areas."
              actions={
                <WorkAreaChartTypeSelector value={sourceChartType} onChange={setSourceChartType} />
              }
            >
              <WorkAreaFlexibleSeries
                data={safeData.source_distribution || []}
                type={sourceChartType}
                color="#14b8a6"
              />
            </WorkAreaChartCard>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <WorkAreaChartCard
              title="Escalation Aging Analysis"
              subtitle="Delay bucket view showing where business cases are maturing into risk."
              actions={
                <WorkAreaChartTypeSelector value={agingChartType} onChange={setAgingChartType} />
              }
            >
              <WorkAreaFlexibleSeries
                data={safeData.aging_analysis || []}
                type={agingChartType}
                color="#f59e0b"
              />
            </WorkAreaChartCard>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <WorkAreaChartCard
              title="Department Hotspots"
              subtitle="Business areas currently generating the highest escalation concentration."
              actions={
                <WorkAreaChartTypeSelector value={hotspotChartType} onChange={setHotspotChartType} />
              }
            >
              <WorkAreaFlexibleSeries
                data={safeData.department_hotspots || []}
                type={hotspotChartType}
                color="#8b5cf6"
              />
            </WorkAreaChartCard>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <WorkAreaChartCard
              title="Owner Active Load"
              subtitle="Active escalation ownership load across responsible users and teams."
              actions={
                <WorkAreaChartTypeSelector value={ownerChartType} onChange={setOwnerChartType} />
              }
            >
              <WorkAreaFlexibleSeries
                data={safeData.owner_load || []}
                type={ownerChartType}
                color="#06b6d4"
              />
            </WorkAreaChartCard>
          </Grid>
        </Grid>

        {activeBottomTab === "insights" ? (
          <WorkAreaInsightsCard
            title="AI Escalation Insights"
            subtitle="Derived from business escalation mix, severity, source concentration, and aging pressure."
            insights={safeData.insights || []}
          />
        ) : (
          <WorkAreaRegisterCard
            title="Escalation Register"
            loadingText={registerLoading ? "Loading escalation register rows..." : undefined}
            footerNote={
              !registerLoading && safeData.escalations.length === 0 && registerCount > 0
                ? `${registerCount} escalation records are available, but register rows are still being prepared.`
                : null
            }
          >
            <Stack spacing={2}>
              <Box sx={{ display: "flex", gap: 1.25, flexWrap: "wrap", alignItems: "center" }}>
                <TextField
                  size="small"
                  placeholder="Search escalation register"
                  value={registerSearch}
                  onChange={(event) => setRegisterSearch(event.target.value)}
                  sx={{ minWidth: 240, flex: "1 1 240px" }}
                />
                <TextField
                  select
                  size="small"
                  label="Aging"
                  value={agingFilter}
                  onChange={(event) => setAgingFilter(event.target.value)}
                  sx={{ minWidth: 130 }}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="0-5">0-5 days</MenuItem>
                  <MenuItem value="6-10">6-10 days</MenuItem>
                  <MenuItem value="11-20">11-20 days</MenuItem>
                  <MenuItem value="21+">21+ days</MenuItem>
                </TextField>
                <TextField
                  select
                  size="small"
                  label="Department"
                  value={departmentFilter}
                  onChange={(event) => setDepartmentFilter(event.target.value)}
                  sx={{ minWidth: 160 }}
                >
                  <MenuItem value="all">All</MenuItem>
                  {departmentOptions.map((option: string) => (
                    <MenuItem key={option} value={option}>
                      {option}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  select
                  size="small"
                  label="Owner"
                  value={ownerFilter}
                  onChange={(event) => setOwnerFilter(event.target.value)}
                  sx={{ minWidth: 160 }}
                >
                  <MenuItem value="all">All</MenuItem>
                  {ownerOptions.map((option: string) => (
                    <MenuItem key={option} value={option}>
                      {option}
                    </MenuItem>
                  ))}
                </TextField>
              </Box>

              {pagedEscalations.length ? (
                <Stack spacing={1.5}>
                  {pagedEscalations.map((e: any) => (
                    <Paper
                      key={e.escalation_id}
                      variant="outlined"
                      sx={{ p: 2, borderRadius: 2.5, overflow: "hidden" }}
                    >
                      <Stack spacing={1}>
                        <Typography sx={{ fontWeight: 700 }}>
                          {e.title || e.escalation_id}
                        </Typography>

                        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                          <Chip size="small" label={e.status} color={statusColor[e.status] || "default"} />
                          <Chip size="small" label={e.severity} color={severityColor[e.severity] || "default"} />
                          <Chip
                            size="small"
                            label={e.sla_breached === "Yes" ? "SLA Breached" : "SLA OK"}
                            color={e.sla_breached === "Yes" ? "error" : "success"}
                          />
                        </Box>

                        <Typography variant="body2">
                          <strong>Escalation ID:</strong> {e.escalation_id}
                        </Typography>
                        <Typography variant="body2">
                          <strong>Source:</strong> {e.source_module} {e.source_id ? `• ${e.source_id}` : ""}
                        </Typography>
                        <Typography variant="body2">
                          <strong>Reason:</strong> {e.escalation_reason || e.description || "-"}
                        </Typography>
                        <Typography variant="body2">
                          <strong>Department:</strong> {e.department || "-"}
                        </Typography>
                        <Typography variant="body2">
                          <strong>Owner:</strong> {e.owner || "-"}
                        </Typography>
                        <Typography variant="body2">
                          <strong>Aging:</strong> {e.aging_days} days
                        </Typography>
                        <Typography variant="body2">
                          <strong>Impact:</strong> ₹{Number(e.estimated_impact || 0).toLocaleString()}
                        </Typography>
                      </Stack>
                    </Paper>
                  ))}
                </Stack>
              ) : (
                <Paper variant="outlined" sx={{ p: 3, borderRadius: 2.5 }}>
                  <Typography color="text.secondary">
                    No escalation records match the current search.
                  </Typography>
                </Paper>
              )}

              <Divider />

              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 2,
                  flexWrap: "wrap",
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  {filteredEscalations.length
                    ? `${registerStart + 1}-${Math.min(
                        registerStart + registerPageSize,
                        filteredEscalations.length
                      )} of ${filteredEscalations.length}`
                    : "0 of 0"}
                </Typography>

                <Stack direction="row" spacing={1}>
                  <Button
                    size="small"
                    variant="outlined"
                    disabled={safeRegisterPage === 0}
                    onClick={() => setRegisterPage((current) => Math.max(0, current - 1))}
                  >
                    Previous
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    disabled={safeRegisterPage >= registerPageCount - 1}
                    onClick={() =>
                      setRegisterPage((current) => Math.min(registerPageCount - 1, current + 1))
                    }
                  >
                    Next
                  </Button>
                </Stack>
              </Box>
            </Stack>
          </WorkAreaRegisterCard>
        )}
      </OutletPage>
    </ModuleGuard>
  );
}
