"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Paper,
  Stack,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import CheckCircleOutlineOutlinedIcon from "@mui/icons-material/CheckCircleOutlineOutlined";
import ErrorOutlineOutlinedIcon from "@mui/icons-material/ErrorOutlineOutlined";
import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined";
import MonitorHeartOutlinedIcon from "@mui/icons-material/MonitorHeartOutlined";
import TextSnippetOutlinedIcon from "@mui/icons-material/TextSnippetOutlined";
import DnsOutlinedIcon from "@mui/icons-material/DnsOutlined";
import HttpsOutlinedIcon from "@mui/icons-material/HttpsOutlined";
import PsychologyAltOutlinedIcon from "@mui/icons-material/PsychologyAltOutlined";
import SettingsSuggestOutlinedIcon from "@mui/icons-material/SettingsSuggestOutlined";

import AccessDenied from "@/components/auth/AccessDenied";
import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import { useAuth } from "@/context/AuthContext";
import {
  getPlatformHealth,
  testDatabaseConfig,
  testOpenAIConfig,
  type PlatformHealthResponse,
} from "@/services/platformService";

function HealthMetricCard({
  title,
  value,
  subtitle,
  icon,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
}) {
  return (
    <Card sx={{ border: "1px solid", borderColor: "divider", height: "100%" }}>
      <CardContent>
        <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "flex-start", gap: 2 }}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              {title}
            </Typography>
            <Typography variant="h5" sx={{ fontWeight: 800, mt: 1 }}>
              {value}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
              {subtitle}
            </Typography>
          </Box>
          <Box sx={{ color: "primary.main", "& svg": { fontSize: 28 } }}>{icon}</Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

function StatusRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <Stack
      direction={{ xs: "column", md: "row" }}
      spacing={1.25}
      sx={{ justifyContent: "space-between", py: 1.1, borderBottom: "1px solid", borderColor: "divider" }}
    >
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 600, textAlign: { xs: "left", md: "right" } }}>
        {value}
      </Typography>
    </Stack>
  );
}

export default function AugmisHealthPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState("ocr");
  const [health, setHealth] = useState<PlatformHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [openAiTestLoading, setOpenAiTestLoading] = useState(false);
  const [databaseTestLoading, setDatabaseTestLoading] = useState(false);
  const [openAiTestMessage, setOpenAiTestMessage] = useState("");
  const [databaseTestMessage, setDatabaseTestMessage] = useState("");
  const [openAiTestError, setOpenAiTestError] = useState("");
  const [databaseTestError, setDatabaseTestError] = useState("");

  async function loadHealth() {
    setLoading(true);
    setError("");
    try {
      const data = await getPlatformHealth();
      setHealth(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to load AUGMIS health.");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadHealth();
  }, []);

  async function handleTestOpenAI() {
    setOpenAiTestLoading(true);
    setOpenAiTestError("");
    setOpenAiTestMessage("");
    try {
      const result = await testOpenAIConfig();
      setOpenAiTestMessage(result.data.message);
      await loadHealth();
    } catch (err: any) {
      setOpenAiTestError(err?.response?.data?.detail || "OpenAI test failed.");
    } finally {
      setOpenAiTestLoading(false);
    }
  }

  async function handleTestDatabase() {
    setDatabaseTestLoading(true);
    setDatabaseTestError("");
    setDatabaseTestMessage("");
    try {
      const result = await testDatabaseConfig();
      setDatabaseTestMessage(result.data.message);
      await loadHealth();
    } catch (err: any) {
      setDatabaseTestError(err?.response?.data?.detail || "Database test failed.");
    } finally {
      setDatabaseTestLoading(false);
    }
  }

  return (
    <ModuleGuard moduleName="settings" permission="admin:settings">
      {user?.role !== "SUPER_ADMIN" ? (
        <AccessDenied />
      ) : (
        <OutletPage
          title="AUGMIS Health"
          description="Platform-level operational diagnostics for OCR readiness, datasource posture, and backend configuration health."
          actions={
            <Stack direction="row" spacing={1.25}>
              <Button component={Link} href="/settings/augmis-admin/platform-config" variant="outlined">
                Open Platform Config
              </Button>
              <Button variant="contained" startIcon={<RefreshOutlinedIcon />} onClick={loadHealth}>
                Refresh Health
              </Button>
            </Stack>
          }
        >
          {error ? <Alert severity="error" sx={{ mb: 2.5 }}>{error}</Alert> : null}

          <Grid container spacing={2.5} sx={{ mb: 2.5 }}>
            <Grid size={{ xs: 12, md: 4 }}>
              <HealthMetricCard
                title="Backend Health"
                value={health?.ok ? "Healthy" : loading ? "Loading..." : "Unavailable"}
                subtitle={health?.service || "Platform API status"}
                icon={<MonitorHeartOutlinedIcon />}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <HealthMetricCard
                title="OCR Status"
                value={
                  health?.ocr?.available
                    ? "Available"
                    : loading
                    ? "Loading..."
                    : "Unavailable"
                }
                subtitle={health?.ocr?.tesseract_cmd || "Tesseract command resolution"}
                icon={health?.ocr?.available ? <CheckCircleOutlineOutlinedIcon /> : <ErrorOutlineOutlinedIcon />}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <HealthMetricCard
                title="Datasource"
                value={health?.datasource?.exists ? "Available" : loading ? "Loading..." : "Optional"}
                subtitle={health?.datasource?.configured_path || "Deprecated legacy mount hint"}
                icon={<DnsOutlinedIcon />}
              />
            </Grid>
          </Grid>

          <Paper
            elevation={0}
            sx={{
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              overflow: "hidden",
            }}
          >
            <Tabs
              value={tab}
              onChange={(_, nextValue) => setTab(nextValue)}
              sx={{ px: 2, pt: 1.5, borderBottom: "1px solid", borderColor: "divider" }}
            >
              <Tab value="ocr" label="OCR Status" />
              <Tab value="openai" label="OpenAI Status" />
              <Tab value="database" label="Database Status" />
              <Tab value="security" label="Security / Auth" />
              <Tab value="diagnostics" label="Platform Diagnostics" />
            </Tabs>

            <Box sx={{ p: 2.5 }}>
              {tab === "ocr" ? (
                <Stack spacing={2}>
                  <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
                    <Chip
                      color={health?.ocr?.available ? "success" : "warning"}
                      label={`OCR: ${health?.ocr?.status || (loading ? "loading" : "unknown")}`}
                    />
                    <Chip
                      variant="outlined"
                      label={`pytesseract: ${health?.ocr?.pytesseract_installed ? "installed" : "missing"}`}
                    />
                    <Chip
                      variant="outlined"
                      label={`pypdfium2: ${health?.ocr?.pypdfium2_installed ? "installed" : "missing"}`}
                    />
                  </Stack>

                  {health?.ocr?.available === false ? (
                    <Alert severity="warning">
                      OCR is unavailable. Scanned PDFs may index with weak or missing text until Tesseract is configured and affected repositories are reindexed.
                    </Alert>
                  ) : null}

                  <Paper
                    elevation={0}
                    sx={{
                      p: 2.25,
                      borderRadius: 2.5,
                      border: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <Stack spacing={0}>
                      <StatusRow label="Availability" value={String(health?.ocr?.available ?? false)} />
                      <StatusRow label="Status" value={health?.ocr?.status || "-"} />
                      <StatusRow label="Error" value={health?.ocr?.error || "-"} />
                      <StatusRow label="Resolved Tesseract Command" value={health?.ocr?.tesseract_cmd || "-"} />
                      <StatusRow
                        label="Configured Tesseract Command"
                        value={health?.ocr?.configured_tesseract_cmd || "-"}
                      />
                      <StatusRow
                        label="OpenAI Model"
                        value={health?.model || "-"}
                      />
                      <StatusRow
                        label="Embedding Model"
                        value={health?.embedding_model || "-"}
                      />
                    </Stack>
                  </Paper>

                  <Paper
                    elevation={0}
                    sx={{
                      p: 2.25,
                      borderRadius: 2.5,
                      border: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <Stack spacing={1.1}>
                      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                        <TextSnippetOutlinedIcon color="primary" />
                        <Typography variant="h6" sx={{ fontWeight: 800 }}>
                          Operational Guidance
                        </Typography>
                      </Stack>
                      <Typography variant="body2" color="text.secondary">
                        When OCR is unavailable, scanned or image-heavy PDFs may be indexed with `low_text` or `empty_text`,
                        which weakens Copilot retrieval and enterprise search quality.
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Once OCR becomes available, run repository reindex on affected repositories so searchable text and
                        citations are rebuilt using OCR output.
                      </Typography>
                    </Stack>
                  </Paper>
                </Stack>
              ) : null}

              {tab === "openai" ? (
                <Stack spacing={2}>
                  <Stack direction="row" spacing={1.25}>
                    <Button
                      variant="contained"
                      startIcon={<RefreshOutlinedIcon />}
                      onClick={handleTestOpenAI}
                      disabled={openAiTestLoading}
                    >
                      Test OpenAI
                    </Button>
                  </Stack>

                  {openAiTestMessage ? <Alert severity="success">{openAiTestMessage}</Alert> : null}
                  {openAiTestError ? <Alert severity="error">{openAiTestError}</Alert> : null}

                  <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
                    <Chip
                      color={health?.openai?.available ? "success" : "warning"}
                      label={`OpenAI: ${health?.openai?.status || (loading ? "loading" : "unknown")}`}
                    />
                    <Chip variant="outlined" label={`SDK: ${health?.openai?.sdk_version || "-"}`} />
                    <Chip
                      variant="outlined"
                      label={`API Key: ${health?.openai?.api_key_configured ? "configured" : "missing"}`}
                    />
                  </Stack>

                  {health?.openai?.error ? <Alert severity="warning">{health.openai.error}</Alert> : null}

                  <Paper elevation={0} sx={{ p: 2.25, borderRadius: 2.5, border: "1px solid", borderColor: "divider" }}>
                    <Stack spacing={0}>
                      <StatusRow label="Availability" value={String(health?.openai?.available ?? false)} />
                      <StatusRow label="Status" value={health?.openai?.status || "-"} />
                      <StatusRow label="OpenAI Model" value={health?.openai?.model || "-"} />
                      <StatusRow label="Embedding Model" value={health?.openai?.embedding_model || "-"} />
                      <StatusRow label="SDK Version" value={health?.openai?.sdk_version || "-"} />
                    </Stack>
                  </Paper>

                  <Alert severity="info">
                    Changing OpenAI API key, chat model, or embedding model is tracked in Platform Config. Some services initialize these at startup, so updates should be treated as restart-sensitive.
                  </Alert>
                </Stack>
              ) : null}

              {tab === "database" ? (
                <Stack spacing={2}>
                  <Stack direction="row" spacing={1.25}>
                    <Button
                      variant="contained"
                      startIcon={<RefreshOutlinedIcon />}
                      onClick={handleTestDatabase}
                      disabled={databaseTestLoading}
                    >
                      Test Database
                    </Button>
                  </Stack>

                  {databaseTestMessage ? <Alert severity="success">{databaseTestMessage}</Alert> : null}
                  {databaseTestError ? <Alert severity="error">{databaseTestError}</Alert> : null}

                  <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
                    <Chip
                      color={health?.database?.available ? "success" : "error"}
                      label={`Database: ${health?.database?.status || (loading ? "loading" : "unknown")}`}
                    />
                    <Chip
                      variant="outlined"
                      label={`pgvector: ${health?.database?.pgvector_enabled ? "enabled" : "disabled"}`}
                    />
                    <Chip variant="outlined" label={`Driver: ${health?.database?.driver || "-"}`} />
                  </Stack>

                  {health?.database?.error ? <Alert severity="error">{health.database.error}</Alert> : null}

                  <Paper elevation={0} sx={{ p: 2.25, borderRadius: 2.5, border: "1px solid", borderColor: "divider" }}>
                    <Stack spacing={0}>
                      <StatusRow label="Availability" value={String(health?.database?.available ?? false)} />
                      <StatusRow label="Status" value={health?.database?.status || "-"} />
                      <StatusRow label="Engine" value={health?.database?.engine || "-"} />
                      <StatusRow label="Driver" value={health?.database?.driver || "-"} />
                      <StatusRow label="Host" value={health?.database?.host || "-"} />
                      <StatusRow label="Database Name" value={health?.database?.database || "-"} />
                      <StatusRow label="pgvector Enabled" value={String(health?.database?.pgvector_enabled ?? false)} />
                    </Stack>
                  </Paper>
                </Stack>
              ) : null}

              {tab === "security" ? (
                <Stack spacing={2}>
                  <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
                    <Chip variant="outlined" label={`Email Provider: ${health?.security?.email_provider || "-"}`} />
                    <Chip
                      color={health?.security?.smtp_host_configured ? "success" : "default"}
                      label={`SMTP: ${health?.security?.smtp_host_configured ? "configured" : "not configured"}`}
                    />
                    <Chip
                      color={health?.security?.mfa_enabled ? "success" : "default"}
                      label={`MFA: ${health?.security?.mfa_enabled ? "enabled" : "disabled"}`}
                    />
                    <Chip
                      color={health?.security?.google_login_enabled ? "success" : "default"}
                      label={`Google Login: ${health?.security?.google_login_enabled ? "enabled" : "disabled"}`}
                    />
                  </Stack>

                  <Paper elevation={0} sx={{ p: 2.25, borderRadius: 2.5, border: "1px solid", borderColor: "divider" }}>
                    <Stack spacing={0}>
                      <StatusRow label="Email Provider" value={health?.security?.email_provider || "-"} />
                      <StatusRow label="SMTP Host Configured" value={String(health?.security?.smtp_host_configured ?? false)} />
                      <StatusRow label="SMTP From Email" value={health?.security?.smtp_from_email || "-"} />
                      <StatusRow label="Google Login Enabled" value={String(health?.security?.google_login_enabled ?? false)} />
                      <StatusRow label="MFA Enabled" value={String(health?.security?.mfa_enabled ?? false)} />
                      <StatusRow label="Self Registration Enabled" value={String(health?.security?.self_registration_enabled ?? false)} />
                      <StatusRow label="Invite Onboarding Enabled" value={String(health?.security?.invite_onboarding_enabled ?? false)} />
                      <StatusRow label="Reset Link Enabled" value={String(health?.security?.reset_link_enabled ?? false)} />
                    </Stack>
                  </Paper>
                </Stack>
              ) : null}

              {tab === "diagnostics" ? (
                <Stack spacing={2}>
                  <Grid container spacing={2}>
                    <Grid size={{ xs: 12, md: 4 }}>
                      <HealthMetricCard
                        title="Runtime"
                        value={health?.platform_diagnostics?.runtime_platform || "Unknown"}
                        subtitle={`Python ${health?.platform_diagnostics?.python_version || "-"}`}
                        icon={<MonitorHeartOutlinedIcon />}
                      />
                    </Grid>
                    <Grid size={{ xs: 12, md: 4 }}>
                      <HealthMetricCard
                        title="Vector Backend"
                        value={health?.platform_diagnostics?.vector_backend || "-"}
                        subtitle="Configured vector engine"
                        icon={<PsychologyAltOutlinedIcon />}
                      />
                    </Grid>
                    <Grid size={{ xs: 12, md: 4 }}>
                      <HealthMetricCard
                        title="Restart Required"
                        value={health?.platform_diagnostics?.config?.restart_required ? "Yes" : "No"}
                        subtitle="Pending runtime config changes"
                        icon={<SettingsSuggestOutlinedIcon />}
                      />
                    </Grid>
                  </Grid>

                  {health?.datasource?.deprecated ? (
                    <Alert severity="info">
                      `DATASOURCE_PATH` is deprecated for production. Repository `source_path` and connector configuration are the real runtime source of truth.
                    </Alert>
                  ) : null}

                  <Paper elevation={0} sx={{ p: 2.25, borderRadius: 2.5, border: "1px solid", borderColor: "divider" }}>
                    <Stack spacing={0}>
                      <StatusRow label="Scheduler Mode" value={health?.platform_diagnostics?.scheduler?.mode || "-"} />
                      <StatusRow label="Scheduler Enabled" value={String(health?.platform_diagnostics?.scheduler?.enabled ?? false)} />
                      <StatusRow
                        label="Scheduler Interval Minutes"
                        value={String(health?.platform_diagnostics?.scheduler?.interval_minutes ?? "-")}
                      />
                      <StatusRow label="Scheduler Timezone" value={health?.platform_diagnostics?.scheduler?.timezone || "-"} />
                    </Stack>
                  </Paper>

                  <Paper elevation={0} sx={{ p: 2.25, borderRadius: 2.5, border: "1px solid", borderColor: "divider" }}>
                    <Stack spacing={1.1}>
                      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                        <HttpsOutlinedIcon color="primary" />
                        <Typography variant="h6" sx={{ fontWeight: 800 }}>
                          Important Library Versions
                        </Typography>
                      </Stack>
                      {Object.entries(health?.platform_diagnostics?.libraries || {}).map(([name, version]) => (
                        <StatusRow key={name} label={name} value={version || "-"} />
                      ))}
                    </Stack>
                  </Paper>
                </Stack>
              ) : null}
            </Box>
          </Paper>
        </OutletPage>
      )}
    </ModuleGuard>
  );
}
