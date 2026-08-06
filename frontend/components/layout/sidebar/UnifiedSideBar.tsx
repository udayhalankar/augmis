"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useContext, useMemo, useState, type ReactNode } from "react";

import {
  Box,
  Collapse,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Tooltip,
} from "@mui/material";

import BadgeOutlinedIcon from "@mui/icons-material/BadgeOutlined";
import BusinessCenterOutlinedIcon from "@mui/icons-material/BusinessCenterOutlined";
import ChevronLeftRoundedIcon from "@mui/icons-material/ChevronLeftRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";

import { useAuth } from "@/context/AuthContext";
import { ColorModeContext } from "@/theme/ThemeContextProvider";
import { getShellTokens } from "@/theme/theme";

type MenuItem = {
  label: string;
  path: string;
  icon: ReactNode;
  accentColor?: string;
  module?: string;
  permission?: string;
};

const infomenticaItems: MenuItem[] = [
  {
    label: "Executive Dashboard",
    path: "/infomentica",
    icon: <DashboardOutlinedIcon />,
    accentColor: "#4A8CFF",
    module: "dashboard",
    permission: "dashboard:view",
  },
  {
    label: "AI Copilot",
    path: "/copilot",
    icon: <DashboardOutlinedIcon />,
    accentColor: "#A855F7",
    module: "copilot",
    permission: "copilot:use",
  },
  {
    label: "Enterprise Search",
    path: "/search",
    icon: <SearchOutlinedIcon />,
    accentColor: "#38BDF8",
    module: "documents",
    permission: "documents:read",
  },
  {
    label: "Escalations",
    path: "/escalations",
    icon: <ReportProblemOutlinedIcon />,
    accentColor: "#F97316",
    module: "escalations",
    permission: "escalation:read",
  },
  {
    label: "Document Intelligence",
    path: "/documents",
    icon: <DescriptionOutlinedIcon />,
    accentColor: "#F59E0B",
    module: "documents",
    permission: "documents:read",
  },
  {
    label: "Business Areas",
    path: "/business-areas",
    icon: <BusinessCenterOutlinedIcon />,
    accentColor: "#22C55E",
    module: "documents",
    permission: "documents:read",
  },
  {
    label: "Settings",
    path: "/settings",
    icon: <SettingsOutlinedIcon />,
    accentColor: "#94A3B8",
    module: "settings",
    permission: "admin:settings",
  },
];

const symployeeItems: MenuItem[] = [
  {
    label: "Overview",
    path: "/synthetic-employees/document-controller",
    icon: <BadgeOutlinedIcon />,
    accentColor: "#38BDF8",
  },
  {
    label: "Work Queue",
    path: "/synthetic-employees/document-controller/inbox",
    icon: <BadgeOutlinedIcon />,
    accentColor: "#14B8A6",
  },
  {
    label: "Documents",
    path: "/synthetic-employees/document-controller/documents",
    icon: <BadgeOutlinedIcon />,
    accentColor: "#3B82F6",
  },
  {
    label: "Records",
    path: "/synthetic-employees/document-controller/records",
    icon: <BadgeOutlinedIcon />,
    accentColor: "#14B8A6",
  },
  {
    label: "Communications & Transmittals",
    path: "/synthetic-employees/document-controller/transmittals",
    icon: <BadgeOutlinedIcon />,
    accentColor: "#8B5CF6",
  },
  // {
  //   label: "Recommendations",
  //   path: "/synthetic-employees/document-controller/recommendations",
  //   icon: <BadgeOutlinedIcon />,
  //   accentColor: "#A855F7",
  // },
  // {
  //   label: "Approvals",
  //   path: "/synthetic-employees/document-controller/approvals",
  //   icon: <BadgeOutlinedIcon />,
  //   accentColor: "#22C55E",
  // },
  // {
  //   label: "Commands",
  //   path: "/synthetic-employees/document-controller/commands",
  //   icon: <BadgeOutlinedIcon />,
  //   accentColor: "#F97316",
  // },
  // {
  //   label: "Registers",
  //   path: "/synthetic-employees/document-controller/registers",
  //   icon: <BadgeOutlinedIcon />,
  //   accentColor: "#EAB308",
  // },
  {
    label: "Configuration",
    path: "/synthetic-employees/document-controller/configuration",
    icon: <SettingsOutlinedIcon />,
    accentColor: "#94A3B8",
  },
  {
    label: "Navigation",
    path: "/synthetic-employees/document-controller/navigation",
    icon: <SettingsOutlinedIcon />,
    accentColor: "#94A3B8",
  },
];

export default function UnifiedSidebar({
  collapsed = false,
  onToggleCollapse,
}: {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}) {
  const pathname = usePathname();
  const { shellMode } = useContext(ColorModeContext);
  const { hasModule, hasPermission } = useAuth();
  const shell = useMemo(() => getShellTokens(shellMode), [shellMode]);
  const isCool = shellMode === "COOL";

  const [infomenticaOpen, setInfomenticaOpen] = useState(
    !pathname.startsWith("/synthetic-employees")
  );
  const [symployeesOpen, setSymployeesOpen] = useState(
    pathname.startsWith("/synthetic-employees")
  );
  const [documentControllerOpen, setDocumentControllerOpen] = useState(
    pathname.startsWith("/synthetic-employees/document-controller")
  );

  const visibleInfomenticaItems = useMemo(
    () =>
      infomenticaItems.filter(
        (item) =>
          (!item.module || hasModule(item.module)) &&
          (!item.permission || hasPermission(item.permission))
      ),
    [hasModule, hasPermission]
  );

  function isSelected(path: string) {
    if (path === "/synthetic-employees/document-controller") {
      return pathname === path;
    }

    return pathname === path || (path !== "/" && pathname.startsWith(`${path}/`));
  }

  function togglePrimarySection(section: "infomentica" | "symployees") {
    if (section === "infomentica") {
      setInfomenticaOpen((value) => {
        const next = !value;
        if (next) setSymployeesOpen(false);
        return next;
      });
      return;
    }

    setSymployeesOpen((value) => {
      const next = !value;
      if (next) setInfomenticaOpen(false);
      return next;
    });
  }

  function renderNestedItem(item: MenuItem) {
    const selected = isSelected(item.path);

    return (
      <ListItemButton
        key={item.path}
        component={Link}
        href={item.path}
        selected={selected}
        disableRipple
        sx={{
          minHeight: 30,
          py: 0.25,
          px: collapsed ? 1 : 0.9,
          pl: collapsed ? 1 : isCool ? 3.2 : 4.4,
          mb: 0.15,
          borderRadius: isCool ? 1.6 : 1,
          justifyContent: "flex-start",
          color: selected ? shell.sidebarSelectedText : shell.sidebarMuted,
          backgroundColor: selected ? shell.sidebarSelectedBg : "transparent",
          borderLeft: isCool
            ? `3px solid ${selected ? shell.sidebarSelectedBorder : "transparent"}`
            : "3px solid transparent",
          transition:
            "background-color 140ms ease, color 140ms ease, transform 140ms ease",
          "&.Mui-selected": {
            color: shell.sidebarSelectedText,
            backgroundColor: shell.sidebarSelectedBg,
          },
          "&.Mui-selected:hover": {
            backgroundColor: shell.sidebarSelectedBg,
          },
          "&:hover": {
            color: selected ? shell.sidebarSelectedText : shell.sidebarText,
            backgroundColor: selected ? shell.sidebarSelectedBg : shell.sidebarHover,
          },
          "& .MuiListItemText-root": {
            my: 0,
          },
          "& .MuiListItemText-primary": {
            fontFamily: "Inter, Roboto, sans-serif",
            fontSize: 12,
            lineHeight: 1.25,
            fontWeight: selected ? 700 : 500,
            letterSpacing: 0,
          },
        }}
      >
        {isCool ? (
          <ListItemIcon
            sx={{
              minWidth: collapsed ? 0 : 28,
              justifyContent: "center",
              color: item.accentColor || shell.sidebarMuted,
              "& svg": { fontSize: 14 },
            }}
          >
            {item.icon}
          </ListItemIcon>
        ) : null}
        {!collapsed ? <ListItemText primary={item.label} /> : null}
      </ListItemButton>
    );
  }

  function renderItem(item: MenuItem, nested = false) {
    const selected = isSelected(item.path);

    const button = (
      <ListItemButton
        key={item.path}
        component={Link}
        href={item.path}
        selected={selected}
        disableRipple
        sx={{
          minHeight: nested ? 30 : 38,
          py: nested ? 0.25 : 0.55,
          px: collapsed ? 1 : nested ? 0.9 : 0.6,
          pl: collapsed ? 1 : nested ? 3.2 : 0.6,
          mb: nested ? 0.15 : 0.35,
          borderRadius: isCool ? 1.6 : 1,
          justifyContent: collapsed ? "center" : "flex-start",
          color: selected ? shell.sidebarSelectedText : shell.sidebarMuted,
          backgroundColor: selected ? shell.sidebarSelectedBg : "transparent",
          borderLeft: isCool
            ? `3px solid ${selected ? shell.sidebarSelectedBorder : "transparent"}`
            : "3px solid transparent",
          transition:
            "background-color 140ms ease, color 140ms ease, transform 140ms ease",
          "&.Mui-selected": {
            color: shell.sidebarSelectedText,
            backgroundColor: shell.sidebarSelectedBg,
          },
          "&.Mui-selected:hover": {
            backgroundColor: shell.sidebarSelectedBg,
          },
          "&:hover": {
            color: selected ? shell.sidebarSelectedText : shell.sidebarText,
            backgroundColor: selected ? shell.sidebarSelectedBg : shell.sidebarHover,
          },
          "& .MuiListItemText-root": {
            my: 0,
          },
          "& .MuiListItemText-primary": {
            fontFamily: "Inter, Roboto, sans-serif",
            fontSize: nested ? 12 : 14,
            lineHeight: nested ? 1.25 : 1.35,
            fontWeight: selected ? 700 : nested ? 500 : 600,
            letterSpacing: 0,
          },
        }}
      >
        {!nested || collapsed ? (
          <ListItemIcon
            sx={{
              minWidth: collapsed ? 0 : 34,
              justifyContent: "center",
              color: selected
                ? shell.sidebarSelectedText
                : isCool
                  ? item.accentColor || shell.sidebarMuted
                  : "#94A3B8",
              "& svg": { fontSize: 16 },
            }}
          >
            {item.icon}
          </ListItemIcon>
        ) : null}

        {!collapsed ? <ListItemText primary={item.label} /> : null}
      </ListItemButton>
    );

    return collapsed ? (
      <Tooltip key={item.path} title={item.label} placement="right">
        {button}
      </Tooltip>
    ) : (
      button
    );
  }

  function renderSection(
    label: string,
    icon: ReactNode,
    open: boolean,
    selected: boolean,
    onToggle: () => void,
    path?: string
  ) {
    const button = (
      <ListItemButton
        component={path ? Link : "button"}
        href={path}
        onClick={onToggle}
        disableRipple
        sx={{
          minHeight: 40,
          py: 0.6,
          px: collapsed ? 1 : 0.6,
          mb: 0.35,
          borderRadius: isCool ? 1.6 : 1,
          justifyContent: collapsed ? "center" : "flex-start",
          color: selected ? shell.sidebarText : shell.sidebarMuted,
          backgroundColor: "transparent",
          transition: "background-color 140ms ease, color 140ms ease",
          "&:hover": {
            color: shell.sidebarText,
            backgroundColor: shell.sidebarHover,
          },
          "& .MuiListItemText-root": {
            my: 0,
          },
          "& .MuiListItemText-primary": {
            fontFamily: "Inter, Roboto, sans-serif",
            fontSize: 13.25,
            lineHeight: 1.28,
            fontWeight: selected ? 620 : 560,
            letterSpacing: "-0.01em",
          },
        }}
      >
        <ListItemIcon
          sx={{
            minWidth: collapsed ? 0 : 34,
            justifyContent: "center",
            color: selected ? shell.sidebarSelectedText : "#94A3B8",
            "& svg": { fontSize: 16 },
          }}
        >
          {icon}
        </ListItemIcon>

        {!collapsed ? (
          <>
            <ListItemText primary={label} />
            {open ? (
              <ExpandLessIcon sx={{ fontSize: 18, color: shell.sidebarMuted }} />
            ) : (
              <ExpandMoreIcon sx={{ fontSize: 18, color: shell.sidebarMuted }} />
            )}
          </>
        ) : null}
      </ListItemButton>
    );

    return collapsed ? (
      <Tooltip title={label} placement="right">
        {button}
      </Tooltip>
    ) : (
      button
    );
  }

  function renderSubsection(
    label: string,
    open: boolean,
    selected: boolean,
    onToggle: () => void,
    path?: string
  ) {
    return (
      <ListItemButton
        component={path ? Link : "button"}
        href={path}
        onClick={onToggle}
        disableRipple
        sx={{
          minHeight: 32,
          py: 0.35,
          px: 1.05,
          pl: 3.2,
          mb: 0.15,
          borderRadius: isCool ? 1.6 : 1,
          color: selected ? shell.sidebarSelectedText : shell.sidebarMuted,
          backgroundColor: "transparent",
          transition: "background-color 140ms ease, color 140ms ease",
          "&:hover": {
            color: selected ? shell.sidebarSelectedText : shell.sidebarText,
            backgroundColor: selected ? shell.sidebarSelectedBg : shell.sidebarHover,
          },
          "& .MuiListItemText-root": {
            my: 0,
          },
          "& .MuiListItemText-primary": {
            fontFamily: "Inter, Roboto, sans-serif",
            fontSize: 12,
            lineHeight: 1.25,
            fontWeight: selected ? 700 : 500,
            letterSpacing: 0,
          },
        }}
      >
        <ListItemText primary={label} />
        {open ? (
          <ExpandLessIcon sx={{ fontSize: 16, color: shell.sidebarMuted }} />
        ) : (
          <ExpandMoreIcon sx={{ fontSize: 16, color: shell.sidebarMuted }} />
        )}
      </ListItemButton>
    );
  }

  return (
    <Box
      component="aside"
      sx={{
        position: "fixed",
        top: isCool ? 0 : shell.topbarHeight,
        left: 0,
        bottom: 0,
        zIndex: 1100,
        width: collapsed ? 67 : 225,
        height: isCool ? "100vh" : `calc(100vh - ${shell.topbarHeight}px)`,
        bgcolor: shell.sidebarBg,
        borderRight: `1px solid ${shell.sidebarBorder}`,
        boxShadow: "none",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        transition: "width 180ms ease",
      }}
    >
      <Box
        sx={{
          height: isCool ? 112 : 55,
          px: isCool ? 1.5 : 1.25,
          display: "flex",
          flexDirection: isCool ? "column" : "row",
          alignItems: collapsed ? "center" : isCool ? "stretch" : "flex-end",
          justifyContent: collapsed ? "center" : isCool ? "space-between" : "flex-end",
          gap: isCool ? 1.25 : 0,
          pb: isCool ? 1.2 : 0.15,
          pt: isCool ? 1.2 : 0,
          borderBottom: isCool ? `1px solid ${shell.sidebarBrandBorder}` : "none",
          bgcolor: isCool ? shell.sidebarBrandBg : shell.sidebarBg,
        }}
      >
        {isCool && !collapsed ? (
          <Box sx={{ px: 0.1, pt: 0.15 }}>
            <Box
              component="img"
              src="/augmis-logocombined1-26june2026.png"
              alt="AUGMIS logo"
              sx={{
                width: "100%",
                maxWidth: 168,
                height: "auto",
                display: "block",
              }}
            />
            <Box
              sx={{
                mt: 0.55,
                fontSize: 10,
                color: shell.sidebarMuted,
                lineHeight: 1.35,
                letterSpacing: "0.02em",
              }}
            >
              Enterprise workspace
            </Box>
          </Box>
        ) : null}

        <IconButton
          size="small"
          onClick={onToggleCollapse}
          sx={{
            width: 30,
            height: 30,
            alignSelf: isCool && !collapsed ? "flex-end" : undefined,
            mr: isCool && !collapsed ? 0.4 : 0,
            border: `1px solid ${shell.sidebarCollapseBorder}`,
            color: isCool ? "#E2E8F0" : shell.sidebarText,
          }}
        >
          {collapsed ? (
            <ChevronRightRoundedIcon fontSize="small" />
          ) : (
            <ChevronLeftRoundedIcon fontSize="small" />
          )}
        </IconButton>
      </Box>

      <Box
        sx={{
          flex: 1,
          px: collapsed ? 1 : 1.5,
          py: isCool ? 1 : 0.4,
          overflowY: "auto",
        }}
      >
        <List disablePadding>
          {renderSection(
            "Infomentica",
            <DashboardOutlinedIcon />,
            infomenticaOpen,
            !pathname.startsWith("/synthetic-employees"),
            () => togglePrimarySection("infomentica"),
            "/infomentica"
          )}

          {!collapsed ? (
            <Collapse in={infomenticaOpen} timeout="auto" unmountOnExit>
              <List disablePadding>
                {visibleInfomenticaItems.map((item) => renderItem(item, true))}
              </List>
            </Collapse>
          ) : null}

          {renderSection(
            "Synthetic Employees",
            <BadgeOutlinedIcon />,
            symployeesOpen,
            pathname.startsWith("/synthetic-employees"),
            () => togglePrimarySection("symployees"),
            "/synthetic-employees"
          )}

          {!collapsed ? (
            <Collapse in={symployeesOpen} timeout="auto" unmountOnExit>
              <List disablePadding>
                {renderSubsection(
                  "Document Controller",
                  documentControllerOpen,
                  pathname.startsWith("/synthetic-employees/document-controller"),
                  () => setDocumentControllerOpen((value) => !value),
                  "/synthetic-employees/document-controller"
                )}
                <Collapse in={documentControllerOpen} timeout="auto" unmountOnExit>
                  <List disablePadding>
                    {symployeeItems.map((item) => renderNestedItem(item))}
                  </List>
                </Collapse>
              </List>
            </Collapse>
          ) : null}
        </List>
      </Box>
    </Box>
  );
}

export function SympSidebar({
  open = true,
  onToggle,
}: {
  open?: boolean;
  onToggle?: () => void;
}) {
  return <UnifiedSidebar collapsed={!open} onToggleCollapse={onToggle} />;
}
