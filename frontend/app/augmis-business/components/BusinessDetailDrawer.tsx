"use client";

import type { ReactNode } from "react";

import CloseIcon from "@mui/icons-material/Close";
import {
  Alert,
  Box,
  CircularProgress,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";

import BusinessTabs, { type BusinessTabItem } from "./BusinessTabs";

export default function BusinessDetailDrawer({
  open,
  onClose,
  title,
  subtitle,
  chips,
  actions,
  tabs,
  activeTab,
  onTabChange,
  loading = false,
  error,
  children,
  width = 780,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  chips?: ReactNode;
  actions?: ReactNode;
  tabs?: BusinessTabItem[];
  activeTab?: string;
  onTabChange?: (value: string) => void;
  loading?: boolean;
  error?: string | null;
  children: ReactNode;
  width?: number;
}) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose}>
      <Box
        sx={{
          width: { xs: "100vw", sm: width },
          maxWidth: "100vw",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          bgcolor: "#F8FAFC",
        }}
      >
        <Box
          sx={{
            px: 2.5,
            py: 2,
            background: "linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)",
            borderBottom: "1px solid #D9E2EC",
          }}
        >
          <Stack spacing={1.2}>
            <Stack direction="row" spacing={1.2} sx={{ alignItems: "flex-start", justifyContent: "space-between" }}>
              <Box sx={{ minWidth: 0 }}>
                <Typography sx={{ fontSize: 24, fontWeight: 800, color: "#0F172A", lineHeight: 1.2 }}>
                  {title}
                </Typography>
                {subtitle ? (
                  <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 14 }}>
                    {subtitle}
                  </Typography>
                ) : null}
              </Box>
              <IconButton onClick={onClose}>
                <CloseIcon />
              </IconButton>
            </Stack>
            {chips ? (
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flexWrap: "wrap" }}>{chips}</Box>
            ) : null}
            {actions ? (
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>{actions}</Box>
            ) : null}
            {tabs && activeTab && onTabChange ? (
              <>
                <Divider />
                <BusinessTabs compact value={activeTab} onChange={onTabChange} items={tabs} />
              </>
            ) : null}
          </Stack>
        </Box>
        <Box sx={{ flex: 1, overflowY: "auto", px: 2.5, py: 2.25 }}>
          {loading ? (
            <Stack sx={{ py: 10, alignItems: "center" }} spacing={1.2}>
              <CircularProgress size={28} />
              <Typography sx={{ color: "#475569" }}>Loading details...</Typography>
            </Stack>
          ) : error ? (
            <Alert severity="error">{error}</Alert>
          ) : (
            <Stack spacing={2}>{children}</Stack>
          )}
        </Box>
      </Box>
    </Drawer>
  );
}
