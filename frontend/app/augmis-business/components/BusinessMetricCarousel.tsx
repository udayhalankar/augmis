"use client";

import { useEffect, useRef, useState } from "react";

import ChevronLeftRoundedIcon from "@mui/icons-material/ChevronLeftRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import { Box, IconButton, Paper, Stack, Typography } from "@mui/material";

export type BusinessMetricItem = {
  key: string;
  title: string;
  value: string | number;
  subtitle: string;
  icon?: React.ReactNode;
  accent?: string;
};

export function BusinessMetricCard({ item }: { item: BusinessMetricItem }) {
  return (
    <Paper
      elevation={0}
      sx={{
        minWidth: { xs: 220, md: 248 },
        maxWidth: { xs: 220, md: 248 },
        borderRadius: "10px",
        border: "2px solid #0F3D5E",
        overflow: "hidden",
        flex: "0 0 auto",
        bgcolor: "#FFFFFF",
        minHeight: 182,
      }}
    >
      <Box
        sx={{
          px: 1.75,
          py: 1,
          background: item.accent || "linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)",
          borderBottom: "2px solid #0F3D5E",
        }}
      >
        <Stack direction="row" spacing={0.85} sx={{ alignItems: "center" }}>
          {item.icon ? <Box sx={{ display: "flex", color: "#0F4C81" }}>{item.icon}</Box> : null}
          <Typography sx={{ fontSize: 13, fontWeight: 800, color: "#0F172A" }}>{item.title}</Typography>
        </Stack>
      </Box>
      <Box
        sx={{
          px: 1.75,
          py: 1.6,
          minHeight: 124,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "space-between",
          textAlign: "center",
        }}
      >
        <Typography sx={{ fontSize: 42, fontWeight: 800, color: "#0F172A", lineHeight: 1 }}>
          {item.value}
        </Typography>
        <Typography sx={{ mt: 1, color: "#334155", fontSize: 12.5, lineHeight: 1.45, maxWidth: 184 }}>
          {item.subtitle}
        </Typography>
      </Box>
    </Paper>
  );
}

export default function BusinessMetricCarousel({ items }: { items: BusinessMetricItem[] }) {
  const railRef = useRef<HTMLDivElement | null>(null);
  const [scrollState, setScrollState] = useState({ left: true, right: false });

  function updateScrollState() {
    const rail = railRef.current;
    if (!rail) {
      return;
    }
    setScrollState({
      left: rail.scrollLeft <= 4,
      right: rail.scrollLeft + rail.clientWidth >= rail.scrollWidth - 4,
    });
  }

  function scrollByDirection(direction: "left" | "right") {
    const rail = railRef.current;
    if (!rail) {
      return;
    }
    rail.scrollBy({ left: direction === "left" ? -540 : 540, behavior: "smooth" });
    window.setTimeout(updateScrollState, 220);
  }

  useEffect(() => {
    updateScrollState();
  }, [items.length]);

  if (!items.length) {
    return null;
  }

  return (
    <Box sx={{ position: "relative", bgcolor: "transparent" }}>
      <IconButton
        size="small"
        aria-label="Scroll metrics left"
        disabled={scrollState.left}
        onClick={() => scrollByDirection("left")}
        sx={{
          position: "absolute",
          left: { xs: -10, md: -18 },
          top: "50%",
          transform: "translateY(-50%)",
          zIndex: 2,
          bgcolor: "#FFFFFF",
          border: "1px solid rgba(255,255,255,0.72)",
          boxShadow: "0 10px 24px rgba(15, 23, 42, 0.18)",
          borderRadius: "6px",
          width: 42,
          height: 62,
          "&.Mui-disabled": {
            opacity: 0.35,
            bgcolor: "rgba(255,255,255,0.82)",
          },
        }}
      >
        <ChevronLeftRoundedIcon fontSize="small" />
      </IconButton>
      <Box
        ref={railRef}
        onScroll={updateScrollState}
        sx={{
          overflowX: "auto",
          scrollBehavior: "smooth",
          scrollbarWidth: "none",
          msOverflowStyle: "none",
          pl: 0,
          pr: { xs: 0.5, md: 1 },
          py: 0.25,
          bgcolor: "transparent",
          "&::-webkit-scrollbar": {
            display: "none",
          },
        }}
      >
        <Stack
          direction="row"
          spacing={0.8}
          sx={{
            minWidth: "max-content",
            py: 0.25,
            alignItems: "stretch",
          }}
        >
          {items.map((item) => (
            <BusinessMetricCard key={item.key} item={item} />
          ))}
        </Stack>
      </Box>
      <IconButton
        size="small"
        aria-label="Scroll metrics right"
        disabled={scrollState.right}
        onClick={() => scrollByDirection("right")}
        sx={{
          position: "absolute",
          right: { xs: -10, md: -18 },
          top: "50%",
          transform: "translateY(-50%)",
          zIndex: 2,
          bgcolor: "#FFFFFF",
          border: "1px solid rgba(255,255,255,0.72)",
          boxShadow: "0 10px 24px rgba(15, 23, 42, 0.18)",
          borderRadius: "6px",
          width: 42,
          height: 62,
          "&.Mui-disabled": {
            opacity: 0.35,
            bgcolor: "rgba(255,255,255,0.82)",
          },
        }}
      >
        <ChevronRightRoundedIcon fontSize="small" />
      </IconButton>
    </Box>
  );
}
