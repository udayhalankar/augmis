"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Box,
  Button,
  Chip,
  FormControl,
  InputLabel,
  MenuItem as MuiMenuItem,
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  Dialog, DialogTitle, DialogContent,  DialogActions,
  Select,
  TextField,
  Stack,
  Typography,
} from "@mui/material";
import {
  Area,
  AreaChart,
  Cell,
  Bar,
  BarChart,
  CartesianGrid,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import AssessmentOutlinedIcon from "@mui/icons-material/AssessmentOutlined";
import ArrowForwardRoundedIcon from "@mui/icons-material/ArrowForwardRounded";
import { OutletPage } from "@/components/layout/OutletPage";
import apiClient from "@/services/apiClient";

const CARD_RADIUS = 5;
const BLUE = "#082f73";

type DashboardData = {
  total_documents?: number;
  total_repository_items?: number;
  indexed_documents?: number;
  total_chunks?: number;
  high_risk_count?: number;
  medium_risk_count?: number;
  low_risk_count?: number;
  critical_risk_count?: number;
  business_areas?: Record<string, number>;
  business_area_count?: number;
  risk_distribution?: Record<string, number>;
  ai_identified_risk_count?: number;
  configured_rule_risk_count?: number;
  risk_signal_rows?: Array<{
    source?: string;
    signal_origin?: string;
    business_area?: string;
    risk_level?: string;
    label?: string;
    compiled_check?: string;
    record_id?: string;
    document_id?: string;
    repository_id?: string;
    file_name?: string;
    field?: string;
    operator?: string;
    expected?: string | number | boolean | string[] | null;
    actual?: string | number | boolean | string[] | null;
    record_date?: string | null;
  }>;
};

type RiskSignalRow = NonNullable<DashboardData["risk_signal_rows"]>[number];

function SurfaceCard({
  children,
  sx,
}: {
  children: ReactNode;
  sx?: Record<string, any>;
}) {
  return (
    <Box
      sx={{
        borderRadius: `${CARD_RADIUS}px`,
        border: "1px solid rgba(15, 23, 42, 0.12)",
        // bgcolor: "#ffffff",
        boxShadow: "0 10px 24px rgba(15, 23, 42, 0.05)",
        overflow: "hidden",
        minWidth: 0,
        ...sx,
      }}
    >
      {children}
    </Box>
  );
}

function MetricCard({
  label,
  value,
  caption,
  accent,
}: {
  label: string;
  value: string | number;
  caption: string;
  accent: string;
}) {
  return (
    <SurfaceCard
      sx={{
        p: 2,
        height: 126,
        display: "flex",
        alignItems: "center",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, width: "100%" }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="body2" sx={{ color: "#5b6475", mb: 0.75 }}>
            {label}
          </Typography>
          <Typography sx={{ fontSize: "1.80rem", lineHeight: 2, fontWeight: 500, color: "#1f2937" }}>
            {value}
          </Typography>
          <Typography variant="body2" sx={{ mt: 1, color: "#5b6475", maxWidth: 250 }}>
            {caption}
          </Typography>
        </Box>
        <Box
          sx={{
            width: 31,
            height: 31,
            borderRadius: "999px",
            bgcolor: accent,
            display: "grid",
            placeItems: "center",
            color: "#ffffff",
            flexShrink: 0,
          }}
        >
          <AssessmentOutlinedIcon sx={{ fontSize: 15 }} />
        </Box>
      </Box>
    </SurfaceCard>
  );
}

type MiniChartItem = {
  label: string;
  value: number;
  color: string;
};

function MiniBars({ items }: { items: MiniChartItem[] }) {
  const maxValue = Math.max(...items.map((item) => item.value), 1);
  const chartHeight = 180;

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))`,
        gap: 1.2,
        alignItems: "end",
        height: chartHeight,
      }}
    >
      {items.map((item) => (
        <Box key={`${item.label}-${item.value}`} sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 0.75 }}>
          <Tooltip title={`${item.label}: ${item.value}`} arrow placement="top">
            <Box
              sx={{
                width: "100%",
                height: `${item.value <= 0 ? 4 : Math.max(4, Math.round((item.value / maxValue) * chartHeight))}px`,
                borderRadius: `${CARD_RADIUS}px`,
                // bgcolor: item.color,
                opacity: 0.95,
                cursor: "help",
              }}
            />
          </Tooltip>
        </Box>
      ))}
    </Box>
  );
}

function MiniBarChart({
  items,
  height = 180,
  showLegend = false,
}: {
  items: MiniChartItem[];
  height?: number;
  showLegend?: boolean;
}) {
  const chartData = items.filter((item) => item.value > 0);

  if (chartData.length === 0) {
    return (
      <Box sx={{ width: "100%", height, display: "grid", placeItems: "center", color: "#667085" }}>
        No data
      </Box>
    );
  }

  return (
    <Box sx={{ width: "100%" }}>
      <Box sx={{ width: "100%", height }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" hide />
            <YAxis hide />
            <RechartsTooltip
              formatter={(value, name) => [`${value}`, name]}
              contentStyle={{
                borderRadius: `${CARD_RADIUS}px`,
                borderColor: "#d1d5db",
                boxShadow: "0 10px 24px rgba(15, 23, 42, 0.08)",
              }}
            />
            <Bar dataKey="value" radius={[8, 8, 0, 0]} maxBarSize={52}>
              {chartData.map((item) => (
                <Cell key={item.label} fill={item.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Box>

      {showLegend && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: `repeat(${chartData.length}, minmax(0, 1fr))`,
            mt: 1,
            width: "100%",
          }}
        >
          {chartData.map((item) => (
            <Box
              key={item.label}
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 0.5,
                minWidth: 0,
                px: 0.5,
                textAlign: "center",
              }}
            >
              <Box sx={{ width: 9, height: 9, borderRadius: "999px", flexShrink: 0 }} />
              <Typography
                variant="caption"
                sx={{
                  color: "#667085",
                  fontWeight: 700,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {item.label}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}

function MiniPieOrDonut({
  items,
  donut = false,
}: {
  items: MiniChartItem[];
  donut?: boolean;
}) {
  const visibleItems = items.filter((item) => item.value > 0);

  if (visibleItems.length === 0) {
    return (
      <Box sx={{ width: "100%", height: 180, display: "grid", placeItems: "center", color: "#667085" }}>
        No data
      </Box>
    );
  }

  const chartItems = visibleItems;

  return (
    <Box sx={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", minHeight: 0 }}>
      <Box sx={{ width: "100%", flex: "1 1 auto", minHeight: 180, pt: 0.9 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartItems}
              dataKey="value"
              nameKey="label"
              cx="50%"
              cy="50%"
              innerRadius={donut ? 22 : 0}
              outerRadius={donut ? 88 : 92}
              paddingAngle={donut ? 4 : 3}
              stroke="none"
            >
              {chartItems.map((item) => (
                <Cell key={item.label} fill={item.color} />
              ))}
            </Pie>
            <RechartsTooltip
              formatter={(value, name) => [`${value}`, name]}
              contentStyle={{
                borderRadius: `${CARD_RADIUS}px`,
                borderColor: "#d1d5db",
                boxShadow: "0 10px 24px rgba(15, 23, 42, 0.08)",
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(3, max-content)",
          justifyContent: "center",
          alignContent: "end",
          columnGap: 0.75,
          rowGap: 0.05,
          mt: "auto",
          pt: 0.15,
          mx: "auto",
          maxWidth: "94%",
        }}
      >
        {chartItems.map((item) => (
          <Box key={`${item.label}-${item.value}`} sx={{ display: "flex", alignItems: "center", gap: 0.45, minWidth: 0, whiteSpace: "nowrap" }}>
            <Box sx={{ width: 10, height: 10, borderRadius: "999px", 
              // bgcolor: item.color, 
              flexShrink: 0 }} />
            <Typography variant="caption" sx={{ color: "#667085", fontWeight: 700, lineHeight: 1, whiteSpace: "nowrap" }}>
              {item.label}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

export default function EdbPage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [businessAreaFilter, setBusinessAreaFilter] = useState("All");
  const [riskFilter, setRiskFilter] = useState("All");
  const [dateRangeFilter, setDateRangeFilter] = useState("All");
  const [riskSearch, setRiskSearch] = useState("");
  const [riskTableBusinessAreaFilter, setRiskTableBusinessAreaFilter] = useState("All");
  const [riskTableLevelFilter, setRiskTableLevelFilter] = useState("All");
  const [riskTablePage, setRiskTablePage] = useState(0);
  const [riskTableSortBy, setRiskTableSortBy] = useState<"risk_level" | "business_area" | "label" | "file_name" | "actual" | "expected" | "source">("risk_level");
  const [riskTableSortDirection, setRiskTableSortDirection] = useState<"asc" | "desc">("desc");

  const [summary, setSummary] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryOpen, setSummaryOpen] = useState(false);

   async function generateExecutiveSummary() {
  setSummaryLoading(true);
  try {
    const res = await apiClient.get("/api/dashboard/executive-summary");
    setSummary(res.data.summary || res.data.executive_summary || res.data.answer || "");
    setSummaryOpen(true);
  } catch (err) {
    setSummary("Unable to generate executive summary at this time.");
    setSummaryOpen(true);
  } finally {
    setSummaryLoading(false);
  }
}

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      setLoading(true);

      try {
        const response = await apiClient.get("/api/dashboard", {
          params: {
            business_area: businessAreaFilter,
            risk_level: riskFilter,
            date_range: dateRangeFilter,
          },
        });
        if (active) {
          setDashboard(response.data);
        }
      } catch (error) {
        console.error("Dashboard load failed:", error);
        if (active) {
          setDashboard({});
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

   

    void loadDashboard();

    return () => {
      active = false;
    };
  }, [businessAreaFilter, riskFilter, dateRangeFilter]);

  const totalRepositoryItems =
    dashboard?.total_repository_items ?? dashboard?.total_documents ?? 0;
  const indexedDocuments = dashboard?.indexed_documents ?? totalRepositoryItems;
  const totalChunks = dashboard?.total_chunks ?? 0;
  const highRisk =
    dashboard?.high_risk_count ??
    dashboard?.critical_risk_count ??
    dashboard?.risk_distribution?.High ??
    dashboard?.risk_distribution?.Critical ??
    0;
  const mediumRisk =
    dashboard?.medium_risk_count ?? dashboard?.risk_distribution?.Medium ?? 0;
  const lowRisk = dashboard?.low_risk_count ?? dashboard?.risk_distribution?.Low ?? 0;
  const businessAreaCount =
    dashboard?.business_area_count ??
    Object.keys(dashboard?.business_areas || {}).length;
  const aiIdentifiedRiskCount = dashboard?.ai_identified_risk_count ?? 0;
  const configuredRuleRiskCount = dashboard?.configured_rule_risk_count ?? 0;
  const riskSignalRows = dashboard?.risk_signal_rows ?? [];

  const metrics = [
    {
      label: "Repository Items",
      value: totalRepositoryItems,
      caption: "Tenant repositories records ",
      accent: "#2d62f1",
    },
    {
      label: "Knowledge Chunks",
      value: totalChunks,
      caption: "Searchable enterprise knowledge units",
      accent: "#15b67a",
    },
    {
      label: "High Risk Items",
      value: highRisk,
      caption: "Requires management attention",
      accent: "#ef4d4d",
    },
    {
      label: "Business Areas",
      value: businessAreaCount,
      caption: "Detected operational categories",
      accent: "#f59e0b",
    },
  ];

  const businessAreaEntries = useMemo(() => {
    return Object.entries(dashboard?.business_areas || {})
      .filter(([, value]) => typeof value === "number")
      .sort((left, right) => right[1] - left[1]);
  }, [dashboard?.business_areas]);

  const businessAreaOptions = useMemo(() => {
    const options = businessAreaEntries.map(([label]) => label);
    return ["All", ...options];
  }, [businessAreaEntries]);

  const riskDistributionEntries = useMemo(() => {
    return Object.entries(dashboard?.risk_distribution || {})
      .filter(([, value]) => typeof value === "number")
      .sort((left, right) => right[1] - left[1]);
  }, [dashboard?.risk_distribution]);

  const riskOptions = useMemo(() => {
    const options = riskDistributionEntries.map(([label]) => label);
    return ["All", ...options];
  }, [riskDistributionEntries]);

  const riskTableBusinessAreaOptions = useMemo(() => {
    const values = Array.from(
      new Set(
        riskSignalRows
          .map((row) => String(row.business_area || "").trim())
          .filter(Boolean)
      )
    ).sort((left, right) => left.localeCompare(right));

    return ["All", ...values];
  }, [riskSignalRows]);

  const riskTableLevelOptions = useMemo(() => {
    const values = Array.from(
      new Set(
        [
          ...Object.keys(dashboard?.risk_distribution || {}),
          ...riskSignalRows.map((row) => String(row.risk_level || "").trim()),
        ].filter(Boolean)
      )
    ).sort((left, right) => left.localeCompare(right));

    return ["All", ...values];
  }, [dashboard?.risk_distribution, riskSignalRows]);

  const filteredRiskSignalRows = useMemo(() => {
    const normalizedSearch = riskSearch.trim().toLowerCase();

    return riskSignalRows.filter((row) => {
      if (
        riskTableBusinessAreaFilter !== "All" &&
        String(row.business_area || "").trim() !== riskTableBusinessAreaFilter
      ) {
        return false;
      }

      if (riskTableLevelFilter !== "All" && String(row.risk_level || "").trim() !== riskTableLevelFilter) {
        return false;
      }

      if (!normalizedSearch) {
        return true;
      }

      const searchable = [
        row.business_area,
        row.risk_level,
        row.label,
        row.compiled_check,
        row.file_name,
        row.field,
        row.source,
        formatValue(row.actual),
        formatValue(row.expected),
      ]
        .join(" ")
        .toLowerCase();

      return searchable.includes(normalizedSearch);
    });
  }, [riskSearch, riskSignalRows, riskTableBusinessAreaFilter, riskTableLevelFilter]);

  const sortedRiskSignalRows = useMemo(() => {
    const getSortValue = (row: RiskSignalRow) => {
      switch (riskTableSortBy) {
        case "business_area":
          return String(row.business_area || "");
        case "label":
          return String(row.label || row.compiled_check || "");
        case "file_name":
          return String(row.file_name || "");
        case "actual":
          return formatValue(row.actual);
        case "expected":
          return row.operator ? `${row.operator} ${formatValue(row.expected)}` : formatValue(row.expected);
        case "source":
          return row.source === "ai_extracted_fact" ? "AI extracted fact" : "Configured rule";
        case "risk_level":
        default: {
          const riskOrder: Record<string, number> = { Critical: 4, High: 3, Medium: 2, Low: 1 };
          return riskOrder[String(row.risk_level || "").trim()] ?? 0;
        }
      }
    };

    return [...filteredRiskSignalRows].sort((left, right) => {
      const leftValue = getSortValue(left);
      const rightValue = getSortValue(right);

      if (typeof leftValue === "number" && typeof rightValue === "number") {
        return riskTableSortDirection === "asc" ? leftValue - rightValue : rightValue - leftValue;
      }

      const comparison = String(leftValue).localeCompare(String(rightValue), undefined, {
        numeric: true,
        sensitivity: "base",
      });
      return riskTableSortDirection === "asc" ? comparison : -comparison;
    });
  }, [filteredRiskSignalRows, riskTableSortBy, riskTableSortDirection]);

  const pagedRiskSignalRows = useMemo(() => {
    const start = riskTablePage * 10;
    return sortedRiskSignalRows.slice(start, start + 10);
  }, [riskTablePage, sortedRiskSignalRows]);

  useEffect(() => {
    setRiskTablePage(0);
  }, [riskSearch, riskTableBusinessAreaFilter, riskTableLevelFilter]);

  const enterpriseOverviewData = [
    { name: "Repository Items", value: totalRepositoryItems },
    { name: "Indexed Documents", value: indexedDocuments },
    { name: "Chunks", value: totalChunks },
    { name: "Risk Items", value: highRisk + mediumRisk + lowRisk },
    { name: "Business Areas", value: businessAreaCount },
  ];

  const snapshotItems = [
    `${totalRepositoryItems} repository items tracked across ${businessAreaCount} business areas.`,
    `${indexedDocuments} indexed documents and ${totalChunks} searchable chunks are live.`,
    `${highRisk} high-risk items are currently active in the dashboard.`,
    `${aiIdentifiedRiskCount} AI signals and ${configuredRuleRiskCount} rule findings are represented in the snapshot.`,
  ];

  const dateRangeOptions = ["All", "Last 7 Days", "Last 30 Days", "This Quarter", "This Year"];

  const riskBars =
    riskDistributionEntries.length > 0
      ? riskDistributionEntries.slice(0).map(([label, value], index) => ({
          label,
          value,
          color: ["#2d62f1", "#7c3aed", "#15b67a", "#f59e0b", "#ef4d4d"][index % 5],
        }))
      : [
          { label: "High", value: highRisk, color: "#ef4d4d" },
          { label: "Medium", value: mediumRisk, color: "#f59e0b" },
          { label: "Low", value: lowRisk, color: "#15b67a" },
        ];

  const drilldownRows = [
  {
    kind: "donut",
    title: "Risk Distribution",
    items: [
      { label: "High", value: highRisk, color: "#ef4d4d" },
      { label: "Medium", value: mediumRisk, color: "#f59e0b" },
      { label: "Low", value: lowRisk, color: "#15b67a" },
      { label: "Critical", value: dashboard?.critical_risk_count ?? 0, color: "#7c3aed" },
      { label: "AI Signals", value: aiIdentifiedRiskCount, color: "#2d62f1" },
    ].filter((item) => item.value > 0),
  },
  {
    kind: "area",
    title: "Enterprise Intelligence Overview",
    items: [],
  },
  {
    kind: "pie",
    title: "Index Composition",
    items: [
      { label: "Repository Items", value: totalRepositoryItems, color: "#2d62f1" },
      { label: "Indexed Documents", value: indexedDocuments, color: "#15b67a" },
      { label: "Chunks", value: totalChunks, color: "#7c3aed" },
      { label: "Risk Items", value: highRisk + mediumRisk + lowRisk, color: "#f59e0b" },
      { label: "Business Areas", value: businessAreaCount, color: "#ef4d4d" },
    ],
  },
];

  function formatValue(value: string | number | boolean | string[] | null | undefined) {
    if (Array.isArray(value)) return value.join(", ");
    if (typeof value === "boolean") return value ? "Yes" : "No";
    if (value === null || value === undefined || value === "") return "-";
    return String(value);
  }

  function handleRiskTableSort(
    column: "risk_level" | "business_area" | "label" | "file_name" | "actual" | "expected" | "source"
  ) {
    if (riskTableSortBy === column) {
      setRiskTableSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }

    setRiskTableSortBy(column);
    setRiskTableSortDirection(column === "risk_level" ? "desc" : "asc");
  }

  if (loading) {
    return (
      <OutletPage title="Executive Dashboard">
        <Box sx={{ height: "100%", minHeight: 0, display: "grid", placeItems: "center" }}>
          <Typography variant="body2" sx={{ color: "#5b6475" }}>
            Loading live dashboard data...
          </Typography>
        </Box>
      </OutletPage>
    );
  }

  return (
    <OutletPage
      title="Executive Dashboard"
      actions={
        <Button
          variant="contained"
          startIcon={<AutoAwesomeOutlinedIcon />}
          endIcon={<ArrowForwardRoundedIcon />}
          onClick={generateExecutiveSummary}
          disabled={summaryLoading}
          sx={{
            bgcolor: "#bce58f",
            color: "#12336b",
            borderRadius: `${CARD_RADIUS}px`,
            boxShadow: "none",
            px: 1.35,
            py: 0.45,
            minHeight: 0,
            fontSize: "0.7rem",
            fontWeight: 700,
            "&:hover": { bgcolor: "#acd97a", boxShadow: "none" },
          }}
        >
          {summaryLoading ? "Generating..." : "Generate Executive Summary"}
        </Button>
      }
    >
      <Box sx={{ display: "flex", flexDirection: "column", minHeight: 0, height: "100%", overflowY: "auto", px: 0, pt: 0 }}>
        <Box sx={{ pt: 2, pb: 2, px: 0, display: "flex", flexDirection: "column", minHeight: 0, flex: 1 }}>
            <SurfaceCard sx={{ p: 2, mb: 2, 
              // bgcolor: "#fbfcff", 
              flexShrink: 0 }}>
              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(4, minmax(0, 1fr))" }, gap: 2 }}>
                <FormControl size="small" fullWidth>
                  <InputLabel>Business Area</InputLabel>
                  <Select
                    label="Business Area"
                    value={businessAreaFilter}
                    onChange={(event) => setBusinessAreaFilter(String(event.target.value))}
                  >
                    {businessAreaOptions.map((option) => (
                      <MuiMenuItem key={option} value={option}>
                        {option}
                      </MuiMenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" fullWidth>
                  <InputLabel>Risk Level</InputLabel>
                  <Select
                    label="Risk Level"
                    value={riskFilter}
                    onChange={(event) => setRiskFilter(String(event.target.value))}
                  >
                    {riskOptions.map((option) => (
                      <MuiMenuItem key={option} value={option}>
                        {option}
                      </MuiMenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" fullWidth>
                  <InputLabel>Date Range</InputLabel>
                  <Select
                    label="Date Range"
                    value={dateRangeFilter}
                    onChange={(event) => setDateRangeFilter(String(event.target.value))}
                  >
                    {dateRangeOptions.map((option) => (
                      <MuiMenuItem key={option} value={option}>
                        {option}
                      </MuiMenuItem>
                    ))}
                  </Select>
                </FormControl>
                <Box sx={{ display: "flex", alignItems: "end" }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => {
                      setBusinessAreaFilter("All");
                      setRiskFilter("All");
                      setDateRangeFilter("All");
                    }}
                    sx={{
                      height: 40,
                      borderRadius: `${CARD_RADIUS}px`,
                      borderColor: "rgba(45, 98, 241, 0.35)",
                      color: "#2d62f1",
                      fontWeight: 500,
                      // bgcolor: "#fff",
                    }}
                  >
                    Reset
                  </Button>
                </Box>
              </Box>
              <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: "wrap", rowGap: 1 }}>
                <Chip label={`Business Area: ${businessAreaFilter}`} sx={{ borderRadius: `${CARD_RADIUS}px`, bgcolor: "#eef2ff", color: "#334155", fontWeight: 700 }} />
                <Chip label={`Risk: ${riskFilter}`} sx={{ borderRadius: `${CARD_RADIUS}px`, 
                // bgcolor: "#eef2ff", 
                color: "#334155", fontWeight: 700 }} />
                <Chip label={`Date Range: ${dateRangeFilter}`} sx={{ borderRadius: `${CARD_RADIUS}px`, 
                // bgcolor: "#eef2ff", 
                color: "#334155", fontWeight: 700 }} />
              </Stack>
            </SurfaceCard>

            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(4, minmax(0, 1fr))" }, gap: 2, mb: 2 }}>
              {metrics.map((metric) => (
                <MetricCard key={metric.label} {...metric} />
              ))}
            </Box>

            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" }, gap: 2, mb: 2 }}>
              {drilldownRows.map((panel) => (
                <SurfaceCard key={panel.title} sx={{ p: 1.8, 
                // bgcolor: "#fbfcff", 
                display: "flex", flexDirection: "column", flexShrink: 0, minHeight: 300 }}>
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 1.5,
                      mb: 1,
                    }}
                  >
                    <Typography
                      sx={{
                        fontSize: "0.79rem",
                        fontWeight: 700,
                        color: "#183b7a",
                        letterSpacing: "0.01em",
                        WebkitFontSmoothing: "antialiased",
                        textRendering: "optimizeLegibility",
                      }}
                    >
                      {panel.title}
                    </Typography>
                    <Typography variant="caption" sx={{ color: "#667085", fontWeight: 700, whiteSpace: "nowrap" }}>
                      Live indicators
                    </Typography>
                  </Box>
                  <Box sx={{ mt: 0.85, flex: 1, minHeight: 0, display: "flex" }}>
                    {panel.kind === "area" ? (
  <Box sx={{ width: "100%", height: 220 }}>
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={enterpriseOverviewData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="edbTopAreaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#2d62f1" stopOpacity={0.35} />
            <stop offset="95%" stopColor="#2d62f1" stopOpacity={0.05} />
          </linearGradient>
        </defs>

        <XAxis
          dataKey="name"
          tickLine={false}
          axisLine={{ stroke: "#d1d5db" }}
          tick={{ fill: "#6b7280", fontSize: 11 }}
        />

        <YAxis
          tickLine={false}
          axisLine={{ stroke: "#d1d5db" }}
          tick={{ fill: "#6b7280", fontSize: 11 }}
        />

        <RechartsTooltip
          contentStyle={{
            borderRadius: `${CARD_RADIUS}px`,
            borderColor: "#d1d5db",
            boxShadow: "0 10px 24px rgba(15, 23, 42, 0.08)",
          }}
        />

        <Area
          type="monotone"
          dataKey="value"
          stroke="#2d62f1"
          strokeWidth={3}
          fill="url(#edbTopAreaFill)"
          dot={{ r: 4, stroke: "#ffffff", strokeWidth: 2, fill: "#2d62f1" }}
          activeDot={{ r: 5 }}
        />
              </AreaChart>
            </ResponsiveContainer>
                      </Box>
                    ) : panel.kind === "donut" ? (
                      <MiniPieOrDonut items={panel.items} donut />
                    ) : panel.kind === "pie" ? (
                      <MiniPieOrDonut items={panel.items} />
                    ) : (
                      <MiniBarChart items={panel.items} />
                    )}
                  </Box>
                  {panel.kind === "bars" ? (
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns: "repeat(3, max-content)",
                        justifyContent: "center",
                        alignContent: "end",
                        columnGap: 0.75,
                        rowGap: 0.1,
                        mt: 0.25,
                        mx: "auto",
                        maxWidth: "94%",
                      }}
                    >
                      {panel.items.map((item) => (
                        <Box
                          key={`${panel.title}-${item.label}`}
                          sx={{ display: "flex", alignItems: "center", gap: 0.45, minWidth: 0, flexShrink: 0, whiteSpace: "nowrap" }}
                        >
                          <Box sx={{ width: 9, height: 9, borderRadius: "999px", bgcolor: item.color, flexShrink: 0 }} />
                          <Typography variant="caption" sx={{ color: "#667085", fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", lineHeight: 1 }}>
                            {item.label}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  ) : null}
                </SurfaceCard>
              ))}
            </Box>

            <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", lg: "repeat(3, minmax(0, 1fr))" },
                    gap: 2,
                    mb: 2,
                    alignItems: "stretch",
                  }}
                >
              <SurfaceCard
                  sx={{
                    p: 2,
                    display: "flex",
                    flexDirection: "column",
                    height: "100%",
                    gridColumn: { xs: "span 1", lg: "span 2" },
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: "0.85rem",
                      fontWeight: 700,
                      color: "#183b7a",
                      mb: 0.5,
                      letterSpacing: "0.01em",
                      WebkitFontSmoothing: "antialiased",
                      textRendering: "optimizeLegibility",
                    }}
                  >
                    Business Area Analysis
                  </Typography>

                  <Typography variant="body2" sx={{ color: "#667085", mb: 2 }}>
                    Distribution of repository activity across business areas.
                  </Typography>

                  <Box sx={{ width: "100%", flex: 1, minHeight: 260 }}>
                    <MiniBarChart
                      height={230}
                      showLegend
                      items={
                        businessAreaEntries.length > 0
                          ? businessAreaEntries.slice(0).map(([label, value], index) => ({
                              label,
                              value,
                              color: ["#2d62f1", "#7c3aed", "#15b67a", "#f59e0b", "#ef4d4d"][index % 5],
                            }))
                          : [{ label: "No Data", value: 0, color: "#d1d5db" }]
                      }
                    />
                  </Box>
                </SurfaceCard>

              <SurfaceCard sx={{ p: 2, display: "flex", flexDirection: "column", height: "100%" }}>
                <Typography
                  sx={{
                    fontSize: "0.85rem",
                    fontWeight: 700,
                    color: "#183b7a",
                    mb: 0.5,
                    letterSpacing: "0.01em",
                    WebkitFontSmoothing: "antialiased",
                    textRendering: "optimizeLegibility",
                  }}
                >
                  Executive Snapshot
                </Typography>
                <Typography variant="body2" sx={{ color: "#667085", mb: 2 }}>
                  Key points to review before opening the full workspace.
                </Typography>
                <Stack spacing={1.2} sx={{ flex: 1, minHeight: 0 }}>
                  {snapshotItems.map((item, index) => (
                    <Box
                      key={item}
                      sx={{
                        p: 1.4,
                        borderRadius: `${CARD_RADIUS}px`,
                        // bgcolor: index === 0 ? "rgba(45, 98, 241, 0.08)" : "rgba(15, 23, 42, 0.03)",
                        border: "1px solid rgba(15, 23, 42, 0.08)",
                      }}
                    >
                      <Typography sx={{ fontSize: "0.92rem", color: "#1f2937", lineHeight: 1.35 }}>
                        {item}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              </SurfaceCard>
            </Box>

            <SurfaceCard sx={{ p: 2, mb: 2, display: "flex", flexDirection: "column", flexShrink: 0 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: { xs: "flex-start", md: "center" },
                  justifyContent: "space-between",
                  gap: 2,
                  mb: 0.5,
                  flexWrap: "wrap",
                }}
              >
                <Box>
                  <Typography
                    sx={{
                      fontSize: "0.85rem",
                      fontWeight: 700,
                      color: "#183b7a",
                      mb: 0.5,
                      letterSpacing: "0.01em",
                      WebkitFontSmoothing: "antialiased",
                      textRendering: "optimizeLegibility",
                    }}
                  >
                    Risk Signal Drilldown
                  </Typography>
                  <Typography variant="body2" sx={{ color: "#667085" }}>
                    Exact AI-identified or configured business risk matches behind the dashboard counts.
                  </Typography>
                </Box>
                <Chip label={`${filteredRiskSignalRows.length} rows shown`} variant="outlined" />
              </Box>

              <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mt: 2, mb: 2 }}>
                <TextField
                  fullWidth
                  size="small"
                  label="Search risk signals"
                  value={riskSearch}
                  onChange={(event) => setRiskSearch(event.target.value)}
                  placeholder="Search by reason, file, value..."
                />
                <FormControl size="small" sx={{ minWidth: 220 }}>
                  <InputLabel>Business Area</InputLabel>
                  <Select
                    label="Business Area"
                    value={riskTableBusinessAreaFilter}
                    onChange={(event) => setRiskTableBusinessAreaFilter(String(event.target.value))}
                  >
                    {riskTableBusinessAreaOptions.map((option) => (
                      <MuiMenuItem key={option} value={option}>
                        {option}
                      </MuiMenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" sx={{ minWidth: 180 }}>
                  <InputLabel>Risk Level</InputLabel>
                  <Select
                    label="Risk Level"
                    value={riskTableLevelFilter}
                    onChange={(event) => setRiskTableLevelFilter(String(event.target.value))}
                  >
                    {riskTableLevelOptions.map((option) => (
                      <MuiMenuItem key={option} value={option}>
                        {option}
                      </MuiMenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Stack>

              {sortedRiskSignalRows.length > 0 ? (
                <TableContainer sx={{ maxHeight: 320 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell sortDirection={riskTableSortBy === "risk_level" ? riskTableSortDirection : false}>
                          <TableSortLabel
                            active={riskTableSortBy === "risk_level"}
                            direction={riskTableSortBy === "risk_level" ? riskTableSortDirection : "asc"}
                            onClick={() => handleRiskTableSort("risk_level")}
                          >
                            Risk Level
                          </TableSortLabel>
                        </TableCell>
                        <TableCell sortDirection={riskTableSortBy === "business_area" ? riskTableSortDirection : false}>
                          <TableSortLabel
                            active={riskTableSortBy === "business_area"}
                            direction={riskTableSortBy === "business_area" ? riskTableSortDirection : "asc"}
                            onClick={() => handleRiskTableSort("business_area")}
                          >
                            Business Area
                          </TableSortLabel>
                        </TableCell>
                        <TableCell sortDirection={riskTableSortBy === "label" ? riskTableSortDirection : false}>
                          <TableSortLabel
                            active={riskTableSortBy === "label"}
                            direction={riskTableSortBy === "label" ? riskTableSortDirection : "asc"}
                            onClick={() => handleRiskTableSort("label")}
                          >
                            Escalation Reason
                          </TableSortLabel>
                        </TableCell>
                        <TableCell sortDirection={riskTableSortBy === "file_name" ? riskTableSortDirection : false}>
                          <TableSortLabel
                            active={riskTableSortBy === "file_name"}
                            direction={riskTableSortBy === "file_name" ? riskTableSortDirection : "asc"}
                            onClick={() => handleRiskTableSort("file_name")}
                          >
                            File
                          </TableSortLabel>
                        </TableCell>
                        <TableCell sortDirection={riskTableSortBy === "actual" ? riskTableSortDirection : false}>
                          <TableSortLabel
                            active={riskTableSortBy === "actual"}
                            direction={riskTableSortBy === "actual" ? riskTableSortDirection : "asc"}
                            onClick={() => handleRiskTableSort("actual")}
                          >
                            Observed
                          </TableSortLabel>
                        </TableCell>
                        <TableCell sortDirection={riskTableSortBy === "expected" ? riskTableSortDirection : false}>
                          <TableSortLabel
                            active={riskTableSortBy === "expected"}
                            direction={riskTableSortBy === "expected" ? riskTableSortDirection : "asc"}
                            onClick={() => handleRiskTableSort("expected")}
                          >
                            Expected
                          </TableSortLabel>
                        </TableCell>
                        <TableCell sortDirection={riskTableSortBy === "source" ? riskTableSortDirection : false}>
                          <TableSortLabel
                            active={riskTableSortBy === "source"}
                            direction={riskTableSortBy === "source" ? riskTableSortDirection : "asc"}
                            onClick={() => handleRiskTableSort("source")}
                          >
                            Signal Source
                          </TableSortLabel>
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {pagedRiskSignalRows.map((row, index) => (
                        <TableRow key={`${row.document_id || row.record_id || "risk"}-${index}`} hover>
                          <TableCell>
                            <Chip
                              size="small"
                              color={
                                row.risk_level === "High"
                                  ? "error"
                                  : row.risk_level === "Medium"
                                    ? "warning"
                                    : "success"
                              }
                              label={row.risk_level || "Unclassified"}
                            />
                          </TableCell>
                          <TableCell>{row.business_area || "-"}</TableCell>
                          <TableCell>{row.label || row.compiled_check || "-"}</TableCell>
                          <TableCell>{row.file_name || "-"}</TableCell>
                          <TableCell>{formatValue(row.actual)}</TableCell>
                          <TableCell>{row.operator ? `${row.operator} ${formatValue(row.expected)}` : formatValue(row.expected)}</TableCell>
                          <TableCell>{row.source === "ai_extracted_fact" ? "AI extracted fact" : "Configured rule"}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Box sx={{ minHeight: 160, display: "grid", placeItems: "center", color: "#667085" }}>
                  No matched risk signals to show.
                </Box>
              )}

              {sortedRiskSignalRows.length > 0 ? (
                <TablePagination
                  component="div"
                  count={sortedRiskSignalRows.length}
                  page={riskTablePage}
                  onPageChange={(_, nextPage) => setRiskTablePage(nextPage)}
                  rowsPerPage={10}
                  rowsPerPageOptions={[10]}
                />
              ) : null}

              
            </SurfaceCard>
        </Box>
      <Dialog open={summaryOpen} onClose={() => setSummaryOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Executive Summary</DialogTitle>
        <DialogContent>
            <Typography sx={{ whiteSpace: "pre-line" }}>{summary}</Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setSummaryOpen(false)}>Close</Button>
          </DialogActions>
        </Dialog>
      </Box>
      </OutletPage>

  );
}


// "use client";

// import { useEffect, useMemo, useState } from "react";
// import { useRouter } from "next/navigation";
// import {
//   Box,
//   Grid,
//   Card,
//   CardContent,
//   Typography,
//   Button,
//   Chip,
//   MenuItem,
//   FormControl,
//   InputLabel,
//   Select,
//   Stack,
//   LinearProgress,
//   CircularProgress,
//   useTheme,
//   Table,
//   TableBody,
//   TableCell,
//   TableContainer,
//   TableHead,
//   TableRow,
//   TextField,
//   TablePagination,
// } from "@mui/material";

// import DescriptionIcon from "@mui/icons-material/Description";
// import WarningAmberIcon from "@mui/icons-material/WarningAmber";
// import BusinessIcon from "@mui/icons-material/Business";
// import AccessTimeIcon from "@mui/icons-material/AccessTime";
// import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
// import TrendingUpIcon from "@mui/icons-material/TrendingUp";

// import ModuleGuard from "@/components/auth/ModuleGuard";
// import { OutletPage } from "@/components/layout/OutletPage";
// import apiClient from "@/services/apiClient";
// import { getBusinessAreaCatalog } from "@/services/businessAreaService";

// import {
//   ResponsiveContainer,
//   PieChart,
//   Pie,
//   Cell,
//   Tooltip,
//   BarChart,
//   Bar,
//   XAxis,
//   YAxis,
//   CartesianGrid,
//   Legend,
//   AreaChart,
//   Area,
// } from "recharts";

// type DashboardData = {
//   total_documents?: number;
//   total_repository_items?: number;
//   indexed_documents?: number;
//   total_chunks?: number;
//   high_risk_count?: number;
//   medium_risk_count?: number;
//   low_risk_count?: number;
//   business_areas?: Record<string, number>;
//   business_area_count?: number;
//   risk_distribution?: Record<string, number>;
//   ai_identified_risk_count?: number;
//   configured_rule_risk_count?: number;
//   risk_signal_rows?: Array<{
//     source?: string;
//     signal_origin?: string;
//     business_area?: string;
//     risk_level?: string;
//     label?: string;
//     compiled_check?: string;
//     record_id?: string;
//     document_id?: string;
//     repository_id?: string;
//     file_name?: string;
//     field?: string;
//     operator?: string;
//     expected?: string | number | boolean | string[] | null;
//     actual?: string | number | boolean | string[] | null;
//     record_date?: string | null;
//   }>;
// };

// type BusinessAreaCatalogItem = {
//   slug?: string;
//   name?: string;
//   display_name?: string;
//   repository_count?: number;
//   active_repository_count?: number;
// };

// function MetricCard({
//   title,
//   value,
//   subtitle,
//   icon,
//   severity,
// }: {
//   title: string;
//   value: string | number;
//   subtitle: string;
//   icon: React.ReactNode;
//   severity?: "success" | "warning" | "error" | "info";
// }) {
//   const color =
//     severity === "error"
//       ? "error.main"
//       : severity === "warning"
//       ? "warning.main"
//       : severity === "success"
//       ? "success.main"
//       : "primary.main";

//   return (
//     <Card sx={{ height: "100%", border: "1px solid", borderColor: "divider" }}>
//       <CardContent>
//         <Stack
//           direction="row"
//           sx={{ justifyContent: "space-between", alignItems: "center" }}
//         >
//           <Box>
//             <Typography variant="body2" color="text.secondary">
//               {title}
//             </Typography>

//             <Typography variant="h4" sx={{ fontWeight: 800, mt: 1 }}>
//               {value}
//             </Typography>

//             <Typography variant="caption" color="text.secondary">
//               {subtitle}
//             </Typography>
//           </Box>

//           <Box
//             sx={{
//               width: 52,
//               height: 52,
//               borderRadius: 3,
//               display: "grid",
//               placeItems: "center",
//               bgcolor: color,
//               color: "#fff",
//             }}
//           >
//             {icon}
//           </Box>
//         </Stack>
//       </CardContent>
//     </Card>
//   );
// }

// function AnalyticsCard({
//   title,
//   subtitle,
//   children,
// }: {
//   title: string;
//   subtitle: string;
//   children: React.ReactNode;
// }) {
//   return (
//     <Card sx={{ height: "100%", border: "1px solid", borderColor: "divider" }}>
//       <CardContent>
//         <Typography variant="h6">{title}</Typography>
//         <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
//           {subtitle}
//         </Typography>
//         <Box sx={{ width: "100%", height: 300 }}>{children}</Box>
//       </CardContent>
//     </Card>
//   );
// }

// export default function ExecutiveDashboardPage() {
//   const theme = useTheme();
//   const router = useRouter();

//   const [dashboard, setDashboard] = useState<DashboardData | null>(null);
//   const [summary, setSummary] = useState("");
//   const [loading, setLoading] = useState(true);
//   const [summaryLoading, setSummaryLoading] = useState(false);
//   const [businessAreaFilter, setBusinessAreaFilter] = useState("All");
//   const [riskFilter, setRiskFilter] = useState("All");
//   const [dateRangeFilter, setDateRangeFilter] = useState("All");
//   const [businessAreaCatalog, setBusinessAreaCatalog] = useState<BusinessAreaCatalogItem[]>([]);
//   const [riskSearch, setRiskSearch] = useState("");
//   const [riskTableBusinessAreaFilter, setRiskTableBusinessAreaFilter] = useState("All");
//   const [riskTableLevelFilter, setRiskTableLevelFilter] = useState("All");
//   const [riskTablePage, setRiskTablePage] = useState(0);

//   async function loadDashboard() {
//     setLoading(true);

//     try {
//       const res = await apiClient.get("/api/dashboard", {
//         params: {
//           business_area: businessAreaFilter,
//           risk_level: riskFilter,
//           date_range: dateRangeFilter,
//         },
//       });
//       setDashboard(res.data);
//     } catch (err) {
//       console.error("Dashboard load failed:", err);
//       setDashboard({});
//     } finally {
//       setLoading(false);
//     }
//   }

//   async function generateExecutiveSummary() {
//     setSummaryLoading(true);

//     try {
//       const res = await apiClient.get("/api/dashboard/executive-summary");
//       setSummary(
//         res.data.summary || res.data.executive_summary || res.data.answer || ""
//       );
//     } catch (err) {
//       console.error("Executive summary failed:", err);
//       setSummary("Unable to generate executive summary at this time.");
//     } finally {
//       setSummaryLoading(false);
//     }
//   }

//   useEffect(() => {
//     loadDashboard();
//   }, [businessAreaFilter, riskFilter, dateRangeFilter]);

//   useEffect(() => {
//     let active = true;

//     async function loadBusinessAreaCatalog() {
//       try {
//         const response = await getBusinessAreaCatalog();
//         if (!active) return;
//         setBusinessAreaCatalog(response?.data || []);
//       } catch (err) {
//         console.error("Business area catalog load failed:", err);
//         if (active) {
//           setBusinessAreaCatalog([]);
//         }
//       }
//     }

//     void loadBusinessAreaCatalog();

//     return () => {
//       active = false;
//     };
//   }, []);

//   const totalRepositoryItems =
//     dashboard?.total_repository_items ?? dashboard?.total_documents ?? 0;
//   const indexedDocuments = dashboard?.indexed_documents ?? totalRepositoryItems;
//   const totalChunks = dashboard?.total_chunks ?? 0;

//   const highRisk =
//     dashboard?.high_risk_count ?? dashboard?.risk_distribution?.High ?? 0;

//   const mediumRisk =
//     dashboard?.medium_risk_count ?? dashboard?.risk_distribution?.Medium ?? 0;

//   const lowRisk =
//     dashboard?.low_risk_count ?? dashboard?.risk_distribution?.Low ?? 0;

//   const totalRisk = highRisk + mediumRisk + lowRisk || 1;
//   const aiIdentifiedRiskCount = dashboard?.ai_identified_risk_count ?? 0;
//   const configuredRuleRiskCount = dashboard?.configured_rule_risk_count ?? 0;

//   const riskChartData = [
//     { name: "High Risk", value: highRisk },
//     { name: "Medium Risk", value: mediumRisk },
//     { name: "Low Risk", value: lowRisk },
//   ];
//   const riskSignalRows = dashboard?.risk_signal_rows ?? [];

//   const businessAreaData = Object.entries(dashboard?.business_areas || {}).map(
//     ([name, value]) => ({
//       name,
//       value,
//     })
//   );

//   const businessAreaOptions = useMemo(() => {
//     const options = businessAreaCatalog
//       .filter((item) => (item.active_repository_count ?? item.repository_count ?? 0) > 0)
//       .map((item) => {
//         const value = String(item.slug || item.name || "").trim();
//         const label = String(item.display_name || item.name || item.slug || "").trim();
//         return value && label ? { value, label } : null;
//       })
//       .filter(Boolean) as Array<{ value: string; label: string }>;

//     return [{ value: "All", label: "All" }, ...options];
//   }, [businessAreaCatalog]);

//   const riskTableBusinessAreaOptions = useMemo(() => {
//     const values = Array.from(
//       new Set(
//         riskSignalRows
//           .map((row) => String(row.business_area || "").trim())
//           .filter(Boolean)
//       )
//     ).sort((left, right) => left.localeCompare(right));

//     return ["All", ...values];
//   }, [riskSignalRows]);

//   const filteredRiskSignalRows = useMemo(() => {
//     const normalizedSearch = riskSearch.trim().toLowerCase();

//     return riskSignalRows.filter((row) => {
//       if (
//         riskTableBusinessAreaFilter !== "All" &&
//         String(row.business_area || "").trim() !== riskTableBusinessAreaFilter
//       ) {
//         return false;
//       }

//       if (
//         riskTableLevelFilter !== "All" &&
//         String(row.risk_level || "").trim() !== riskTableLevelFilter
//       ) {
//         return false;
//       }

//       if (!normalizedSearch) {
//         return true;
//       }

//       const searchable = [
//         row.business_area,
//         row.risk_level,
//         row.label,
//         row.compiled_check,
//         row.file_name,
//         row.field,
//         formatValue(row.actual),
//         formatValue(row.expected),
//       ]
//         .join(" ")
//         .toLowerCase();

//       return searchable.includes(normalizedSearch);
//     });
//   }, [
//     riskSearch,
//     riskSignalRows,
//     riskTableBusinessAreaFilter,
//     riskTableLevelFilter,
//   ]);

//   const pagedRiskSignalRows = useMemo(() => {
//     const start = riskTablePage * 5;
//     return filteredRiskSignalRows.slice(start, start + 5);
//   }, [filteredRiskSignalRows, riskTablePage]);

//   const riskOptions = useMemo(() => {
//     const values = Array.from(
//       new Set(
//         [
//           ...Object.keys(dashboard?.risk_distribution || {}),
//           ...riskSignalRows.map((row) => String(row.risk_level || "").trim()),
//         ].filter(Boolean)
//       )
//     ).sort((left, right) => left.localeCompare(right));

//     return ["All", ...values];
//   }, [dashboard?.risk_distribution, riskSignalRows]);
//   const selectedBusinessAreaLabel =
//     businessAreaOptions.find((area) => area.value === businessAreaFilter)?.label ||
//     businessAreaFilter;

//   const dateRangeOptions = [
//     "All",
//     "Last 7 Days",
//     "Last 30 Days",
//     "This Quarter",
//     "This Year",
//   ];

//   const indexCompositionData = [
//     { name: "Indexed Documents", value: indexedDocuments },
//     { name: "Chunks", value: totalChunks },
//   ];

//   const intelligenceTrendData = [
//     { name: "Repository Items", value: totalRepositoryItems },
//     { name: "Indexed Documents", value: indexedDocuments },
//     { name: "Chunks", value: totalChunks },
//     { name: "Risk Items", value: highRisk + mediumRisk + lowRisk },
//     { name: "Business Areas", value: dashboard?.business_area_count ?? businessAreaData.length },
//   ];

//   const chartColors = [
//     theme.palette.error.main,
//     theme.palette.warning.main,
//     theme.palette.success.main,
//     theme.palette.primary.main,
//   ];

//   function formatValue(
//     value: string | number | boolean | string[] | null | undefined
//   ) {
//     if (Array.isArray(value)) return value.join(", ");
//     if (typeof value === "boolean") return value ? "Yes" : "No";
//     if (value === null || value === undefined || value === "") return "-";
//     return String(value);
//   }

//   function slugifyBusinessArea(value: string | undefined) {
//     return String(value || "")
//       .trim()
//       .toLowerCase()
//       .replace(/\s+/g, "_");
//   }

//   function openRiskSignal(row: NonNullable<DashboardData["risk_signal_rows"]>[number]) {
//     if (row.repository_id) {
//       router.push(`/reports/repository-report?repositoryId=${encodeURIComponent(row.repository_id)}`);
//       return;
//     }

//     const businessAreaSlug = slugifyBusinessArea(row.business_area);
//     if (businessAreaSlug) {
//       router.push(`/business-areas/${encodeURIComponent(businessAreaSlug)}`);
//     }
//   }

//   useEffect(() => {
//     setRiskTablePage(0);
//   }, [riskSearch, riskTableBusinessAreaFilter, riskTableLevelFilter]);

//   if (loading) {
//     return (
//       <ModuleGuard moduleName="dashboard" permission="dashboard:view">
//         <Box sx={{ display: "grid", placeItems: "center", minHeight: "60vh" }}>
//           <CircularProgress />
//         </Box>
//       </ModuleGuard>
//     );
//   }

//   return (
//     <ModuleGuard moduleName="dashboard" permission="dashboard:view">
//       <OutletPage
//         title="Executive Dashboard"
//       >
//         <Button
//           variant="contained"
//           startIcon={<AutoAwesomeIcon />}
//           onClick={generateExecutiveSummary}
//           disabled={summaryLoading}
//           sx={{ alignSelf: "flex-end", mb: 2 }}
//         >
//           {summaryLoading ? "Generating..." : "Generate Executive Summary"}
//         </Button>

//       <Card sx={{ border: "1px solid", borderColor: "divider", mb: 2.5 }}>
//         <CardContent sx={{ px: 2.5, pt: 4.5, pb: 4.5 }}>
//           <Stack
//             direction={{ xs: "column", md: "row" }}
//             spacing={2}
//             sx={{ alignItems: { xs: "stretch", md: "center" } }}
//           >
//             <FormControl fullWidth size="small">
//               <InputLabel>Business Area</InputLabel>
//               <Select
//                 label="Business Area"
//                 value={businessAreaFilter}
//                 onChange={(e) => setBusinessAreaFilter(e.target.value)}
//               >
//                 {businessAreaOptions.map((area) => (
//                   <MenuItem key={area.value} value={area.value}>
//                     {area.label}
//                   </MenuItem>
//                 ))}
//               </Select>
//             </FormControl>

//             <FormControl fullWidth size="small">
//               <InputLabel>Risk Level</InputLabel>
//               <Select
//                 label="Risk Level"
//                 value={riskFilter}
//                 onChange={(e) => setRiskFilter(e.target.value)}
//               >
//                 {riskOptions.map((risk) => (
//                   <MenuItem key={risk} value={risk}>
//                     {risk}
//                   </MenuItem>
//                 ))}
//               </Select>
//             </FormControl>

//             <FormControl fullWidth size="small">
//               <InputLabel>Date Range</InputLabel>
//               <Select
//                 label="Date Range"
//                 value={dateRangeFilter}
//                 onChange={(e) => setDateRangeFilter(e.target.value)}
//               >
//                 {dateRangeOptions.map((range) => (
//                   <MenuItem key={range} value={range}>
//                     {range}
//                   </MenuItem>
//                 ))}
//               </Select>
//             </FormControl>

//             <Button
//               variant="outlined"
//               onClick={() => {
//                 setBusinessAreaFilter("All");
//                 setRiskFilter("All");
//                 setDateRangeFilter("All");
//               }}
//               sx={{ minWidth: 120 }}
//             >
//               Reset
//             </Button>
//           </Stack>

//           <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: "wrap" }}>
//             <Chip label={`Business Area: ${selectedBusinessAreaLabel}`} />
//             <Chip label={`Risk: ${riskFilter}`} />
//             <Chip label={`Date Range: ${dateRangeFilter}`} />
//           </Stack>
//         </CardContent>
//       </Card>

//       <Grid container spacing={2.5}>
//         <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
//           <MetricCard
//             title="Repository Items"
//             value={totalRepositoryItems}
//             subtitle="Records available from tenant repositories"
//             icon={<DescriptionIcon />}
//             severity="info"
//           />
//         </Grid>

//         <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
//           <MetricCard
//             title="Knowledge Chunks"
//             value={totalChunks}
//             subtitle="Searchable enterprise knowledge units"
//             icon={<TrendingUpIcon />}
//             severity="success"
//           />
//         </Grid>

//         <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
//           <MetricCard
//             title="High Risk Items"
//             value={highRisk}
//             subtitle="Requires management attention"
//             icon={<WarningAmberIcon />}
//             severity="error"
//           />
//         </Grid>

//         <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
//           <MetricCard
//             title="Business Areas"
//             value={dashboard?.business_area_count ?? businessAreaData.length}
//             subtitle="Detected operational categories"
//             icon={<BusinessIcon />}
//             severity="warning"
//           />
//         </Grid>

//         <Grid size={{ xs: 12, lg: 8 }} sx={{ display: "flex" }}>
//           <Card sx={{ width: "100%", height: "100%", border: "1px solid", borderColor: "divider" }}>
//             <CardContent sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
//               <Stack
//                 direction="row"
//                 sx={{ mb: 2, justifyContent: "space-between" }}
//               >
//                 <Box>
//                   <Typography variant="h6">Risk Distribution</Typography>
//                   <Typography variant="body2" color="text.secondary">
//                     AI-identified risk exposure from extracted business facts and configured checks
//                   </Typography>
//                 </Box>

//                 <Stack direction="row" spacing={1}>
//                   <Chip label="AI-identified" color="warning" size="small" />
//                   <Chip label="Live RAG Index" color="primary" size="small" />
//                 </Stack>
//               </Stack>

//               <Stack spacing={2.2} sx={{ flex: 1, justifyContent: "center" }}>
//                 <Box>
//                   <Stack direction="row" sx={{ justifyContent: "space-between" }}>
//                     <Typography>High Risk</Typography>
//                     <Typography>{highRisk}</Typography>
//                   </Stack>
//                   <LinearProgress
//                     variant="determinate"
//                     value={(highRisk / totalRisk) * 100}
//                     color="error"
//                     sx={{ height: 10, borderRadius: 5, mt: 1 }}
//                   />
//                 </Box>

//                 <Box>
//                   <Stack direction="row" sx={{ justifyContent: "space-between" }}>
//                     <Typography>Medium Risk</Typography>
//                     <Typography>{mediumRisk}</Typography>
//                   </Stack>
//                   <LinearProgress
//                     variant="determinate"
//                     value={(mediumRisk / totalRisk) * 100}
//                     color="warning"
//                     sx={{ height: 10, borderRadius: 5, mt: 1 }}
//                   />
//                 </Box>

//                 <Box>
//                   <Stack direction="row" sx={{ justifyContent: "space-between" }}>
//                     <Typography>Low Risk</Typography>
//                     <Typography>{lowRisk}</Typography>
//                   </Stack>
//                   <LinearProgress
//                     variant="determinate"
//                     value={(lowRisk / totalRisk) * 100}
//                     color="success"
//                     sx={{ height: 10, borderRadius: 5, mt: 1 }}
//                   />
//                 </Box>
//               </Stack>
//             </CardContent>
//           </Card>
//         </Grid>

//         <Grid size={{ xs: 12, lg: 4 }} sx={{ display: "flex", alignItems: "stretch" }}>
//           <Card sx={{ width: "100%", height: "100%", border: "1px solid", borderColor: "divider" }}>
//             <CardContent
//               sx={{
//                 width: "100%",
//                 height: "100%",
//                 display: "flex",
//                 flexDirection: "column",
//                 justifyContent: "center",
//               }}
//             >
//               <Stack
//                 direction="row"
//                 spacing={1}
//                 sx={{ mb: 2, alignItems: "center" }}
//               >
//                 <AccessTimeIcon color="primary" />
//                 <Typography variant="h6">Executive Snapshot</Typography>
//               </Stack>

//               <Stack spacing={1.5}>
//                 <Chip label={`${totalRepositoryItems} repository items tracked`} variant="outlined" />
//                 <Chip label={`${totalChunks} chunks available for search`} variant="outlined" />
//                 <Chip
//                   label={`${highRisk} AI-identified high-risk observations`}
//                   color={highRisk > 0 ? "error" : "success"}
//                 />
//                 <Chip
//                   label={`${aiIdentifiedRiskCount} fact-backed AI signals, ${configuredRuleRiskCount} configured-rule findings`}
//                   variant="outlined"
//                 />
//                 <Chip label="Source-backed AI answers enabled" color="primary" />
//               </Stack>
//             </CardContent>
//           </Card>
//         </Grid>




//         <Grid size={{ xs: 12 }}>
//           <Card sx={{ border: "1px solid", borderColor: "divider" }}>
//             <CardContent>
//               <Stack
//                 direction={{ xs: "column", md: "row" }}
//                 sx={{ mb: 2, justifyContent: "space-between", alignItems: { xs: "flex-start", md: "center" } }}
//                 spacing={1}
//               >
//                 <Box>
//                   <Typography variant="h6">Risk Signal Drill-Down</Typography>
//                   <Typography variant="body2" color="text.secondary">
//                     Exact AI-identified or configured business risk matches behind the dashboard counts
//                   </Typography>
//                 </Box>
//                 <Chip
//                   label={`${filteredRiskSignalRows.length} rows shown`}
//                   variant="outlined"
//                 />
//               </Stack>

//               <Stack
//                 direction={{ xs: "column", md: "row" }}
//                 spacing={1.5}
//                 sx={{ mb: 2 }}
//               >
//                 <TextField
//                   fullWidth
//                   size="small"
//                   label="Search risk signals"
//                   value={riskSearch}
//                   onChange={(event) => setRiskSearch(event.target.value)}
//                   placeholder="Search by reason, file, value..."
//                 />
//                 <FormControl size="small" sx={{ minWidth: 220 }}>
//                   <InputLabel>Business Area</InputLabel>
//                   <Select
//                     label="Business Area"
//                     value={riskTableBusinessAreaFilter}
//                     onChange={(event) => setRiskTableBusinessAreaFilter(String(event.target.value))}
//                   >
//                     {riskTableBusinessAreaOptions.map((option) => (
//                       <MenuItem key={option} value={option}>
//                         {option}
//                       </MenuItem>
//                     ))}
//                   </Select>
//                 </FormControl>
//                 <FormControl size="small" sx={{ minWidth: 180 }}>
//                   <InputLabel>Risk Level</InputLabel>
//                   <Select
//                     label="Risk Level"
//                     value={riskTableLevelFilter}
//                     onChange={(event) => setRiskTableLevelFilter(String(event.target.value))}
//                   >
//                     {riskOptions.map((option) => (
//                       <MenuItem key={option} value={option}>
//                         {option}
//                       </MenuItem>
//                     ))}
//                   </Select>
//                 </FormControl>
//               </Stack>

//               {filteredRiskSignalRows.length > 0 ? (
//                 <TableContainer>
//                   <Table size="small">
//                     <TableHead>
//                       <TableRow>
//                         <TableCell>Risk Level</TableCell>
//                         <TableCell>Business Area</TableCell>
//                         <TableCell>Escalation Reason</TableCell>
//                         <TableCell>File</TableCell>
//                         <TableCell>Observed</TableCell>
//                         <TableCell>Expected</TableCell>
//                         <TableCell>Signal Source</TableCell>
//                       </TableRow>
//                     </TableHead>
//                     <TableBody>
//                       {pagedRiskSignalRows.map((row, index) => (
//                         <TableRow
//                           key={`${row.document_id || row.record_id || "risk"}-${index}`}
//                           hover
//                           onClick={() => openRiskSignal(row)}
//                           sx={{ cursor: row.repository_id || row.business_area ? "pointer" : "default" }}
//                         >
//                           <TableCell>
//                             <Chip
//                               size="small"
//                               color={
//                                 row.risk_level === "High"
//                                   ? "error"
//                                   : row.risk_level === "Medium"
//                                   ? "warning"
//                                   : "success"
//                               }
//                               label={row.risk_level || "Unclassified"}
//                             />
//                           </TableCell>
//                           <TableCell>{row.business_area || "-"}</TableCell>
//                           <TableCell>{row.label || row.compiled_check || "-"}</TableCell>
//                           <TableCell>{row.file_name || "-"}</TableCell>
//                           <TableCell>{formatValue(row.actual)}</TableCell>
//                           <TableCell>
//                             {row.operator ? `${row.operator} ${formatValue(row.expected)}` : formatValue(row.expected)}
//                           </TableCell>
//                           <TableCell>
//                             {row.source === "ai_extracted_fact"
//                               ? "AI extracted fact"
//                               : "Configured rule"}
//                           </TableCell>
//                         </TableRow>
//                       ))}
//                     </TableBody>
//                   </Table>
//                 </TableContainer>
                
//               ) : (
//                 <Stack
//                   sx={{
//                     minHeight: 160,
//                     alignItems: "center",
//                     justifyContent: "center",
//                     textAlign: "center",
//                     color: "text.secondary",
//                     px: 3,
//                   }}
//                 >
//                   <Typography variant="body1" sx={{ fontWeight: 600, color: "text.primary" }}>
//                     No matched risk signals to show
//                   </Typography>
//                   <Typography variant="body2">
//                     Once extracted facts or business-area checks detect a risk, the exact record and reason will appear here.
//                   </Typography>
//                 </Stack>
//               )}

//               {filteredRiskSignalRows.length > 0 ? (
//                 <TablePagination
//                   component="div"
//                   count={filteredRiskSignalRows.length}
//                   page={riskTablePage}
//                   onPageChange={(_, page) => setRiskTablePage(page)}
//                   rowsPerPage={5}
//                   rowsPerPageOptions={[5]}
//                 />
//               ) : null}
//             </CardContent>
//           </Card>
//         </Grid>

        

//         <Grid size={{ xs: 12, lg: 4 }}>
//           <AnalyticsCard
//             title="Risk Donut"
//             subtitle="High, medium and low split across AI-identified business risk signals"
//           >
//             {highRisk + mediumRisk + lowRisk > 0 ? (
//               <ResponsiveContainer>
//                 <PieChart>
//                   <Pie
//                     data={riskChartData}
//                     dataKey="value"
//                     nameKey="name"
//                     innerRadius={65}
//                     outerRadius={100}
//                     paddingAngle={4}
//                   >
//                     {riskChartData.map((entry, index) => (
//                       <Cell key={entry.name} fill={chartColors[index]} />
//                     ))}
//                   </Pie>
//                   <Tooltip />
//                   <Legend />
//                 </PieChart>
//               </ResponsiveContainer>
//             ) : (
//               <Stack
//                 sx={{
//                   height: "100%",
//                   minHeight: 260,
//                   alignItems: "center",
//                   justifyContent: "center",
//                   textAlign: "center",
//                   color: "text.secondary",
//                   px: 3,
//                 }}
//               >
//                 <Typography variant="body1" sx={{ fontWeight: 600, color: "text.primary" }}>
//                   No AI risk signals detected yet
//                 </Typography>
//                 <Typography variant="body2">
//                   Risk distribution will appear here once extracted facts or configured business-area checks identify matched risks.
//                 </Typography>
//               </Stack>
//             )}
//           </AnalyticsCard>
//         </Grid>

        

//         <Grid size={{ xs: 12, lg: 4 }}>
//           <AnalyticsCard
//             title="Business Area Analysis"
//             subtitle="Document intelligence by operating area"
//           >
//             <ResponsiveContainer>
//               <BarChart
//                 data={businessAreaData}
//                 margin={{ top: 8, right: 20, left: 20, bottom: 4 }}
//               >
//                 <CartesianGrid strokeDasharray="3 3" />
//                 <XAxis
//                   dataKey="name"
//                   tick={{ fontSize: 11 }}
//                   tickMargin={8}
//                   padding={{ left: 18, right: 18 }}
//                 />
//                 <YAxis width={28} />
//                 <Tooltip />
//                 <Bar
//                   dataKey="value"
//                   fill={theme.palette.primary.main}
//                   radius={[8, 8, 0, 0]}
//                   maxBarSize={22}
//                 />
//               </BarChart>
//             </ResponsiveContainer>
//           </AnalyticsCard>
//         </Grid>

//         <Grid size={{ xs: 12, lg: 4 }}>
//           <AnalyticsCard
//             title="Index Composition"
//             subtitle="Documents versus searchable chunks"
//           >
//             <ResponsiveContainer>
//               <PieChart>
//                 <Pie
//                   data={indexCompositionData}
//                   dataKey="value"
//                   nameKey="name"
//                   outerRadius={105}
//                   label
//                 >
//                   {indexCompositionData.map((entry, index) => (
//                     <Cell
//                       key={entry.name}
//                       fill={
//                         index === 0
//                           ? theme.palette.primary.main
//                           : theme.palette.success.main
//                       }
//                     />
//                   ))}
//                 </Pie>
//                 <Tooltip />
//                 <Legend />
//               </PieChart>
//             </ResponsiveContainer>
//           </AnalyticsCard>
//         </Grid>

//         <Grid size={{ xs: 12 }}>
//           <AnalyticsCard
//             title="Enterprise Intelligence Overview"
//             subtitle="Current AI knowledge base composition"
//           >
//             <ResponsiveContainer>
//               <AreaChart data={intelligenceTrendData}>
//                 <defs>
//                   <linearGradient id="intelligenceColor" x1="0" y1="0" x2="0" y2="1">
//                     <stop
//                       offset="5%"
//                       stopColor={theme.palette.primary.main}
//                       stopOpacity={0.8}
//                     />
//                     <stop
//                       offset="95%"
//                       stopColor={theme.palette.primary.main}
//                       stopOpacity={0.1}
//                     />
//                   </linearGradient>
//                 </defs>
//                 <CartesianGrid strokeDasharray="3 3" />
//                 <XAxis dataKey="name" />
//                 <YAxis />
//                 <Tooltip />
//                 <Area
//                   type="monotone"
//                   dataKey="value"
//                   stroke={theme.palette.primary.main}
//                   fill="url(#intelligenceColor)"
//                   strokeWidth={3}
//                 />
//               </AreaChart>
//             </ResponsiveContainer>
//           </AnalyticsCard>
//         </Grid>

//         {summary && (
//           <Grid size={{ xs: 12 }}>
//             <Card sx={{ border: "1px solid", borderColor: "divider" }}>
//               <CardContent>
//                 <Typography variant="h6" sx={{ mb: 1 }}>
//                   AI Executive Summary
//                 </Typography>

//                 <Typography
//                   color="text.secondary"
//                   sx={{
//                     whiteSpace: "pre-line",
//                     lineHeight: 1.8,
//                   }}
//                 >
//                   {summary}
//                 </Typography>
//               </CardContent>
//             </Card>
//           </Grid>
//         )}
//       </Grid>
//       </OutletPage>
//     </ModuleGuard>
//   );
// }
