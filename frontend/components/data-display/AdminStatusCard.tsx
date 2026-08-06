"use client";

import type { ReactNode } from "react";

import { Box, Paper, Stack, Typography } from "@mui/material";

type SimpleSx = Record<string, any>;

function mergeSx(...items: Array<SimpleSx | undefined>) {
  return items.reduce<SimpleSx>((acc, item) => {
    if (!item) {
      return acc;
    }
    return { ...acc, ...item };
  }, {});
}

export const ADMIN_STATUS_CARD_SX = {
  p: 0,
  overflow: "hidden",
  borderRadius: "18px",
  borderColor: "#CFD9E8",
  boxShadow: "0 10px 28px rgba(15, 23, 42, 0.08)",
  bgcolor: "#F8FBFF",
  "&.MuiPaper-rounded": {
    borderRadius: "8px !important",
  },
} as const;

export const ADMIN_STATUS_CARD_GRADIENTS = [
  "linear-gradient(135deg, #31415F 0%, #757A82 100%)",
  "linear-gradient(135deg, #1D4ED8 0%, #3B82F6 100%)",
  "linear-gradient(135deg, #0F766E 0%, #14B8A6 100%)",
  "linear-gradient(135deg, #7C3AED 0%, #A855F7 100%)",
] as const;

type AdminStatusCardProps = {
  caption?: ReactNode;
  currentLabel?: ReactNode;
  gradient: string;
  paperSx?: SimpleSx;
  title: ReactNode;
  value: ReactNode;
};

export function AdminStatusCard({
  caption,
  currentLabel = "Current",
  gradient,
  paperSx,
  title,
  value,
}: AdminStatusCardProps) {
  return (
    <Paper variant="outlined" sx={mergeSx(ADMIN_STATUS_CARD_SX, paperSx)}>
      <Box
        sx={{
          px: 3,
          py: 1.5,
          backgroundImage: gradient,
          color: "#FFFFFF",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <Typography
          sx={{
            color: "#FFFFFF",
            fontSize: 12,
            fontWeight: 600,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
          }}
        >
          {title}
        </Typography>
      </Box>

      <Stack spacing={0.25} sx={{ px: 3, py: 2.25 }}>
        <Typography
          sx={{
            color: "#5A6B85",
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
          }}
        >
          {currentLabel}
        </Typography>
        <Typography
          sx={{
            fontSize: "2.1rem",
            lineHeight: 1,
            fontWeight: 800,
            color: "#102A43",
          }}
        >
          {value}
        </Typography>
        {caption ? <Typography sx={{ fontSize: 12, color: "#7B8794" }}>{caption}</Typography> : null}
      </Stack>
    </Paper>
  );
}
