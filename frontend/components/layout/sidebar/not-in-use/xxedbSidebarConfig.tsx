"use client";

import type { ReactNode } from "react";

import AssessmentOutlinedIcon from "@mui/icons-material/AssessmentOutlined";
import BusinessCenterOutlinedIcon from "@mui/icons-material/BusinessCenterOutlined";
import DashboardCustomizeOutlinedIcon from "@mui/icons-material/DashboardCustomizeOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import Groups2OutlinedIcon from "@mui/icons-material/Groups2Outlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";

export type EdbSidebarItem = {
  label: string;
  href: string;
  icon: ReactNode;
};

export const edbSidebarItems: EdbSidebarItem[] = [
  {
    label: "Executive Dashboard",
    href: "/infomentica",
    icon: <DashboardCustomizeOutlinedIcon fontSize="small" />,
  },
  {
    label: "AI Co-Pilot",
    href: "/copilot",
    icon: <Groups2OutlinedIcon fontSize="small" />,
  },
  {
    label: "Enterprise Search",
    href: "/search",
    icon: <SearchOutlinedIcon fontSize="small" />,
  },
  {
    label: "Business Area Intelligence",
    href: "/business-areas",
    icon: <BusinessCenterOutlinedIcon fontSize="small" />,
  },
  {
    label: "Repository Reports",
    href: "/reports/repository-report",
    icon: <AssessmentOutlinedIcon fontSize="small" />,
  },
  {
    label: "Other Reports",
    href: "/reports",
    icon: <AssessmentOutlinedIcon fontSize="small" />,
  },
  {
    label: "Settings",
    href: "/settings",
    icon: <SettingsOutlinedIcon fontSize="small" />,
  },
  {
    label: "Escalations",
    href: "/escalations",
    icon: <ReportProblemOutlinedIcon fontSize="small" />,
  },
  {
    label: "Document Intelligence",
    href: "/documents",
    icon: <DescriptionOutlinedIcon fontSize="small" />,
  },
];
