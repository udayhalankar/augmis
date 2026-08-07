import type { ReactNode } from "react";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { AugmisBusinessShell } from "./components/AugmisBusinessShell";

export default function AugmisBusinessLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <ModuleGuard moduleName="augmis_business" permission="business_development:read">
      <AugmisBusinessShell>{children}</AugmisBusinessShell>
    </ModuleGuard>
  );
}
