"use client";

import { ModulePlaceholderPage } from "../_components/ModulePlaceholderPage";

export default function DocumentControllerDeliverablesPage() {
  return (
    <ModulePlaceholderPage
      title="Deliverables"
      description="Placeholder page for planned deliverables, submission schedules, and overdue performance."
      scopeItems={[
        "Expected document register",
        "Planned vs actual submission dates",
        "Overdue and due-soon monitoring",
        "Approval and resubmission progress",
      ]}
    />
  );
}
