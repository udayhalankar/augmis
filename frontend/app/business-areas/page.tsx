"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Pagination,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ArrowForwardOutlinedIcon from "@mui/icons-material/ArrowForwardOutlined";
import BusinessCenterOutlinedIcon from "@mui/icons-material/BusinessCenterOutlined";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import DatasetOutlinedIcon from "@mui/icons-material/DatasetOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import { getBusinessAreaCatalog } from "@/services/businessAreaService";

type BusinessAreaCard = {
  slug: string;
  name: string;
  display_name: string;
  description: string;
  path: string;
  repository_count: number;
  active_repository_count: number;
  tracked_files: number;
  documents_indexed: number;
  chunks_indexed: number;
  status_label: string;
  status_tone: "success" | "warning" | "error" | "info" | "default";
  needs_attention_count: number;
  has_indexed_data: boolean;
};

const CARDS_PER_PAGE = 15;

function toneColor(tone: BusinessAreaCard["status_tone"]) {
  if (tone === "success") return "#14b8a6";
  if (tone === "warning") return "#f59e0b";
  if (tone === "error") return "#ef4444";
  if (tone === "info") return "#2563eb";
  return "#64748b";
}

export default function BusinessAreasPage() {
  const [cards, setCards] = useState<BusinessAreaCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    let active = true;

    async function loadCatalog() {
      setLoading(true);
      setError("");
      try {
        const response = await getBusinessAreaCatalog();
        if (!active) return;
        setCards(response?.data || []);
      } catch (err: any) {
        if (!active) return;
        setError(err?.response?.data?.detail || "Unable to load business area intelligence.");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadCatalog();
    return () => {
      active = false;
    };
  }, []);

  const pageCount = Math.max(1, Math.ceil(cards.length / CARDS_PER_PAGE));
  const visibleCards = useMemo(() => {
    const start = (page - 1) * CARDS_PER_PAGE;
    return cards.slice(start, start + CARDS_PER_PAGE);
  }, [cards, page]);

  useEffect(() => {
    if (page > pageCount) {
      setPage(pageCount);
    }
  }, [page, pageCount]);

  return (
    <ModuleGuard moduleName="documents" permission="documents:read">
      <OutletPage title="Business Area Intelligence">
        {error ? (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        ) : null}

        {loading ? (
          <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", py: 6 }}>
            <CircularProgress size={22} />
            <Typography>Loading business area catalog...</Typography>
          </Stack>
        ) : null}

        {!loading && !cards.length ? (
          <Alert severity="info">
            No business areas are available yet. Add a repository with a work area to make it appear here immediately.
          </Alert>
        ) : null}

        {!loading && cards.length ? (
          <>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  sm: "repeat(2, minmax(0, 1fr))",
                  md: "repeat(3, minmax(0, 1fr))",
                  lg: "repeat(4, minmax(0, 1fr))",
                  xl: "repeat(5, minmax(0, 1fr))",
                },
                gap: "var(--outlet-grid-gap)",
              }}
            >
              {visibleCards.map((card) => {
                const accent = toneColor(card.status_tone);
                return (
                  <Paper
                    key={card.slug}
                    elevation={0}
                    sx={{
                      borderRadius: 3,
                      border: "1px solid",
                      borderColor: "divider",
                      minHeight: 232,
                      p: 2.25,
                      display: "flex",
                      flexDirection: "column",
                      background:
                        "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.96) 100%)",
                      boxShadow: "0 16px 28px rgba(15,23,42,0.08)",
                    }}
                  >
                    <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "flex-start", gap: 1.2 }}>
                      <Box
                        sx={{
                          width: 38,
                          height: 38,
                          borderRadius: "50%",
                          bgcolor: `${accent}16`,
                          color: accent,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                          "& svg": { fontSize: 21 },
                        }}
                      >
                        <BusinessCenterOutlinedIcon />
                      </Box>
                      <Chip
                        size="small"
                        label={card.status_label}
                        sx={{
                          bgcolor: `${accent}14`,
                          color: accent,
                          border: "1px solid",
                          borderColor: `${accent}2c`,
                          fontWeight: 500,
                        }}
                      />
                    </Stack>

                    <Stack
                      direction="row"
                      sx={{
                        mt: 1.65,
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 1,
                      }}
                    >
                      <Typography variant="h6" sx={{ fontWeight: 600, lineHeight: 1.15 }}>
                        {card.display_name}
                      </Typography>
                    </Stack>
                    <Typography color="text.secondary" sx={{ mt: 0.75, minHeight: 44 }}>
                      {card.description}
                    </Typography>

                    <Stack spacing={1.1} sx={{ mt: 1.75 }}>
                      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                        <FolderOpenOutlinedIcon sx={{ fontSize: 16, color: "#2563eb" }} />
                        <Typography variant="body2">Repositories: {card.repository_count}</Typography>
                      </Stack>
                      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                        <DescriptionOutlinedIcon sx={{ fontSize: 16, color: "#14b8a6" }} />
                        <Typography variant="body2">Files tracked: {card.tracked_files}</Typography>
                      </Stack>
                      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                        <DatasetOutlinedIcon sx={{ fontSize: 16, color: "#8b5cf6" }} />
                        <Typography variant="body2">Indexed chunks: {card.chunks_indexed}</Typography>
                      </Stack>
                    </Stack>

                    {card.needs_attention_count > 0 ? (
                      <Stack direction="row" spacing={0.8} sx={{ flexWrap: "wrap", mt: 1.5 }}>
                        <Chip
                          size="small"
                          icon={<WarningAmberOutlinedIcon />}
                          label={`${card.needs_attention_count} alert${card.needs_attention_count === 1 ? "" : "s"}`}
                          sx={{
                            bgcolor: "rgba(245,158,11,0.14)",
                            color: "#b45309",
                            border: "1px solid rgba(245,158,11,0.28)",
                          }}
                        />
                      </Stack>
                    ) : null}

                    <Button
                      component={Link}
                      href={card.path}
                      variant="outlined"
                      endIcon={<ArrowForwardOutlinedIcon />}
                      sx={{ mt: 2.25, alignSelf: "flex-start", fontWeight: 600 }}
                    >
                      Open Workspace
                    </Button>
                  </Paper>
                );
              })}
            </Box>

            <Stack direction="row" sx={{ justifyContent: "center", mt: 3 }}>
              <Pagination
                count={pageCount}
                page={page}
                onChange={(_, value) => setPage(value)}
                color="primary"
                shape="rounded"
                showFirstButton
                showLastButton
              />
            </Stack>
          </>
        ) : null}
      </OutletPage>
    </ModuleGuard>
  );
}

