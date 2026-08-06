"use client";

import { ModulePlaceholderPage } from "../_components/ModulePlaceholderPage";

export default function OverdueTasksPage() {
  return (
    <ModulePlaceholderPage
      title="Overdue Tasks"
      description="Reserved for overdue review, approval, acknowledgement, and action-task follow-up."
      scopeItems={[
        "Overdue work queue",
        "Task ageing and breach visibility",
        "Owner escalation tracking",
        "Recovery and closure monitoring",
      ]}
    />
  );
}
