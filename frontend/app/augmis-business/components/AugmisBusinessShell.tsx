"use client";

import type { ReactNode } from "react";

import { Paper, Stack, Typography } from "@mui/material";

import BusinessPageFrame from "./BusinessPageFrame";

export function AugmisBusinessShell({ children }: { children: ReactNode }) {
  return <Stack spacing={1.6}>{children}</Stack>;
}

export function AugmisBusinessOverviewPage() {
  return (
    <BusinessPageFrame
      title="AUGMIS Business Overview"
      description="Enterprise sales intelligence workspace across opportunities, leads, prospects, replies, tasks, connectors, and pipeline execution."
    >
      <Paper elevation={0} sx={{ p: 2, borderRadius: "10px", border: "1px dashed #CBD5E1", bgcolor: "#F8FAFC" }}>
        <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Overview workspace moved to live dashboards</Typography>
        <Typography sx={{ mt: 0.6, color: "#475569" }}>
          Use the active AUGMIS Business routes for live opportunities, pipeline, discovery, reply handling, and task operations.
        </Typography>
      </Paper>
    </BusinessPageFrame>
  );
}

export function AugmisBusinessEmptyStatePage({
  title,
  description,
  primaryLabel,
}: {
  title: string;
  description: string;
  primaryLabel: string;
}) {
  return (
    <BusinessPageFrame title={title} description={description}>
      <Paper
        elevation={0}
        sx={{
          p: 2.1,
          borderRadius: "10px",
          border: "1px dashed #CBD5E1",
          bgcolor: "#F8FAFC",
        }}
      >
        <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{title}</Typography>
        <Typography sx={{ mt: 0.7, color: "#475569" }}>{description}</Typography>
        <Typography sx={{ mt: 1.1, color: "#64748B", fontSize: 13 }}>
          Next focus area: {primaryLabel}
        </Typography>
      </Paper>
    </BusinessPageFrame>
  );
}
