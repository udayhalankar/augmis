"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import ArrowForwardRoundedIcon from "@mui/icons-material/ArrowForwardRounded";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import LanOutlinedIcon from "@mui/icons-material/LanOutlined";
import TaskAltOutlinedIcon from "@mui/icons-material/TaskAltOutlined";
import TimelineOutlinedIcon from "@mui/icons-material/TimelineOutlined";
import {
  Box,
  Button,
  Chip,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

import { OutletPage } from "@/components/layout/OutletPage";

type RouteItem = {
  label: string;
  href: string;
  blurb: string;
};

const routeItems: RouteItem[] = [
  { label: "Overview", href: "/augmis-business", blurb: "Module summary and launch surface" },
  {
    label: "Opportunities",
    href: "/augmis-business/opportunities",
    blurb: "Target accounts and active opportunities",
  },
  {
    label: "Leads",
    href: "/augmis-business/leads",
    blurb: "Lead intake, scoring, and qualification",
  },
  {
    label: "Prospects",
    href: "/augmis-business/prospects",
    blurb: "Prospect research and segmentation",
  },
  {
    label: "Pipeline",
    href: "/augmis-business/pipeline",
    blurb: "Stage progression and conversion tracking",
  },
  {
    label: "Replies",
    href: "/augmis-business/replies",
    blurb: "Inbound outreach responses and handling",
  },
  {
    label: "Tasks",
    href: "/augmis-business/tasks",
    blurb: "Operator tasks and follow-up actions",
  },
  {
    label: "Connectors",
    href: "/augmis-business/connectors",
    blurb: "Source systems and ingestion controls",
  },
  {
    label: "Control Centre",
    href: "/augmis-business/control-centre",
    blurb: "Guardrails, orchestration, and audit posture",
  },
];

const capabilityCards = [
  {
    title: "Opportunity Mapping",
    description: "Coordinate account discovery, qualification, and pipeline visibility.",
    icon: <TimelineOutlinedIcon sx={{ color: "#2563EB" }} />,
  },
  {
    title: "Connector Readiness",
    description: "Prepare CRM, email, and research connectors without changing backend behavior yet.",
    icon: <LanOutlinedIcon sx={{ color: "#0F766E" }} />,
  },
  {
    title: "Operator Workflow",
    description: "Reserve dedicated surfaces for tasks, approvals, and response triage.",
    icon: <TaskAltOutlinedIcon sx={{ color: "#B45309" }} />,
  },
];

export function AugmisBusinessShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <Stack spacing={3}>
      <Paper
        elevation={0}
        sx={{
          borderRadius: 3,
          border: "1px solid #D9E2EC",
          background:
            "linear-gradient(135deg, rgba(13,45,78,0.98) 0%, rgba(25,93,161,0.95) 58%, rgba(222,239,255,0.92) 100%)",
          color: "#F8FAFC",
          overflow: "hidden",
        }}
      >
        <Stack
          direction={{ xs: "column", lg: "row" }}
          spacing={2}
          sx={{ px: { xs: 2.5, md: 3 }, py: { xs: 2.5, md: 3 } }}
        >
          <Box sx={{ flex: 1 }}>
            <Chip
              label="Phase 1 Shell"
              size="small"
              sx={{
                mb: 1.5,
                bgcolor: "rgba(255,255,255,0.14)",
                color: "#F8FAFC",
                border: "1px solid rgba(255,255,255,0.18)",
              }}
            />
            <Typography variant="h4" sx={{ fontWeight: 700, letterSpacing: "-0.02em" }}>
              AUGMIS Business Development Agent
            </Typography>
            <Typography sx={{ mt: 1.25, maxWidth: 760, color: "rgba(248,250,252,0.88)" }}>
              This shell reuses the enterprise application frame, authentication flow, and
              protected-route behavior. Domain logic, connectors, and persistence remain deferred
              to later phases.
            </Typography>
          </Box>
          <Stack spacing={1.25} sx={{ minWidth: { lg: 320 }, alignSelf: "stretch" }}>
            {capabilityCards.map((card) => (
              <Paper
                key={card.title}
                elevation={0}
                sx={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 1.25,
                  px: 1.5,
                  py: 1.25,
                  borderRadius: 2.5,
                  bgcolor: "rgba(255,255,255,0.9)",
                  color: "#0F172A",
                  border: "1px solid rgba(255,255,255,0.5)",
                }}
              >
                <Box sx={{ mt: 0.15 }}>{card.icon}</Box>
                <Box>
                  <Typography sx={{ fontWeight: 700, fontSize: 14 }}>{card.title}</Typography>
                  <Typography sx={{ mt: 0.35, fontSize: 13, color: "#475569" }}>
                    {card.description}
                  </Typography>
                </Box>
              </Paper>
            ))}
          </Stack>
        </Stack>
      </Paper>

      <Paper
        elevation={0}
        sx={{
          borderRadius: 3,
          border: "1px solid #E2E8F0",
          px: { xs: 1.25, md: 1.5 },
          py: 1.25,
        }}
      >
        <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
          {routeItems.map((item) => {
            const selected =
              pathname === item.href ||
              (item.href !== "/augmis-business" && pathname.startsWith(`${item.href}/`));

            return (
              <Button
                key={item.href}
                component={Link}
                href={item.href}
                variant={selected ? "contained" : "text"}
                color={selected ? "primary" : "inherit"}
                sx={{
                  borderRadius: 999,
                  px: 1.6,
                  textTransform: "none",
                  fontWeight: 600,
                  color: selected ? "#FFFFFF" : "#334155",
                  bgcolor: selected ? "#0F4C81" : "#F8FAFC",
                  border: selected ? "1px solid #0F4C81" : "1px solid #E2E8F0",
                  "&:hover": {
                    bgcolor: selected ? "#0B3B63" : "#EFF6FF",
                  },
                }}
              >
                {item.label}
              </Button>
            );
          })}
        </Stack>
      </Paper>

      {children}
    </Stack>
  );
}

export function AugmisBusinessOverviewPage() {
  return (
    <OutletPage
      title="AUGMIS Business Development Agent"
      description="Phase 1 route shell for opportunities, lead operations, prospecting, pipeline visibility, replies, tasks, connectors, and control-centre workflows."
    >
      <Stack spacing={2.5}>
        <Paper
          elevation={0}
          sx={{
            borderRadius: 3,
            border: "1px solid #E2E8F0",
            p: { xs: 2.25, md: 3 },
          }}
        >
          <Stack spacing={1.25}>
            <Typography variant="h6" sx={{ fontWeight: 700, color: "#0F172A" }}>
              Module shell established
            </Typography>
            <Typography sx={{ color: "#475569", maxWidth: 840 }}>
              The frontend route set is now reserved inside the enterprise shell. Backend APIs,
              database models, connector execution, and AI-driven workflows have not been added in
              this phase.
            </Typography>
          </Stack>
        </Paper>

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
          {routeItems
            .filter((item) => item.href !== "/augmis-business")
            .map((item) => (
              <Paper
                key={item.href}
                elevation={0}
                sx={{
                  p: 2.25,
                  borderRadius: 3,
                  border: "1px solid #E2E8F0",
                  minHeight: 176,
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <Box
                  sx={{
                    width: 42,
                    height: 42,
                    borderRadius: 2.5,
                    display: "grid",
                    placeItems: "center",
                    bgcolor: "#E0F2FE",
                    color: "#0F4C81",
                    mb: 1.5,
                  }}
                >
                  <HubOutlinedIcon fontSize="small" />
                </Box>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{item.label}</Typography>
                <Typography sx={{ mt: 0.9, color: "#475569", flex: 1 }}>{item.blurb}</Typography>
                <Button
                  component={Link}
                  href={item.href}
                  endIcon={<ArrowForwardRoundedIcon />}
                  sx={{
                    mt: 2,
                    alignSelf: "flex-start",
                    px: 0,
                    textTransform: "none",
                    fontWeight: 700,
                  }}
                >
                  Open section
                </Button>
              </Paper>
            ))}
        </Box>
      </Stack>
    </OutletPage>
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
    <OutletPage title={title} description={description}>
      <Paper
        elevation={0}
        sx={{
          borderRadius: 3,
          border: "1px solid #E2E8F0",
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            px: { xs: 2.25, md: 3 },
            py: { xs: 2.5, md: 3.25 },
            background:
              "linear-gradient(180deg, rgba(239,246,255,0.9) 0%, rgba(248,250,252,0.95) 100%)",
            borderBottom: "1px solid #E2E8F0",
          }}
        >
          <Chip
            label="Planned"
            size="small"
            sx={{
              mb: 1.5,
              bgcolor: "#FFF7ED",
              color: "#C2410C",
              border: "1px solid #FED7AA",
            }}
          />
          <Typography variant="h5" sx={{ fontWeight: 700, color: "#0F172A" }}>
            {title}
          </Typography>
          <Typography sx={{ mt: 1, maxWidth: 760, color: "#475569" }}>{description}</Typography>
        </Box>

        <Stack
          direction={{ xs: "column", lg: "row" }}
          spacing={2}
          sx={{ px: { xs: 2.25, md: 3 }, py: { xs: 2.25, md: 2.75 } }}
        >
          <Paper
            elevation={0}
            sx={{
              flex: 1,
              p: 2,
              borderRadius: 2.5,
              border: "1px solid #E2E8F0",
              bgcolor: "#FFFFFF",
            }}
          >
            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
              Phase 1 status
            </Typography>
            <Typography sx={{ mt: 0.9, color: "#475569" }}>
              The route shell is active and aligned to the enterprise layout. Data services,
              forms, and automation controls will be introduced after architecture approval.
            </Typography>
          </Paper>

          <Paper
            elevation={0}
            sx={{
              flex: 1,
              p: 2,
              borderRadius: 2.5,
              border: "1px solid #E2E8F0",
              bgcolor: "#FFFFFF",
            }}
          >
            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
              Next implementation area
            </Typography>
            <Typography sx={{ mt: 0.9, color: "#475569" }}>
              {primaryLabel} will connect to tenant-scoped APIs, module permissions, and audit
              coverage in later phases without creating a separate application shell.
            </Typography>
          </Paper>
        </Stack>
      </Paper>
    </OutletPage>
  );
}
