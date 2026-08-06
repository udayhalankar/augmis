"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined";

import AccessDenied from "@/components/auth/AccessDenied";
import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import { useAuth } from "@/context/AuthContext";
import {
  getPlatformConfig,
  updatePlatformConfig,
  type PlatformConfigField,
  type PlatformConfigResponse,
} from "@/services/platformService";

type FormState = {
  openai_api_key: string;
  openai_model: string;
  openai_embedding_model: string;
  database_url: string;
  ocr_tesseract_cmd: string;
};

const EMPTY_FORM: FormState = {
  openai_api_key: "",
  openai_model: "",
  openai_embedding_model: "",
  database_url: "",
  ocr_tesseract_cmd: "",
};

function fieldMap(fields: PlatformConfigField[]) {
  return Object.fromEntries(fields.map((field) => [field.key, field])) as Record<string, PlatformConfigField>;
}

export default function PlatformConfigPage() {
  const { user } = useAuth();
  const [config, setConfig] = useState<PlatformConfigResponse | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  async function loadConfig() {
    setLoading(true);
    setError("");
    setMessage("");
    setFieldErrors({});
    try {
      const result = await getPlatformConfig();
      setConfig(result.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to load platform configuration.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadConfig();
  }, []);

  const fieldsByKey = useMemo(() => fieldMap(config?.fields || []), [config]);

  async function handleSave() {
    setSaving(true);
    setError("");
    setMessage("");
    setFieldErrors({});
    try {
      const payload = {
        ...(form.openai_api_key.trim() ? { openai_api_key: form.openai_api_key.trim() } : {}),
        openai_model: form.openai_model.trim() || fieldsByKey.openai_model?.value || "",
        openai_embedding_model:
          form.openai_embedding_model.trim() || fieldsByKey.openai_embedding_model?.value || "",
        ...(form.database_url.trim() ? { database_url: form.database_url.trim() } : {}),
        ocr_tesseract_cmd:
          form.ocr_tesseract_cmd.trim() || fieldsByKey.ocr_tesseract_cmd?.value || "",
      };

      const result = await updatePlatformConfig(payload);
      setConfig(result.data);
      setForm(EMPTY_FORM);
      setMessage(
        result.data.restart_required
          ? "Platform configuration saved. Some changes require a backend restart to take effect."
          : "Platform configuration saved."
      );
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (detail && typeof detail === "object" && !Array.isArray(detail)) {
        setFieldErrors(detail);
        setError("Please fix the validation errors and try again.");
      } else {
        setError(detail || "Unable to save platform configuration.");
      }
    } finally {
      setSaving(false);
    }
  }

  function handleFieldChange(key: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  return (
    <ModuleGuard moduleName="settings" permission="admin:settings">
      {user?.role !== "SUPER_ADMIN" ? (
        <AccessDenied />
      ) : (
        <OutletPage
          title="Platform Config"
          actions={
            <Stack direction="row" spacing={1.25}>
              <Button variant="outlined" startIcon={<RefreshOutlinedIcon />} onClick={loadConfig}>
                Reload Config
              </Button>
              <Button variant="contained" startIcon={<SaveOutlinedIcon />} onClick={handleSave} disabled={saving || loading}>
                Save Config
              </Button>
            </Stack>
          }
        >
          {error ? <Alert severity="error" sx={{ mb: 2.5 }}>{error}</Alert> : null}
          {message ? <Alert severity="success" sx={{ mb: 2.5 }}>{message}</Alert> : null}
          {config?.restart_required ? (
            <Alert severity="warning" sx={{ mb: 2.5 }}>
              One or more saved settings are restart-sensitive. Restart the backend to fully apply OpenAI or database changes.
            </Alert>
          ) : null}

          <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
            <Stack spacing={2.25}>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 800 }}>
                  Runtime Configuration
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Non-secret values are shown directly. Secret values remain masked and can only be replaced by entering a new value.
                </Typography>
              </Box>

              <TextField
                label="OpenAI API Key"
                type="password"
                value={form.openai_api_key}
                onChange={(event) => handleFieldChange("openai_api_key", event.target.value)}
                placeholder={fieldsByKey.openai_api_key?.masked_value || "Enter new API key"}
                helperText={
                  fieldErrors.openai_api_key ||
                  `Current value: ${fieldsByKey.openai_api_key?.masked_value || "not configured"}`
                }
                error={Boolean(fieldErrors.openai_api_key)}
                fullWidth
              />

              <TextField
                label="OpenAI Model"
                value={form.openai_model || fieldsByKey.openai_model?.value || ""}
                onChange={(event) => handleFieldChange("openai_model", event.target.value)}
                helperText={
                  fieldErrors.openai_model ||
                  (fieldsByKey.openai_model?.pending_restart
                    ? "Restart required to fully apply this change."
                    : "Current runtime model value.")
                }
                error={Boolean(fieldErrors.openai_model)}
                fullWidth
              />

              <TextField
                label="OpenAI Embedding Model"
                value={form.openai_embedding_model || fieldsByKey.openai_embedding_model?.value || ""}
                onChange={(event) => handleFieldChange("openai_embedding_model", event.target.value)}
                helperText={
                  fieldErrors.openai_embedding_model ||
                  (fieldsByKey.openai_embedding_model?.pending_restart
                    ? "Restart required to fully apply this change."
                    : "Current embedding model value.")
                }
                error={Boolean(fieldErrors.openai_embedding_model)}
                fullWidth
              />

              <TextField
                label="Database URL"
                type="password"
                value={form.database_url}
                onChange={(event) => handleFieldChange("database_url", event.target.value)}
                placeholder={fieldsByKey.database_url?.masked_value || "Enter new database URL"}
                helperText={
                  fieldErrors.database_url ||
                  `Current value: ${fieldsByKey.database_url?.masked_value || "not configured"}`
                }
                error={Boolean(fieldErrors.database_url)}
                fullWidth
              />

              <TextField
                label="OCR Tesseract Command"
                value={form.ocr_tesseract_cmd || fieldsByKey.ocr_tesseract_cmd?.value || ""}
                onChange={(event) => handleFieldChange("ocr_tesseract_cmd", event.target.value)}
                helperText={
                  fieldErrors.ocr_tesseract_cmd ||
                  (fieldsByKey.ocr_tesseract_cmd?.applies_live
                    ? "This setting can apply live without a restart."
                    : "Restart required.")
                }
                error={Boolean(fieldErrors.ocr_tesseract_cmd)}
                fullWidth
              />
            </Stack>
          </Paper>

          <Paper elevation={0} sx={{ mt: 2.5, p: 2.5, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
            <Stack spacing={1.25}>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                DATASOURCE_PATH Advisory
              </Typography>
              <Typography variant="body2" color="text.secondary">
                `DATASOURCE_PATH` is deprecated for production. Repository `source_path` and connector configuration drive actual tenant repository behavior in live environments.
              </Typography>
              <Typography variant="body2" color="text.secondary">
                You can remove `DATASOURCE_PATH` from `.env` if you are not relying on it for local-only health signaling. It is not required for AWS production repository operation.
              </Typography>
            </Stack>
          </Paper>
        </OutletPage>
      )}
    </ModuleGuard>
  );
}

