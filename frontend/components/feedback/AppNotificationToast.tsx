"use client";

import type { SyntheticEvent } from "react";

import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import { Alert, Snackbar, type AlertColor } from "@mui/material";

type AppNotificationToastProps = {
  open: boolean;
  message: string | null;
  severity?: AlertColor;
  autoHideDuration?: number;
  onClose: () => void;
};

const SEVERITY_ICON = {
  success: <CheckCircleRoundedIcon fontSize="inherit" />,
  error: <ErrorOutlineRoundedIcon fontSize="inherit" />,
  warning: <WarningAmberRoundedIcon fontSize="inherit" />,
  info: <InfoOutlinedIcon fontSize="inherit" />,
} as const;

export function AppNotificationToast({
  open,
  message,
  severity = "success",
  autoHideDuration = 4200,
  onClose,
}: AppNotificationToastProps) {
  const handleClose = (_event?: Event | SyntheticEvent, reason?: string) => {
    if (reason === "clickaway") {
      return;
    }
    onClose();
  };

  return (
    <Snackbar
      open={open && Boolean(message)}
      autoHideDuration={autoHideDuration}
      onClose={handleClose}
      anchorOrigin={{ vertical: "top", horizontal: "right" }}
      sx={{
        top: { xs: 78, sm: 92 },
        right: { xs: 16, sm: 24 },
        left: { xs: 16, sm: "auto" },
      }}
    >
      <Alert
        onClose={handleClose}
        severity={severity}
        icon={SEVERITY_ICON[severity]}
        variant="filled"
        sx={{
          minWidth: { xs: "100%", sm: 360 },
          maxWidth: 520,
          borderRadius: "14px",
          px: 1.25,
          py: 0.25,
          alignItems: "center",
          boxShadow: "0 18px 40px rgba(15, 23, 42, 0.18)",
          "& .MuiAlert-icon": {
            fontSize: 22,
            alignItems: "center",
            mr: 1,
          },
          "& .MuiAlert-message": {
            py: 0.95,
            fontSize: 14,
            lineHeight: 1.45,
            fontWeight: 500,
          },
          "& .MuiAlert-action": {
            pt: 0.5,
          },
        }}
      >
        {message}
      </Alert>
    </Snackbar>
  );
}
