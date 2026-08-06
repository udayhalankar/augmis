"use client";

import Link from "next/link";
import { Button } from "@mui/material";
import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import PriceChangeOutlinedIcon from "@mui/icons-material/PriceChangeOutlined";
import TrackChangesOutlinedIcon from "@mui/icons-material/TrackChangesOutlined";
import DnsOutlinedIcon from "@mui/icons-material/DnsOutlined";
import StorageOutlinedIcon from "@mui/icons-material/StorageOutlined";
import ExtensionOutlinedIcon from "@mui/icons-material/ExtensionOutlined";
import AccountBalanceWalletOutlinedIcon from "@mui/icons-material/AccountBalanceWalletOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import MonitorHeartOutlinedIcon from "@mui/icons-material/MonitorHeartOutlined";
import SettingsSuggestOutlinedIcon from "@mui/icons-material/SettingsSuggestOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import LanOutlinedIcon from "@mui/icons-material/LanOutlined";

import AccessDenied from "@/components/auth/AccessDenied";
import ModuleGuard from "@/components/auth/ModuleGuard";
import { type LauncherCardItem, LauncherCardGrid } from "@/components/layout/LauncherCardGrid";
import { OutletPage } from "@/components/layout/OutletPage";
import { useAuth } from "@/context/AuthContext";

const adminCards: LauncherCardItem[] = [
  {
    title: "AUGMIS Auth Governance",
    description:
      "Master-admin controls for password policy, registration rules, throttling, lockout, and provider rollout.",
    status: "Live",
    href: "/settings/auth-governance",
    icon: <AdminPanelSettingsOutlinedIcon />,
    items: ["Password policy", "Registration policy", "Login throttling", "Feature rollout flags"],
  },
  {
    title: "Create / Modify SaaS Plans",
    description:
      "Create commercial plans, adjust limits, define enterprise entitlements, and evolve plan features.",
    status: "Planned",
    icon: <PriceChangeOutlinedIcon />,
    items: ["Plan catalog", "Usage limits", "Feature entitlements", "Commercial policy"],
  },
  {
    title: "Manage Scope",
    description:
      "Control module scope, permissions, and governed rollout boundaries across the AUGMIS platform.",
    status: "Live",
    href: "/settings/scope",
    icon: <TrackChangesOutlinedIcon />,
    items: ["Permissions map", "Module boundaries", "Role scope", "Feature control"],
  },
  {
    title: "Database Settings",
    description:
      "Centralized platform database controls, connection posture, and operational configuration.",
    status: "Planned",
    icon: <DnsOutlinedIcon />,
    items: ["Connection settings", "Retention rules", "Maintenance posture", "Operational controls"],
  },
  {
    title: "Storage Management",
    description:
      "Supervise repository storage behavior, platform ingestion footprint, and allocation patterns.",
    status: "Live",
    href: "/settings/repositories",
    icon: <StorageOutlinedIcon />,
    items: ["Repository storage", "Ingestion footprint", "Sync controls", "Capacity review"],
  },
  {
    title: "Add New Module",
    description:
      "Prepare new product modules for controlled rollout with scope, permission, and shell alignment.",
    status: "Live",
    href: "/settings/scope",
    icon: <ExtensionOutlinedIcon />,
    items: ["Module registry", "Permission model", "Menu rollout", "Access governance"],
  },
  {
    title: "Customer Accounts & Billing",
    description:
      "Review tenant subscriptions, account posture, commercial readiness, and customer operating status.",
    status: "Live",
    href: "/settings",
    icon: <AccountBalanceWalletOutlinedIcon />,
    items: ["Tenant subscriptions", "Billing posture", "Usage visibility", "Commercial readiness"],
  },
  {
    title: "AUGMIS Business Reports",
    description:
      "Platform-level reporting for adoption, tenants, repositories, intelligence usage, and governance signals.",
    status: "Planned",
    icon: <InsightsOutlinedIcon />,
    items: ["Tenant analytics", "Platform KPIs", "Usage trends", "Governance reporting"],
  },
  {
    title: "Migration Agents",
    description:
      "Monitor local migration agents, watched root paths, heartbeat posture, and recent file activity from one admin surface.",
    status: "Live",
    href: "/settings/augmis-admin/agents",
    icon: <LanOutlinedIcon />,
    items: ["Agent status", "Heartbeat visibility", "Watched roots", "Recent file events"],
  },
  {
    title: "AUGMIS Health",
    description:
      "Inspect platform readiness signals for OCR, datasource configuration, and backend operating posture.",
    status: "Live",
    href: "/settings/augmis-admin/health",
    icon: <MonitorHeartOutlinedIcon />,
    items: ["OCR status", "Datasource readiness", "Model configuration", "Backend diagnostics"],
  },
  {
    title: "Platform Config",
    description:
      "Review and update platform-level runtime configuration with validation, masking, and restart guidance.",
    status: "Live",
    href: "/settings/augmis-admin/platform-config",
    icon: <SettingsSuggestOutlinedIcon />,
    items: ["OpenAI settings", "Database config", "OCR command", "Restart advisories"],
  },
  {
    title: "Server Logs",
    description:
      "Investigate backend app logs, captured frontend errors, and existing audit activity from one admin page.",
    status: "Live",
    href: "/settings/augmis-admin/server-logs",
    icon: <FactCheckOutlinedIcon />,
    items: ["Backend runtime logs", "Frontend error capture", "Audit activity", "Issue investigation"],
  },
];

export default function AugmisAdminPage() {
  const { user } = useAuth();

  return (
    <ModuleGuard moduleName="settings" permission="admin:settings">
      {user?.role !== "SUPER_ADMIN" ? (
        <AccessDenied />
      ) : (
        <OutletPage
          title="AUGMIS Admin"
          actions={
            <Button component={Link} href="/settings/auth-governance" variant="contained">
              Open Governance
            </Button>
          }
        >
          <LauncherCardGrid cards={adminCards} cardsPerPage={6} />
        </OutletPage>
      )}
    </ModuleGuard>
  );
}

