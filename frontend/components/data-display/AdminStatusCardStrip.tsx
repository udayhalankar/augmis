"use client";

import type { ReactNode } from "react";

import { useEffect, useMemo, useState } from "react";

import ChevronLeftRoundedIcon from "@mui/icons-material/ChevronLeftRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import { Box, Grid, IconButton } from "@mui/material";

import { ADMIN_STATUS_CARD_GRADIENTS, AdminStatusCard } from "./AdminStatusCard";

type SimpleSx = Record<string, any>;

export type AdminStatusMetric = {
  caption?: ReactNode;
  currentLabel?: ReactNode;
  label: ReactNode;
  value: ReactNode;
};

type AdminStatusCardStripProps = {
  cardPaperSx?: SimpleSx;
  cardsPerPage?: number;
  containerSx?: SimpleSx;
  itemGridSize?: {
    xs?: number;
    sm?: number;
    md?: number;
    lg?: number;
    xl?: number;
  };
  metrics: AdminStatusMetric[];
};

export function AdminStatusCardStrip({
  cardPaperSx,
  cardsPerPage = 4,
  containerSx,
  itemGridSize = { xs: 12, md: 6, xl: 3 },
  metrics,
}: AdminStatusCardStripProps) {
  const [page, setPage] = useState(0);

  const maxPage = Math.max(0, Math.ceil(metrics.length / cardsPerPage) - 1);
  const safePage = Math.min(page, maxPage);
  const visibleMetrics = useMemo(
    () => metrics.slice(safePage * cardsPerPage, (safePage + 1) * cardsPerPage),
    [cardsPerPage, metrics, safePage]
  );

  useEffect(() => {
    setPage(0);
  }, [metrics, cardsPerPage]);

  return (
    <Box sx={{ position: "relative", ...containerSx }}>
      {metrics.length > cardsPerPage ? (
        <>
          <IconButton
            size="small"
            disabled={safePage === 0}
            onClick={() => setPage((value) => Math.max(0, value - 1))}
            sx={{
              position: "absolute",
              left: -20,
              top: "50%",
              transform: "translateY(-50%)",
              zIndex: 2,
              border: "1px solid #CBD5E1",
              bgcolor: "#FFFFFF",
              boxShadow: "0 6px 16px rgba(15, 23, 42, 0.12)",
              "&:hover": {
                bgcolor: "#FFFFFF",
              },
            }}
          >
            <ChevronLeftRoundedIcon fontSize="small" />
          </IconButton>

          <IconButton
            size="small"
            disabled={safePage >= maxPage}
            onClick={() => setPage((value) => Math.min(maxPage, value + 1))}
            sx={{
              position: "absolute",
              right: -20,
              top: "50%",
              transform: "translateY(-50%)",
              zIndex: 2,
              border: "1px solid #CBD5E1",
              bgcolor: "#FFFFFF",
              boxShadow: "0 6px 16px rgba(15, 23, 42, 0.12)",
              "&:hover": {
                bgcolor: "#FFFFFF",
              },
            }}
          >
            <ChevronRightRoundedIcon fontSize="small" />
          </IconButton>
        </>
      ) : null}

      <Grid container spacing={2}>
        {visibleMetrics.map((metric, index) => (
          <Grid key={`${String(metric.label)}-${index}`} size={itemGridSize}>
            <AdminStatusCard
              title={metric.label}
              value={metric.value}
              caption={metric.caption}
              currentLabel={metric.currentLabel}
              gradient={
                ADMIN_STATUS_CARD_GRADIENTS[
                  (safePage * cardsPerPage + index) % ADMIN_STATUS_CARD_GRADIENTS.length
                ]
              }
              paperSx={cardPaperSx}
            />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
