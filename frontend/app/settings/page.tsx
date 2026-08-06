"use client";

import Link from "next/link";
import { Alert } from "@mui/material";
import ReceiptLongOutlinedIcon from "@mui/icons-material/ReceiptLongOutlined";
import PeopleAltOutlinedIcon from "@mui/icons-material/PeopleAltOutlined";
import SourceOutlinedIcon from "@mui/icons-material/SourceOutlined";
import HistoryEduOutlinedIcon from "@mui/icons-material/HistoryEduOutlined";
import SecurityOutlinedIcon from "@mui/icons-material/SecurityOutlined";
import DatasetLinkedOutlinedIcon from "@mui/icons-material/DatasetLinkedOutlined";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import { type LauncherCardItem, LauncherCardGrid } from "@/components/layout/LauncherCardGrid";
import { useAuth } from "@/context/AuthContext";

export default function SettingsPage() {
  const { user } = useAuth();

  const settingsCards: LauncherCardItem[] = [
    {
      title: "Summary & Billing",
      description:
        "Review tenant subscription status, active plan, usage posture, and commercial readiness.",
      href: "/settings/summary-billing",
      icon: <ReceiptLongOutlinedIcon />,
      items: ["Plan summary", "Billing posture", "Usage limits", "Current entitlements"],
    },
    {
      title: "Manage Users",
      description:
        "Create, edit, invite, and govern tenant users with role-based access controls.",
      href: "/settings/users",
      icon: <PeopleAltOutlinedIcon />,
      items: ["User list", "Role management", "Invite onboarding", "Permissions"],
    },
    {
      title: "Manage Repositories",
      description:
        "Configure repositories, sync behavior, indexing controls, and storage-aware ingestion settings.",
      href: "/settings/repositories",
      icon: <SourceOutlinedIcon />,
      items: ["Repository catalog", "Sync controls", "Reindex actions", "Connection review"],
    },
    {
      title: "Audit Logs",
      description:
        "Inspect governed operational events, user actions, and security-relevant system activity.",
      href: "/settings/audit",
      icon: <HistoryEduOutlinedIcon />,
      items: ["User actions", "Auth events", "Admin activity", "Operational traceability"],
    },
    {
      title: "Security",
      description:
        "Manage password changes, sessions, device logout, and tenant-level security visibility.",
      href: "/settings/security",
      icon: <SecurityOutlinedIcon />,
      items: ["Password controls", "Active sessions", "Logout everywhere", "Security audit view"],
    },
    {
      title: "Data Management",
      description:
        "Govern operational scope, data handling controls, and tenant-side platform management settings.",
      href: "/settings/scope",
      icon: <DatasetLinkedOutlinedIcon />,
      items: ["Manage scope", "Module access", "Data governance", "Operational controls"],
    },
  ];

  return (
    <ModuleGuard moduleName="settings" permission="admin:settings">
      <OutletPage title="Settings">
        <LauncherCardGrid cards={settingsCards} cardsPerPage={6} />

        {user?.role === "SUPER_ADMIN" ? (
          <Alert severity="info" sx={{ mt: 3 }}>
            AUGMIS-wide master controls remain available from <Link href="/settings/augmis-admin">AUGMIS Admin</Link>.
          </Alert>
        ) : null}
      </OutletPage>
    </ModuleGuard>
  );
}

