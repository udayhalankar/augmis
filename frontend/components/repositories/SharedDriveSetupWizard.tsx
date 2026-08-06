"use client";

import { useEffect, useState } from "react";
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


export default function SharedDriveSetupWizard({
  rootPath,
  setRootPath,
  sourcePath,
  setSourcePath,
}: {
  rootPath: string;
  setRootPath: (value: string) => void;
  sourcePath?: string;
  setSourcePath?: (value: string) => void;
}) {
  const [loadingRoots, setLoadingRoots] = useState(false);
  const [loadingFolders, setLoadingFolders] = useState(false);
  const [roots, setRoots] = useState<any[]>([]);
  const [folders, setFolders] = useState<any[]>([]);
  const [browsePath, setBrowsePath] = useState(sourcePath || rootPath || "");
  const [message, setMessage] = useState("");
  const isErrorMessage = /failed|does not exist|not mounted|invalid/i.test(message);

  useEffect(() => {
    setBrowsePath(sourcePath || rootPath || "");
  }, [sourcePath, rootPath]);

  useEffect(() => {
    setRoots([]);
    setFolders([]);
  }, [rootPath]);

  const discoverRoots = async () => {
    if (!rootPath.trim()) {
      setMessage("Enter a root path before browsing shared drive contents.");
      return;
    }

    setLoadingRoots(true);
    setMessage("");

    try {
      const data = await repositorySyncApi.discoverSharedDriveRoots(rootPath);
      setRoots(data);
      setMessage(`Found ${data.length} folder(s) under the selected root.`);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "Root discovery failed");
    } finally {
      setLoadingRoots(false);
    }
  };

  const discoverFolders = async () => {
    if (!rootPath.trim()) {
      setMessage("Enter a root path before browsing shared drive folders.");
      return;
    }

    setLoadingFolders(true);
    setMessage("");

    try {
      const data = await repositorySyncApi.discoverSharedDriveFolders(
        rootPath,
        browsePath || rootPath
      );
      setFolders(data);
      setMessage(`Found ${data.length} folder(s).`);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "Folder discovery failed");
    } finally {
      setLoadingFolders(false);
    }
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle2" fontWeight={800} sx={{ mb: 1 }}>
        Shared Drive Setup
      </Typography>

      <Alert severity="info" sx={{ mb: 2 }}>
        Use the picker to select a mounted root path and then choose the folder path to ingest.
        You can enter either Linux-style paths like <code>/mnt/d/Infomentica_Shared</code> or Windows-style
        paths like <code>D:\Infomentica_Shared</code>. Relative folder names are resolved under the selected root.
      </Alert>

      {message && (
        <Alert severity={isErrorMessage ? "error" : "info"} sx={{ mb: 2 }}>
          {message}
        </Alert>
      )}

      <Stack spacing={2}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
          <Button variant="outlined" onClick={discoverRoots} disabled={loadingRoots}>
            {loadingRoots ? "Loading..." : "Browse Root Contents"}
          </Button>
        </Stack>

        {!!roots.length && (
          <TextField
            select
            fullWidth
            label="Select Root Path"
            value={rootPath || ""}
            onChange={(e) => setRootPath(e.target.value)}
          >
            {roots.map((root) => (
              <MenuItem key={root.path} value={root.path}>
                {root.path}
              </MenuItem>
            ))}
          </TextField>
        )}

        <TextField
          fullWidth
          label="Root Path"
          value={rootPath}
          onChange={(e) => setRootPath(e.target.value)}
          helperText="This is the shared mount point or top-level repository path. Windows paths are normalized when possible."
        />

        {typeof setSourcePath === "function" && (
          <>
            <Divider />

            <TextField
              fullWidth
              label="Browse Folder Path"
              value={browsePath}
              onChange={(e) => setBrowsePath(e.target.value)}
              helperText="Choose a folder under the selected root path. A simple folder name like dssd will be treated as /path/to/root/dssd."
            />

            <Button
              variant="outlined"
              onClick={discoverFolders}
              disabled={loadingFolders || !rootPath}
            >
              {loadingFolders ? "Loading..." : "Browse Folders"}
            </Button>

            {!!folders.length && (
              <TextField
                select
                fullWidth
                label="Select Shared Drive Folder"
                value={sourcePath || ""}
                onChange={(e) => setSourcePath?.(e.target.value)}
              >
                {folders.map((folder) => (
                  <MenuItem key={folder.path} value={folder.path}>
                    {folder.path}
                  </MenuItem>
                ))}
              </TextField>
            )}

            <TextField
              fullWidth
              label="Shared Drive Folder Path"
              value={sourcePath || ""}
              onChange={(e) => setSourcePath?.(e.target.value)}
              helperText="This is the folder path that will act as the repository source."
            />
          </>
        )}
      </Stack>
    </Box>
  );
}
