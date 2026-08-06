"use client";

import { Stack } from "@mui/material";

import { LifecycleEventTimeline } from "../_components/LifecycleEventTimeline";
import { ModulePlaceholderPage } from "../_components/ModulePlaceholderPage";

export default function DocumentControllerLifecycleHistoryPage() {
  return (
    <Stack spacing={2}>
      <ModulePlaceholderPage
        title="Lifecycle History"
        description="Placeholder page for document lifecycle events and state-transition history."
        scopeItems={[
          "Lifecycle transition audit trail",
          "State-dimension history",
          "Who changed what and why",
          "Linked workflow, approval, and transmittal references",
        ]}
      />
      <LifecycleEventTimeline
        events={[
          {
            id: "placeholder-created",
            title: "Lifecycle event placeholder",
            detail: "This timeline will display immutable lifecycle transitions once backend support is added.",
          },
        ]}
      />
    </Stack>
  );
}
