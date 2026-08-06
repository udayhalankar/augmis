"use client";

import { ModulePlaceholderPage } from "../../_components/ModulePlaceholderPage";

export default function DossiersPage() {
  return (
    <ModulePlaceholderPage
      title="Dossiers"
      description="Reserved for final handover package assembly and completeness validation."
      scopeItems={[
        "Handover package definitions",
        "Document index generation",
        "Missing item checks",
        "Acceptance status tracking",
      ]}
    />
  );
}
