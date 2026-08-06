"use client";

import { useRouter } from "next/navigation";

import {
  ADMIN_TOP_MENU_POST_MENU_BLOCK_SX,
  ADMIN_TOP_MENU_POST_MENU_CONTENT_SX,
  AdminTopMenu,
} from "@/components/data-display/AdminTopMenu";
import { OutletPage } from "@/components/layout/OutletPage";
import { Chip, Paper, Stack, Typography } from "@mui/material";

type WorkQueueMenuItem = {
  key: string;
  label: string;
  href: string;
};

export default function CompletionStatusPage() {
  const router = useRouter();

  const menuItems: WorkQueueMenuItem[] = [
    { key: "inbox", label: "Inbox", href: "/synthetic-employees/document-controller/inbox" },
    { key: "reviews", label: "Reviews", href: "/synthetic-employees/document-controller/inbox?tab=reviews" },
    { key: "exceptions", label: "Exceptions", href: "/synthetic-employees/document-controller/inbox?tab=exceptions" },
    {
      key: "overdue-tasks",
      label: "Overdue Tasks",
      href: "/synthetic-employees/document-controller/inbox?tab=overdue-tasks",
    },
    { key: "approvals", label: "Approvals", href: "/synthetic-employees/document-controller/inbox?tab=approvals" },
    { key: "commands", label: "Actions", href: "/synthetic-employees/document-controller/inbox?tab=commands" },
    {
      key: "connector-commands",
      label: "Connector Actions",
      href: "/synthetic-employees/document-controller/commands",
    },
    { key: "registers", label: "Registers", href: "/synthetic-employees/document-controller/inbox?tab=registers" },
    {
      key: "recommendations",
      label: "Recommendations",
      href: "/synthetic-employees/document-controller/inbox?tab=recommendations",
    },
    {
      key: "completion-status",
      label: "Completion Status",
      href: "/synthetic-employees/document-controller/handover/completion-status",
    },
  ];

  return (
    <OutletPage
      title="Work Queue"
      description="Combined operational workspace for inbox review, approvals, actions, registers, recommendations, exceptions, overdue follow-up, and linked action or completion-status drilldowns."
    >
      <Stack spacing={0}>
        <AdminTopMenu
          menuItems={menuItems.map(({ key, label }) => ({ key, label }))}
          value="completion-status"
          onChange={(value) => {
            const target = menuItems.find((item) => item.key === value);
            if (target?.href) {
              router.push(target.href);
            }
          }}
          fullBleed
          bleedSx={{ mt: -7 }}
          borderColor="divider"
        />

        <Paper
          variant="outlined"
          sx={{ ...ADMIN_TOP_MENU_POST_MENU_BLOCK_SX, p: 3, borderRadius: 2 }}
        >
          <Stack spacing={2}>
            <Stack
              direction="row"
              spacing={1}
              useFlexGap
              sx={{ alignItems: "center", flexWrap: "wrap" }}
            >
              <Typography variant="h6" fontWeight={700}>
                Completion Status
              </Typography>
              <Chip label="Future module" size="small" variant="outlined" />
            </Stack>

            <Typography variant="body2" color="text.secondary">
              This page is reserved for closeout readiness, missing deliverables, and handover progress reporting.
            </Typography>

            <Stack spacing={1}>
              {[
                "Readiness dashboard",
                "Outstanding deliverables",
                "Forecast to completion",
                "Handover milestone status",
              ].map((item) => (
                <Paper
                  key={item}
                  variant="outlined"
                  sx={{ px: 1.5, py: 1, borderRadius: 1.5 }}
                >
                  <Typography variant="body2" fontWeight={500}>
                    {item}
                  </Typography>
                </Paper>
              ))}
            </Stack>
          </Stack>
        </Paper>
      </Stack>
    </OutletPage>
  );
}
