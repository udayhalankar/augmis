"use client";

import Link from "next/link";

import {
  Chip,
  Grid,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

import { AdminTableCard } from "@/components/data-display/AdminTableCard";
import { OutletPage } from "@/components/layout/OutletPage";
import { DocumentControllerAdminMenu } from "../_components/DocumentControllerAdminMenu";

type NavSection = {
  title: string;
  href?: string;
  items?: Array<{
    label: string;
    href?: string;
  }>;
};

const navigationSections: NavSection[] = [
  {
    title: "Control Centre",
    href: "/synthetic-employees/document-controller/control-center",
  },
  {
    title: "My Work",
    items: [
      { label: "Inbox", href: "/synthetic-employees/document-controller/inbox" },
      { label: "Reviews", href: "/synthetic-employees/document-controller/reviews" },
      { label: "Approvals", href: "/synthetic-employees/document-controller/approvals" },
      { label: "Exceptions", href: "/synthetic-employees/document-controller/exceptions" },
      { label: "Overdue Tasks", href: "/synthetic-employees/document-controller/overdue-tasks" },
    ],
  },
  {
    title: "Documents",
    items: [
      {
        label: "Master Document Register",
        href: "/synthetic-employees/document-controller/registers",
      },
      {
        label: "Deliverables Register",
        href: "/synthetic-employees/document-controller/deliverables",
      },
      {
        label: "Revision Control",
        href: "/synthetic-employees/document-controller/revision-control",
      },
      {
        label: "Document Relationships",
        href: "/synthetic-employees/document-controller/document-relationships",
      },
      {
        label: "Lifecycle History",
        href: "/synthetic-employees/document-controller/lifecycle-history",
      },
      {
        label: "Document Detail",
        href: "/synthetic-employees/document-controller/documents",
      },
    ],
  },
  {
    title: "Communications",
    href: "/synthetic-employees/document-controller/communications",
    items: [
      {
        label: "Transmittals",
        href: "/synthetic-employees/document-controller/transmittals",
      },
      {
        label: "Incoming Transmittals",
        href: "/synthetic-employees/document-controller/communications/incoming-transmittals",
      },
      {
        label: "Outgoing Transmittals",
        href: "/synthetic-employees/document-controller/communications/outgoing-transmittals",
      },
      {
        label: "Correspondence",
        href: "/synthetic-employees/document-controller/communications/correspondence",
      },
      {
        label: "Acknowledgements",
        href: "/synthetic-employees/document-controller/communications/acknowledgements",
      },
    ],
  },
  {
    title: "Records",
    href: "/synthetic-employees/document-controller/records",
    items: [
      {
        label: "Active Records",
        href: "/synthetic-employees/document-controller/records/active-records",
      },
      {
        label: "Vital Records",
        href: "/synthetic-employees/document-controller/records/vital-records",
      },
      {
        label: "Inactive Records",
        href: "/synthetic-employees/document-controller/records/inactive-records",
      },
      {
        label: "Retention Review",
        href: "/synthetic-employees/document-controller/records/retention-review",
      },
      {
        label: "Legal Holds",
        href: "/synthetic-employees/document-controller/records/legal-holds",
      },
      {
        label: "Disposition",
        href: "/synthetic-employees/document-controller/records/disposition",
      },
      {
        label: "Archive",
        href: "/synthetic-employees/document-controller/records/archive",
      },
      {
        label: "Archive Transfers",
        href: "/synthetic-employees/document-controller/archive-transfers",
      },
    ],
  },
  {
    title: "Handover",
    href: "/synthetic-employees/document-controller/handover",
    items: [
      { label: "Dossiers", href: "/synthetic-employees/document-controller/handover/dossiers" },
      {
        label: "As-Built Register",
        href: "/synthetic-employees/document-controller/handover/as-built-register",
      },
      {
        label: "Completion Status",
        href: "/synthetic-employees/document-controller/handover/completion-status",
      },
    ],
  },
  {
    title: "Automation",
    items: [
      {
        label: "Recommendations",
        href: "/synthetic-employees/document-controller/recommendations",
      },
      { label: "Actions", href: "/synthetic-employees/document-controller/commands" },
      {
        label: "Automation History",
        href: "/synthetic-employees/document-controller/automation-history",
      },
    ],
  },
  {
    title: "Reports",
  },
  {
    title: "Configuration",
    href: "/synthetic-employees/document-controller/configuration",
  },
];

function PlaceholderSection({
  title,
  href,
  items,
}: {
  title: string;
  href?: string;
  items?: Array<{
    label: string;
    href?: string;
  }>;
}) {
  return (
    <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2, height: "100%" }}>
      <Stack spacing={1.5}>
        <Stack
          direction="row"
          spacing={1}
          sx={{ alignItems: "center", justifyContent: "space-between" }}
        >
          {href ? (
            <Typography
              component={Link}
              href={href}
              variant="h6"
              fontWeight={700}
              sx={{ color: "primary.main", textDecoration: "none" }}
            >
              {title}
            </Typography>
          ) : (
            <Typography variant="h6" fontWeight={700}>
              {title}
            </Typography>
          )}
          <Chip
            label={href ? "Linked" : "Placeholder"}
            size="small"
            variant="outlined"
            color={href ? "primary" : "default"}
          />
        </Stack>

        {items?.length ? (
          <Stack spacing={1}>
            {items.map((item) => (
              <Paper
                key={`${title}-${item.label}`}
                component={item.href ? Link : "div"}
                href={item.href}
                variant="outlined"
                sx={{
                  px: 1.5,
                  py: 1,
                  borderRadius: 1.5,
                  bgcolor: "background.paper",
                  textDecoration: "none",
                  color: "inherit",
                  borderColor: item.href ? "primary.light" : "divider",
                }}
              >
                <Stack
                  direction="row"
                  spacing={1}
                  sx={{ justifyContent: "space-between", alignItems: "center" }}
                >
                  <Typography
                    variant="body2"
                    fontWeight={500}
                    sx={{ color: item.href ? "primary.main" : "text.primary" }}
                  >
                    {item.label}
                  </Typography>
                  <Chip
                    label={item.href ? "Open" : "Pending"}
                    size="small"
                    variant="outlined"
                    color={item.href ? "primary" : "default"}
                  />
                </Stack>
              </Paper>
            ))}
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Link slot reserved for future route mapping.
          </Typography>
        )}
      </Stack>
    </Paper>
  );
}

export default function DocumentControllerNavigationPage() {
  return (
    <OutletPage
      title="Document Controller Navigation"
      description="Placeholder structure for Synthetic Employees > Document Controller. Links can be assigned later without changing the information architecture."
    >
      <Stack spacing={0}>
        <DocumentControllerAdminMenu value="navigation" />

        <Stack spacing={3} sx={{ pt: 2 }}>
          <AdminTableCard
            title="Document Controller Navigation"
            description="Shared route map for work queue, documents, communications, records, handover, automation, and configuration."
            accentLabel="Navigation"
            bodySx={{ p: 3 }}
          >
            <Stack spacing={3}>
              <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2 }}>
                <Stack spacing={1}>
                  <Typography variant="body2" color="text.secondary">
                    Synthetic Employees
                  </Typography>
                  <Typography variant="h5" fontWeight={700}>
                    Document Controller
                  </Typography>
                </Stack>
              </Paper>

              <Grid container spacing={2}>
                {navigationSections.map((section) => (
                  <Grid key={section.title} size={{ xs: 12, md: 6, xl: 4 }}>
                    <PlaceholderSection title={section.title} href={section.href} items={section.items} />
                  </Grid>
                ))}
              </Grid>
            </Stack>
          </AdminTableCard>
        </Stack>
      </Stack>
    </OutletPage>
  );
}
