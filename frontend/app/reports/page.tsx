"use client";

import { useEffect, useMemo, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableHead,
  TableCell,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import AssessmentOutlinedIcon from "@mui/icons-material/AssessmentOutlined";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import FindInPageOutlinedIcon from "@mui/icons-material/FindInPageOutlined";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import apiClient from "@/services/apiClient";
import { repositorySyncApi } from "@/services/repositorySyncApi";

type RepositoryRecord = {
  repository_id: string;
  repository_name: string;
  business_area: string;
  source_type: string;
};

type FolderItem = {
  connector_file_id: string;
  file_name: string;
  file_path?: string | null;
  inferred_type_label: string;
  inferred_type: string;
  status: "aligned" | "needs_review" | "unknown";
  status_label: string;
  severity_score: number;
  severity_label: string;
  confidence: number;
  reason?: string | null;
  classification_mode: "ai" | "heuristic";
  sync_status?: string;
  tracking_state?: "tracked" | "discovered_not_tracked";
  open_target: {
    repository_id: string;
    connector_file_id: string;
  } | null;
  metadata?: {
    chunk_count?: number;
    parser?: string;
    text_status?: string;
  };
};

type FolderSummary = {
  folder_path: string;
  folder_name: string;
  file_count: number;
  dominant_type_label: string;
  mismatch_count: number;
  alignment_status: string;
  types_found: Array<{ label: string; count: number }>;
  items: FolderItem[];
};

type ContentReport = {
  repository_id: string;
  repository_name: string;
  business_area: string;
  root_folder_label: string;
  expected_types: Array<{ type: string; label: string }>;
  status_options: Array<{ value: string; label: string }>;
  summary: {
    total_files: number;
    tracked_files?: number;
    live_untracked_files?: number;
    folder_count: number;
    mismatch_files: number;
    aligned_files: number;
    unknown_files: number;
    classification_mode: "ai" | "heuristic";
    classification_details?: {
      mode: "ai" | "heuristic" | "ai_with_fallback";
      display_label: string;
      fallback_reason?: string | null;
      error_id?: string | null;
      error_message?: string | null;
      batches_attempted?: number;
      batches_failed?: number;
    };
    source_scan?: {
      discovered_files?: number;
      tracked_files?: number;
      live_untracked_files?: number;
      error?: {
        mode?: string;
        error_id?: string | null;
        error_message?: string | null;
      } | null;
    };
    type_distribution: Array<{ label: string; count: number }>;
    status_distribution: Array<{ status: string; label: string; count: number }>;
  };
  folders: FolderSummary[];
  filtered_summary?: {
    total_files: number;
    folder_count: number;
    mismatch_files: number;
    aligned_files: number;
    unknown_files: number;
  };
  pagination?: {
    page: number;
    page_size: number;
    total_pages: number;
    total_folders: number;
    has_previous: boolean;
    has_next: boolean;
  };
};

function getClassificationModeLabel(mode: "ai" | "heuristic") {
  return mode === "ai" ? "AI-assisted" : "Rule-based fallback";
}

function getClassificationModeDescription(
  mode: "ai" | "heuristic",
  details?: ContentReport["summary"]["classification_details"]
) {
  if (details?.fallback_reason) {
    return details.fallback_reason;
  }

  return mode === "ai"
    ? "OpenAI-based classification is active for this report, with rules still available as fallback."
    : "Heuristic means rule-based classification from file name, folder path, and indexed text because AI classification was unavailable or not confident enough.";
}

function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function RepositoryFolderItemsTable({
  folder,
  reportRootLabel,
  openingFileId,
  onOpenFile,
}: {
  folder: FolderSummary;
  reportRootLabel: string;
  openingFileId: string;
  onOpenFile: (item: FolderItem) => void;
}) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);

  const filteredRows = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return folder.items;

    return folder.items.filter((item) => {
      const haystack = [
        item.file_name,
        item.file_path,
        item.inferred_type_label,
        item.status_label,
        item.severity_label,
        item.reason,
        item.metadata?.parser,
        item.metadata?.text_status,
        item.tracking_state,
        String(item.severity_score),
        String(item.confidence),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(query);
    });
  }, [folder.items, search]);

  useEffect(() => {
    setPage(0);
  }, [folder.folder_path]);

  useEffect(() => {
    if (page > 0 && page * rowsPerPage >= filteredRows.length) {
      setPage(0);
    }
  }, [filteredRows.length, page, rowsPerPage]);

  const start = page * rowsPerPage;
  const visibleRows = filteredRows.slice(start, start + rowsPerPage);

  return (
    <Stack spacing={2}>
      <TextField
        fullWidth
        size="small"
        label="Search files"
        placeholder="Search by file name, status, type, or path"
        value={search}
        onChange={(event) => {
          setSearch(event.target.value);
          setPage(0);
        }}
      />

      <Box sx={{ overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>File</TableCell>
              <TableCell>AI Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Severity</TableCell>
              <TableCell>Index Info</TableCell>
              <TableCell align="right">Open</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {visibleRows.length > 0 ? (
              visibleRows.map((item) => (
                <TableRow key={item.connector_file_id} hover>
                  <TableCell>
                    <Typography sx={{ fontWeight: item.status === "needs_review" ? 700 : 500 }}>
                      {item.file_name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {item.file_path || reportRootLabel}
                    </Typography>
                    {item.reason ? (
                      <Typography
                        variant="body2"
                        color={item.status === "needs_review" ? "warning.main" : "text.secondary"}
                      >
                        {item.reason}
                      </Typography>
                    ) : null}
                    {item.tracking_state === "discovered_not_tracked" ? (
                      <Typography variant="body2" color="info.main">
                        Live source file detected, but not yet tracked by repository sync.
                      </Typography>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    <Stack spacing={0.75}>
                      <Typography>{item.inferred_type_label}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Confidence {Math.round(item.confidence * 100)}% • {getClassificationModeLabel(item.classification_mode)}
                      </Typography>
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      color={
                        item.status === "needs_review"
                          ? "warning"
                          : item.status === "unknown"
                          ? "default"
                          : "success"
                      }
                      label={item.status_label}
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      variant={item.severity_score >= 50 ? "filled" : "outlined"}
                      color={
                        item.severity_score >= 80
                          ? "error"
                          : item.severity_score >= 50
                          ? "warning"
                          : "default"
                      }
                      label={`${item.severity_label} (${item.severity_score})`}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      Sync: {item.tracking_state === "discovered_not_tracked" ? "Not tracked yet" : item.sync_status || "-"} • Parser: {item.metadata?.parser || "-"} • Chunks: {item.metadata?.chunk_count ?? 0}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      variant={item.status === "needs_review" ? "contained" : "outlined"}
                      startIcon={<OpenInNewOutlinedIcon />}
                      onClick={() => onOpenFile(item)}
                      disabled={openingFileId === item.connector_file_id || !item.open_target}
                    >
                      {openingFileId === item.connector_file_id
                        ? "Opening..."
                        : item.open_target
                        ? "Open File"
                        : "Sync First"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography variant="body2" color="text.secondary">
                    No matching files found.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Box>

      <TablePagination
        component="div"
        count={filteredRows.length}
        page={page}
        onPageChange={(_, nextPage) => setPage(nextPage)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(event) => {
          setRowsPerPage(Number(event.target.value));
          setPage(0);
        }}
        rowsPerPageOptions={[5, 10, 25]}
      />
    </Stack>
  );
}

export default function ReportsPage() {
  const [repositories, setRepositories] = useState<RepositoryRecord[]>([]);
  const [selectedRepositoryId, setSelectedRepositoryId] = useState("");
  const [report, setReport] = useState<ContentReport | null>(null);
  const [loadingRepositories, setLoadingRepositories] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [openingFileId, setOpeningFileId] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");

  async function loadReport(repositoryId: string, nextPage = page, nextStatus = statusFilter) {
    if (!repositoryId) return;
    setLoadingReport(true);
    setError("");
    try {
      const data = await repositorySyncApi.getRepositoryContentReport(repositoryId, {
        page: nextPage,
        pageSize: 4,
        status: nextStatus,
      });
      setReport(data);
    } catch (loadError: any) {
      setReport(null);
      setError(
        loadError?.response?.data?.detail ||
          "Unable to load repository content report."
      );
    } finally {
      setLoadingReport(false);
    }
  }

  useEffect(() => {
    async function loadRepositories() {
      setLoadingRepositories(true);
      setError("");
      try {
        const response = await apiClient.get("/api/repositories");
        const data = Array.isArray(response.data?.data) ? response.data.data : [];
        setRepositories(data);
        if (data.length > 0) {
          setSelectedRepositoryId((current) => current || data[0].repository_id);
        }
      } catch (loadError: any) {
        setError(
          loadError?.response?.data?.detail ||
            "Unable to load repositories for reports."
        );
      } finally {
        setLoadingRepositories(false);
      }
    }

    void loadRepositories();
  }, []);

  useEffect(() => {
    if (selectedRepositoryId) {
      void loadReport(selectedRepositoryId, page, statusFilter);
    }
  }, [selectedRepositoryId, page, statusFilter]);

  async function handleOpenFile(item: FolderItem) {
    if (!item.open_target) return;
    setOpeningFileId(item.connector_file_id);
    try {
      const { blob, contentType } = await repositorySyncApi.getRepositoryFileContent(
        item.open_target.repository_id,
        item.open_target.connector_file_id
      );
      const fileBlob =
        blob instanceof Blob
          ? blob
          : new Blob([blob], {
              type: typeof contentType === "string" ? contentType : "application/octet-stream",
            });
      const url = URL.createObjectURL(fileBlob);
      window.open(url, "_blank", "noopener,noreferrer");
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (openError: any) {
      setError(
        openError?.response?.data?.detail ||
          "Unable to open the selected file."
      );
    } finally {
      setOpeningFileId("");
    }
  }

  function exportCsv() {
    if (!report) return;
    const rows = report.folders.flatMap((folder) =>
      folder.items.map((item) => ({
        repository_name: report.repository_name,
        repository_business_area: report.business_area,
        folder_name: folder.folder_name,
        folder_path: folder.folder_path,
        file_name: item.file_name,
        file_path: item.file_path || "",
        inferred_type: item.inferred_type_label,
        status: item.status_label,
        severity_score: item.severity_score,
        severity_label: item.severity_label,
        confidence: item.confidence,
        classification_mode: item.classification_mode,
        parser: item.metadata?.parser || "",
        chunk_count: item.metadata?.chunk_count ?? 0,
        reason: item.reason || "",
      }))
    );

    const header = Object.keys(rows[0] || {
      repository_name: "",
      repository_business_area: "",
      folder_name: "",
      folder_path: "",
      file_name: "",
      file_path: "",
      inferred_type: "",
      status: "",
      severity_score: "",
      severity_label: "",
      confidence: "",
      classification_mode: "",
      parser: "",
      chunk_count: "",
      reason: "",
    });
    const csv = [
      header.join(","),
      ...rows.map((row) =>
        header
          .map((key) => `"${String((row as Record<string, unknown>)[key] ?? "").replace(/"/g, '""')}"`)
          .join(",")
      ),
    ].join("\n");

    downloadBlob(
      new Blob([csv], { type: "text/csv;charset=utf-8" }),
      `${report.repository_name.replace(/\s+/g, "_")}_repository_content_report.csv`
    );
  }

  function exportPdf() {
    window.print();
  }

  const filteredSummary = report?.filtered_summary || {
    total_files: 0,
    folder_count: 0,
    mismatch_files: 0,
    aligned_files: 0,
    unknown_files: 0,
  };

  return (
    <ModuleGuard moduleName="documents" permission="documents:read">
      <OutletPage title="Repository Content Report">
        {/* ALWAYS VISIBLE FILTERS */}
              <Card
                sx={{
                  border: "1px solid",
                  borderColor: "divider",
                  mb: 2.5,
                  flexShrink: 0,
                  position: "relative",
                  zIndex: 2,
                  bgcolor: "#ffffff",
                }}
              >
                <CardContent>
                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    spacing={2}
                    sx={{ alignItems: { xs: "stretch", md: "center" } }}
                  >
                    <FormControl fullWidth size="small">
                      <InputLabel id="report-repository-label">Repository</InputLabel>
                      <Select
                        labelId="report-repository-label"
                        label="Repository"
                        value={selectedRepositoryId}
                        onChange={(event) => {
                          setPage(1);
                          setSelectedRepositoryId(String(event.target.value));
                        }}
                        disabled={loadingRepositories || repositories.length === 0}
                      >
                        {repositories.map((repository) => (
                          <MenuItem
                            key={repository.repository_id}
                            value={repository.repository_id}
                          >
                            {repository.repository_name} ({repository.business_area})
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    <FormControl sx={{ minWidth: 180 }} size="small">
                      <InputLabel id="report-status-filter-label">Status</InputLabel>
                      <Select
                        labelId="report-status-filter-label"
                        label="Status"
                        value={statusFilter}
                        onChange={(event) => {
                          setPage(1);
                          setStatusFilter(String(event.target.value));
                        }}
                      >
                        {(report?.status_options || [{ value: "all", label: "All" }]).map(
                          (option) => (
                            <MenuItem key={option.value} value={option.value}>
                              {option.label}
                            </MenuItem>
                          )
                        )}
                      </Select>
                    </FormControl>

                    <Button
                      variant="outlined"
                      onClick={() => void loadReport(selectedRepositoryId, page, statusFilter)}
                      disabled={!selectedRepositoryId || loadingReport}
                      sx={{ minWidth: 140 }}
                    >
                      Refresh
                    </Button>
                  </Stack>

                  {error ? (
                    <Alert severity="warning" sx={{ mt: 2 }}>
                      {error}
                    </Alert>
                  ) : null}
                </CardContent>
              </Card>

        {loadingRepositories || loadingReport ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress />
          </Box>
        ) : null}

        {!loadingRepositories && !loadingReport && report ? (
          <Stack spacing={2.5}>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 3 }}>
                <Card>
                  <CardContent>
                    <Stack spacing={1}>
                      <AssessmentOutlinedIcon color="primary" />
                      <Typography variant="h5" sx={{ fontWeight: 700 }}>
                        {filteredSummary.total_files}
                      </Typography>
                      <Typography color="text.secondary">Files In View</Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <Card>
                  <CardContent>
                    <Stack spacing={1}>
                      <FolderOutlinedIcon color="primary" />
                      <Typography variant="h5" sx={{ fontWeight: 700 }}>
                        {filteredSummary.folder_count}
                      </Typography>
                      <Typography color="text.secondary">Folders In View</Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <Card>
                  <CardContent>
                    <Stack spacing={1}>
                      <WarningAmberRoundedIcon color="warning" />
                      <Typography variant="h5" sx={{ fontWeight: 700 }}>
                        {filteredSummary.mismatch_files}
                      </Typography>
                      <Typography color="text.secondary">Needs Review</Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <Card>
                  <CardContent>
                    <Stack spacing={1}>
                      <FindInPageOutlinedIcon color="success" />
                      <Typography variant="h5" sx={{ fontWeight: 700 }}>
                        {report.summary.classification_details?.display_label ||
                          getClassificationModeLabel(report.summary.classification_mode)}
                      </Typography>
                      <Typography color="text.secondary">Classification Mode</Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            <Card>
              <CardContent>
                <Alert severity="info" sx={{ mb: 2 }}>
                  {getClassificationModeDescription(
                    report.summary.classification_mode,
                    report.summary.classification_details
                  )}
                </Alert>

                {report.summary.classification_details?.error_id ? (
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    Error ID: {report.summary.classification_details.error_id}
                    {report.summary.classification_details.error_message
                      ? ` • ${report.summary.classification_details.error_message}`
                      : ""}
                  </Alert>
                ) : null}

                {report.summary.source_scan?.live_untracked_files ? (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    {report.summary.source_scan.live_untracked_files} source file(s) exist in the mounted repository folder but are not yet tracked by sync, so they were added as live-discovered items in this report.
                  </Alert>
                ) : null}

                {report.summary.source_scan?.error?.error_id ? (
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    Source scan unavailable: {report.summary.source_scan.error.error_id}
                    {report.summary.source_scan.error.error_message
                      ? ` • ${report.summary.source_scan.error.error_message}`
                      : ""}
                  </Alert>
                ) : null}

                <Typography variant="h6" gutterBottom>
                  Expected Document Types for {report.business_area}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  `Needs Review` means the AI classified the file as likely unrelated to the repository business area. `Unknown` means the AI could not infer a confident type from the available evidence.
                </Typography>
                <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
                  {report.expected_types.map((item) => (
                    <Chip key={item.type} label={item.label} />
                  ))}
                </Stack>
              </CardContent>
            </Card>

            {report.folders.map((folder) => (
              <Card key={folder.folder_path}>
                <CardContent>
                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    spacing={2}
                    sx={{ mb: 2, justifyContent: "space-between" }}
                  >
                    <Box>
                      <Typography variant="h6">{folder.folder_name}</Typography>
                      <Typography color="text.secondary">
                        {folder.folder_path} • {folder.file_count} files • Dominant type: {folder.dominant_type_label}
                      </Typography>
                    </Box>

                    <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
                      <Chip
                        color={folder.mismatch_count > 0 ? "warning" : "success"}
                        label={
                          folder.mismatch_count > 0
                            ? `${folder.mismatch_count} need review`
                            : "Aligned"
                        }
                      />
                      {folder.types_found.map((type) => (
                        <Chip
                          key={`${folder.folder_path}-${type.label}`}
                          variant="outlined"
                          label={`${type.label}: ${type.count}`}
                        />
                      ))}
                    </Stack>
                  </Stack>

                  <RepositoryFolderItemsTable
                    folder={folder}
                    reportRootLabel={report.root_folder_label}
                    openingFileId={openingFileId}
                    onOpenFile={(item) => {
                      void handleOpenFile(item);
                    }}
                  />
                </CardContent>
              </Card>
            ))}

            {report.pagination ? (
              <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
                <Typography variant="body2" color="text.secondary">
                  Page {report.pagination.page} of {report.pagination.total_pages} • {report.pagination.total_folders} folders
                </Typography>
                <Stack direction="row" spacing={1}>
                  <Button
                    variant="outlined"
                    size="small"
                    disabled={!report.pagination.has_previous || loadingReport}
                    onClick={() => setPage((current) => Math.max(current - 1, 1))}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outlined"
                    size="small"
                    disabled={!report.pagination.has_next || loadingReport}
                    onClick={() =>
                      setPage((current) =>
                        report.pagination
                          ? Math.min(current + 1, report.pagination.total_pages)
                          : current + 1
                      )
                    }
                  >
                    Next
                  </Button>
                </Stack>
              </Box>
            ) : null}
          </Stack>
        ) : null}
      </OutletPage>
    </ModuleGuard>
  );
}

