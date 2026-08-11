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
import PsychologyAltOutlinedIcon from "@mui/icons-material/PsychologyAltOutlined";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import SouthAmericaOutlinedIcon from "@mui/icons-material/SouthAmericaOutlined";
import TimelineOutlinedIcon from "@mui/icons-material/TimelineOutlined";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
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

import { parseApiValidationError } from "@/services/apiErrorParser";
import {
  type AugmisBusinessActivity,
  type AugmisBusinessDashboard,
  type AugmisBusinessDealDeskResponse,
  type AugmisBusinessLead,
  type AugmisBusinessOpportunity,
  type AugmisBusinessTask,
  getAugmisBusinessDashboard,
  getAugmisBusinessDealDesk,
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
import BusinessMetricCarousel, { type BusinessMetricItem } from "./components/BusinessMetricCarousel";
import BusinessPageFrame from "./components/BusinessPageFrame";

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

function recommendationChipStyle(value: string | null | undefined) {
  switch ((value || "").toLowerCase()) {
    case "pursue":
      return { bgcolor: "#DCFCE7", color: "#166534", border: "1px solid #86EFAC" };
    case "skip":
      return { bgcolor: "#FEF2F2", color: "#B42318", border: "1px solid #FECACA" };
    default:
      return { bgcolor: "#FFFBEB", color: "#B45309", border: "1px solid #FDE68A" };
  }
}

function dealDeskSourceChipStyle(sourceType: string | null | undefined) {
  switch ((sourceType || "").toLowerCase()) {
    case "public_procurement":
      return { bgcolor: "#ECFEFF", color: "#0F766E", border: "1px solid #99F6E4" };
    case "marketplace_project":
      return { bgcolor: "#F5F3FF", color: "#6D28D9", border: "1px solid #DDD6FE" };
    case "employment_contract":
      return { bgcolor: "#EFF6FF", color: "#1D4ED8", border: "1px solid #BFDBFE" };
    default:
      return { bgcolor: "#FEF3C7", color: "#B45309", border: "1px solid #FCD34D" };
  }
}

function formatClosingLabel(value: string | null | undefined) {
  if (!value) {
    return { primary: "No deadline provided", secondary: null as string | null };
  }
  const target = new Date(value);
  if (Number.isNaN(target.getTime())) {
    return { primary: value, secondary: null };
  }
  const diff = Math.ceil((target.getTime() - Date.now()) / 86400000);
  if (diff < 0) {
    return { primary: "Expired", secondary: formatDate(value) };
  }
  if (diff === 0) {
    return { primary: "Closing today", secondary: formatDate(value) };
  }
  if (diff === 1) {
    return { primary: "Closing in 1 day", secondary: formatDate(value) };
  }
  return { primary: `Closing in ${diff} days`, secondary: formatDate(value) };
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
  const [dealDesk, setDealDesk] = useState<AugmisBusinessDealDeskResponse | null>(null);
  const [recentOpportunities, setRecentOpportunities] = useState<AugmisBusinessOpportunity[]>([]);
  const [attentionTasks, setAttentionTasks] = useState<AttentionTask[]>([]);
  const [refreshTick, setRefreshTick] = useState(0);
  const [dealDeskLimit, setDealDeskLimit] = useState(10);
  const [dealDeskRecommendation, setDealDeskRecommendation] = useState("all");
  const [dealDeskPriority, setDealDeskPriority] = useState("all");
  const [lastDealDeskRefreshAt, setLastDealDeskRefreshAt] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadOverview() {
      setLoading(true);
      setError("");
      try {
        const [dashboardResult, opportunityResult, openTaskResult, inProgressTaskResult, dealDeskResult] =
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
            getAugmisBusinessDealDesk({
              limit: dealDeskLimit,
              recommendation: dealDeskRecommendation === "all" ? undefined : dealDeskRecommendation,
              priority_band: dealDeskPriority === "all" ? undefined : dealDeskPriority,
            }),
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
        setDealDesk(dealDeskResult.data);
        setRecentOpportunities(opportunityResult.data || []);
        setAttentionTasks(
          mergedTasks.map((task) => ({
            ...task,
            leadTitle: leadMap[task.lead_id]?.title || task.lead_id,
            prospectName: leadMap[task.lead_id]?.prospect?.organization_name || "Not available",
          }))
        );
        setLastDealDeskRefreshAt(new Date().toISOString());
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(parseApiValidationError(loadError, "Unable to load AUGMIS Business overview.").message);
        setDashboard(null);
        setDealDesk(null);
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
  }, [dealDeskLimit, dealDeskPriority, dealDeskRecommendation, refreshTick]);

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
  const dealDeskItems = dealDesk?.items || [];
  const overviewMetrics = useMemo<BusinessMetricItem[]>(
    () => [
      {
        key: "open-opportunities",
        title: "Open Opportunities",
        value: String(dashboard?.open_opportunities ?? 0),
        subtitle: "Live active opportunity records",
        accent: KPI_CARD_STYLES[0],
        icon: <BusinessCenterOutlinedIcon fontSize="small" />,
      },
      {
        key: "converted-opportunities",
        title: "Converted Opportunities",
        value: String(dashboard?.converted_opportunities ?? 0),
        subtitle: "Opportunities already converted to leads",
        accent: KPI_CARD_STYLES[1],
        icon: <ArrowForwardOutlinedIcon fontSize="small" />,
      },
      {
        key: "active-prospects",
        title: "Active Prospects",
        value: String(dashboard?.active_prospects ?? 0),
        subtitle: "Prospects currently active in tenant scope",
        accent: KPI_CARD_STYLES[2],
        icon: <HubOutlinedIcon fontSize="small" />,
      },
      {
        key: "open-leads",
        title: "Open Leads",
        value: String(dashboard?.open_leads ?? 0),
        subtitle: "Leads in active pipeline stages",
        accent: KPI_CARD_STYLES[3],
        icon: <TimelineOutlinedIcon fontSize="small" />,
      },
      {
        key: "pipeline-value",
        title: "Pipeline Value",
        value: formatCurrency(dashboard?.pipeline_value),
        subtitle: "Sum of active lead values",
        accent: KPI_CARD_STYLES[4],
        icon: <CurrencyExchangeOutlinedIcon fontSize="small" />,
      },
      {
        key: "weighted-pipeline",
        title: "Weighted Pipeline",
        value: formatCurrency(dashboard?.weighted_pipeline_value),
        subtitle: "Probability-weighted active lead value",
        accent: KPI_CARD_STYLES[5],
        icon: <InsightsOutlinedIcon fontSize="small" />,
      },
      {
        key: "tasks-due-today",
        title: "Tasks Due Today",
        value: String(dashboard?.tasks_due_today ?? 0),
        subtitle: "Open and in-progress tasks due today",
        accent: KPI_CARD_STYLES[6],
        icon: <EventAvailableOutlinedIcon fontSize="small" />,
      },
      {
        key: "overdue-tasks",
        title: "Overdue Tasks",
        value: String(dashboard?.overdue_tasks ?? 0),
        subtitle: "Tasks already past due and still open",
        accent: KPI_CARD_STYLES[7],
        icon: <AssignmentLateOutlinedIcon fontSize="small" />,
      },
      {
        key: "closing-soon",
        title: "Closing Soon",
        value: String(dashboard?.opportunities_closing_soon.count ?? 0),
        subtitle: "Active opportunities closing within 14 days",
        accent: KPI_CARD_STYLES[8],
        icon: <OpenInNewOutlinedIcon fontSize="small" />,
      },
    ],
    [dashboard]
  );

  return (
    <BusinessPageFrame
      title="AUGMIS Business Overview"
      description="Live commercial visibility across opportunities, pipeline, prospects, tasks, and recent business activity."
    >
      <Stack spacing={2.5}>
        {error ? <Alert severity="error">{error}</Alert> : null}

        {loading ? (
          <Stack sx={{ py: 7, alignItems: "center" }}>
            <CircularProgress size={30} />
          </Stack>
        ) : (
          <>
            <BusinessMetricCarousel items={overviewMetrics} />

            <Stack spacing={1.25}>
              <Typography sx={{ fontSize: 13, color: "#64748B" }}>
                Operational dashboard for live business development execution
              </Typography>
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

            <SectionCard
              title="Daily Deal Desk"
              icon={<PsychologyAltOutlinedIcon fontSize="small" />}
              action={
                <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
                  <Typography sx={{ fontSize: 12, color: "#64748B", mr: 0.5 }}>
                    {lastDealDeskRefreshAt ? `Refreshed ${formatTaskDateTime(lastDealDeskRefreshAt)}` : "Awaiting refresh"}
                  </Typography>
                  <FormControl size="small" sx={{ minWidth: 112 }}>
                    <InputLabel>Recommendation</InputLabel>
                    <Select
                      label="Recommendation"
                      value={dealDeskRecommendation}
                      onChange={(event) => setDealDeskRecommendation(event.target.value)}
                    >
                      <MenuItem value="all">All</MenuItem>
                      <MenuItem value="pursue">Pursue</MenuItem>
                      <MenuItem value="watch">Watch</MenuItem>
                    </Select>
                  </FormControl>
                  <FormControl size="small" sx={{ minWidth: 96 }}>
                    <InputLabel>Priority</InputLabel>
                    <Select
                      label="Priority"
                      value={dealDeskPriority}
                      onChange={(event) => setDealDeskPriority(event.target.value)}
                    >
                      <MenuItem value="all">All</MenuItem>
                      <MenuItem value="A">A</MenuItem>
                      <MenuItem value="B">B</MenuItem>
                      <MenuItem value="C">C</MenuItem>
                    </Select>
                  </FormControl>
                  <FormControl size="small" sx={{ minWidth: 92 }}>
                    <InputLabel>Limit</InputLabel>
                    <Select
                      label="Limit"
                      value={String(dealDeskLimit)}
                      onChange={(event) => setDealDeskLimit(Number(event.target.value))}
                    >
                      <MenuItem value="5">Top 5</MenuItem>
                      <MenuItem value="10">Top 10</MenuItem>
                      <MenuItem value="20">Top 20</MenuItem>
                    </Select>
                  </FormControl>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<RefreshRoundedIcon />}
                    onClick={() => setRefreshTick((value) => value + 1)}
                    sx={{ textTransform: "none", borderRadius: "8px" }}
                  >
                    Refresh
                  </Button>
                </Stack>
              }
            >
              <Stack direction={{ xs: "column", md: "row" }} spacing={1.2} sx={{ justifyContent: "space-between", mb: 1.6 }}>
                <Box>
                  <Typography sx={{ fontSize: 13, fontWeight: 800, letterSpacing: ".08em", color: "#0F4C81" }}>
                    DAILY DEAL DESK
                  </Typography>
                  <Typography sx={{ mt: 0.35, color: "#475569", fontSize: 13 }}>
                    Top commercial opportunities requiring attention today.
                  </Typography>
                </Box>
              </Stack>
              <Box
                sx={{
                  display: "grid",
                  gap: 1.25,
                  gridTemplateColumns: {
                    xs: "repeat(2, minmax(0, 1fr))",
                    md: "repeat(4, minmax(0, 1fr))",
                  },
                  mb: 1.5,
                }}
              >
                <Paper elevation={0} sx={{ p: 1.35, borderRadius: "8px", border: "1px solid #DBEAFE", bgcolor: "#F8FBFF" }}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "flex-start" }}>
                    <Box sx={{ width: 34, height: 34, borderRadius: "9px", display: "grid", placeItems: "center", bgcolor: "#DBEAFE", color: "#1D4ED8" }}>
                      <PsychologyAltOutlinedIcon fontSize="small" />
                    </Box>
                    <Box>
                      <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#64748B" }}>PURSUE TODAY</Typography>
                      <Typography sx={{ fontSize: 24, fontWeight: 800, color: "#0F172A" }}>{dealDesk?.pursue ?? 0}</Typography>
                      <Typography sx={{ fontSize: 12, color: "#475569" }}>High-value opportunities</Typography>
                    </Box>
                  </Stack>
                </Paper>
                <Paper elevation={0} sx={{ p: 1.35, borderRadius: "8px", border: "1px solid #FDE68A", bgcolor: "#FFFBEB" }}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "flex-start" }}>
                    <Box sx={{ width: 34, height: 34, borderRadius: "9px", display: "grid", placeItems: "center", bgcolor: "#FEF3C7", color: "#B45309" }}>
                      <OpenInNewOutlinedIcon fontSize="small" />
                    </Box>
                    <Box>
                      <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#64748B" }}>WATCH</Typography>
                      <Typography sx={{ fontSize: 24, fontWeight: 800, color: "#0F172A" }}>{dealDesk?.watch ?? 0}</Typography>
                      <Typography sx={{ fontSize: 12, color: "#475569" }}>Needs further review</Typography>
                    </Box>
                  </Stack>
                </Paper>
                <Paper elevation={0} sx={{ p: 1.35, borderRadius: "8px", border: "1px solid #BFDBFE", bgcolor: "#EFF6FF" }}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "flex-start" }}>
                    <Box sx={{ width: 34, height: 34, borderRadius: "9px", display: "grid", placeItems: "center", bgcolor: "#DBEAFE", color: "#1D4ED8" }}>
                      <InsightsOutlinedIcon fontSize="small" />
                    </Box>
                    <Box>
                      <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#64748B" }}>PRIORITY A</Typography>
                      <Typography sx={{ fontSize: 24, fontWeight: 800, color: "#0F172A" }}>{dealDesk?.priority_a ?? 0}</Typography>
                      <Typography sx={{ fontSize: 12, color: "#475569" }}>Highest commercial priority</Typography>
                    </Box>
                  </Stack>
                </Paper>
                <Paper elevation={0} sx={{ p: 1.35, borderRadius: "8px", border: "1px solid #FED7AA", bgcolor: "#FFF7ED" }}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "flex-start" }}>
                    <Box sx={{ width: 34, height: 34, borderRadius: "9px", display: "grid", placeItems: "center", bgcolor: "#FFEDD5", color: "#C2410C" }}>
                      <EventAvailableOutlinedIcon fontSize="small" />
                    </Box>
                    <Box>
                      <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#64748B" }}>CLOSING SOON</Typography>
                      <Typography sx={{ fontSize: 24, fontWeight: 800, color: "#0F172A" }}>{dealDesk?.closing_soon ?? 0}</Typography>
                      <Typography sx={{ fontSize: 12, color: "#475569" }}>Within 14 days</Typography>
                    </Box>
                  </Stack>
                </Paper>
              </Box>
              {dealDeskItems.length ? (
                <Stack spacing={1.1}>
                  {dealDeskItems.map((item) => (
                    <Paper
                      key={item.id}
                      elevation={0}
                      sx={{ p: 1.5, borderRadius: "10px", border: "1px solid #E2E8F0", bgcolor: "#FFFFFF" }}
                    >
                      <Stack direction={{ xs: "column", md: "row" }} spacing={1.4} sx={{ justifyContent: "space-between" }}>
                        <Box sx={{ minWidth: 0 }}>
                          <Stack direction="row" spacing={0.75} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.75 }}>
                            <Chip label={item.source_name} size="small" sx={dealDeskSourceChipStyle(item.source_type)} />
                            <Chip
                              label={(item.commercial_recommendation || "watch").toUpperCase()}
                              size="small"
                              sx={recommendationChipStyle(item.commercial_recommendation)}
                            />
                          </Stack>
                          <Typography sx={{ mt: 0.8, fontWeight: 700, color: "#0F172A" }}>{item.title}</Typography>
                          <Typography sx={{ mt: 0.45, color: "#475569", fontSize: 13 }}>
                            {item.organization_name || "Not available"}
                          </Typography>
                          <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12.5 }}>
                            {item.source_name} · {formatTaskLabel(item.source_type)}
                          </Typography>
                          <Box
                            sx={{
                              mt: 1.1,
                              display: "grid",
                              gap: 0.9,
                              gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", lg: "repeat(4, minmax(0, 1fr))" },
                            }}
                          >
                            <Paper elevation={0} sx={{ p: 1, borderRadius: "8px", border: "1px solid #E2E8F0", bgcolor: "#F8FAFC" }}>
                              <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#64748B" }}>Preliminary Match</Typography>
                              <Typography sx={{ mt: 0.35, fontWeight: 800, color: "#0F172A" }}>
                                {item.preliminary_relevance_score == null ? "N/A" : Math.round(item.preliminary_relevance_score)}
                              </Typography>
                            </Paper>
                            <Paper elevation={0} sx={{ p: 1, borderRadius: "8px", border: "1px solid #E2E8F0", bgcolor: "#F8FAFC" }}>
                              <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#64748B" }}>Commercial Priority</Typography>
                              <Typography sx={{ mt: 0.35, fontWeight: 800, color: "#0F172A" }}>
                                {`Priority ${item.commercial_priority_band || "?"} · ${item.commercial_priority_score == null ? "N/A" : Math.round(item.commercial_priority_score)}`}
                              </Typography>
                            </Paper>
                            <Paper elevation={0} sx={{ p: 1, borderRadius: "8px", border: "1px solid #E2E8F0", bgcolor: "#F8FAFC" }}>
                              <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#64748B" }}>Delivery</Typography>
                              <Typography sx={{ mt: 0.35, fontWeight: 800, color: "#0F172A" }}>
                                {`${item.delivery_model || "Solo / AI-assisted"} · ${item.delivery_complexity || "unknown"}`}
                              </Typography>
                            </Paper>
                            <Paper elevation={0} sx={{ p: 1, borderRadius: "8px", border: "1px solid #E2E8F0", bgcolor: "#F8FAFC" }}>
                              <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#64748B" }}>Value</Typography>
                              <Typography sx={{ mt: 0.35, fontWeight: 800, color: "#0F172A" }}>
                                {item.data_quality_status || "Not disclosed"}
                              </Typography>
                            </Paper>
                          </Box>
                          <Box sx={{ mt: 1.1, display: "grid", gap: 0.8 }}>
                            <Typography sx={{ fontSize: 12.5, color: "#334155" }}>
                              <Box component="span" sx={{ fontWeight: 700, color: "#0F172A" }}>Closing:</Box>{" "}
                              {formatClosingLabel(item.closing_date).primary}
                              {formatClosingLabel(item.closing_date).secondary ? ` · ${formatClosingLabel(item.closing_date).secondary}` : ""}
                            </Typography>
                            <Typography sx={{ fontSize: 12.5, color: "#334155" }}>
                              <Box component="span" sx={{ fontWeight: 700, color: "#0F172A" }}>Best Experience Match:</Box>{" "}
                              {item.top_experience_match?.name || "Not available"}
                            </Typography>
                            <Typography sx={{ fontSize: 12.5, color: "#334155" }}>
                              <Box component="span" sx={{ fontWeight: 700, color: "#0F172A" }}>Why it matters:</Box>{" "}
                              {item.commercial_recommendation_reasons_json?.[0] || "Awaiting deterministic commercial summary."}
                            </Typography>
                          </Box>
                        </Box>
                        <Stack spacing={0.7} sx={{ alignItems: { md: "flex-end" }, minWidth: { md: 154 } }}>
                          <Chip
                            label={`Priority ${item.commercial_priority_band || "?"} • ${item.commercial_priority_score ?? "Not scored"}`}
                            size="small"
                            sx={{ bgcolor: "#EFF6FF", color: "#1D4ED8", border: "1px solid #BFDBFE" }}
                          />
                          <Button component={Link} href="/augmis-business/connectors" variant="outlined" size="small" sx={{ textTransform: "none", borderRadius: "8px" }}>
                            Open
                          </Button>
                          <Button component={Link} href="/augmis-business/connectors" variant="contained" size="small" sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "#2563EB" }}>
                            Import
                          </Button>
                        </Stack>
                      </Stack>
                    </Paper>
                  ))}
                </Stack>
              ) : (
                <EmptySection
                  title="No ranked discoveries yet"
                  description="Run the connected discovery sources and recalculate priorities to populate the daily deal desk."
                />
              )}
            </SectionCard>

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
    </BusinessPageFrame>
  );
}
