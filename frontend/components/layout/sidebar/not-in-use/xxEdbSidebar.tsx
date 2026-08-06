"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  Box,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  Tooltip,
  Typography,
} from "@mui/material";

import ChevronLeftOutlinedIcon from "@mui/icons-material/ChevronLeftOutlined";
import ChevronRightOutlinedIcon from "@mui/icons-material/ChevronRightOutlined";

import type { EdbSidebarItem } from "./edbSidebarConfig";

const HEADER_BLUE = "#082f73";
const CARD_RADIUS = 5;
const MENU_ITEM_HEIGHT = 32;

function isItemActive(pathname: string, href: string) {
  if (href === "/business-areas") {
    return pathname === href || pathname.startsWith("/business-areas/");
  }

  if (href === "/reports/repository-report") {
    return pathname === href || pathname.startsWith("/reports/repository-report/");
  }

  if (href === "/reports") {
    return pathname === href;
  }

  if (href === "/settings") {
    return pathname === href || pathname.startsWith("/settings/");
  }

  if (href === "/documents") {
    return pathname === href || pathname.startsWith("/documents/");
  }

  return pathname === href;
}

export default function EdbSidebar({
  items,
  title = "Menu",
  collapsed = false,
  onToggleCollapse,
}: {
  items: EdbSidebarItem[];
  title?: string;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}) {
  const pathname = usePathname();

  return (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        minHeight: 0,
      }}
    >
      <Box
        sx={{
          height: 39,
          flexShrink: 0,
          bgcolor: HEADER_BLUE,
          color: "#ffffff",
          px: 1.25,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 1,
        }}
      >
        <Typography
          sx={{
            fontSize: "0.76rem",
            fontWeight: 700,
            color: "#fff",
            lineHeight: 1.1,
            letterSpacing: "0.01em",
          }}
        >
          {title}
        </Typography>

        <IconButton
          size="small"
          onClick={onToggleCollapse}
          sx={{
            color: "#fff",
            borderRadius: `${CARD_RADIUS}px`,
            p: 0.25,
            width: 24,
            height: 24,
          }}
        >
          {collapsed ? (
            <ChevronRightOutlinedIcon sx={{ fontSize: 18 }} />
          ) : (
            <ChevronLeftOutlinedIcon sx={{ fontSize: 18 }} />
          )}
        </IconButton>
      </Box>

      <Box
        sx={{
          p: 1,
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
        }}
      >
        <List
          disablePadding
          dense
          sx={{
            p: 0,
            m: 0,
            display: "flex",
            flexDirection: "column",
            gap: "6px",
          }}
        >
          {items.map((item) => {
            const selected = isItemActive(pathname, item.href);

            const menuItem = (
              <ListItemButton
                key={item.href}
                component={Link}
                href={item.href}
                selected={selected}
                disableGutters
                sx={{
                  height: MENU_ITEM_HEIGHT,
                  minHeight: `${MENU_ITEM_HEIGHT}px !important`,
                  maxHeight: `${MENU_ITEM_HEIGHT}px !important`,
                  p: "0 !important",
                  px: collapsed ? 0 : 1,
                  borderRadius: `${CARD_RADIUS}px`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: collapsed ? "center" : "flex-start",
                  color: selected ? "#183b7a" : "#415064",
                  bgcolor: selected ? "rgba(24, 59, 122, 0.08)" : "transparent",
                  border: selected
                    ? "1px solid rgba(24, 59, 122, 0.12)"
                    : "1px solid transparent",

                  "&.MuiListItemButton-root": {
                    minHeight: `${MENU_ITEM_HEIGHT}px !important`,
                    height: `${MENU_ITEM_HEIGHT}px !important`,
                    paddingTop: "0 !important",
                    paddingBottom: "0 !important",
                  },

                  "& .MuiListItemIcon-root": {
                    color: "inherit",
                  },

                  "&:hover": {
                    bgcolor: "rgba(24, 59, 122, 0.08)",
                    borderColor: "rgba(24, 59, 122, 0.14)",
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: collapsed ? 0 : 28,
                    width: collapsed ? 22 : 28,
                    height: MENU_ITEM_HEIGHT,
                    mr: collapsed ? 0 : 0.4,
                    color: "inherit",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,

                    "& svg": {
                      fontSize: 18,
                    },
                  }}
                >
                  {item.icon}
                </ListItemIcon>

                {!collapsed && (
                  <Typography
                    sx={{
                      fontSize: "0.78rem",
                      fontWeight: selected ? 700 : 500,
                      lineHeight: 1,
                      whiteSpace: "nowrap",
                      m: 0,
                    }}
                  >
                    {item.label}
                  </Typography>
                )}
              </ListItemButton>
            );

            return collapsed ? (
              <Tooltip key={item.href} title={item.label} placement="right">
                <Box>{menuItem}</Box>
              </Tooltip>
            ) : (
              menuItem
            );
          })}
        </List>
      </Box>
    </Box>
  );
}
