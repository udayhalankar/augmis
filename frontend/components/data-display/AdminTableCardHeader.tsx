"use client";

import type { ReactNode } from "react";

import { Chip, Stack, Typography } from "@mui/material";

type SimpleSx = Record<string, any>;

function mergeSx(...items: Array<SimpleSx | undefined>) {
  return items.reduce<SimpleSx>((acc, item) => {
    if (!item) {
      return acc;
    }
    return { ...acc, ...item };
  }, {});
}

export const ADMIN_TABLE_CARD_HEADER_SX = {
  px: 3,
  py: 1.8,
  bgcolor: "#315FB5",
  color: "#FFFFFF",
  borderBottom: "1px solid rgba(255,255,255,0.12)",
} as const;

export const ADMIN_TABLE_CARD_HEADER_WITH_ACTIONS_SX = {
  py: 1.35,
  alignItems: { xs: "stretch", md: "center" },
} as const;

export const ADMIN_TABLE_CARD_TITLE_SX = {
  fontSize: "1.05rem",
  fontWeight: 600,
  lineHeight: 1.2,
  color: "#FFFFFF",
} as const;

export const ADMIN_TABLE_CARD_DESCRIPTION_SX = {
  mt: 0.6,
  fontSize: "0.92rem",
  lineHeight: 1.45,
  color: "rgba(255,255,255,0.92)",
} as const;

export const ADMIN_TABLE_CARD_ACCENT_CHIP_SX = {
  height: 20,
  fontWeight: 600,
  color: "#FFFFFF",
  bgcolor: "rgba(255,255,255,0.12)",
  borderColor: "rgba(255,255,255,0.28)",
  "& .MuiChip-label": {
    px: 1.4,
  },
} as const;

export const ADMIN_TABLE_CARD_ACTIONS_SX = {
  alignItems: { xs: "flex-start", md: "center" },
  justifyContent: { xs: "flex-start", md: "flex-end" },
  flexWrap: "wrap",
  "& .MuiTextField-root": {
    "& .MuiOutlinedInput-root": {
      minHeight: 34,
      bgcolor: "#FFFFFF",
    },
    "& .MuiInputBase-input": {
      py: 0.8,
    },
  },
} as const;

type AdminTableCardHeaderProps = {
  accentLabel?: ReactNode;
  actions?: ReactNode;
  description?: ReactNode;
  descriptionSx?: SimpleSx;
  headerSx?: SimpleSx;
  title: ReactNode;
  titleSx?: SimpleSx;
};

export function AdminTableCardHeader({
  accentLabel,
  actions,
  description,
  descriptionSx,
  headerSx,
  title,
  titleSx,
}: AdminTableCardHeaderProps) {
  const hasActions = Boolean(accentLabel || actions);

  return (
    <Stack
      direction={{ xs: "column", md: "row" }}
      spacing={hasActions ? 1.25 : 2}
      sx={mergeSx(
        ADMIN_TABLE_CARD_HEADER_SX,
        hasActions ? ADMIN_TABLE_CARD_HEADER_WITH_ACTIONS_SX : undefined,
        headerSx,
      )}
    >
      <Stack spacing={0} sx={{ flex: 1, minWidth: 0, justifyContent: "center" }}>
        <Typography sx={mergeSx(ADMIN_TABLE_CARD_TITLE_SX, titleSx)}>{title}</Typography>
        {description ? (
          <Typography sx={mergeSx(ADMIN_TABLE_CARD_DESCRIPTION_SX, descriptionSx)}>
            {description}
          </Typography>
        ) : null}
      </Stack>

      <Stack
        direction="row"
        spacing={1.25}
        sx={ADMIN_TABLE_CARD_ACTIONS_SX}
      >
        {accentLabel ? (
          <Chip
            label={accentLabel}
            variant="outlined"
            sx={ADMIN_TABLE_CARD_ACCENT_CHIP_SX}
          />
        ) : null}
        {actions}
      </Stack>
    </Stack>
  );
}
