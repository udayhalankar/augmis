"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { CircularProgress, Stack } from "@mui/material";

import { OutletPage } from "@/components/layout/OutletPage";

export default function DocumentControllerCommandsPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/synthetic-employees/document-controller/inbox");
  }, [router]);

  return (
    <OutletPage
      title="Work Queue"
      description="Combined operational workspace for inbox review, approvals, actions, registers, recommendations, exceptions, overdue follow-up, and linked action or completion-status drilldowns."
    >
      <Stack sx={{ minHeight: 240, alignItems: "center", justifyContent: "center" }}>
        <CircularProgress />
      </Stack>
    </OutletPage>
  );
}
