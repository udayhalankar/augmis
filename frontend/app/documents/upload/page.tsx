"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Typography,
} from "@mui/material";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { rebuildRepository, uploadRepositoryDocument } from "@/services/ingestionService";
import { getMyRepositoryAccess } from "@/services/repositoryService";

export default function DocumentUploadPage() {
  const [repoAccess, setRepoAccess] = useState<any[]>([]);
  const [repositoryId, setRepositoryId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadRepos() {
    setLoading(true);
    setError("");

    try {
      const result = await getMyRepositoryAccess();

      if (result.success) {
        const ingestRepos = result.data.filter((row: any) => row.can_ingest);
        setRepoAccess(ingestRepos);

        if (ingestRepos.length > 0) {
          setRepositoryId(ingestRepos[0].repository_id);
        }
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to load repository access");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRepos();
  }, []);

  async function handleUpload() {
    if (!repositoryId || !file) return;

    setUploading(true);
    setMessage("");
    setError("");

    try {
      const result = await uploadRepositoryDocument(repositoryId, file);

      if (result.success) {
        setMessage(
          `Uploaded and indexed successfully. Chunks indexed: ${result.indexing?.data?.chunks_indexed || 0}`
        );
        setFile(null);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleRebuild() {
    if (!repositoryId) return;

    setUploading(true);
    setMessage("");
    setError("");

    try {
      const result = await rebuildRepository(repositoryId);

      if (result.ok || result.success) {
        setMessage(
          result.message ||
            `Repository rebuild completed. Indexed ${result.indexed_files || 0} files and ${result.chunks || 0} chunks.`
        );
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Rebuild failed");
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return (
      <ModuleGuard moduleName="documents" permission="documents:upload">
        <Box sx={{ p: 4, display: "flex", alignItems: "center", gap: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading repository access...</Typography>
        </Box>
      </ModuleGuard>
    );
  }

  return (
    <ModuleGuard moduleName="documents" permission="documents:upload">
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 800, mb: 1 }}>
          Upload Repository Document
        </Typography>

        <Typography color="text.secondary" sx={{ mb: 3 }}>
          Upload files into a tenant repository. Metadata will be stamped automatically for secure search and RAG.
        </Typography>

        <Paper
          elevation={0}
          sx={{
            p: 3,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            maxWidth: 720,
          }}
        >
          {repoAccess.length === 0 ? (
            <Alert severity="warning">
              You do not have ingestion access to any repository.
            </Alert>
          ) : (
            <Stack gap={2.5}>
              {message && <Alert severity="success">{message}</Alert>}
              {error && <Alert severity="error">{error}</Alert>}

              <FormControl fullWidth>
                <InputLabel>Repository</InputLabel>
                <Select
                  label="Repository"
                  value={repositoryId}
                  onChange={(e) => setRepositoryId(e.target.value)}
                >
                  {repoAccess.map((row) => (
                    <MenuItem key={row.repository_id} value={row.repository_id}>
                      {row.repository?.repository_name} - {row.repository?.business_area}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button variant="outlined" component="label">
                Select File
                <input
                  hidden
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
              </Button>

              {file && (
                <Typography variant="body2">
                  Selected file: <b>{file.name}</b>
                </Typography>
              )}

              <Stack direction="row" gap={1.5}>
                <Button
                  variant="contained"
                  disabled={!file || !repositoryId || uploading}
                  onClick={handleUpload}
                >
                  {uploading ? <CircularProgress size={22} /> : "Upload"}
                </Button>

                <Button
                  variant="outlined"
                  disabled={!repositoryId || uploading}
                  onClick={handleRebuild}
                >
                  Rebuild Repository Index
                </Button>
              </Stack>
            </Stack>
          )}
        </Paper>
      </Box>
    </ModuleGuard>
  );
}
