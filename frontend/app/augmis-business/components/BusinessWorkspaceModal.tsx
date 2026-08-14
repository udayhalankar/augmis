"use client";

import type { ReactNode } from "react";

import CloseIcon from "@mui/icons-material/Close";
import {
  Box,
  Dialog,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";

type BusinessWorkspaceModalProps = {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  subtitle?: ReactNode;
  chips?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  maxWidth?: number;
  contentSx?: Record<string, unknown>;
};

export default function BusinessWorkspaceModal({
  open,
  onClose,
  title,
  subtitle,
  chips,
  actions,
  children,
  maxWidth = 1180,
  contentSx,
}: BusinessWorkspaceModalProps) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth={false}
      scroll="paper"
      slotProps={{
        paper: {
          sx: {
            width: "min(96vw, 100%)",
            maxWidth,
            borderRadius: "14px",
            overflow: "hidden",
            bgcolor: "#F8FAFC",
            boxShadow: "0 28px 80px rgba(15, 23, 42, 0.28)",
          },
        },
        backdrop: {
          sx: {
            backgroundColor: "rgba(15, 23, 42, 0.46)",
            backdropFilter: "blur(3px)",
          },
        },
      }}
    >
      <Box
        sx={{
          px: 2.6,
          py: 2.1,
          color: "#F8FAFC",
          background:
            "linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 64, 175, 0.94) 58%, rgba(153, 27, 27, 0.88) 100%)",
        }}
      >
        <Stack spacing={1.25}>
          <Stack direction="row" spacing={1.4} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
            <Box sx={{ minWidth: 0 }}>
              <Typography sx={{ fontSize: 28, lineHeight: 1.15, fontWeight: 800, color: "inherit" }}>
                {title}
              </Typography>
              {subtitle ? (
                <Typography sx={{ mt: 0.7, fontSize: 13, color: "rgba(226, 232, 240, 0.88)" }}>
                  {subtitle}
                </Typography>
              ) : null}
            </Box>
            <IconButton
              onClick={onClose}
              sx={{
                color: "#F8FAFC",
                border: "1px solid rgba(255,255,255,0.18)",
                bgcolor: "rgba(255,255,255,0.08)",
                "&:hover": {
                  bgcolor: "rgba(255,255,255,0.16)",
                },
              }}
            >
              <CloseIcon />
            </IconButton>
          </Stack>
          {chips ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.8, flexWrap: "wrap" }}>{chips}</Box>
          ) : null}
          {actions ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>{actions}</Box>
          ) : null}
        </Stack>
      </Box>
      <Box
        sx={{
          px: 2.6,
          py: 2.4,
          ...contentSx,
        }}
      >
        {children}
      </Box>
    </Dialog>
  );
}
