"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AdminTopMenu } from "@/components/data-display/AdminTopMenu";

const BUSINESS_MENU_ITEMS = [
  { key: "/augmis-business", label: "Overview" },
  { key: "/augmis-business/opportunities", label: "Opportunities" },
  { key: "/augmis-business/leads", label: "Leads" },
  { key: "/augmis-business/prospects", label: "Prospects" },
  { key: "/augmis-business/pipeline", label: "Pipeline" },
  { key: "/augmis-business/replies", label: "Replies" },
  { key: "/augmis-business/tasks", label: "Tasks" },
  { key: "/augmis-business/connectors", label: "Connectors" },
  { key: "/augmis-business/control-centre", label: "Control Centre" },
];

function activeBusinessPath(pathname: string) {
  const exact = BUSINESS_MENU_ITEMS.find((item) => item.key === pathname);
  if (exact) {
    return exact.key;
  }
  const nested = BUSINESS_MENU_ITEMS.find(
    (item) => item.key !== "/augmis-business" && pathname.startsWith(`${item.key}/`)
  );
  return nested?.key || "/augmis-business";
}

export default function AugmisBusinessTopMenu() {
  const pathname = usePathname();
  const value = activeBusinessPath(pathname);

  return (
    <AdminTopMenu
      value={value}
      onChange={() => {}}
      fullBleed
      bleedSx={{ mt: -7 }}
      borderColor="divider"
      tabsSx={{
        "& .MuiTab-root": {
          px: 1.5,
          color: "#475569",
          fontWeight: 700,
          fontSize: 13,
          textTransform: "none",
          minWidth: "max-content",
        },
        "& .Mui-selected": {
          color: "#0F4C81",
        },
        "& .MuiTabs-indicator": {
          height: 3,
          borderRadius: 0,
          backgroundColor: "#2E5BFF",
        },
      }}
      menuItems={BUSINESS_MENU_ITEMS.map((item) => ({
        key: item.key,
        label: (
          <Link
            href={item.key}
            style={{ color: "inherit", textDecoration: "none", display: "block", padding: "2px 0" }}
          >
            {item.label}
          </Link>
        ),
      }))}
    />
  );
}
