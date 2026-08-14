"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";

import ChevronLeftRoundedIcon from "@mui/icons-material/ChevronLeftRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import { Box, IconButton, Paper, Stack, Typography } from "@mui/material";

export type BusinessStatusCardItem = {
  key: string;
  title: string;
  value: ReactNode;
  description: string;
  icon?: ReactNode;
  gradient?: string;
  iconTint?: string;
  iconSurface?: string;
};

const MAX_VISIBLE_CARDS = 5;

function BusinessStatusCard({ item }: { item: BusinessStatusCardItem }) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.25,
        borderRadius: "8px",
        border: "1px solid #D9E2EC",
        background: item.gradient || "linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%)",
        minHeight: 152,
      }}
    >
      <Stack sx={{ height: "100%" }}>
        <Stack direction="row" spacing={1.25} sx={{ alignItems: "flex-start", justifyContent: "space-between" }}>
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography
              sx={{
                fontSize: 12,
                fontWeight: 700,
                color: "#64748B",
                textTransform: "uppercase",
                letterSpacing: ".05em",
              }}
            >
              {item.title}
            </Typography>
          </Box>
          {item.icon ? (
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: "10px",
                display: "grid",
                placeItems: "center",
                flexShrink: 0,
                bgcolor: item.iconSurface || "rgba(255,255,255,0.72)",
                color: item.iconTint || "#1D4ED8",
              }}
            >
              {item.icon}
            </Box>
          ) : null}
        </Stack>
        <Typography sx={{ mt: 1.35, fontSize: 26, fontWeight: 700, color: "#0F172A", lineHeight: 1.1 }}>
          {item.value}
        </Typography>
        <Box sx={{ flex: 1 }} />
        <Typography
          sx={{
            mt: 1.15,
            color: "#334155",
            fontSize: 13,
            lineHeight: 1.35,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
          title={item.description}
        >
          {item.description}
        </Typography>
      </Stack>
    </Paper>
  );
}

export default function BusinessStatusCardStrip({ items }: { items: BusinessStatusCardItem[] }) {
  const [offset, setOffset] = useState(0);
  const canShuffle = items.length > MAX_VISIBLE_CARDS;
  const maxOffset = Math.max(0, items.length - MAX_VISIBLE_CARDS);

  useEffect(() => {
    setOffset((current) => Math.min(current, maxOffset));
  }, [maxOffset]);

  const visibleItems = useMemo(() => {
    const start = Math.min(offset, maxOffset);
    return items.slice(start, start + MAX_VISIBLE_CARDS);
  }, [items, maxOffset, offset]);

  if (!items.length) {
    return null;
  }

  return (
    <Stack spacing={1.25}>
      <Stack
        direction="row"
        sx={{
          alignItems: "center",
          justifyContent: "flex-end",
        }}
      >
        {canShuffle ? (
          <Stack direction="row" spacing={0.6}>
            <IconButton
              size="small"
              disabled={offset === 0}
              onClick={() => setOffset((current) => Math.max(0, current - 1))}
              sx={{
                borderRadius: "8px",
                border: "1px solid #D9E2EC",
                bgcolor: "#FFFFFF",
                width: 36,
                height: 36,
              }}
            >
              <ChevronLeftRoundedIcon fontSize="small" />
            </IconButton>
            <IconButton
              size="small"
              disabled={offset >= maxOffset}
              onClick={() => setOffset((current) => Math.min(maxOffset, current + 1))}
              sx={{
                borderRadius: "8px",
                border: "1px solid #D9E2EC",
                bgcolor: "#FFFFFF",
                width: 36,
                height: 36,
              }}
            >
              <ChevronRightRoundedIcon fontSize="small" />
            </IconButton>
          </Stack>
        ) : null}
      </Stack>
      <Box
        sx={{
          display: "grid",
          gap: 1.75,
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, minmax(0, 1fr))",
            lg: canShuffle
              ? `repeat(${MAX_VISIBLE_CARDS}, minmax(0, 1fr))`
              : `repeat(${Math.min(visibleItems.length, MAX_VISIBLE_CARDS)}, minmax(0, 1fr))`,
          },
        }}
      >
        {visibleItems.map((item) => (
          <BusinessStatusCard key={item.key} item={item} />
        ))}
      </Box>
    </Stack>
  );
}
