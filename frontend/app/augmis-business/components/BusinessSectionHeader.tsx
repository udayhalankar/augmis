"use client";

import { Box, Chip, Stack, Typography } from "@mui/material";

export default function BusinessSectionHeader({
  title,
  subtitle,
  icon,
  actions,
  count,
  accent = "linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)",
}: {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  count?: string | number;
  accent?: string;
}) {
  return (
    <Box
      sx={{
        px: 2,
        py: 1.15,
        background: accent,
        borderBottom: "1px solid #E2E8F0",
      }}
    >
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={1}
        sx={{ justifyContent: "space-between", alignItems: { md: "center" } }}
      >
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", minWidth: 0 }}>
          {icon ? <Box sx={{ display: "flex", color: "#2563EB" }}>{icon}</Box> : null}
          <Box sx={{ minWidth: 0 }}>
            <Stack direction="row" spacing={0.8} sx={{ alignItems: "center", flexWrap: "wrap" }}>
              <Typography sx={{ fontWeight: 800, color: "#0F172A" }}>{title}</Typography>
              {count != null ? (
                <Chip
                  size="small"
                  label={String(count)}
                  sx={{ height: 22, bgcolor: "#FFFFFF", border: "1px solid #D9E2EC", fontWeight: 700 }}
                />
              ) : null}
            </Stack>
            {subtitle ? (
              <Typography sx={{ mt: 0.25, color: "#475569", fontSize: 13 }}>{subtitle}</Typography>
            ) : null}
          </Box>
        </Stack>
        {actions ? <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>{actions}</Stack> : null}
      </Stack>
    </Box>
  );
}
