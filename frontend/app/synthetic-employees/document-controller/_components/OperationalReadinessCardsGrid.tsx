"use client";

import { useState, type MouseEvent } from "react";
import Link from "next/link";

import {
  Box,
  Button,
  Collapse,
  Grid,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

import type {
  OperationalMetricRow,
  OperationalSection,
} from "./useDocumentControllerOperationalData";

function summarizeRows(rows: OperationalMetricRow[]) {
  return rows
    .map((row) => row.value)
    .filter((value): value is number => typeof value === "number")
    .reduce((sum, value) => sum + value, 0);
}

function statusLabel(section: OperationalSection) {
  return summarizeRows(section.rows) > 0 ? "Live" : "Not Started";
}

function statusBg(section: OperationalSection) {
  return summarizeRows(section.rows) > 0 ? "rgba(34,197,94,0.16)" : "rgba(255,255,255,0.18)";
}

function statusColor(section: OperationalSection) {
  return summarizeRows(section.rows) > 0 ? "#DCFCE7" : "#FFFFFF";
}

function compactLabel(label: string) {
  return label.replace(/\s+/g, " ").trim().split(" ").slice(0, 2).join(" ");
}

function RowList({
  rows,
}: {
  rows: OperationalMetricRow[];
}) {
  return (
    <>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.9fr) 70px 76px",
          columnGap: 1.25,
          px: 1,
          pb: 0.65,
          borderBottom: "1px solid #e2e8f0",
        }}
      >
        <Typography sx={{ fontSize: 9, fontWeight: 700, color: "#94a3b8", letterSpacing: ".07em" }}>
          READINESS LIST
        </Typography>
        <Typography sx={{ fontSize: 9, fontWeight: 700, color: "#94a3b8", letterSpacing: ".07em" }}>
          COUNT
        </Typography>
        <Typography sx={{ fontSize: 9, fontWeight: 700, color: "#94a3b8", letterSpacing: ".07em" }}>
          ACTION
        </Typography>
      </Box>

      <Stack spacing={0}>
        {rows.map((row, index) => (
          <Box
            key={`${row.label}-${index}`}
            sx={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.9fr) 70px 76px",
              columnGap: 1.25,
              alignItems: "center",
              px: 1,
              py: 0.8,
              minHeight: 34,
              borderBottom: index === rows.length - 1 ? "none" : "1px solid #e2e8f0",
            }}
          >
            <Stack spacing={0.15} sx={{ minWidth: 0 }}>
              <Stack direction="row" spacing={0.9} sx={{ alignItems: "flex-start", minWidth: 0 }}>
                <Box
                  sx={{
                    width: 7,
                    height: 7,
                    mt: 0.45,
                    borderRadius: "50%",
                    flexShrink: 0,
                    bgcolor: "#94a3b8",
                  }}
                />
                <Typography
                  sx={{
                    fontSize: 11,
                    fontWeight: 500,
                    lineHeight: 1.2,
                    color: "#1e293b",
                    wordBreak: "break-word",
                  }}
                >
                  {row.label}
                </Typography>
              </Stack>
              {row.detail ? (
                <Typography sx={{ pl: 2, fontSize: 9, color: "#94a3b8", lineHeight: 1.2 }}>
                  {row.detail}
                </Typography>
              ) : null}
            </Stack>

            <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#64748b" }}>
              {row.value ?? "-"}
            </Typography>

            {row.href ? (
              <Button
                component={Link}
                href={row.href}
                size="small"
                variant="text"
                sx={{
                  minWidth: 0,
                  px: 0,
                  justifyContent: "flex-start",
                  fontSize: 10,
                  fontWeight: 600,
                  textTransform: "none",
                }}
              >
                Open
              </Button>
            ) : (
              <Typography sx={{ fontSize: 10, fontWeight: 600, color: "#94a3b8" }}>-</Typography>
            )}
          </Box>
        ))}
      </Stack>
    </>
  );
}

function OperationalReadinessCard({ section }: { section: OperationalSection }) {
  const [expanded, setExpanded] = useState(false);
  const totalValue = summarizeRows(section.rows);
  const miniRows = section.rows.slice(0, 4);
  const deliveryRate = section.rows.length
    ? Math.round(((section.summary[1]?.value || 0) / section.rows.length) * 100)
    : 0;
  const toggleExpanded = () => setExpanded((value) => !value);
  const handleCardClick = (event: MouseEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement;

    if (target.closest("a,button")) {
      return;
    }

    toggleExpanded();
  };

  return (
    <Paper
      variant="outlined"
      onClick={handleCardClick}
      sx={{
        overflow: "hidden",
        borderRadius: "12px",
        border: "2px solid #e2e8f0",
        bgcolor: "#fff",
        boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        cursor: "pointer",
      }}
    >
      <Box
        sx={{
          minHeight: 100,
        }}
      >
        <Box
          sx={{
            backgroundImage: "linear-gradient(135deg, #374151 0%, #6B7280 100%)",
            px: 1.65,
            py: 1.1,
            minHeight: 154,
            display: "grid",
            gridTemplateRows: "auto auto auto",
          }}
        >
          <Stack direction="row" spacing={0.75} sx={{ alignItems: "flex-start", justifyContent: "space-between", mb: 0.8 }}>
            <Typography
              sx={{
                fontSize: 12,
                fontWeight: 600,
                color: "#fff",
                textTransform: "uppercase",
                letterSpacing: "0.12em",
                lineHeight: 1.2,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                flex: 1,
                minWidth: 0,
                minHeight: 24,
                display: "flex",
                alignItems: "flex-start",
              }}
            >
              {section.title}
            </Typography>

            <Box
              sx={{
                fontSize: 8,
                fontWeight: 800,
                background: statusBg(section),
                color: statusColor(section),
                px: 0.9,
                py: 0.35,
                borderRadius: "7px",
                whiteSpace: "nowrap",
                border: "1px solid rgba(255,255,255,0.22)",
              }}
            >
              {statusLabel(section)}
            </Box>
          </Stack>

          <Typography
            sx={{
              fontSize: 8,
              color: "rgba(255,255,255,0.45)",
              mb: 0.9,
              minHeight: 8,
            }}
          >
            {section.mode === "live" ? "Operational list" : "Planned handover list"}
          </Typography>

          <Stack direction="row" spacing={0} sx={{ alignItems: "stretch", mb: 0.9, minHeight: 42 }}>
            {section.summary.map((metric, index) => (
              <Stack
                key={`${section.key}-${metric.label}`}
                spacing={0.4}
                sx={{
                  flex: 1,
                  textAlign: "center",
                  borderLeft: index === 0 ? "none" : "1px solid rgba(255,255,255,0.15)",
                }}
              >
                <Typography
                  sx={{
                    fontSize: 7,
                    fontWeight: 700,
                    color: "rgba(255,255,255,0.5)",
                    textTransform: "uppercase",
                    letterSpacing: "0.07em",
                  }}
                >
                  {metric.label}
                </Typography>
                <Typography
                  sx={{
                    fontSize: 26,
                    fontWeight: 900,
                    color: "#fff",
                    lineHeight: 1,
                    letterSpacing: "-0.02em",
                    textShadow: "0 0 12px rgba(255,255,255,0.28), 0 1px 3px rgba(0,0,0,0.3)",
                  }}
                >
                  {metric.value}
                </Typography>
              </Stack>
            ))}
          </Stack>

          <Box sx={{ mt: 0.2, alignSelf: "end" }}>
            <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 0.25 }}>
              <Typography sx={{ fontSize: 8, color: "rgba(255,255,255,0.55)", letterSpacing: "0.03em" }}>
                Delivery Rate
              </Typography>
              <Typography sx={{ fontSize: 9, fontWeight: 700, color: "#fff" }}>
                {deliveryRate}%
              </Typography>
            </Stack>
            <Box sx={{ height: 7, bgcolor: "rgba(255,255,255,0.12)", borderRadius: "4px", overflow: "hidden" }}>
              <Box
                sx={{
                  height: 7,
                  borderRadius: "4px",
                  width: `${deliveryRate}%`,
                  bgcolor: "#fff",
                  opacity: 0.9,
                }}
              />
            </Box>
            <Stack direction="row" sx={{ justifyContent: "space-between", mt: 0.15 }}>
              <Typography sx={{ fontSize: 7, color: "rgba(255,255,255,0.3)" }}>0</Typography>
              <Typography sx={{ fontSize: 7, color: "rgba(255,255,255,0.3)" }}>100%</Typography>
            </Stack>
          </Box>
        </Box>

        <Box
          sx={{
            px: 1.5,
            py: 0.65,
            bgcolor: "#f8fafc",
            borderTop: "1px solid #f1f5f9",
            minHeight: 52,
          }}
        >
          <Stack direction="row" spacing={0.75}>
            {miniRows.map((row) => (
              <Box
                key={`${section.key}-mini-${row.label}`}
                sx={{
                  flex: 1,
                  minWidth: 0,
                  minHeight: 38,
                  display: "grid",
                  gridTemplateRows: "8px 24px",
                  rowGap: 3,
                }}
              >
                <Box sx={{ height: 8, borderRadius: "4px", bgcolor: "#e2e8f0", mb: 0.35 }} />
                <Typography
                  sx={{
                    fontSize: 8,
                    fontWeight: 700,
                    color: "#94a3b8",
                    textTransform: "uppercase",
                    lineHeight: 1.1,
                    minHeight: 24,
                    display: "flex",
                    alignItems: "flex-start",
                  }}
                >
                  {compactLabel(row.label)}
                </Typography>
              </Box>
            ))}
          </Stack>
        </Box>
      </Box>

      <Collapse in={expanded} timeout="auto" unmountOnExit>
        <Box sx={{ px: 2, py: 1.5, bgcolor: "#f8fafc" }}>
          <RowList rows={section.rows} />

          <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center", pt: 1.25 }}>
            <Typography sx={{ fontSize: 10, color: "#64748b" }}>
              {section.mode === "live" ? `${totalValue} total signals` : "Configuration-driven handover checklist"}
            </Typography>
            <Button component={Link} href={section.href} variant="outlined" size="small">
              Open Section
            </Button>
          </Stack>
        </Box>
      </Collapse>
    </Paper>
  );
}

export function OperationalReadinessCardsGrid({
  sections,
}: {
  sections: OperationalSection[];
}) {
  return (
    <Grid container spacing={2} sx={{ alignItems: "flex-start" }}>
      {sections.map((section) => (
        <Grid key={section.key} size={{ xs: 12, md: 6, xl: 3 }} sx={{ display: "flex" }}>
          <OperationalReadinessCard section={section} />
        </Grid>
      ))}
    </Grid>
  );
}
