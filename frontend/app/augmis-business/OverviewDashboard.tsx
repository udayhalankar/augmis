"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import ArrowForwardOutlinedIcon from "@mui/icons-material/ArrowForwardOutlined";
import AssignmentLateOutlinedIcon from "@mui/icons-material/AssignmentLateOutlined";
import BusinessCenterOutlinedIcon from "@mui/icons-material/BusinessCenterOutlined";
import ChecklistOutlinedIcon from "@mui/icons-material/ChecklistOutlined";
import CurrencyExchangeOutlinedIcon from "@mui/icons-material/CurrencyExchangeOutlined";
import DonutLargeOutlinedIcon from "@mui/icons-material/DonutLargeOutlined";
import EventAvailableOutlinedIcon from "@mui/icons-material/EventAvailableOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import SouthAmericaOutlinedIcon from "@mui/icons-material/SouthAmericaOutlined";
import TimelineOutlinedIcon from "@mui/icons-material/TimelineOutlined";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { OutletPage } from "@/components/layout/OutletPage";
import { parseApiValidationError } from "@/services/apiErrorParser";
import {
  type AugmisBusinessActivity,
  type AugmisBusinessDashboard,
  type AugmisBusinessLead,
  type AugmisBusinessOpportunity,
  type AugmisBusinessTask,
  getAugmisBusinessDashboard,
  getAugmisBusinessLead,
  listAugmisBusinessOpportunities,
  listAugmisBusinessTasks,
} from "@/services/augmisBusinessService";
import {
  TaskPriorityChip,
  TaskStatusChip,
  formatTaskDateTime,
  formatTaskLabel,
  getTaskTimingLabel,
} from "./components/BusinessTaskUI";

const KPI_CARD_STYLES = [
  "linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)",
  "linear-gradient(90deg, #DCFCE7 0%, #F0FDF4 100%)",
  "linear-gradient(90deg, #FEF3C7 0%, #FFFBEB 100%)",
  "linear-gradient(90deg, #FEE2E2 0%, #FFF1F2 100%)",
  "linear-gradient(90deg, #E0EAFF 0%, #F8FAFC 100%)",
  "linear-gradient(90deg, #D1FAE5 0%, #F0FDFA 100%)",
  "linear-gradient(90deg, #E0F2FE 0%, #F8FAFC 100%)",
  "linear-gradient(90deg, #FDE68A 0%, #FFFBEB 100%)",
  "linear-gradient(90deg, #FECACA 0%, #FFF5F5 100%)",
];

const CHART_COLORS = ["#2563EB", "#0F766E", "#F59E0B", "#DC2626", "#7C3AED", "#0891B2"];

type AttentionTask = AugmisBusinessTask & {
  leadTitle: string;
  prospectName: string;
};

function formatCurrency(value: number | null | undefined) {
  if (value == null) {
    return "0";
  }
  return value.toLocaleString(undefined, {
    maximumFractionDigits: 0,
  });
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Not available";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString();
}

function daysRemaining(value: string | null | undefined) {
  if (!value) {
    return null;
  }
  const target = new Date(value);
  if (Number.isNaN(target.getTime())) {
    return null;
  }
  const now = new Date();
  const diff = Math.ceil((target.getTime() - now.getTime()) / 86400000);
  return diff;
}

function MetricCard({
  title,
  value,
  subtitle,
  gradient,
  icon,
}: {
  title: string;
  value: string;
  subtitle: string;
  gradient: string;
  icon: React.ReactNode;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        borderRadius: "8px",
        border: "1px solid #D9E2EC",
        overflow: "hidden",
        minHeight: 126,
      }}
    >
      <Box sx={{ px: 2, py: 1.15, background: gradient, borderBottom: "1px solid #E2E8F0" }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <Box sx={{ color: "#0F4C81", display: "flex" }}>{icon}</Box>
          <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{title}</Typography>
        </Stack>
      </Box>
      <Box sx={{ px: 2, py: 1.8 }}>
        <Typography sx={{ fontSize: 28, fontWeight: 800, color: "#0F172A", lineHeight: 1 }}>
          {value}
        </Typography>
        <Typography sx={{ mt: 1, color: "#64748B", fontSize: 13 }}>{subtitle}</Typography>
      </Box>
    </Paper>
  );
}

function SectionCard({
  title,
  icon,
  action,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Paper
      elevation={0}
      sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}
    >
      <Box
        sx={{
          px: 2,
          py: 1.3,
          background: "linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)",
          borderBottom: "1px solid #E2E8F0",
        }}
      >
        <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between" }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Box sx={{ color: "#2563EB", display: "flex" }}>{icon}</Box>
            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{title}</Typography>
          </Stack>
          {action}
        </Stack>
      </Box>
      <Box sx={{ p: 2 }}>{children}</Box>
    </Paper>
  );
}

function EmptySection({ title, description }: { title: string; description: string }) {
  return (
    <Paper
      elevation={0}
      sx={{ p: 2.4, borderRadius: "8px", border: "1px dashed #CBD5E1", bgcolor: "#F8FAFC" }}
    >
      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{title}</Typography>
      <Typography sx={{ mt: 0.7, color: "#475569" }}>{description}</Typography>
    </Paper>
  );
}

export default function OverviewDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dashboard, setDashboard] = useState<AugmisBusinessDashboard | null>(null);
  const [recentOpportunities, setRecentOpportunities] = useState<AugmisBusinessOpportunity[]>([]);
  const [attentionTasks, setAttentionTasks] = useState<AttentionTask[]>([]);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    let active = true;

    async function loadOverview() {
      setLoading(true);
      setError("");
      try {
        const [dashboardResult, opportunityResult, openTaskResult, inProgressTaskResult] =
          await Promise.all([
            getAugmisBusinessDashboard(),
            listAugmisBusinessOpportunities({
              page: 1,
              page_size: 6,
              sort_by: "updated_at",
              sort_order: "desc",
            }),
            listAugmisBusinessTasks({ page: 1, page_size: 8, status: "open" }),
            listAugmisBusinessTasks({ page: 1, page_size: 8, status: "in_progress" }),
          ]);

        const mergedTasks = [...(openTaskResult.data || []), ...(inProgressTaskResult.data || [])]
          .sort((left, right) => {
            const leftTime = left.due_at ? new Date(left.due_at).getTime() : Number.MAX_SAFE_INTEGER;
            const rightTime = right.due_at ? new Date(right.due_at).getTime() : Number.MAX_SAFE_INTEGER;
            return leftTime - rightTime;
          })
          .slice(0, 8);

        const uniqueLeadIds = Array.from(new Set(mergedTasks.map((task) => task.lead_id)));
        const leadRows = await Promise.all(
          uniqueLeadIds.map(async (leadId) => {
            try {
              const leadResult = await getAugmisBusinessLead(leadId);
              return leadResult.data;
            } catch {
              return null;
            }
          })
        );
        const leadMap = leadRows.reduce<Record<string, AugmisBusinessLead>>((acc, lead) => {
          if (lead) {
            acc[lead.id] = lead;
          }
          return acc;
        }, {});

        if (!active) {
          return;
        }

        setDashboard(dashboardResult.data);
        setRecentOpportunities(opportunityResult.data || []);
        setAttentionTasks(
          mergedTasks.map((task) => ({
            ...task,
            leadTitle: leadMap[task.lead_id]?.title || task.lead_id,
            prospectName: leadMap[task.lead_id]?.prospect?.organization_name || "Not available",
          }))
        );
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(parseApiValidationError(loadError, "Unable to load AUGMIS Business overview.").message);
        setDashboard(null);
        setRecentOpportunities([]);
        setAttentionTasks([]);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadOverview();

    return () => {
      active = false;
    };
  }, [refreshTick]);

  const stageChartData = useMemo(
    () =>
      (dashboard?.leads_by_stage || []).map((item) => ({
        stage: formatTaskLabel(item.lead_stage),
        count: item.count,
      })),
    [dashboard]
  );

  const sourceChartData = dashboard?.opportunities_by_source || [];
  const marketChartData = dashboard?.opportunities_by_market || [];
  const closingSoonItems = dashboard?.opportunities_closing_soon.items || [];
  const recentActivities = dashboard?.recent_activities || [];

  return (
    <OutletPage
      title="AUGMIS Business Overview"
      description="Live commercial visibility across opportunities, pipeline, prospects, tasks, and recent business activity."
    >
      <Stack spacing={2.5}>
        {error ? <Alert severity="error">{error}</Alert> : null}

        <Stack direction={{ xs: "column", md: "row" }} spacing={1.25} sx={{ justifyContent: "space-between" }}>
          <Stack spacing={0.35}>
            <Typography sx={{ fontSize: 13, color: "#64748B" }}>
              Operational dashboard for live business development execution
            </Typography>
          </Stack>
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
            <Button
              component={Link}
              href="/augmis-business/tasks?create=1"
              variant="contained"
              startIcon={<ChecklistOutlinedIcon />}
              sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "#2563EB", "&:hover": { bgcolor: "#1D4ED8" } }}
            >
              New Task
            </Button>
            <Button
              component={Link}
              href="/augmis-business/pipeline"
              variant="contained"
              startIcon={<TimelineOutlinedIcon />}
              sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "#0F766E", "&:hover": { bgcolor: "#115E59" } }}
            >
              View Pipeline
            </Button>
            <Button
              component={Link}
              href="/augmis-business/opportunities"
              variant="outlined"
              sx={{ textTransform: "none", borderRadius: "8px" }}
            >
              Opportunities
            </Button>
            <Button
              component={Link}
              href="/augmis-business/prospects"
              variant="outlined"
              sx={{ textTransform: "none", borderRadius: "8px" }}
            >
              Prospects
            </Button>
            <Button
              variant="outlined"
              startIcon={<RefreshRoundedIcon />}
              onClick={() => setRefreshTick((value) => value + 1)}
              sx={{ textTransform: "none", borderRadius: "8px" }}
            >
              Refresh
            </Button>
          </Stack>
        </Stack>

        {loading ? (
          <Stack sx={{ py: 7, alignItems: "center" }}>
            <CircularProgress size={30} />
          </Stack>
        ) : (
          <>
            <Box
              sx={{
                display: "grid",
                gap: 2,
                gridTemplateColumns: {
                  xs: "1fr",
                  md: "repeat(2, minmax(0, 1fr))",
                  xl: "repeat(3, minmax(0, 1fr))",
                },
              }}
            >
              <MetricCard
                title="Open Opportunities"
                value={String(dashboard?.open_opportunities ?? 0)}
                subtitle="Live active opportunity records"
                gradient={KPI_CARD_STYLES[0]}
                icon={<BusinessCenterOutlinedIcon fontSize="small" />}
              />
              <MetricCard
                title="Converted Opportunities"
                value={String(dashboard?.converted_opportunities ?? 0)}
                subtitle="Opportunities already converted to leads"
                gradient={KPI_CARD_STYLES[1]}
                icon={<ArrowForwardOutlinedIcon fontSize="small" />}
              />
              <MetricCard
                title="Active Prospects"
                value={String(dashboard?.active_prospects ?? 0)}
                subtitle="Prospects currently active in tenant scope"
                gradient={KPI_CARD_STYLES[2]}
                icon={<HubOutlinedIcon fontSize="small" />}
              />
              <MetricCard
                title="Open Leads"
                value={String(dashboard?.open_leads ?? 0)}
                subtitle="Leads in active pipeline stages"
                gradient={KPI_CARD_STYLES[3]}
                icon={<TimelineOutlinedIcon fontSize="small" />}
              />
              <MetricCard
                title="Pipeline Value"
                value={formatCurrency(dashboard?.pipeline_value)}
                subtitle="Sum of active lead values"
                gradient={KPI_CARD_STYLES[4]}
                icon={<CurrencyExchangeOutlinedIcon fontSize="small" />}
              />
              <MetricCard
                title="Weighted Pipeline"
                value={formatCurrency(dashboard?.weighted_pipeline_value)}
                subtitle="Probability-weighted active lead value"
                gradient={KPI_CARD_STYLES[5]}
                icon={<InsightsOutlinedIcon fontSize="small" />}
              />
              <MetricCard
                title="Tasks Due Today"
                value={String(dashboard?.tasks_due_today ?? 0)}
                subtitle="Open and in-progress tasks due today"
                gradient={KPI_CARD_STYLES[6]}
                icon={<EventAvailableOutlinedIcon fontSize="small" />}
              />
              <MetricCard
                title="Overdue Tasks"
                value={String(dashboard?.overdue_tasks ?? 0)}
                subtitle="Tasks already past due and still open"
                gradient={KPI_CARD_STYLES[7]}
                icon={<AssignmentLateOutlinedIcon fontSize="small" />}
              />
              <MetricCard
                title="Closing Soon"
                value={String(dashboard?.opportunities_closing_soon.count ?? 0)}
                subtitle="Active opportunities closing within 14 days"
                gradient={KPI_CARD_STYLES[8]}
                icon={<OpenInNewOutlinedIcon fontSize="small" />}
              />
            </Box>

            <Box
              sx={{
                display: "grid",
                gap: 2,
                gridTemplateColumns: {
                  xs: "1fr",
                  xl: "minmax(0, 1.35fr) minmax(0, 1fr)",
                },
              }}
            >
              <SectionCard title="Pipeline by Stage" icon={<DonutLargeOutlinedIcon fontSize="small" />}>
                {stageChartData.length ? (
                  <Box sx={{ height: 280 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={stageChartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="stage" tick={{ fontSize: 12 }} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                        <Tooltip />
                        <Bar dataKey="count" radius={[6, 6, 0, 0]} fill="#2563EB" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                ) : (
                  <EmptySection
                    title="No pipeline data yet"
                    description="Lead stage counts will appear here once tenant-scoped lead records are available."
                  />
                )}
              </SectionCard>

              <SectionCard
                title="Today's / Attention Required"
                icon={<ChecklistOutlinedIcon fontSize="small" />}
                action={
                  <Button
                    component={Link}
                    href="/augmis-business/tasks"
                    endIcon={<ArrowForwardOutlinedIcon />}
                    sx={{ textTransform: "none" }}
                  >
                    View Tasks
                  </Button>
                }
              >
                {attentionTasks.length ? (
                  <Stack spacing={1.2}>
                    {attentionTasks.map((task) => (
                      <Paper
                        key={task.id}
                        elevation={0}
                        sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}
                      >
                        <Stack
                          direction={{ xs: "column", md: "row" }}
                          spacing={1.2}
                          sx={{ justifyContent: "space-between" }}
                        >
                          <Box>
                            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{task.title}</Typography>
                            <Typography sx={{ mt: 0.45, color: "#475569", fontSize: 13 }}>
                              {task.leadTitle} • {task.prospectName}
                            </Typography>
                            <Typography sx={{ mt: 0.45, color: "#64748B", fontSize: 12.5 }}>
                              Due {formatDate(task.due_at)} • {getTaskTimingLabel(task)}
                            </Typography>
                          </Box>
                          <Stack direction="row" spacing={0.75} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.75 }}>
                            <TaskPriorityChip priority={task.priority} />
                            <TaskStatusChip status={task.task_status} />
                          </Stack>
                        </Stack>
                      </Paper>
                    ))}
                  </Stack>
                ) : (
                  <EmptySection
                    title="No attention tasks"
                    description="Open or in-progress tasks with near-term due dates will show here."
                  />
                )}
              </SectionCard>
            </Box>

            <Box
              sx={{
                display: "grid",
                gap: 2,
                gridTemplateColumns: {
                  xs: "1fr",
                  xl: "minmax(0, 1.35fr) minmax(0, 1fr)",
                },
              }}
            >
              <SectionCard
                title="Top / Recent Opportunities"
                icon={<BusinessCenterOutlinedIcon fontSize="small" />}
                action={
                  <Button
                    component={Link}
                    href="/augmis-business/opportunities"
                    endIcon={<ArrowForwardOutlinedIcon />}
                    sx={{ textTransform: "none" }}
                  >
                    Open Opportunities
                  </Button>
                }
              >
                {recentOpportunities.length ? (
                  <Stack spacing={1.2}>
                    {recentOpportunities.map((opportunity) => (
                      <Paper
                        key={opportunity.id}
                        elevation={0}
                        sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}
                      >
                        <Stack
                          direction={{ xs: "column", md: "row" }}
                          spacing={1.2}
                          sx={{ justifyContent: "space-between" }}
                        >
                          <Box>
                            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                              {opportunity.title}
                            </Typography>
                            <Typography sx={{ mt: 0.45, color: "#475569", fontSize: 13 }}>
                              {opportunity.organization_name} • {opportunity.source_type}
                            </Typography>
                            <Typography sx={{ mt: 0.45, color: "#64748B", fontSize: 12.5 }}>
                              Status: {formatTaskLabel(opportunity.opportunity_status)} • Closing{" "}
                              {formatDate(opportunity.closing_at)}
                            </Typography>
                          </Box>
                          <Stack spacing={0.45} sx={{ alignItems: { md: "flex-end" } }}>
                            <Typography sx={{ fontWeight: 700, color: "#0F4C81" }}>
                              Fit score: {opportunity.fit_score != null ? opportunity.fit_score : "Not available"}
                            </Typography>
                            {opportunity.opportunity_status === "converted" ? (
                              <Typography sx={{ color: "#067647", fontWeight: 700, fontSize: 12.5 }}>
                                Converted
                              </Typography>
                            ) : null}
                            {daysRemaining(opportunity.closing_at) != null &&
                            (daysRemaining(opportunity.closing_at) || 0) <= 7 ? (
                              <Typography sx={{ color: "#B54708", fontWeight: 700, fontSize: 12.5 }}>
                                Closing soon
                              </Typography>
                            ) : null}
                          </Stack>
                        </Stack>
                      </Paper>
                    ))}
                  </Stack>
                ) : (
                  <EmptySection
                    title="No recent opportunities"
                    description="Recent opportunity activity will appear here when live records are available."
                  />
                )}
              </SectionCard>

              <SectionCard title="Closing Soon" icon={<EventAvailableOutlinedIcon fontSize="small" />}>
                {closingSoonItems.length ? (
                  <Stack spacing={1.2}>
                    {closingSoonItems.map((opportunity) => {
                      const remaining = daysRemaining(opportunity.closing_at);
                      const color =
                        remaining != null && remaining <= 3
                          ? "#B42318"
                          : remaining != null && remaining <= 7
                            ? "#B54708"
                            : "#0F172A";
                      return (
                        <Paper
                          key={opportunity.id}
                          elevation={0}
                          sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}
                        >
                          <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                            {opportunity.title}
                          </Typography>
                          <Typography sx={{ mt: 0.45, color: "#475569", fontSize: 13 }}>
                            {opportunity.organization_name}
                          </Typography>
                          <Typography sx={{ mt: 0.45, color, fontWeight: 700, fontSize: 12.5 }}>
                            Closes {formatDate(opportunity.closing_at)}
                            {remaining != null ? ` • ${remaining} day${remaining === 1 ? "" : "s"} remaining` : ""}
                          </Typography>
                        </Paper>
                      );
                    })}
                  </Stack>
                ) : (
                  <EmptySection
                    title="No closing-soon opportunities"
                    description="Opportunities with imminent closing dates will appear here."
                  />
                )}
              </SectionCard>
            </Box>

            <Box
              sx={{
                display: "grid",
                gap: 2,
                gridTemplateColumns: {
                  xs: "1fr",
                  xl: "repeat(2, minmax(0, 1fr))",
                },
              }}
            >
              <SectionCard title="Opportunities by Source" icon={<InsightsOutlinedIcon fontSize="small" />}>
                {sourceChartData.length ? (
                  <Box sx={{ height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={sourceChartData}
                          dataKey="count"
                          nameKey="source_type"
                          innerRadius={52}
                          outerRadius={82}
                          paddingAngle={2}
                        >
                          {sourceChartData.map((entry, index) => (
                            <Cell key={entry.source_type} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </Box>
                ) : (
                  <EmptySection
                    title="No source analytics yet"
                    description="Source distribution appears once live opportunity records exist."
                  />
                )}
              </SectionCard>

              <SectionCard title="Opportunities by Market" icon={<SouthAmericaOutlinedIcon fontSize="small" />}>
                {marketChartData.length ? (
                  <Box sx={{ height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={marketChartData} layout="vertical" margin={{ top: 8, right: 16, left: 16, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
                        <YAxis dataKey="market" type="category" width={88} tick={{ fontSize: 12 }} />
                        <Tooltip />
                        <Bar dataKey="count" radius={[0, 6, 6, 0]} fill="#0F766E" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                ) : (
                  <EmptySection
                    title="No market analytics yet"
                    description="Country or region clustering appears when opportunity market data is available."
                  />
                )}
              </SectionCard>
            </Box>

            {recentActivities.length ? (
              <SectionCard title="Recent Activity" icon={<ChecklistOutlinedIcon fontSize="small" />}>
                <Stack spacing={1.2}>
                  {recentActivities.map((activity: AugmisBusinessActivity) => (
                    <Paper
                      key={activity.id}
                      elevation={0}
                      sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}
                    >
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{activity.subject}</Typography>
                      <Typography sx={{ mt: 0.45, color: "#475569", fontSize: 13 }}>
                        {formatTaskLabel(activity.activity_type)} • {formatTaskDateTime(activity.activity_at || activity.created_at)}
                      </Typography>
                      {activity.description ? (
                        <Typography sx={{ mt: 0.7, color: "#334155" }}>{activity.description}</Typography>
                      ) : null}
                    </Paper>
                  ))}
                </Stack>
              </SectionCard>
            ) : null}
          </>
        )}
      </Stack>
    </OutletPage>
  );
}
