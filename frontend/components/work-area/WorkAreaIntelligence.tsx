"use client";

import { useMemo, useState, type MouseEvent, type ReactNode } from "react";
import {
  Box,
  Button,
  Chip,
  Menu,
  MenuItem,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { OutletPage } from "@/components/layout/OutletPage";

export type WorkAreaChartType = "bar" | "horizontalBar" | "line" | "area" | "pie" | "donut";

export type WorkAreaMetric = {
  title: string;
  value: ReactNode;
  subtitle: string;
  icon: ReactNode;
  accent: string;
  iconColor?: string;
};

export const workAreaChartPalette = [
  "#2563eb",
  "#14b8a6",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4",
];

function normalizePieDonutData(data: Array<Record<string, any>>) {
  const normalized = [...data]
    .map((entry) => ({
      ...entry,
      value: Number(entry?.value || 0),
      name: String(entry?.name || "Unknown"),
    }))
    .filter((entry) => entry.value > 0)
    .sort((a, b) => b.value - a.value);

  if (normalized.length <= 6) {
    return normalized;
  }

  const primary = normalized.slice(0, 6);
  const otherTotal = normalized.slice(6).reduce((sum, entry) => sum + entry.value, 0);

  if (otherTotal > 0) {
    primary.push({ name: "Other", value: otherTotal });
  }

  return primary;
}

function ChartTooltip({
  active,
  payload,
  label,
  valueFormatter,
}: {
  active?: boolean;
  payload?: Array<{ value: number | string; name?: string; payload?: Record<string, any> }>;
  label?: string;
  valueFormatter?: (value: number | string) => string;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <Paper
      elevation={0}
      sx={{
        px: 1.5,
        py: 1.1,
        borderRadius: 2,
        border: "1px solid",
        borderColor: "divider",
        boxShadow: "0 14px 32px rgba(15,23,42,0.14)",
        minWidth: 140,
      }}
    >
      {label ? (
        <Typography variant="body2" sx={{ fontWeight: 700, mb: 0.5 }}>
          {label}
        </Typography>
      ) : null}
      {payload.map((item, index) => (
        <Typography key={`${item.name || "value"}-${index}`} variant="body2" color="text.secondary">
          {(item.name || "Value")}: {valueFormatter ? valueFormatter(item.value) : item.value}
        </Typography>
      ))}
    </Paper>
  );
}

export function WorkAreaMasterPage({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <OutletPage title={title} description={description}>
      <Box className="work-area-page">
        {children}
      </Box>
    </OutletPage>
  );
}

export function WorkAreaMetricStrip({ metrics }: { metrics: WorkAreaMetric[] }) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: {
          xs: "1fr",
          sm: "repeat(2, minmax(0, 1fr))",
          lg: "repeat(3, minmax(0, 1fr))",
          xl: "repeat(6, minmax(0, 1fr))",
        },
        gap: "var(--outlet-grid-gap)",
      }}
    >
      {metrics.map((metric) => (
        <Paper
          key={metric.title}
          className="work-area-metric-card"
          elevation={0}
          sx={{
            p: 2.5,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            height: "100%",
            display: "flex",
            alignItems: "stretch",
            justifyContent: "space-between",
            gap: 2,
          }}
        >
          <Box sx={{ minWidth: 0 }}>
            <Typography className="work-area-metric-card__title" variant="body2" color="text.secondary">
              {metric.title}
            </Typography>
            <Typography className="work-area-metric-card__value" variant="h4" sx={{ mt: 1.1, fontWeight: 800, lineHeight: 1 }}>
              {metric.value}
            </Typography>
            <Typography className="work-area-metric-card__subtitle" variant="body2" color="text.secondary" sx={{ mt: 1.2 }}>
              {metric.subtitle}
            </Typography>
          </Box>

          <Box
            sx={{
              width: 30,
              height: 30,
              borderRadius: "50%",
              bgcolor: metric.accent,
              color: metric.iconColor || "#fff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              boxShadow: `0 8px 14px ${metric.accent}20`,
              "& svg": {
                fontSize: 18,
              },
            }}
          >
            {metric.icon}
          </Box>
        </Paper>
      ))}
    </Box>
  );
}

export function WorkAreaChartCard({
  title,
  subtitle,
  children,
  actions,
  height = 312,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
  height?: number;
}) {
  return (
    <Paper
      className="work-area-chart-card"
      elevation={0}
      sx={{
        p: 2.5,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
        height,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        sx={{ justifyContent: "space-between", alignItems: { xs: "flex-start", sm: "flex-start" }, gap: 1.2 }}
      >
        <Typography className="work-area-chart-card__title" variant="h6" sx={{ fontWeight: 800 }}>
          {title}
        </Typography>
        {actions ? <Box sx={{ flexShrink: 0 }}>{actions}</Box> : null}
      </Stack>
      {subtitle ? (
        <Typography className="work-area-chart-card__subtitle" variant="body2" color="text.secondary" sx={{ mt: 0.6 }}>
          {subtitle}
        </Typography>
      ) : null}
      <Box sx={{ flexGrow: 1, minHeight: 0, mt: 1.35 }}>
        {children}
      </Box>
    </Paper>
  );
}

export function WorkAreaChartTypeSelector({
  value,
  onChange,
  options = ["bar", "horizontalBar", "line", "area", "pie", "donut"],
}: {
  value: WorkAreaChartType;
  onChange: (next: WorkAreaChartType) => void;
  options?: WorkAreaChartType[];
}) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const labelMap: Record<WorkAreaChartType, string> = {
    bar: "Bar",
    horizontalBar: "Horizontal",
    line: "Line",
    area: "Area",
    pie: "Pie",
    donut: "Donut",
  };
  const open = Boolean(anchorEl);

  function handleOpen(event: MouseEvent<HTMLElement>) {
    setAnchorEl(event.currentTarget);
  }

  function handleClose() {
    setAnchorEl(null);
  }

  return (
    <>
      <Button
        variant="outlined"
        size="small"
        endIcon={<KeyboardArrowDownIcon />}
        onClick={handleOpen}
        sx={{ minWidth: 138, justifyContent: "space-between", fontWeight: 700 }}
      >
        {labelMap[value]}
      </Button>
      <Menu anchorEl={anchorEl} open={open} onClose={handleClose}>
        {options.map((option) => (
          <MenuItem
            key={option}
            selected={option === value}
            onClick={() => {
              onChange(option);
              handleClose();
            }}
          >
            {labelMap[option]}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}

export function WorkAreaBarSeries({
  data,
  color = "#2563eb",
  valueFormatter,
}: {
  data: Array<Record<string, any>>;
  color?: string;
  valueFormatter?: (value: number | string) => string;
}) {
  const tickFormatter = (value: string) => {
    const text = String(value || "");
    return text.length > 12 ? `${text.slice(0, 10)}...` : text;
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={data}
        margin={{ top: 8, right: 10, left: 10, bottom: 8 }}
        barCategoryGap="24%"
      >
        <defs>
          <linearGradient id={`barGradient-${color.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={1} />
            <stop offset="100%" stopColor={color} stopOpacity={0.72} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#dbe5f1" strokeDasharray="4 4" vertical={false} />
        <XAxis
          dataKey="name"
          tickLine={false}
          axisLine={false}
          tick={{ fill: "#64748b", fontSize: 10 }}
          tickFormatter={tickFormatter}
          interval={0}
          minTickGap={12}
          angle={-18}
          textAnchor="end"
          height={40}
        />
        <YAxis
          allowDecimals={false}
          tickLine={false}
          axisLine={false}
          tick={{ fill: "#64748b", fontSize: 11 }}
          width={34}
        />
        <Tooltip content={<ChartTooltip valueFormatter={valueFormatter} />} cursor={{ fill: "rgba(37,99,235,0.08)" }} />
        <Bar
          dataKey="value"
          fill={`url(#barGradient-${color.replace("#", "")})`}
          radius={[10, 10, 0, 0]}
          maxBarSize={44}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function WorkAreaFlexibleSeries({
  data,
  type,
  color = "#2563eb",
  valueFormatter,
}: {
  data: Array<Record<string, any>>;
  type: WorkAreaChartType;
  color?: string;
  valueFormatter?: (value: number | string) => string;
}) {
  const pieData = useMemo(() => normalizePieDonutData(data), [data]);
  const tickFormatter = (value: string) => {
    const text = String(value || "");
    return text.length > 12 ? `${text.slice(0, 10)}...` : text;
  };
  const gradientId = `workAreaSeries-${type}-${color.replace("#", "")}`;

  if (type === "donut" || type === "pie") {
    return (
      <Stack sx={{ height: "100%" }}>
        <Box sx={{ flexGrow: 1, minHeight: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart margin={{ top: 0, right: 8, left: 8, bottom: 0 }}>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="48%"
                innerRadius={type === "donut" ? 62 : 0}
                outerRadius={88}
                paddingAngle={type === "donut" ? 2 : 1}
                stroke="none"
              >
                {pieData.map((entry, index) => (
                  <Cell
                    key={`${entry.name || "slice"}-${index}`}
                    fill={workAreaChartPalette[index % workAreaChartPalette.length]}
                  />
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip valueFormatter={valueFormatter} />} />
            </PieChart>
          </ResponsiveContainer>
        </Box>

        <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", mt: 0.75 }}>
          {pieData.map((entry, index) => (
            <Chip
              key={`${entry.name || "legend"}-${index}`}
              size="small"
              label={`${entry.name}: ${valueFormatter ? valueFormatter(entry.value) : entry.value}`}
              sx={{
                bgcolor: `${workAreaChartPalette[index % workAreaChartPalette.length]}14`,
                color: workAreaChartPalette[index % workAreaChartPalette.length],
                border: "1px solid",
                borderColor: `${workAreaChartPalette[index % workAreaChartPalette.length]}33`,
              }}
            />
          ))}
        </Stack>
      </Stack>
    );
  }

  if (type === "horizontalBar") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 8, right: 14, left: 2, bottom: 4 }}
          barCategoryGap="20%"
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={color} stopOpacity={0.9} />
              <stop offset="100%" stopColor={color} stopOpacity={0.68} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#dbe5f1" strokeDasharray="4 4" horizontal={true} vertical={false} />
          <XAxis
            type="number"
            allowDecimals={false}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#64748b", fontSize: 11 }}
          />
          <YAxis
            type="category"
            dataKey="name"
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#64748b", fontSize: 11 }}
            tickFormatter={tickFormatter}
            width={98}
          />
          <Tooltip content={<ChartTooltip valueFormatter={valueFormatter} />} cursor={{ fill: "rgba(37,99,235,0.08)" }} />
          <Bar dataKey="value" fill={`url(#${gradientId})`} radius={[0, 10, 10, 0]} maxBarSize={28} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (type === "line") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 10, left: 10, bottom: 8 }}>
          <CartesianGrid stroke="#dbe5f1" strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="name"
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={tickFormatter}
            interval={0}
            minTickGap={12}
            angle={-18}
            textAnchor="end"
            height={40}
          />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: "#64748b", fontSize: 11 }} width={34} />
          <Tooltip content={<ChartTooltip valueFormatter={valueFormatter} />} />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (type === "area") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 10, left: 10, bottom: 8 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.44} />
              <stop offset="100%" stopColor={color} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#dbe5f1" strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="name"
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={tickFormatter}
            interval={0}
            minTickGap={12}
            angle={-18}
            textAnchor="end"
            height={40}
          />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: "#64748b", fontSize: 11 }} width={34} />
          <Tooltip content={<ChartTooltip valueFormatter={valueFormatter} />} />
          <Area type="monotone" dataKey="value" stroke={color} fill={`url(#${gradientId})`} strokeWidth={3} />
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  return <WorkAreaBarSeries data={data} color={color} valueFormatter={valueFormatter} />;
}

export function WorkAreaDonutSeries({
  data,
  valueFormatter,
}: {
  data: Array<Record<string, any>>;
  valueFormatter?: (value: number | string) => string;
}) {
  return (
    <Stack sx={{ height: "100%" }}>
      <Box sx={{ flexGrow: 1, minHeight: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart margin={{ top: 8, right: 16, left: 16, bottom: 8 }}>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={72}
              outerRadius={112}
              paddingAngle={3}
              stroke="none"
            >
              {data.map((entry, index) => (
                <Cell
                  key={`${entry.name || "slice"}-${index}`}
                  fill={workAreaChartPalette[index % workAreaChartPalette.length]}
                />
              ))}
            </Pie>
            <Tooltip content={<ChartTooltip valueFormatter={valueFormatter} />} />
          </PieChart>
        </ResponsiveContainer>
      </Box>

      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", mt: 1.5 }}>
        {data.map((entry, index) => (
          <Chip
            key={`${entry.name || "legend"}-${index}`}
            size="small"
            label={`${entry.name}: ${valueFormatter ? valueFormatter(entry.value) : entry.value}`}
            sx={{
              bgcolor: `${workAreaChartPalette[index % workAreaChartPalette.length]}14`,
              color: workAreaChartPalette[index % workAreaChartPalette.length],
              border: "1px solid",
              borderColor: `${workAreaChartPalette[index % workAreaChartPalette.length]}33`,
            }}
          />
        ))}
      </Stack>
    </Stack>
  );
}

export function WorkAreaInsightsCard({
  title,
  subtitle,
  insights,
}: {
  title: string;
  subtitle?: string;
  insights: string[];
}) {
  return (
    <Paper
      className="work-area-insights-card"
      elevation={0}
      sx={{
        mt: 3,
        p: 2.5,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Typography className="work-area-insights-card__title" variant="h6" sx={{ fontWeight: 800 }}>
        {title}
      </Typography>

      {subtitle ? (
        <Typography className="work-area-insights-card__subtitle" variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2 }}>
          {subtitle}
        </Typography>
      ) : null}

      <Stack spacing={1.15}>
        {insights.map((insight, index) => (
          <Stack key={index} direction="row" spacing={1.2} sx={{ alignItems: "flex-start" }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                bgcolor: workAreaChartPalette[index % workAreaChartPalette.length],
                mt: "9px",
                flexShrink: 0,
              }}
            />
            <Typography className="work-area-insights-card__item">{insight}</Typography>
          </Stack>
        ))}
      </Stack>
    </Paper>
  );
}

export function WorkAreaRegisterCard({
  title,
  loadingText,
  children,
  footerNote,
}: {
  title: string;
  loadingText?: string;
  children: ReactNode;
  footerNote?: string | null;
}) {
  return (
    <Paper
      className="work-area-register-card"
      elevation={0}
      sx={{
        mt: 3,
        p: 2.5,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Typography className="work-area-register-card__title" variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
        {title}
      </Typography>

      {loadingText ? (
        <Typography className="work-area-register-card__loading" variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {loadingText}
        </Typography>
      ) : null}

      {children}

      {footerNote ? (
        <Typography className="work-area-register-card__footer" variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
          {footerNote}
        </Typography>
      ) : null}
    </Paper>
  );
}
