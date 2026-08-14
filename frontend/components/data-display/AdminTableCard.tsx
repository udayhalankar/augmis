"use client";

import type { ReactNode } from "react";

import { Box, Paper, Typography } from "@mui/material";

import { AdminTableCardHeader } from "./AdminTableCardHeader";
import { AdminTableCardMenu } from "./AdminTableCardMenu";

type SimpleSx = Record<string, any>;

function mergeSx(...items: Array<SimpleSx | undefined>) {
  return items.reduce<SimpleSx>((acc, item) => {
    if (!item) {
      return acc;
    }
    return { ...acc, ...item };
  }, {});
}

export const ADMIN_TABLE_CARD_SX = {
  width: "100%",
  overflow: "hidden",
  borderRadius: "18px",
  borderColor: "#C9D8F0",
  boxShadow: "0 10px 24px rgba(15, 23, 42, 0.06)",
  bgcolor: "#F6FAFF",
  "&.MuiPaper-rounded": {
    borderRadius: "8px !important",
  },
} as const;

export const ADMIN_TABLE_CARD_BODY_SX = {
  bgcolor: "#F6FAFF",
} as const;

export const ADMIN_TABLE_CARD_SUMMARY_SX = {
  px: 3,
  py: 0.9,
  borderTop: "1px solid #D8E1EE",
  bgcolor: "#F6FAFF",
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 2,
  minHeight: 54,
} as const;

export const ADMIN_TABLE_CARD_SUMMARY_TEXT_SX = {
  fontSize: 13,
  lineHeight: 1.35,
  color: "#486581",
} as const;

export const ADMIN_TABLE_CARD_FOOTER_END_SX = {
  display: "flex",
  alignItems: "center",
  justifyContent: "flex-end",
  minWidth: 0,
} as const;

export const ADMIN_TABLE_CARD_PAGINATION_SX = {
  border: "none",
  bgcolor: "transparent",
  "& .MuiTablePagination-toolbar": {
    minHeight: "unset",
    px: 0,
    justifyContent: "flex-end",
  },
  "& .MuiTablePagination-spacer": {
    flex: "1 1 auto",
  },
  "& .MuiTablePagination-selectLabel, & .MuiTablePagination-input, & .MuiTablePagination-select, & .MuiTablePagination-selectIcon": {
    display: "none",
  },
  "& .MuiTablePagination-displayedRows": {
    m: 0,
    color: "#102A43",
    fontSize: 12.5,
    lineHeight: 1.35,
  },
  "& .MuiTablePagination-actions": {
    ml: 1,
  },
} as const;

type AdminTableCardProps = {
  accentLabel?: ReactNode;
  actions?: ReactNode;
  bodySx?: SimpleSx;
  children: ReactNode;
  description?: ReactNode;
  descriptionSx?: SimpleSx;
  headerActions?: ReactNode;
  headerSx?: SimpleSx;
  menuActions?: ReactNode;
  menuSx?: SimpleSx;
  paperSx?: SimpleSx;
  footerEnd?: ReactNode;
  summary?: ReactNode;
  summarySx?: SimpleSx;
  tabs?: Array<{ key: string; label: ReactNode }>;
  tabsSx?: SimpleSx;
  title: ReactNode;
  titleSx?: SimpleSx;
  value?: string;
  onTabChange?: (value: string) => void;
};

export function AdminTableCard({
  accentLabel,
  actions,
  bodySx,
  children,
  description,
  descriptionSx,
  headerActions,
  headerSx,
  menuActions,
  menuSx,
  onTabChange,
  paperSx,
  footerEnd,
  summary,
  summarySx,
  tabs,
  tabsSx,
  title,
  titleSx,
  value,
}: AdminTableCardProps) {
  const resolvedHeaderActions = headerActions || actions;

  return (
    <Paper variant="outlined" sx={mergeSx(ADMIN_TABLE_CARD_SX, paperSx)}>
      <AdminTableCardHeader
        title={title}
        description={description}
        accentLabel={accentLabel}
        actions={resolvedHeaderActions}
        headerSx={headerSx}
        titleSx={titleSx}
        descriptionSx={descriptionSx}
      />

      {tabs && tabs.length > 0 && value !== undefined && onTabChange ? (
        <AdminTableCardMenu
          tabs={tabs}
          value={value}
          onChange={onTabChange}
          actions={menuActions}
          menuSx={menuSx}
          tabsSx={tabsSx}
        />
      ) : null}

      <Box sx={mergeSx(ADMIN_TABLE_CARD_BODY_SX, bodySx)}>{children}</Box>

      {summary || footerEnd ? (
        <Box sx={mergeSx(ADMIN_TABLE_CARD_SUMMARY_SX, summarySx)}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            {typeof summary === "string" || typeof summary === "number" ? (
              <Typography sx={ADMIN_TABLE_CARD_SUMMARY_TEXT_SX}>{summary}</Typography>
            ) : (
              summary
            )}
          </Box>
          {footerEnd ? <Box sx={ADMIN_TABLE_CARD_FOOTER_END_SX}>{footerEnd}</Box> : null}
        </Box>
      ) : null}
    </Paper>
  );
}
