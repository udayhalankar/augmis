"use client";

import { type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  Box,
  Collapse,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Tooltip,
  Typography,
} from "@mui/material";

import AssignmentTurnedInIcon from "@mui/icons-material/AssignmentTurnedIn";
import BusinessCenterIcon from "@mui/icons-material/BusinessCenter";
import StorefrontIcon from "@mui/icons-material/Storefront";
import DashboardIcon from "@mui/icons-material/Dashboard";
import SearchIcon from "@mui/icons-material/Search";
import DescriptionIcon from "@mui/icons-material/Description";
import SettingsIcon from "@mui/icons-material/Settings";
import ShoppingCartCheckoutIcon from "@mui/icons-material/ShoppingCartCheckout";
import ReportProblemIcon from "@mui/icons-material/ReportProblem";
import AssessmentOutlinedIcon from "@mui/icons-material/AssessmentOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ChevronLeftOutlinedIcon from "@mui/icons-material/ChevronLeftOutlined";
import ChevronRightOutlinedIcon from "@mui/icons-material/ChevronRightOutlined";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { getBusinessAreaCatalog } from "@/services/businessAreaService";

const menuItems = [
  {
    label: "Executive Dashboard",
    icon: <DashboardIcon />,
    path: "/edb",
    module: "dashboard",
    permission: "dashboard:view",
  },
  {
    label: "AI Copilot",
    icon: (
      <Box
        component="img"
        src="/augmis_logo_transparent_bg.png"
        alt="Augmis copilot"
        sx={{ width: 17, height: 17, objectFit: "contain", display: "block" }}
      />
    ),
    path: "/copilot",
    module: "copilot",
    permission: "copilot:use",
  },
  {
    label: "Enterprise Search",
    icon: <SearchIcon />,
    path: "/search",
    module: "documents",
    permission: "documents:read",
  },
  {
    label: "Proposal Intelligence",
    icon: <AssignmentTurnedInIcon />,
    path: "/proposals",
    module: "proposals",
    permission: "proposal:read",
  },
  {
    label: "Vendor Intelligence",
    icon: <StorefrontIcon />,
    path: "/vendors",
    module: "vendors",
    permission: "vendor:read",
  },
  {
    label: "Procurement Intelligence",
    icon: <ShoppingCartCheckoutIcon />,
    path: "/procurement",
    module: "procurement",
    permission: "procurement:read",
  },
  {
    label: "Escalations",
    icon: <ReportProblemIcon />,
    path: "/escalations",
    module: "escalations",
    permission: "escalation:read",
  },
  {
    label: "Document Intelligence",
    icon: <DescriptionIcon />,
    path: "/documents",
    module: "documents",
    permission: "documents:read",
  },
  {
    label: "Reports",
    icon: <AssessmentOutlinedIcon />,
    path: "/reports",
    module: "documents",
    permission: "documents:read",
  },
  {
    label: "Settings",
    icon: <SettingsIcon />,
    path: "/settings",
    module: "settings",
    permission: "admin:settings",
  },
  {
    label: "AUGMIS Admin",
    icon: <FactCheckOutlinedIcon />,
    path: "/settings/augmis-admin",
    module: "settings",
    permission: "admin:settings",
  },
];

type SidebarItem = (typeof menuItems)[number];
type DynamicBusinessAreaItem = {
  label: string;
  icon: ReactNode;
  path: string;
};

const hiddenBusinessAreaSlugs = new Set(["general", "sales"]);
const hiddenBusinessAreaLabels = new Set(["general", "proposal intelligence"]);

function businessAreaLabel(slug: string, displayName: string) {
  if (slug === "sales") return "Proposal Intelligence";
  if (slug === "vendors") return "Vendor Intelligence";
  if (slug === "procurement") return "Procurement Intelligence";
  return displayName;
}

function businessAreaIcon(slug: string) {
  if (slug === "sales") return <AssignmentTurnedInIcon />;
  if (slug === "vendors") return <StorefrontIcon />;
  if (slug === "procurement") return <ShoppingCartCheckoutIcon />;
  return <BusinessCenterIcon />;
}

export default function Sidebar({
  collapsed = false,
  onToggleCollapse,
}: {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}) {
  const pathname = usePathname();
  const { hasModule, hasPermission, user } = useAuth();
  const canViewBusinessAreas = hasModule("documents") && hasPermission("documents:read");
  const [businessAreaMenuItems, setBusinessAreaMenuItems] = useState<DynamicBusinessAreaItem[]>([]);

  useEffect(() => {
    let active = true;

    async function loadBusinessAreaMenu() {
      if (!canViewBusinessAreas) {
        if (active) {
          setBusinessAreaMenuItems([]);
        }
        return;
      }

      try {
        const response = await getBusinessAreaCatalog();
        if (!active) return;
        const nextItems = (response?.data || [])
          .map((item: any) => {
            const slug = String(item.slug || "");
            const label = businessAreaLabel(
              slug,
              String(item.display_name || item.name || "")
            );

            return {
              label,
              icon: businessAreaIcon(slug),
              path: String(item.path || `/business-areas/${slug}`),
              slug,
            };
          })
          .filter(
            (item) =>
              !hiddenBusinessAreaSlugs.has(item.slug.toLowerCase()) &&
              !hiddenBusinessAreaLabels.has(item.label.trim().toLowerCase())
          )
          .map(({ slug: _slug, ...item }) => item);
        setBusinessAreaMenuItems(nextItems);
      } catch {
        if (active) {
          setBusinessAreaMenuItems([]);
        }
      }
    }

    void loadBusinessAreaMenu();

    return () => {
      active = false;
    };
  }, [canViewBusinessAreas, user?.tenant_id]);

  const visibleItems = menuItems.filter((item) => {
    return hasModule(item.module) && hasPermission(item.permission);
  });
  const businessAreaItems = useMemo(
    () =>
      canViewBusinessAreas
        ? businessAreaMenuItems
        : [],
    [businessAreaMenuItems, canViewBusinessAreas]
  );
  const standardItems = useMemo(
    () =>
      visibleItems.filter(
        (item) =>
          !["/proposals", "/vendors", "/procurement", "/reports", "/settings/augmis-admin"].includes(
            item.path
          )
      ),
    [visibleItems]
  );
  const augmisAdminItem = useMemo(
    () =>
      user?.role === "SUPER_ADMIN"
        ? visibleItems.find((item) => item.path === "/settings/augmis-admin")
        : undefined,
    [user?.role, visibleItems]
  );
  const reportsItems = useMemo(
    () => visibleItems.filter((item) => ["/reports"].includes(item.path)),
    [visibleItems]
  );
  const reportSubItems = useMemo(() => {
    const items: Array<Pick<SidebarItem, "label" | "icon" | "path">> = [
      {
        label: "Repository Content Report",
        icon: <AssessmentOutlinedIcon />,
        path: "/reports",
      },
    ];

    if (hasModule("settings") && hasPermission("admin:users")) {
      items.push({
        label: "Repository Report",
        icon: <FactCheckOutlinedIcon />,
        path: "/reports/repository-report",
      });
    }

    return items;
  }, [hasModule, hasPermission]);
  const [businessAreaOpen, setBusinessAreaOpen] = useState(
    pathname.startsWith("/business-areas") ||
      ["/proposals", "/vendors", "/procurement"].includes(pathname)
  );
  const [reportsOpen, setReportsOpen] = useState(
    pathname.startsWith("/reports")
  );

  useEffect(() => {
    if (
      pathname.startsWith("/business-areas") ||
      ["/proposals", "/vendors", "/procurement"].includes(pathname)
    ) {
      setBusinessAreaOpen(true);
      setReportsOpen(false);
    }
    if (pathname.startsWith("/reports")) {
      setReportsOpen(true);
      setBusinessAreaOpen(false);
    }
  }, [pathname]);

  function renderMenuItem(
    item: Pick<SidebarItem, "label" | "icon" | "path">,
    nested = false
  ) {
    const button = (
      <ListItemButton
        key={item.path}
        component={Link}
        href={item.path}
        selected={pathname === item.path}
        sx={{
          mb: 0.35,
          borderRadius: 2,
          minHeight: nested ? 36 : 40,
          px: collapsed ? 1 : nested ? 1.75 : 1.25,
          py: nested ? 0.35 : 0.45,
          pl: collapsed ? 1 : nested ? 5.25 : 1.25,
          justifyContent: collapsed ? "center" : "flex-start",
          color: pathname === item.path ? "primary.main" : "#4b5563",
          bgcolor: pathname === item.path ? "action.selected" : "transparent",
          "& .MuiListItemIcon-root": {
            color: pathname === item.path ? "primary.main" : "#4b5563",
          },
          "&:hover": {
            bgcolor: "primary.main",
            color: "#fff",
            "& .MuiListItemIcon-root": {
              color: "#fff",
            },
          },
        }}
      >
        <ListItemIcon
          sx={{
            minWidth: collapsed ? 0 : nested ? 28 : 32,
            mr: collapsed ? 0 : 0,
            justifyContent: "center",
            "& svg": {
              fontSize: nested ? 14 : 15,
            },
            "& img": {
              width: nested ? 14 : 17,
              height: nested ? 14 : 17,
            },
          }}
        >
          {item.icon}
        </ListItemIcon>
        {!collapsed ? (
          <ListItemText
            primary={item.label}
            sx={{
              "& .MuiTypography-root": {
                fontSize: nested ? "12px" : "13px",
                fontWeight: nested ? 400 : 500,
                letterSpacing: 0.1,
                lineHeight: 1.15,
              },
            }}
          />
        ) : null}
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

  function renderGroupedMenuButton({
    keyValue,
    label,
    selected,
    icon,
    open,
    onClick,
  }: {
    keyValue: string;
    label: string;
    selected: boolean;
    icon: ReactNode;
    open: boolean;
    onClick: () => void;
  }) {
    const button = (
      <ListItemButton
        key={keyValue}
        onClick={onClick}
        selected={selected}
        sx={{
          mb: 0.35,
          borderRadius: 2,
          minHeight: 40,
          px: collapsed ? 1 : 1.25,
          py: 0.45,
          justifyContent: collapsed ? "center" : "flex-start",
          color: selected ? "primary.main" : "#4b5563",
          bgcolor: selected ? "action.selected" : "transparent",
          "& .MuiListItemIcon-root": {
            color: selected ? "primary.main" : "#4b5563",
          },
          "&:hover": {
            bgcolor: "primary.main",
            color: "#fff",
            "& .MuiListItemIcon-root": {
              color: "#fff",
            },
          },
        }}
      >
        <ListItemIcon
          sx={{
            minWidth: collapsed ? 0 : 32,
            justifyContent: "center",
            "& svg": {
              fontSize: 15,
            },
          }}
        >
          {icon}
        </ListItemIcon>
        {!collapsed ? (
          <ListItemText
            primary={label}
            sx={{
              "& .MuiTypography-root": {
                fontSize: "13px",
                fontWeight: 500,
                letterSpacing: 0.1,
                lineHeight: 1.15,
              },
            }}
          />
        ) : null}
        {!collapsed ? open ? (
          <ExpandLessIcon sx={{ fontSize: 16, color: "inherit" }} />
        ) : (
          <ExpandMoreIcon sx={{ fontSize: 16, color: "inherit" }} />
        ) : null}
      </ListItemButton>
    );

    return collapsed ? (
      <Tooltip key={keyValue} title={label} placement="right">
        {button}
      </Tooltip>
    ) : (
      button
    );
  }

  function renderLinkedExpandableMenuButton({
    keyValue,
    label,
    path,
    selected,
    icon,
    open,
    hasChildren,
    onToggle,
  }: {
    keyValue: string;
    label: string;
    path: string;
    selected: boolean;
    icon: ReactNode;
    open: boolean;
    hasChildren: boolean;
    onToggle: () => void;
  }) {
    if (collapsed) {
      return (
        <Tooltip key={keyValue} title={label} placement="right">
          <ListItemButton
            component={Link}
            href={path}
            selected={selected}
            sx={{
              mb: 0.35,
              borderRadius: 2,
              minHeight: 40,
              px: 1,
              py: 0.45,
              justifyContent: "center",
              color: selected ? "primary.main" : "#4b5563",
              bgcolor: selected ? "action.selected" : "transparent",
              "& .MuiListItemIcon-root": {
                color: selected ? "primary.main" : "#4b5563",
              },
              "&:hover": {
                bgcolor: "primary.main",
                color: "#fff",
                "& .MuiListItemIcon-root": {
                  color: "#fff",
                },
              },
            }}
          >
            <ListItemIcon
              sx={{
                minWidth: 0,
                justifyContent: "center",
                "& svg": {
                  fontSize: 15,
                },
              }}
            >
              {icon}
            </ListItemIcon>
          </ListItemButton>
        </Tooltip>
      );
    }

    const linkedButton = (
      <ListItemButton
        component={Link}
        href={path}
        selected={selected}
        sx={{
          borderRadius: 2,
          minHeight: 40,
          px: 1.25,
          py: 0.45,
          flex: 1,
          color: selected ? "primary.main" : "#4b5563",
          bgcolor: selected ? "action.selected" : "transparent",
          "& .MuiListItemIcon-root": {
            color: selected ? "primary.main" : "#4b5563",
          },
          "&:hover": {
            bgcolor: "primary.main",
            color: "#fff",
            "& .MuiListItemIcon-root": {
              color: "#fff",
            },
          },
        }}
      >
        <ListItemIcon
          sx={{
            minWidth: 32,
            justifyContent: "center",
            "& svg": {
              fontSize: 15,
            },
          }}
        >
          {icon}
        </ListItemIcon>
        <ListItemText
          primary={label}
          sx={{
            "& .MuiTypography-root": {
              fontSize: "13px",
              fontWeight: 500,
              letterSpacing: 0.1,
              lineHeight: 1.15,
            },
          }}
        />
      </ListItemButton>
    );

    if (!hasChildren) {
      return linkedButton;
    }

    return (
      <Box
        key={keyValue}
        sx={{
          display: "flex",
          alignItems: "stretch",
          gap: 0.5,
          mb: 0.35,
        }}
      >
        {linkedButton}

        <IconButton
          size="small"
          onClick={onToggle}
          sx={{
            width: 28,
            height: 28,
            alignSelf: "center",
            borderRadius: 1,
            color: selected ? "primary.main" : "#4b5563",
            bgcolor: "transparent",
            "&:hover": {
              bgcolor: "action.hover",
              color: "primary.main",
            },
          }}
        >
          {open ? (
            <ExpandLessIcon sx={{ fontSize: 16 }} />
          ) : (
            <ExpandMoreIcon sx={{ fontSize: 16 }} />
          )}
        </IconButton>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        width: collapsed ? 88 : 240,
        height: "100vh",
        bgcolor: "background.paper",
        borderRight: "1px solid",
        borderColor: "divider",
        position: "fixed",
        left: 0,
        top: 0,
        px: 2,
        pb: 2,
        // Keep the menu closer to the header while preserving a small visual gap.
        pt: "calc(70px + 4px)",
        display: "flex",
        flexDirection: "column",
        transition: "width 220ms ease",
        overflowX: "hidden",
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: collapsed ? "center" : "flex-end",
          mb: 1.25,
        }}
      >
        <Tooltip
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          placement="right"
        >
          <IconButton
            size="small"
            onClick={onToggleCollapse}
            sx={{
              border: "1px solid",
              borderColor: "divider",
              color: "#4b5563",
            }}
          >
            {collapsed ? (
              <ChevronRightOutlinedIcon fontSize="small" />
            ) : (
              <ChevronLeftOutlinedIcon fontSize="small" />
            )}
          </IconButton>
        </Tooltip>
      </Box>

      <List sx={{ mt: "-25px", ml: "-10px" }}>
        {standardItems.slice(0, 3).map((item) => (
          renderMenuItem(item)
        ))}

        {canViewBusinessAreas ? (
          renderLinkedExpandableMenuButton({
            keyValue: "business-area-link-group",
            label: "Business Area Intelligence",
            path: "/business-areas",
            selected:
              pathname.startsWith("/business-areas") ||
              businessAreaItems.some((item) => pathname === item.path),
            icon: <BusinessCenterIcon />,
            open: businessAreaOpen,
            hasChildren: businessAreaItems.length > 0,
            onToggle: () =>
              setBusinessAreaOpen((open) => {
                const nextOpen = !open;
                if (nextOpen) {
                  setReportsOpen(false);
                }
                return nextOpen;
              }),
          })
        ) : null}

        {businessAreaItems.length > 0 && !collapsed && (
          <Collapse in={businessAreaOpen} timeout="auto" unmountOnExit>
            <List disablePadding>
              {businessAreaItems.map((item) => renderMenuItem(item, true))}
            </List>
          </Collapse>
        )}

        {reportsItems.length > 0 && (
          renderGroupedMenuButton({
            keyValue: "reports-group",
            label: "Reports",
            selected: pathname.startsWith("/reports"),
            icon: <AssessmentOutlinedIcon />,
            open: reportsOpen,
            onClick: () =>
              setReportsOpen((open) => {
                const nextOpen = !open;
                if (nextOpen) {
                  setBusinessAreaOpen(false);
                }
                return nextOpen;
              }),
          })
        )}

        {reportsItems.length > 0 && !collapsed && (
          <Collapse in={reportsOpen} timeout="auto" unmountOnExit>
            <List disablePadding>
              {reportSubItems.map((item) => renderMenuItem(item, true))}
            </List>
          </Collapse>
        )}

        {renderMenuItem(
          {
            label: "Settings",
            icon: <SettingsIcon />,
            path: "/settings",
          },
          false
        )}

        {augmisAdminItem ? renderMenuItem(augmisAdminItem) : null}

        {standardItems.slice(3).filter((item) => item.path !== "/settings").map((item) => (
          renderMenuItem(item)
        ))}
      </List>

      <Box sx={{ mt: "auto", pt: 2, textAlign: collapsed ? "center" : "left" }}>
        {collapsed ? (
          <Tooltip title={`Role: ${user?.role || ""}`} placement="right">
            <Typography variant="caption" color="text.secondary">
              {String(user?.role || "").charAt(0)}
            </Typography>
          </Tooltip>
        ) : (
          <Typography variant="caption" color="text.secondary">
            Role: {user?.role}
          </Typography>
        )}
      </Box>
    </Box>
  );
}
