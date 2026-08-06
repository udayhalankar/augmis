"use client";

import type { ReactNode } from "react";

import { Box, Paper, Stack, Tab, Tabs } from "@mui/material";

type SimpleSx = Record<string, any>;

function mergeSx(...items: Array<SimpleSx | undefined>) {
  return items.reduce<SimpleSx>((acc, item) => {
    if (!item) {
      return acc;
    }
    return { ...acc, ...item };
  }, {});
}

export const ADMIN_TOP_MENU_PAPER_SX = {
  mt: 0,
  ml: 0,
  mr: 0,
  width: "100%",
  borderRadius: 0,
  overflow: "hidden",
  borderColor: "#21344D",
  "&.MuiPaper-rounded": {
    borderRadius: "0 !important",
  },
} as const;

export const ADMIN_TOP_MENU_CONTENT_SX = {
  px: 2,
  py: 0,
  bgcolor: "#FFFFFF",
} as const;

export const ADMIN_TOP_MENU_POST_MENU_CONTENT_SX = {
  pt: "31px",
} as const;

export const ADMIN_TOP_MENU_POST_MENU_BLOCK_SX = {
  mt: "21px",
} as const;

export const ADMIN_TOP_MENU_LAYOUT_SX = {
  justifyContent: "space-between",
  alignItems: { xs: "stretch", md: "center" },
  minHeight: 44,
} as const;

export const ADMIN_TOP_MENU_TABS_SX = {
  minHeight: 44,
  "& .MuiTab-root": {
    minHeight: 44,
    textTransform: "none",
    fontWeight: 700,
    fontSize: 13.5,
    px: 2,
    color: "#5A6B85",
  },
  "& .Mui-selected": {
    color: "#1D4ED8",
  },
  "& .MuiTabs-indicator": {
    height: 3,
    borderRadius: 0,
    backgroundColor: "#2E5BFF",
  },
} as const;

type AdminTopMenuItem = {
  key: string;
  label: ReactNode;
};

type AdminTopMenuProps = {
  actions?: ReactNode;
  bleedSx?: SimpleSx;
  borderColor?: string;
  contentSx?: SimpleSx;
  fullBleed?: boolean;
  layoutSx?: SimpleSx;
  menuItems: AdminTopMenuItem[];
  onChange: (value: string) => void;
  paperSx?: SimpleSx;
  tabsSx?: SimpleSx;
  value: string;
};

export function AdminTopMenu({
  actions,
  bleedSx,
  borderColor = "#21344D",
  contentSx,
  fullBleed = false,
  layoutSx,
  menuItems,
  onChange,
  paperSx,
  tabsSx,
  value,
}: AdminTopMenuProps) {
  return (
    <Paper
      variant="outlined"
      sx={mergeSx(
        ADMIN_TOP_MENU_PAPER_SX,
        {
          borderColor,
        },
        fullBleed
          ? {
              ml: -4,
              mr: -5,
              width: "calc(100% + 80px)",
              borderLeft: 0,
              borderRight: 0,
              ...bleedSx,
            }
          : undefined,
        paperSx
      )}
    >
      <Box sx={mergeSx(ADMIN_TOP_MENU_CONTENT_SX, contentSx)}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={2}
          sx={mergeSx(ADMIN_TOP_MENU_LAYOUT_SX, layoutSx)}
        >
          <Tabs
            value={value}
            onChange={(_, nextValue) => onChange(String(nextValue))}
            variant="scrollable"
            sx={mergeSx(ADMIN_TOP_MENU_TABS_SX, tabsSx)}
          >
            {menuItems.map((item) => (
              <Tab key={item.key} value={item.key} label={item.label} disableRipple />
            ))}
          </Tabs>
          {actions ? (
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              {actions}
            </Stack>
          ) : null}
        </Stack>
      </Box>
    </Paper>
  );
}
