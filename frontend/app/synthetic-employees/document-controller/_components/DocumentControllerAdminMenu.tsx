"use client";

import type { ReactNode } from "react";

import { useRouter } from "next/navigation";

import { AdminTopMenu } from "@/components/data-display/AdminTopMenu";

type DocumentControllerAdminMenuProps = {
  actions?: ReactNode;
  value: "overview" | "navigation" | "configuration";
};

const MENU_ITEMS = [
  { key: "overview", label: "Overview", href: "/synthetic-employees/document-controller" },
  {
    key: "navigation",
    label: "Navigation",
    href: "/synthetic-employees/document-controller/navigation",
  },
  {
    key: "configuration",
    label: "Configuration",
    href: "/synthetic-employees/document-controller/configuration",
  },
] as const;

export function DocumentControllerAdminMenu({
  actions,
  value,
}: DocumentControllerAdminMenuProps) {
  const router = useRouter();

  return (
    <AdminTopMenu
      menuItems={MENU_ITEMS.map((item) => ({ key: item.key, label: item.label }))}
      value={value}
      onChange={(nextValue) => {
        const match = MENU_ITEMS.find((item) => item.key === nextValue);
        if (match) {
          router.push(match.href);
        }
      }}
      fullBleed
      bleedSx={{ mt: -7 }}
      borderColor="divider"
      actions={actions}
    />
  );
}
