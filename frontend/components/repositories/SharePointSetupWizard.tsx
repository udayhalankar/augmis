"use client";

import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { repositorySyncApi } from "@/services/repositorySyncApi";

type SharePointDrivesPayload = Parameters<typeof repositorySyncApi.discoverSharePointDrives>[0];


export default function SharePointSetupWizard({
  config,
  setConfig,
}: {
  config: Record<string, string>;
  setConfig: (value: Record<string, string>) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [siteSearch, setSiteSearch] = useState("");
  const [sites, setSites] = useState<any[]>([]);
  const [drives, setDrives] = useState<any[]>([]);
  const [folders, setFolders] = useState<any[]>([]);
  const [folderPath, setFolderPath] = useState(config.folder_path || "/");
  const [message, setMessage] = useState("");

  const update = (key: string, value: string) => {
    setConfig({ ...config, [key]: value });
  };

  const discoverSites = async () => {
    setLoading(true);
    setMessage("");

    try {
      const data = await repositorySyncApi.discoverSharePointSites(config, siteSearch);
      setSites(data);
      setMessage(`Found ${data.length} SharePoint site(s).`);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "Site discovery failed");
    } finally {
      setLoading(false);
    }
  };

  const discoverDrives = async () => {
    setLoading(true);
    setMessage("");

    try {
      const data = await repositorySyncApi.discoverSharePointDrives(
        config as SharePointDrivesPayload
      );
      setDrives(data);
      setMessage(`Found ${data.length} document library drive(s).`);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "Drive discovery failed");
    } finally {
      setLoading(false);
    }
  };

  const discoverFolders = async () => {
    setLoading(true);
    setMessage("");

    try {
      const data = await repositorySyncApi.discoverSharePointFolders(
        config,
        folderPath || "/"
      );
      const foldersOnly = data.filter((item: any) => item.is_folder);
      setFolders(foldersOnly);
      setMessage(`Found ${foldersOnly.length} folder(s).`);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "Folder discovery failed");
    } finally {
      setLoading(false);
    }
  };

  const validateConfig = async () => {
    setLoading(true);
    setMessage("");

    try {
      await repositorySyncApi.validateSharePointConfig(config);
      setMessage("SharePoint configuration is valid.");
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "Validation failed");
    } finally {
      setLoading(false);
    }
  };

  const isCertificateAuth = (config.auth_method || "client_secret") === "certificate";

  return (
    <Box sx={{ mt: 2 }}>
      <Typography fontWeight={800} sx={{ mb: 1 }}>
        SharePoint Setup Helper
      </Typography>

      <Alert severity="info" sx={{ mb: 2 }}>
        Required Azure application permissions: `Sites.Read.All` and `Files.Read.All`.
        Admin consent must be granted before validation.
      </Alert>

      <Alert severity="info" sx={{ mb: 2 }}>
        For production, prefer certificate auth plus env/secret-manager references instead of storing raw secrets in repository config.
      </Alert>

      <Alert severity="warning" sx={{ mb: 2 }}>
        Raw `client_secret`, `certificate_private_key`, and `certificate_passphrase` values are rejected on save. Use env refs or file paths instead.
      </Alert>

      <Alert severity="info" sx={{ mb: 2 }}>
        Saved sensitive fields are redacted when reloaded. Leaving a redacted value unchanged will preserve the existing secret reference.
      </Alert>

      {message && (
        <Alert severity={message.toLowerCase().includes("failed") ? "error" : "info"} sx={{ mb: 2 }}>
          {message}
        </Alert>
      )}

      <Stack spacing={2}>
        <TextField
          select
          fullWidth
          label="Auth Method"
          value={config.auth_method || "client_secret"}
          onChange={(e) => update("auth_method", e.target.value)}
        >
          <MenuItem value="client_secret">Client Secret</MenuItem>
          <MenuItem value="certificate">Certificate</MenuItem>
        </TextField>

        <TextField
          fullWidth
          label="Azure Tenant ID"
          value={config.tenant_id || ""}
          onChange={(e) => update("tenant_id", e.target.value)}
        />

        <TextField
          fullWidth
          label="Azure Client ID"
          value={config.client_id || ""}
          onChange={(e) => update("client_id", e.target.value)}
        />

        {!isCertificateAuth ? (
          <>
            <TextField
              fullWidth
              type="password"
              label="Azure Client Secret"
              value={config.client_secret || ""}
              onChange={(e) => update("client_secret", e.target.value)}
            />
            <TextField
              fullWidth
              label="Client Secret Env Ref"
              placeholder="SHAREPOINT_CLIENT_SECRET"
              value={config.client_secret_env || ""}
              onChange={(e) => update("client_secret_env", e.target.value)}
            />
          </>
        ) : (
          <>
            <TextField
              fullWidth
              label="Certificate Thumbprint"
              value={config.certificate_thumbprint || ""}
              onChange={(e) => update("certificate_thumbprint", e.target.value)}
            />
            <TextField
              fullWidth
              label="Private Key Env Ref"
              placeholder="SHAREPOINT_CERT_PRIVATE_KEY"
              value={config.certificate_private_key_env || ""}
              onChange={(e) => update("certificate_private_key_env", e.target.value)}
            />
            <TextField
              fullWidth
              label="Private Key File Path"
              placeholder="/run/secrets/sharepoint_cert.pem"
              value={config.certificate_private_key_path || ""}
              onChange={(e) => update("certificate_private_key_path", e.target.value)}
            />
            <TextField
              fullWidth
              label="Passphrase Env Ref"
              placeholder="SHAREPOINT_CERT_PASSPHRASE"
              value={config.certificate_passphrase_env || ""}
              onChange={(e) => update("certificate_passphrase_env", e.target.value)}
            />
          </>
        )}

        <Divider />

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            fullWidth
            label="Search Site"
            placeholder="workspace, operations, contracts"
            value={siteSearch}
            onChange={(e) => setSiteSearch(e.target.value)}
          />

          <Button variant="outlined" onClick={discoverSites} disabled={loading}>
            Find Sites
          </Button>
        </Stack>

        {!!sites.length && (
          <TextField
            select
            fullWidth
            label="Select SharePoint Site"
            value={config.site_id || ""}
            onChange={(e) => update("site_id", e.target.value)}
          >
            {sites.map((site) => (
              <MenuItem key={site.id} value={site.id}>
                {site.display_name || site.name}
              </MenuItem>
            ))}
          </TextField>
        )}

        <Button
          variant="outlined"
          onClick={discoverDrives}
          disabled={loading || !config.site_id}
        >
          Discover Document Libraries
        </Button>

        {!!drives.length && (
          <TextField
            select
            fullWidth
            label="Select Document Library"
            value={config.drive_id || ""}
            onChange={(e) => update("drive_id", e.target.value)}
          >
            {drives.map((drive) => (
              <MenuItem key={drive.id} value={drive.id}>
                {drive.name}
              </MenuItem>
            ))}
          </TextField>
        )}

        <Divider />

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            fullWidth
            label="Current Folder Path"
            value={folderPath}
            onChange={(e) => setFolderPath(e.target.value)}
          />

          <Button
            variant="outlined"
            onClick={discoverFolders}
            disabled={loading || !config.drive_id}
          >
            Browse
          </Button>
        </Stack>

        {!!folders.length && (
          <TextField
            select
            fullWidth
            label="Select Folder to Sync"
            value={config.folder_path || ""}
            onChange={(e) => update("folder_path", e.target.value)}
          >
            {folders.map((folder) => (
              <MenuItem key={folder.id} value={folder.path}>
                {folder.path}
              </MenuItem>
            ))}
          </TextField>
        )}

        <Button
          variant="contained"
          onClick={validateConfig}
          disabled={loading || !config.site_id || !config.drive_id}
          startIcon={loading ? <CircularProgress size={16} /> : null}
        >
          Validate SharePoint Config
        </Button>
      </Stack>
    </Box>
  );
}
