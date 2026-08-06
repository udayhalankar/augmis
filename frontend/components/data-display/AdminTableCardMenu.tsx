"use client";

import type { ReactNode } from "react";

import { Box, Tab, Tabs } from "@mui/material";

type SimpleSx = Record<string, any>;

function mergeSx(...items: Array<SimpleSx | undefined>) {
  return items.reduce<SimpleSx>((acc, item) => {
    if (!item) {
      return acc;
    }
    return { ...acc, ...item };
  }, {});
}

export const ADMIN_TABLE_CARD_MENU_SX = {
  px: 1.5,
  bgcolor: "#FFFFFF",
  borderBottom: "1px solid #D7E1F0",
} as const;

export const ADMIN_TABLE_CARD_TABS_SX = {
  minHeight: 56,
  "& .MuiTab-root": {
    minHeight: 56,
    textTransform: "none",
    fontWeight: 700,
    fontSize: "0.92rem",
    color: "#5A6B85",
    px: 2,
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

type AdminTableCardMenuItem = {
  key: string;
  label: ReactNode;
};

type AdminTableCardMenuProps = {
  actions?: ReactNode;
  menuSx?: SimpleSx;
  onChange: (value: string) => void;
  tabs: AdminTableCardMenuItem[];
  tabsSx?: SimpleSx;
  value: string;
};

export function AdminTableCardMenu({
  actions,
  menuSx,
  onChange,
  tabs,
  tabsSx,
  value,
}: AdminTableCardMenuProps) {
  return (
    <Box sx={mergeSx(ADMIN_TABLE_CARD_MENU_SX, menuSx)}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
          flexWrap: "wrap",
        }}
      >
        <Tabs
          value={value}
          onChange={(_, nextValue) => onChange(String(nextValue))}
          variant="scrollable"
          sx={mergeSx(ADMIN_TABLE_CARD_TABS_SX, tabsSx)}
        >
          {tabs.map((tab) => (
            <Tab key={tab.key} value={tab.key} label={tab.label} disableRipple />
          ))}
        </Tabs>
        {actions ? <Box sx={{ py: 1 }}>{actions}</Box> : null}
      </Box>
    </Box>
  );
}
