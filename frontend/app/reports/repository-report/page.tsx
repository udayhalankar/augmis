"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  Typography,
  TextField,
} from "@mui/material";

import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import TextSnippetOutlinedIcon from "@mui/icons-material/TextSnippetOutlined";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import { getBusinessAreaCatalog } from "@/services/businessAreaService";
import apiClient from "@/services/apiClient";
import { repositorySyncApi } from "@/services/repositorySyncApi";

type RepositoryRecord = {
  repository_id: string;
  repository_name: string;
  business_area: string;
};

type BusinessAreaOption = {
  label: string;
  value: string;
};

type RepositoryIndexReport = {
  repository_id: string;
  repository_name: string;
  source_type: string;
  business_area: string;
  ocr?: {
    available?: boolean;
    error?: string | null;
    tesseract_cmd?: string | null;
    configured_tesseract_cmd?: string | null;
  };
  summary?: {
    total_files?: number;
    tracked_files?: number;
    live_only_files?: number;
    detected_source_files?: number;
    indexed_files?: number;
    empty_text_files?: number;
    failed_files?: number;
    ocr_used_files?: number;
    documents_indexed?: number;
    total_chunks?: number;
    duplicate_files?: number;
  };
  source_scan?: {
    mode?: string;
    error_id?: string;
    error_message?: string;
    detected_source_files?: number;
    live_only_files?: number;
  };
  items?: Array<{
    file_name: string;
    file_path?: string | null;
    external_file_id?: string | null;
    sync_status?: string | null;
    index_quality?: string | null;
    tracking_state?: string | null;
    chunk_count?: number | null;
    extracted_characters?: number | null;
    parser?: string | null;
    ocr_used?: boolean;
    duplicate_count?: number;
    failure_stage?: string | null;
    last_error_message?: string | null;
  }>;
};

export default function RepositoryReportPage() {
  const searchParams = useSearchParams();
  const initialRepositoryId = searchParams.get("repositoryId") || "";

  const [repositories, setRepositories] = useState<RepositoryRecord[]>([]);
  const [selectedRepositoryId, setSelectedRepositoryId] = useState(initialRepositoryId);
  const [selectedBusinessArea, setSelectedBusinessArea] = useState("All");
  const [businessAreas, setBusinessAreas] = useState<BusinessAreaOption[]>([
    { label: "All", value: "All" },
  ]);
  const [report, setReport] = useState<RepositoryIndexReport | null>(null);
  const [syncStatus, setSyncStatus] = useState<any | null>(null);
  const [loadingRepositories, setLoadingRepositories] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [error, setError] = useState("");
  const [reportSearch, setReportSearch] = useState("");
  const [reportPage, setReportPage] = useState(0);
  const [reportRowsPerPage, setReportRowsPerPage] = useState(5);

  useEffect(() => {
    if (initialRepositoryId) {
      setSelectedRepositoryId(initialRepositoryId);
    }
  }, [initialRepositoryId]);

  async function loadReport(repositoryId: string) {
    if (!repositoryId) return;
    setLoadingReport(true);
    setError("");
    try {
      const [reportData, statusData] = await Promise.all([
        repositorySyncApi.getRepositoryIndexReport(repositoryId),
        repositorySyncApi.getStatus(repositoryId),
      ]);
      setReport(reportData);
      setSyncStatus(statusData);
    } catch (loadError: any) {
      setReport(null);
      setSyncStatus(null);
      setError(
        loadError?.response?.data?.detail ||
          "Unable to load repository report."
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
        setSelectedRepositoryId((current) => {
          if (current && data.some((repository: RepositoryRecord) => repository.repository_id === current)) {
            return current;
          }
          return data[0]?.repository_id || "";
        });
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
      void loadReport(selectedRepositoryId);
    }
  }, [selectedRepositoryId]);

  useEffect(() => {
    let active = true;

    async function loadBusinessAreas() {
      try {
        const response = await getBusinessAreaCatalog();
        if (!active) return;

        const options = (response?.data || []).map((item: any) => ({
          label: String(item.display_name || item.name || item.slug || ""),
          value: String(item.slug || item.name || ""),
        }));

        setBusinessAreas([{ label: "All", value: "All" }, ...options.filter((item: BusinessAreaOption) => item.label && item.value)]);
      } catch (businessAreaError) {
        console.error("Failed to load business areas for repository report", businessAreaError);
      }
    }

    void loadBusinessAreas();

    return () => {
      active = false;
    };
  }, []);

  const visibleRepositories = useMemo(
    () =>
      selectedBusinessArea === "All"
        ? repositories
        : repositories.filter((repository) => repository.business_area === selectedBusinessArea),
    [repositories, selectedBusinessArea]
  );

  const filteredReportItems = useMemo(() => {
    const query = reportSearch.trim().toLowerCase();
    const items = report?.items || [];

    if (!query) return items;

    return items.filter((item) => {
      const searchable = [
        item.file_name,
        item.file_path,
        item.sync_status,
        item.index_quality,
        item.parser,
        item.failure_stage,
        item.last_error_message,
        item.external_file_id,
        item.tracking_state,
      ]
        .map((value) => String(value || "").toLowerCase())
        .join(" ");

      return searchable.includes(query);
    });
  }, [report?.items, reportSearch]);

  const pagedReportItems = useMemo(
    () =>
      filteredReportItems.slice(
        reportPage * reportRowsPerPage,
        reportPage * reportRowsPerPage + reportRowsPerPage
      ),
    [filteredReportItems, reportPage, reportRowsPerPage]
  );

  useEffect(() => {
    if (!visibleRepositories.length) {
      setSelectedRepositoryId("");
      return;
    }

    if (!visibleRepositories.some((repository) => repository.repository_id === selectedRepositoryId)) {
      setSelectedRepositoryId(visibleRepositories[0].repository_id);
    }
  }, [selectedRepositoryId, visibleRepositories]);

  useEffect(() => {
    setReportPage(0);
  }, [reportSearch, reportRowsPerPage, selectedRepositoryId]);

  useEffect(() => {
    const maxPage = Math.max(0, Math.ceil(filteredReportItems.length / reportRowsPerPage) - 1);
    if (reportPage > maxPage) {
      setReportPage(maxPage);
    }
  }, [filteredReportItems.length, reportPage, reportRowsPerPage]);

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

  function exportCsv() {
    if (!report) return;
    const rows = (report.items || []).map((item) => ({
      repository_name: report.repository_name,
      repository_business_area: report.business_area,
      file_name: item.file_name,
      file_path: item.file_path || "",
      sync_status: item.sync_status || "",
      index_quality: item.index_quality || "",
      chunk_count: item.chunk_count ?? 0,
      extracted_characters: item.extracted_characters ?? 0,
      parser: item.parser || "",
      ocr_used: item.ocr_used ? "Yes" : "No",
      duplicate_count: item.duplicate_count ?? 0,
      failure: item.tracking_state === "discovered_not_tracked"
        ? "not_tracked"
        : item.failure_stage || item.last_error_message || "",
    }));

    const header = Object.keys(rows[0] || {
      repository_name: "",
      repository_business_area: "",
      file_name: "",
      file_path: "",
      sync_status: "",
      index_quality: "",
      chunk_count: "",
      extracted_characters: "",
      parser: "",
      ocr_used: "",
      duplicate_count: "",
      failure: "",
    });

    const csv = [
      header.join(","),
      ...rows.map((row) =>
        header.map((key) => `"${String((row as Record<string, unknown>)[key] ?? "").replace(/"/g, '""')}"`).join(",")
      ),
    ].join("\n");

    downloadBlob(
      new Blob([csv], { type: "text/csv;charset=utf-8" }),
      `${report.repository_name.replace(/\s+/g, "_")}_repository_report.csv`
    );
  }

  function exportPdf() {
    window.print();
  }

  return (
  <ModuleGuard moduleName="settings" permission="admin:users">
    <OutletPage title="Repository Report">
      <Stack
        direction="row"
        spacing={1.5}
        useFlexGap
        sx={{ flexWrap: "wrap", justifyContent: "flex-end", mb: 2.5 }}
      >
        <Button
          variant="outlined"
          startIcon={<DownloadOutlinedIcon />}
          onClick={exportCsv}
          disabled={!report}
        >
          Export CSV
        </Button>

        <Button
          variant="outlined"
          startIcon={<PictureAsPdfOutlinedIcon />}
          onClick={exportPdf}
          disabled={!report}
        >
          Export PDF
        </Button>
      </Stack>

      {/* ALWAYS VISIBLE FILTERS */}
      <Card
        sx={{
          border: "1px solid",
          borderColor: "divider",
          mb: 2.5,
          flexShrink: 0,
          position: "relative",
          zIndex: 2,
        }}
      >
        <CardContent>
          <Stack spacing={2}>
            <TextField
              select
              fullWidth
              size="small"
              label="Business Area"
              value={selectedBusinessArea}
              onChange={(event) => {
                setSelectedBusinessArea(String(event.target.value));
              }}
            >
              {businessAreas.map((businessArea) => (
                <MenuItem key={businessArea.value} value={businessArea.value}>
                  {businessArea.label}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              fullWidth
              size="small"
              label="Repository"
              value={selectedRepositoryId}
              onChange={(event) =>
                setSelectedRepositoryId(String(event.target.value))
              }
              disabled={loadingRepositories || visibleRepositories.length === 0}
            >
              {visibleRepositories.map((repository) => (
                <MenuItem
                  key={repository.repository_id}
                  value={repository.repository_id}
                >
                  {repository.repository_name} ({repository.business_area})
                </MenuItem>
              ))}
            </TextField>
          </Stack>

          {error ? (
            <Alert severity="warning" sx={{ mt: 2 }}>
              {error}
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      {/* LOADER BELOW FILTERS */}
      {loadingRepositories || loadingReport ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress />
        </Box>
      ) : null}

      {/* REPORT BELOW FILTERS */}
      {!loadingRepositories && !loadingReport && report ? (
        <Stack spacing={2.5}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Stack spacing={1}>
                    <DescriptionOutlinedIcon color="primary" />
                    <Typography variant="h5" sx={{ fontWeight: 700 }}>
                      {report.summary?.tracked_files ?? 0}
                    </Typography>
                    <Typography color="text.secondary">Files Tracked</Typography>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Stack spacing={1}>
                    <FactCheckOutlinedIcon color="success" />
                    <Typography variant="h5" sx={{ fontWeight: 700 }}>
                      {report.summary?.indexed_files ?? 0}
                    </Typography>
                    <Typography color="text.secondary">Indexed Files</Typography>
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
                      {report.summary?.empty_text_files ?? 0}
                    </Typography>
                    <Typography color="text.secondary">Empty Text Files</Typography>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Stack spacing={1}>
                    <TextSnippetOutlinedIcon color="primary" />
                    <Typography variant="h5" sx={{ fontWeight: 700 }}>
                      {report.summary?.detected_source_files ??
                        report.summary?.total_files ??
                        0}
                    </Typography>
                    <Typography color="text.secondary">
                      Files Detected In Folder
                    </Typography>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
            <Chip
              size="small"
              color="error"
              label={`Failed: ${report.summary?.failed_files ?? 0}`}
            />
            <Chip size="small" label={`OCR used: ${report.summary?.ocr_used_files ?? 0}`} />
            <Chip size="small" label={`Documents: ${report.summary?.documents_indexed ?? 0}`} />
            <Chip size="small" label={`Hash duplicates: ${report.summary?.duplicate_files ?? 0}`} />
            <Chip size="small" label={`Not tracked yet: ${report.summary?.live_only_files ?? 0}`} />
          </Stack>

          <Alert severity="info">
            Index quality is inferred from extracted text, chunk coverage, OCR usage,
            and failure state. If a scanned PDF has little or no machine-readable
            text, it may stay empty until OCR is available and the repository is
            reindexed.
          </Alert>

          {report.ocr?.available === false ? (
            <Alert severity="warning">
              OCR is currently unavailable for this backend.
              {report.ocr?.error ? ` ${report.ocr.error}.` : null}
              {report.ocr?.configured_tesseract_cmd
                ? ` Configured path: ${report.ocr.configured_tesseract_cmd}.`
                : null}
            </Alert>
          ) : null}

          <Card>
            <CardContent>
              <Stack spacing={2} sx={{ mb: 2 }}>
                <Typography variant="h6">{report.repository_name}</Typography>
                <Typography color="text.secondary">
                  {report.source_type} • {report.business_area}
                </Typography>
                <TextField
                  size="small"
                  fullWidth
                  label="Search table"
                  value={reportSearch}
                  onChange={(event) => setReportSearch(event.target.value)}
                />
              </Stack>

              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>File</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Quality</TableCell>
                    <TableCell>Chunks</TableCell>
                    <TableCell>Chars</TableCell>
                    <TableCell>Parser</TableCell>
                    <TableCell>OCR Used</TableCell>
                    <TableCell>Duplicates</TableCell>
                    <TableCell>Failure</TableCell>
                  </TableRow>
                </TableHead>

                <TableBody>
                  {pagedReportItems.map((item, index) => (
                    <TableRow
                      key={`${item.external_file_id || item.file_name}-${index}`}
                      hover
                    >
                      <TableCell>
                        <Typography sx={{ fontWeight: 700 }}>
                          {item.file_name}
                        </Typography>
                        {item.file_path ? (
                          <Typography variant="caption" color="text.secondary">
                            {item.file_path}
                          </Typography>
                        ) : null}
                      </TableCell>

                      <TableCell>{item.sync_status || "-"}</TableCell>
                      <TableCell>{item.index_quality || "-"}</TableCell>
                      <TableCell>{item.chunk_count ?? 0}</TableCell>
                      <TableCell>{item.extracted_characters ?? "-"}</TableCell>
                      <TableCell>{item.parser || "-"}</TableCell>
                      <TableCell>{item.ocr_used ? "Yes" : "No"}</TableCell>
                      <TableCell>
                        {item.duplicate_count && item.duplicate_count > 1
                          ? `${item.duplicate_count} same-hash files`
                          : "-"}
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {item.tracking_state === "discovered_not_tracked"
                            ? "not_tracked"
                            : item.failure_stage ||
                              item.last_error_message ||
                              "-"}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              <TablePagination
                component="div"
                count={filteredReportItems.length}
                page={reportPage}
                onPageChange={(_, nextPage) => setReportPage(nextPage)}
                rowsPerPage={reportRowsPerPage}
                onRowsPerPageChange={(event) => {
                  setReportRowsPerPage(parseInt(event.target.value, 10));
                  setReportPage(0);
                }}
                rowsPerPageOptions={[5, 10, 25]}
              />
            </CardContent>
          </Card>
        </Stack>
      ) : null}
    </OutletPage>
  </ModuleGuard>
);

  // return (
  //   <ModuleGuard moduleName="settings" permission="admin:users">
  //     <OutletPage title="Repository Report">
  //       <Stack direction="row" spacing={1.5} useFlexGap sx={{ flexWrap: "wrap", justifyContent: "flex-end", mb: 2.5 }}>
  //         <Button
  //           variant="outlined"
  //           startIcon={<DownloadOutlinedIcon />}
  //           onClick={exportCsv}
  //           disabled={!report}
  //         >
  //           Export CSV
  //         </Button>
  //         <Button
  //           variant="outlined"
  //           startIcon={<PictureAsPdfOutlinedIcon />}
  //           onClick={exportPdf}
  //           disabled={!report}
  //         >
  //           Export PDF
  //         </Button>
  //       </Stack>

  //       <Card sx={{ border: "1px solid", borderColor: "divider", mb: 2.5 }}>
  //         <CardContent>
  //           <Stack spacing={2}>
  //             <TextField
  //               select
  //               fullWidth
  //               size="small"
  //               label="Business Area"
  //               value={selectedBusinessArea}
  //               onChange={(event) => {
  //                 setSelectedBusinessArea(String(event.target.value));
  //               }}
  //             >
  //               {businessAreas.map((businessArea) => (
  //                 <MenuItem key={businessArea.value} value={businessArea.value}>
  //                   {businessArea.label}
  //                 </MenuItem>
  //               ))}
  //             </TextField>

  //             <TextField
  //               select
  //               fullWidth
  //               size="small"
  //               label="Repository"
  //               value={selectedRepositoryId}
  //               onChange={(event) => setSelectedRepositoryId(String(event.target.value))}
  //               disabled={loadingRepositories || visibleRepositories.length === 0}
  //             >
  //               {visibleRepositories.map((repository) => (
  //                 <MenuItem key={repository.repository_id} value={repository.repository_id}>
  //                   {repository.repository_name} ({repository.business_area})
  //                 </MenuItem>
  //               ))}
  //             </TextField>
  //           </Stack>

  //           {error ? <Alert severity="warning" sx={{ mt: 2 }}>{error}</Alert> : null}
  //         </CardContent>
  //       </Card>

  //       {loadingRepositories || loadingReport ? (
  //         <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
  //           <CircularProgress />
  //         </Box>
  //       ) : null}

  //       {!loadingRepositories && !loadingReport && report ? (
  //         <Stack spacing={2.5}>
  //           <Grid container spacing={2}>
  //             <Grid size={{ xs: 12, md: 3 }}>
  //               <Card>
  //                 <CardContent>
  //                   <Stack spacing={1}>
  //                     <DescriptionOutlinedIcon color="primary" />
  //                     <Typography variant="h5" sx={{ fontWeight: 700 }}>
  //                       {report.summary?.tracked_files ?? 0}
  //                     </Typography>
  //                     <Typography color="text.secondary">Files Tracked</Typography>
  //                   </Stack>
  //                 </CardContent>
  //               </Card>
  //             </Grid>
  //             <Grid size={{ xs: 12, md: 3 }}>
  //               <Card>
  //                 <CardContent>
  //                   <Stack spacing={1}>
  //                     <FactCheckOutlinedIcon color="success" />
  //                     <Typography variant="h5" sx={{ fontWeight: 700 }}>
  //                       {report.summary?.indexed_files ?? 0}
  //                     </Typography>
  //                     <Typography color="text.secondary">Indexed Files</Typography>
  //                   </Stack>
  //                 </CardContent>
  //               </Card>
  //             </Grid>
  //             <Grid size={{ xs: 12, md: 3 }}>
  //               <Card>
  //                 <CardContent>
  //                   <Stack spacing={1}>
  //                     <WarningAmberRoundedIcon color="warning" />
  //                     <Typography variant="h5" sx={{ fontWeight: 700 }}>
  //                       {report.summary?.empty_text_files ?? 0}
  //                     </Typography>
  //                     <Typography color="text.secondary">Empty Text Files</Typography>
  //                   </Stack>
  //                 </CardContent>
  //               </Card>
  //             </Grid>
  //             <Grid size={{ xs: 12, md: 3 }}>
  //               <Card>
  //                 <CardContent>
  //                   <Stack spacing={1}>
  //                     <TextSnippetOutlinedIcon color="primary" />
  //                     <Typography variant="h5" sx={{ fontWeight: 700 }}>
  //                       {report.summary?.detected_source_files ?? report.summary?.total_files ?? 0}
  //                     </Typography>
  //                     <Typography color="text.secondary">Files Detected In Folder</Typography>
  //                   </Stack>
  //                 </CardContent>
  //               </Card>
  //             </Grid>
  //           </Grid>

  //           <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
  //             <Chip size="small" color="error" label={`Failed: ${report.summary?.failed_files ?? 0}`} />
  //             <Chip size="small" label={`OCR used: ${report.summary?.ocr_used_files ?? 0}`} />
  //             <Chip size="small" label={`Documents: ${report.summary?.documents_indexed ?? 0}`} />
  //             <Chip size="small" label={`Hash duplicates: ${report.summary?.duplicate_files ?? 0}`} />
  //             <Chip size="small" label={`Not tracked yet: ${report.summary?.live_only_files ?? 0}`} />
  //           </Stack>

  //           <Alert severity="info">
  //             Index quality is inferred from extracted text, chunk coverage, OCR usage, and failure state. If a scanned PDF has little or no machine-readable text, it may stay empty until OCR is available and the repository is reindexed.
  //           </Alert>

  //           {report.ocr?.available === false ? (
  //             <Alert severity="warning">
  //               OCR is currently unavailable for this backend.
  //               {report.ocr?.error ? ` ${report.ocr.error}.` : null}
  //               {report.ocr?.configured_tesseract_cmd
  //                 ? ` Configured path: ${report.ocr.configured_tesseract_cmd}.`
  //                 : null}
  //             </Alert>
  //           ) : null}

  //           {(report.summary?.live_only_files ?? 0) > 0 ? (
  //             <Alert severity="warning">
  //               {report.summary?.live_only_files} file(s) exist in the mounted source folder but are not yet tracked by repository sync. Run <strong>Sync</strong> or <strong>Reindex</strong> for this repository to ingest them.
  //             </Alert>
  //           ) : null}

  //           {report.source_scan?.mode !== "available" && report.source_scan?.error_message ? (
  //             <Alert severity="warning">
  //               Source folder scan was unavailable. {report.source_scan.error_message}
  //             </Alert>
  //           ) : null}

  //           {(syncStatus?.last_sync_error ||
  //             syncStatus?.sync_metadata?.discovery_warning?.message) ? (
  //             <Alert
  //               severity={
  //                 syncStatus?.last_sync_status === "failed" ? "error" : "warning"
  //               }
  //             >
  //               {syncStatus?.last_sync_error ||
  //                 syncStatus?.sync_metadata?.discovery_warning?.message}
  //             </Alert>
  //           ) : null}

  //           <Card>
  //             <CardContent>
  //               <Box sx={{ mb: 2 }}>
  //                 <Typography variant="h6">{report.repository_name}</Typography>
  //                 <Typography color="text.secondary">
  //                   {report.source_type} • {report.business_area}
  //                 </Typography>
  //               </Box>

  //               <Table size="small">
  //                 <TableHead>
  //                   <TableRow>
  //                     <TableCell>File</TableCell>
  //                     <TableCell>Status</TableCell>
  //                     <TableCell>Quality</TableCell>
  //                     <TableCell>Chunks</TableCell>
  //                     <TableCell>Chars</TableCell>
  //                     <TableCell>Parser</TableCell>
  //                     <TableCell>OCR Used</TableCell>
  //                     <TableCell>Duplicates</TableCell>
  //                     <TableCell>Failure</TableCell>
  //                   </TableRow>
  //                 </TableHead>
  //                 <TableBody>
  //                   {(report.items || []).map((item, index) => (
  //                     <TableRow key={`${item.external_file_id || item.file_name}-${index}`} hover>
  //                       <TableCell>
  //                         <Typography sx={{ fontWeight: 700 }}>{item.file_name}</Typography>
  //                         {item.file_path ? (
  //                           <Typography variant="caption" color="text.secondary">
  //                             {item.file_path}
  //                           </Typography>
  //                         ) : null}
  //                       </TableCell>
  //                       <TableCell>{item.sync_status || "-"}</TableCell>
  //                       <TableCell>{item.index_quality || "-"}</TableCell>
  //                       <TableCell>{item.chunk_count ?? 0}</TableCell>
  //                       <TableCell>{item.extracted_characters ?? "-"}</TableCell>
  //                       <TableCell>{item.parser || "-"}</TableCell>
  //                       <TableCell>{item.ocr_used ? "Yes" : "No"}</TableCell>
  //                       <TableCell>
  //                         {item.duplicate_count && item.duplicate_count > 1
  //                           ? `${item.duplicate_count} same-hash files`
  //                           : "-"}
  //                       </TableCell>
  //                       <TableCell>
  //                         <Typography variant="caption" color="text.secondary">
  //                           {item.tracking_state === "discovered_not_tracked"
  //                             ? "not_tracked"
  //                             : item.failure_stage || item.last_error_message || "-"}
  //                         </Typography>
  //                       </TableCell>
  //                     </TableRow>
  //                   ))}
  //                 </TableBody>
  //               </Table>
  //             </CardContent>
  //           </Card>
  //         </Stack>
  //       ) : null}
  //     </OutletPage>
  //   </ModuleGuard>
  // );
}

