"use client";

import { ModulePlaceholderPage } from "../_components/ModulePlaceholderPage";

export default function DocumentControllerHandoverPage() {
  return (
    <ModulePlaceholderPage
      title="Handover"
      description="Dedicated module area for final documentation packages, as-built readiness, and closeout completeness."
      scopeItems={[
        "Dossiers",
        "As-Built Register",
        "Completion Status",
      ]}
    />
  );
}
