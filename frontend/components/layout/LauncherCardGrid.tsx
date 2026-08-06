"use client";

import { type ReactNode, useMemo, useState } from "react";
import Link from "next/link";
import {
  Box,
  Button,
  Chip,
  Grid,
  Pagination,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ArrowForwardOutlinedIcon from "@mui/icons-material/ArrowForwardOutlined";

export type LauncherCardItem = {
  title: string;
  description: string;
  href?: string;
  status?: "Live" | "Planned";
  icon: ReactNode;
  items: string[];
};

function LauncherCard({ card }: { card: LauncherCardItem }) {
  const live = (card.status || "Live") === "Live";

  return (
    <Paper
      elevation={0}
      sx={{
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
        overflow: "hidden",
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box
        sx={{
          px: 2.25,
          py: 1.25,
          bgcolor: "#204b78",
          color: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 1,
        }}
      >
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", minWidth: 0 }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              color: "#fff",
              "& svg": { fontSize: 18, color: "#fff" },
            }}
          >
            {card.icon}
          </Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.2, color: "#fff" }}>
            {card.title}
          </Typography>
        </Stack>
        <Chip
          size="small"
          label={live ? "Live" : "Planned"}
          sx={{
            bgcolor: live ? "rgba(255,255,255,0.16)" : "rgba(255,255,255,0.10)",
            color: "#fff",
            fontWeight: 600,
          }}
        />
      </Box>

      <Box sx={{ p: 2.25, display: "flex", flexDirection: "column", flexGrow: 1 }}>
        <Typography color="text.secondary" sx={{ mb: 1.75 }}>
          {card.description}
        </Typography>

        <Stack spacing={0.85} sx={{ mb: 2.25, flexGrow: 1 }}>
          {card.items.map((item) => (
            <Typography key={item} color="text.primary">
              {item}
            </Typography>
          ))}
        </Stack>

        {card.href ? (
          <Button
            component={Link}
            href={card.href}
            variant="outlined"
            endIcon={<ArrowForwardOutlinedIcon />}
            sx={{ alignSelf: "flex-start" }}
          >
            Open Workspace
          </Button>
        ) : (
          <Button variant="outlined" disabled sx={{ alignSelf: "flex-start" }}>
            Coming Soon
          </Button>
        )}
      </Box>
    </Paper>
  );
}

export function LauncherCardGrid({
  cards,
  cardsPerPage = 6,
}: {
  cards: LauncherCardItem[];
  cardsPerPage?: number;
}) {
  const [page, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(cards.length / cardsPerPage));
  const visibleCards = useMemo(() => {
    const start = (page - 1) * cardsPerPage;
    return cards.slice(start, start + cardsPerPage);
  }, [cards, cardsPerPage, page]);

  return (
    <>
      <Grid container spacing={2.5}>
        {visibleCards.map((card) => (
          <Grid key={card.title} size={{ xs: 12, md: 6, xl: 4 }}>
            <LauncherCard card={card} />
          </Grid>
        ))}
      </Grid>

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
  );
}
