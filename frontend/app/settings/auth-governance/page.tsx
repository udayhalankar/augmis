"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  FormControlLabel,
  Grid,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import { useAuth } from "@/context/AuthContext";
import {
  getAuthGovernance,
  updateAuthGovernance,
} from "@/services/authService";

export default function AuthGovernancePage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [settings, setSettings] = useState<any>(null);

  useEffect(() => {
    async function loadGovernance() {
      setLoading(true);
      try {
        const result = await getAuthGovernance();
        setSettings(result.data || null);
      } catch (governanceError: any) {
        setError(
          governanceError?.response?.data?.detail ||
            "Unable to load auth governance settings."
        );
      } finally {
        setLoading(false);
      }
    }

    void loadGovernance();
  }, []);

  function patchSection(section: string, key: string, value: any) {
    setSettings((current: any) => ({
      ...current,
      [section]: {
        ...(current?.[section] || {}),
        [key]: value,
      },
    }));
  }

  async function handleSave() {
    setSaving(true);
    setMessage("");
    setError("");
    try {
      const result = await updateAuthGovernance(settings);
      setSettings(result.data || settings);
      setMessage("AUGMIS auth governance updated successfully.");
    } catch (saveError: any) {
      setError(
        saveError?.response?.data?.detail ||
          "Unable to update auth governance."
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <ModuleGuard moduleName="settings" permission="admin:settings">
        <Box sx={{ p: 4, display: "flex", alignItems: "center", gap: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading AUGMIS auth governance...</Typography>
        </Box>
      </ModuleGuard>
    );
  }

  return (
    <ModuleGuard moduleName="settings" permission="admin:settings">
      <OutletPage
        title="AUGMIS Auth Governance"
        actions={
          <Button variant="contained" onClick={() => void handleSave()} disabled={saving || user?.role !== "SUPER_ADMIN"}>
            {saving ? <CircularProgress size={22} /> : "Save Governance"}
          </Button>
        }
      >
        {user?.role !== "SUPER_ADMIN" ? (
          <Alert severity="warning" sx={{ mb: 3 }}>
            Only the AUGMIS master administrator can manage these settings.
          </Alert>
        ) : null}
        {message ? <Alert severity="success" sx={{ mb: 3 }}>{message}</Alert> : null}
        {error ? <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert> : null}

        {!settings ? (
          <Alert severity="warning">Governance settings are not available.</Alert>
        ) : (
          <Grid container spacing={2.5}>
            <Grid size={{ xs: 12, lg: 6 }}>
              <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
                <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                  Password Policy
                </Typography>
                <TextField
                  fullWidth
                  type="number"
                  label="Minimum Length"
                  value={settings.password_policy?.min_length ?? 10}
                  onChange={(event) =>
                    patchSection("password_policy", "min_length", Number(event.target.value))
                  }
                  sx={{ mb: 2 }}
                />
                <Stack spacing={0.5}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={Boolean(settings.password_policy?.require_uppercase)}
                        onChange={(event) =>
                          patchSection("password_policy", "require_uppercase", event.target.checked)
                        }
                      />
                    }
                    label="Require uppercase"
                  />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={Boolean(settings.password_policy?.require_lowercase)}
                        onChange={(event) =>
                          patchSection("password_policy", "require_lowercase", event.target.checked)
                        }
                      />
                    }
                    label="Require lowercase"
                  />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={Boolean(settings.password_policy?.require_number)}
                        onChange={(event) =>
                          patchSection("password_policy", "require_number", event.target.checked)
                        }
                      />
                    }
                    label="Require number"
                  />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={Boolean(settings.password_policy?.require_symbol)}
                        onChange={(event) =>
                          patchSection("password_policy", "require_symbol", event.target.checked)
                        }
                      />
                    }
                    label="Require symbol"
                  />
                </Stack>
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, lg: 6 }}>
              <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
                <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                  Registration Policy
                </Typography>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={Boolean(settings.registration_policy?.self_registration_enabled)}
                      onChange={(event) =>
                        patchSection("registration_policy", "self_registration_enabled", event.target.checked)
                      }
                    />
                  }
                  label="Enable self-registration"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={Boolean(settings.registration_policy?.domain_validation_enabled)}
                      onChange={(event) =>
                        patchSection("registration_policy", "domain_validation_enabled", event.target.checked)
                      }
                    />
                  }
                  label="Enable domain validation"
                />
                <TextField
                  fullWidth
                  multiline
                  minRows={4}
                  label="Allowed Domains"
                  value={(settings.registration_policy?.allowed_domains || []).join("\n")}
                  onChange={(event) =>
                    patchSection(
                      "registration_policy",
                      "allowed_domains",
                      event.target.value
                        .split("\n")
                        .map((item) => item.trim())
                        .filter(Boolean)
                    )
                  }
                  helperText="One domain per line. Leave blank to allow any domain when validation is disabled."
                  sx={{ mt: 2 }}
                />
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, lg: 6 }}>
              <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
                <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                  Brute-force Protection
                </Typography>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Max Failed Attempts"
                      value={settings.security_policy?.max_failed_attempts ?? 5}
                      onChange={(event) =>
                        patchSection("security_policy", "max_failed_attempts", Number(event.target.value))
                      }
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Lockout Minutes"
                      value={settings.security_policy?.lockout_minutes ?? 15}
                      onChange={(event) =>
                        patchSection("security_policy", "lockout_minutes", Number(event.target.value))
                      }
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Login Rate Window Minutes"
                      value={settings.security_policy?.login_rate_limit_window_minutes ?? 15}
                      onChange={(event) =>
                        patchSection("security_policy", "login_rate_limit_window_minutes", Number(event.target.value))
                      }
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Login Attempts Per Window"
                      value={settings.security_policy?.login_rate_limit_attempts ?? 10}
                      onChange={(event) =>
                        patchSection("security_policy", "login_rate_limit_attempts", Number(event.target.value))
                      }
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      fullWidth
                      type="number"
                      label="OTP Cooldown Seconds"
                      value={settings.security_policy?.otp_resend_cooldown_seconds ?? 60}
                      onChange={(event) =>
                        patchSection("security_policy", "otp_resend_cooldown_seconds", Number(event.target.value))
                      }
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      fullWidth
                      type="number"
                      label="OTP Requests Per Hour"
                      value={settings.security_policy?.otp_request_limit_per_hour ?? 5}
                      onChange={(event) =>
                        patchSection("security_policy", "otp_request_limit_per_hour", Number(event.target.value))
                      }
                    />
                  </Grid>
                </Grid>
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, lg: 6 }}>
              <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
                <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                  Feature Rollout Flags
                </Typography>
                <Stack spacing={0.5}>
                  {[
                    ["google_login_enabled", "Enable Google login rollout"],
                    ["mfa_enabled", "Enable MFA rollout"],
                    ["reset_link_enabled", "Enable reset-link flow"],
                    ["invite_onboarding_enabled", "Enable invite onboarding"],
                    ["self_registration_enabled", "Enable self-registration feature"],
                  ].map(([key, label]) => (
                    <FormControlLabel
                      key={key}
                      control={
                        <Checkbox
                          checked={Boolean(settings.feature_flags?.[key])}
                          onChange={(event) =>
                            patchSection("feature_flags", key, event.target.checked)
                          }
                        />
                      }
                      label={label}
                    />
                  ))}
                </Stack>

                <Alert severity="info" sx={{ mt: 2 }}>
                  Provider readiness remains environment-backed. Feature flags control rollout visibility, while actual Google/MFA providers still depend on secure deployment configuration.
                </Alert>

                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Email provider: {settings.provider_config?.email_provider || "demo"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    SMTP host configured: {settings.provider_config?.smtp_host_configured ? "Yes" : "No"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Google env enabled: {settings.provider_config?.google_login_env_enabled ? "Yes" : "No"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    MFA env enabled: {settings.provider_config?.mfa_env_enabled ? "Yes" : "No"}
                  </Typography>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        )}
      </OutletPage>
    </ModuleGuard>
  );
}

