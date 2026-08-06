"use client";

import { ReactNode } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Chip,
  Divider,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

type Capability = {
  available: boolean;
  label: string;
  reason?: string;
  delivery_mode?: string;
};

// Shared auth-shell sizing tokens so we can tune or roll back the compact layout centrally.
const AUTH_SHELL_DESKTOP_MAX_WIDTH = 820;
const AUTH_SHELL_LEFT_COLUMN = "minmax(330px, 390px)";
const AUTH_SHELL_RIGHT_COLUMN = "minmax(280px, 320px)";
const AUTH_SHELL_DESKTOP_GAP = 14;
const AUTH_SHELL_PANEL_PADDING = 2;
const AUTH_SHELL_LOGO_WIDTH = 96;

export function AuthShell({
  eyebrow = "Secure Workspace Access",
  title,
  description,
  capabilities,
  footer,
  children,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  capabilities?: {
    otp_reset?: Capability;
    google_login?: Capability;
    mfa?: Capability;
  } | null;
  footer?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "#eef3fb",
        px: { xs: 2, md: 4 },
        py: { xs: 3, md: 4 },
      }}
    >
      <Box
        sx={{
          width: "100%",
          maxWidth: { xs: 560, lg: AUTH_SHELL_DESKTOP_MAX_WIDTH },
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            lg: `${AUTH_SHELL_LEFT_COLUMN} ${AUTH_SHELL_RIGHT_COLUMN}`,
          },
          justifyContent: "center",
          alignItems: "stretch",
          gap: { xs: 2, lg: `${AUTH_SHELL_DESKTOP_GAP}px` },
          mx: "auto",
        }}
      >
        <Paper
          elevation={0}
          sx={{
            width: "100%",
            p: { xs: 1.8, md: AUTH_SHELL_PANEL_PADDING },
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            boxShadow: "0 12px 32px rgba(15, 23, 42, 0.08)",
            minHeight: { xs: "auto", lg: 0 },
            height: "100%",
            display: "flex",
          }}
        >
          <Stack spacing={1} sx={{ width: "100%" }}>
            <Box
              component="img"
              src="/augmis_logo_transparent_bg.png"
              alt="Augmis"
              sx={{ width: AUTH_SHELL_LOGO_WIDTH, height: "auto", objectFit: "contain" }}
            />

            <Box>
              <Typography
                sx={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: 0.9,
                  textTransform: "uppercase",
                  color: "primary.main",
                  mb: 0.5,
                }}
              >
                {eyebrow}
              </Typography>
              <Typography sx={{ fontSize: { xs: 40, lg: 34 }, fontWeight: 800, lineHeight: 1, mb: 0.5 }}>
                {title}
              </Typography>
              <Typography sx={{ fontSize: { xs: 16, lg: 13.5 } }} color="text.secondary">{description}</Typography>
            </Box>

            {children}

            {footer ? (
              <>
                <Divider sx={{ my: 0.25 }} />
                <Box>{footer}</Box>
              </>
            ) : null}
          </Stack>
        </Paper>

        <Paper
          elevation={0}
          sx={{
            width: "100%",
            display: { xs: "none", lg: "flex" },
            p: AUTH_SHELL_PANEL_PADDING,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            boxShadow: "0 12px 32px rgba(15, 23, 42, 0.08)",
            bgcolor: "#f8fbff",
            minHeight: 0,
            height: "100%",
          }}
        >
          <Stack spacing={1} sx={{ width: "100%" }}>
            <Box>
              <Typography sx={{ fontSize: 27, fontWeight: 800, lineHeight: 1.1, mb: 0.5 }}>
                Executive Cockpit Identity
              </Typography>
              <Typography sx={{ fontSize: 13.5 }} color="text.secondary">
                Consistent enterprise access for Augmis workspaces, repository-backed intelligence, and governed AI workflows.
              </Typography>
            </Box>

            <Stack direction="row" spacing={0.75} useFlexGap sx={{ flexWrap: "wrap" }}>
              <Chip label="Workspace Registration" color="primary" variant="outlined" />
              <Chip label="OTP Password Reset" color="success" variant="outlined" />
              <Chip label="Enterprise Session Control" color="default" variant="outlined" />
            </Stack>

            {capabilities?.otp_reset?.available ? (
              <Alert severity="info">
                OTP reset is available now.
                {capabilities.otp_reset.delivery_mode === "onscreen_demo"
                  ? " This deployment currently shows the OTP on screen for demo/testing."
                  : ""}
              </Alert>
            ) : null}

            <Stack spacing={1.25}>
              <Typography sx={{ fontWeight: 700 }}>Security Features</Typography>
              <FeatureStatus
                title="Google Sign-In"
                available={Boolean(capabilities?.google_login?.available)}
                reason={capabilities?.google_login?.reason}
              />
              <FeatureStatus
                title="Multi-factor Authentication"
                available={Boolean(capabilities?.mfa?.available)}
                reason={capabilities?.mfa?.reason}
              />
            </Stack>

            <Divider sx={{ my: 0.25 }} />

            <Typography variant="body2" color="text.secondary">
              Need help? Start with <Link href="/login">login</Link>, create a new workspace from <Link href="/register">registration</Link>, or recover access from <Link href="/forgot-password">forgot password</Link>.
            </Typography>
          </Stack>
        </Paper>
      </Box>
    </Box>
  );
}

function FeatureStatus({
  title,
  available,
  reason,
}: {
  title: string;
  available: boolean;
  reason?: string;
}) {
  return (
    <Box
      sx={{
        p: 1.5,
        borderRadius: 2,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
      }}
    >
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 0.5 }}>
        <Typography sx={{ fontWeight: 700 }}>{title}</Typography>
        <Chip
          size="small"
          label={available ? "Available" : "Setup Required"}
          color={available ? "success" : "default"}
        />
      </Stack>
      <Typography variant="body2" color="text.secondary">
        {available ? "This security option is enabled for this deployment." : reason || "This feature is not enabled in the current deployment."}
      </Typography>
    </Box>
  );
}
