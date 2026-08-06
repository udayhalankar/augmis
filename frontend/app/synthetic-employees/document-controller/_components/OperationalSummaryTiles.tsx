"use client";

import { useEffect, useMemo, useState } from "react";
import ChevronLeftRoundedIcon from "@mui/icons-material/ChevronLeftRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import {
  Box,
  Grid,
  IconButton,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

import type { OperationalSummaryTile } from "./useDocumentControllerOperationalData";

function summarizeTotal(tile: OperationalSummaryTile) {
  return tile.items.reduce((sum, item) => sum + (typeof item.value === "number" ? item.value : 0), 0);
}

export function OperationalSummaryTiles({
  tiles,
}: {
  tiles: OperationalSummaryTile[];
}) {
  const [startIndex, setStartIndex] = useState(0);

  const cardsPerPage = 4;
  const maxStartIndex = Math.max(0, tiles.length - cardsPerPage);
  const safeStartIndex = Math.min(startIndex, maxStartIndex);
  const visibleTiles = useMemo(
    () => tiles.slice(safeStartIndex, safeStartIndex + cardsPerPage),
    [cardsPerPage, safeStartIndex, tiles]
  );

  useEffect(() => {
    setStartIndex(0);
  }, [tiles]);

  return (
    <Box sx={{ position: "relative" }}>
      {tiles.length > cardsPerPage ? (
        <>
          <IconButton
            size="small"
            disabled={safeStartIndex === 0}
            onClick={() => setStartIndex((value) => Math.max(0, value - 1))}
            sx={{
              position: "absolute",
              left: -20,
              top: "50%",
              transform: "translateY(-50%)",
              zIndex: 2,
              border: "1px solid #CBD5E1",
              bgcolor: "#FFFFFF",
              boxShadow: "0 6px 16px rgba(15, 23, 42, 0.12)",
              "&:hover": { bgcolor: "#FFFFFF" },
            }}
          >
            <ChevronLeftRoundedIcon fontSize="small" />
          </IconButton>

          <IconButton
            size="small"
            disabled={safeStartIndex >= maxStartIndex}
            onClick={() => setStartIndex((value) => Math.min(maxStartIndex, value + 1))}
            sx={{
              position: "absolute",
              right: -20,
              top: "50%",
              transform: "translateY(-50%)",
              zIndex: 2,
              border: "1px solid #CBD5E1",
              bgcolor: "#FFFFFF",
              boxShadow: "0 6px 16px rgba(15, 23, 42, 0.12)",
              "&:hover": { bgcolor: "#FFFFFF" },
            }}
          >
            <ChevronRightRoundedIcon fontSize="small" />
          </IconButton>
        </>
      ) : null}

      <Grid container spacing={2} sx={{ alignItems: "stretch" }}>
        {visibleTiles.map((tile) => (
          <Grid key={tile.key} size={{ xs: 12, md: 6, xl: 3 }} sx={{ display: "flex" }}>
            <Paper
              variant="outlined"
              sx={{
                borderRadius: "12px",
                border: "1.5px solid #e0e7ff",
                bgcolor: "#fff",
                boxShadow: "0 1px 6px rgba(59,130,246,0.07)",
                px: 1.25,
                py: 0.65,
                minHeight: 69,
                width: "100%",
              }}
            >
              <Stack
                sx={{
                  height: "100%",
                  display: "grid",
                  gridTemplateRows: "auto minmax(50px, auto) 10px 4px",
                  rowGap: 2,
                  pb: 0.5,
                }}
              >
                <Stack direction="row" spacing={1} sx={{ alignItems: "center", justifyContent: "space-between" }}>
                  <Typography
                    sx={{
                      fontSize: 9.6,
                      fontWeight: 800,
                      color: tile.accentColor,
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                    }}
                  >
                    {tile.title}
                  </Typography>
                  <Box
                    sx={{
                      bgcolor: tile.accentSoft,
                      color: tile.accentColor,
                      borderRadius: "6px",
                      px: 0.65,
                      py: 0.1,
                      fontSize: 10.8,
                      fontWeight: 800,
                    }}
                  >
                    {summarizeTotal(tile)} Total
                  </Box>
                </Stack>

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: `repeat(${tile.items.length}, 1fr)`,
                    gap: "4px",
                    alignItems: "stretch",
                  }}
                >
                  {tile.items.map((item) => (
                    <Box
                      key={`${tile.key}-${item.label}`}
                      sx={{
                        background: "#ffffff",
                        borderRadius: "8px",
                        px: 0.45,
                        py: 0.4,
                        textAlign: "center",
                        border: `1px solid ${tile.accentColor}33`,
                        minHeight: 50,
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "center",
                      }}
                    >
                      <Typography
                        sx={{
                          fontSize: 19.2,
                          fontWeight: 900,
                          color: tile.accentColor,
                          lineHeight: 1,
                        }}
                      >
                        {item.value ?? 0}
                      </Typography>
                      <Typography
                        sx={{
                          mt: 0.15,
                          fontSize: 7.8,
                          fontWeight: 700,
                          color: tile.accentColor,
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                          lineHeight: 1.2,
                          minHeight: 18,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        {item.label}
                      </Typography>
                    </Box>
                  ))}
                </Box>

                <Typography
                  sx={{
                    fontSize: 10.8,
                    color: "#94a3b8",
                    textAlign: "center",
                    minHeight: 10,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {tile.note || "Operational summary"}
                </Typography>

                <Box sx={{ height: 4, bgcolor: "#e2e8f0", borderRadius: "2px", overflow: "hidden", mt: -0.25 }}>
                  <Box
                    sx={{
                      height: 4,
                      width: "100%",
                      bgcolor: tile.accentColor,
                      opacity: 0.2,
                      borderRadius: "2px",
                    }}
                  />
                </Box>
              </Stack>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
