"use client";

import type { ReactNode } from "react";

import { Box, Tab, Tabs } from "@mui/material";

export type BusinessTabItem = {
  value: string;
  label: ReactNode;
  disabled?: boolean;
};

export default function BusinessTabs({
  value,
  onChange,
  items,
  compact = false,
  actions,
}: {
  value: string;
  onChange: (value: string) => void;
  items: BusinessTabItem[];
  compact?: boolean;
  actions?: ReactNode;
}) {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: { xs: "stretch", md: "center" },
        justifyContent: "space-between",
        gap: 1,
        flexDirection: { xs: "column", md: "row" },
      }}
    >
      <Tabs
        value={value}
        onChange={(_, nextValue) => onChange(String(nextValue))}
        variant="scrollable"
        scrollButtons="auto"
        sx={{
          minHeight: compact ? 38 : 42,
          "& .MuiTabs-flexContainer": {
            gap: 0.4,
          },
          "& .MuiTab-root": {
            minHeight: compact ? 38 : 42,
            textTransform: "none",
            fontWeight: 700,
            fontSize: compact ? 12.5 : 13,
            color: "#475569",
            px: compact ? 1.2 : 1.5,
            py: 0.45,
            borderRadius: "8px 8px 0 0",
            minWidth: "max-content",
          },
          "& .Mui-selected": {
            color: "#1D4ED8",
          },
          "& .MuiTabs-indicator": {
            height: 3,
            backgroundColor: "#2E5BFF",
            borderRadius: 0,
          },
        }}
      >
        {items.map((item) => (
          <Tab
            key={item.value}
            value={item.value}
            label={item.label}
            disabled={item.disabled}
            disableRipple
          />
        ))}
      </Tabs>
      {actions ? (
        <Box sx={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 1 }}>
          {actions}
        </Box>
      ) : null}
    </Box>
  );
}
