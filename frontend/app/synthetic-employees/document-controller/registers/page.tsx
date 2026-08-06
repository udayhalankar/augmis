"use client";

import { useEffect, useState } from "react";

import {
  Chip,
  CircularProgress,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { OutletPage } from "@/components/layout/OutletPage";
import { getMasterDocumentRegister } from "@/services/symployeeService";

function formatLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function resolveLifecycleStage(item: any) {
  return String(item.document_lifecycle_stage || item.status || "REGISTERED").toUpperCase();
}

function resolveReviewState(item: any) {
  if (item.review_status) {
    return String(item.review_status).toUpperCase();
  }
  if ((item.overdue_workflow_task_count ?? 0) > 0) {
    return "REVIEW_OVERDUE";
  }
  if ((item.pending_recommendation_count ?? 0) > 0 || (item.open_workflow_task_count ?? 0) > 0) {
    return "IN_REVIEW";
  }
  return "REVIEW_COMPLETED";
}

function resolveRecordState(item: any) {
  return String(item.record_status || "NON_RECORD").toUpperCase();
}

export default function DocumentControllerRegistersPage() {
  const [registerData, setRegisterData] = useState<any | null>(null);
  const [searchText, setSearchText] = useState("");
  const [lifecycleFilter, setLifecycleFilter] = useState("ALL");
  const [reviewFilter, setReviewFilter] = useState("ALL");
  const [recordFilter, setRecordFilter] = useState("ALL");
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  useEffect(() => {
    getMasterDocumentRegister().then((result) => {
      setRegisterData(result?.data || { items: [], summary: {} });
    });
  }, []);

  if (!registerData) {
    return (
      <OutletPage
        title="Master Document Register"
        description="Expanded register view for document, review, and compliance visibility."
      >
        <CircularProgress />
      </OutletPage>
    );
  }

  const items = registerData.items || [];
  const summary = registerData.summary || {};
  const normalizedSearch = searchText.trim().toLowerCase();
  const filteredItems = items.filter((item: any) => {
    const matchesSearch =
      !normalizedSearch ||
      [
      item.repository_name,
      item.canonical_document_number,
      item.title,
      item.document_type_code,
      item.project_code,
      item.originator_code,
      item.current_revision_code,
    ]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(normalizedSearch));
    const matchesLifecycle =
      lifecycleFilter === "ALL" || resolveLifecycleStage(item) === lifecycleFilter;
    const matchesReview =
      reviewFilter === "ALL" || resolveReviewState(item) === reviewFilter;
    const matchesRecord =
      recordFilter === "ALL" || resolveRecordState(item) === recordFilter;

    return matchesSearch && matchesLifecycle && matchesReview && matchesRecord;
  });
  const pagedItems = filteredItems.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  return (
    <OutletPage
      title="Master Document Register"
      description="Expanded register view for document, review, and compliance visibility."
    >
      <Stack spacing={3}>
        <Grid container spacing={2}>
          {[
            ["Documents", summary.total_documents ?? items.length],
            ["Repositories", summary.repository_count ?? 0],
            ["Projects", summary.project_count ?? 0],
            ["Metadata Gaps", summary.documents_missing_metadata ?? 0],
            ["Pending Review", summary.documents_pending_review ?? 0],
            ["Overdue", summary.documents_with_overdue_tasks ?? 0],
          ].map(([label, value]) => (
            <Grid key={String(label)} size={{ xs: 12, sm: 6, lg: 2 }}>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
                <Typography color="text.secondary">{label}</Typography>
                <Typography variant="h5" fontWeight={800} sx={{ mt: 1 }}>
                  {value as any}
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>

        <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
          <Stack spacing={2}>
            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={2}
              sx={{
                justifyContent: "space-between",
                alignItems: { xs: "stretch", md: "center" },
              }}
            >
              <Typography color="text.secondary">
                {filteredItems.length} register rows
              </Typography>
              <TextField
                label="Search register"
                value={searchText}
                onChange={(event) => {
                  setSearchText(event.target.value);
                  setPage(0);
                }}
                size="small"
                sx={{ minWidth: { xs: "100%", md: 320 } }}
              />
            </Stack>

            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 4 }}>
                <FormControl size="small" fullWidth>
                  <InputLabel id="mdr-lifecycle-filter-label">Lifecycle</InputLabel>
                  <Select
                    labelId="mdr-lifecycle-filter-label"
                    value={lifecycleFilter}
                    label="Lifecycle"
                    onChange={(event) => {
                      setLifecycleFilter(event.target.value);
                      setPage(0);
                    }}
                  >
                    {["ALL", "REGISTERED", "ACTIVE", "APPROVED", "UNDER_REVIEW", "ARCHIVED", "INACTIVE", "WITHDRAWN", "DISPOSED"].map((value) => (
                      <MenuItem key={value} value={value}>
                        {formatLabel(value)}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <FormControl size="small" fullWidth>
                  <InputLabel id="mdr-review-filter-label">Review State</InputLabel>
                  <Select
                    labelId="mdr-review-filter-label"
                    value={reviewFilter}
                    label="Review State"
                    onChange={(event) => {
                      setReviewFilter(event.target.value);
                      setPage(0);
                    }}
                  >
                    {["ALL", "AWAITING_REVIEW", "IN_REVIEW", "REVIEW_COMPLETED", "REVIEW_OVERDUE", "REVIEW_REJECTED"].map((value) => (
                      <MenuItem key={value} value={value}>
                        {formatLabel(value)}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <FormControl size="small" fullWidth>
                  <InputLabel id="mdr-record-filter-label">Record State</InputLabel>
                  <Select
                    labelId="mdr-record-filter-label"
                    value={recordFilter}
                    label="Record State"
                    onChange={(event) => {
                      setRecordFilter(event.target.value);
                      setPage(0);
                    }}
                  >
                    {["ALL", "NON_RECORD", "RECORD_CANDIDATE", "DECLARED_RECORD", "UNDER_LEGAL_HOLD", "ARCHIVED", "DISPOSITION_PENDING", "DESTROYED", "PERMANENT"].map((value) => (
                      <MenuItem key={value} value={value}>
                        {formatLabel(value)}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Repository</TableCell>
                    <TableCell>Document Number</TableCell>
                    <TableCell>Title</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Project</TableCell>
                    <TableCell>Revision</TableCell>
                    <TableCell>Metadata</TableCell>
                    <TableCell>Review</TableCell>
                    <TableCell>Commands</TableCell>
                    <TableCell>Attention</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pagedItems.map((item: any) => (
                    <TableRow key={item.identity_id} hover>
                      <TableCell>{item.repository_name}</TableCell>
                      <TableCell>{item.canonical_document_number || "-"}</TableCell>
                      <TableCell>
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight={600}>
                            {item.title}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {item.originator_code || "-"}
                          </Typography>
                        </Stack>
                      </TableCell>
                      <TableCell>{item.document_type_code || "-"}</TableCell>
                      <TableCell>{item.project_code || "-"}</TableCell>
                      <TableCell>{item.current_revision_code || item.current_version_label || "-"}</TableCell>
                      <TableCell>
                        <Stack spacing={0.5}>
                          <Typography variant="body2">
                            {item.metadata_completeness_pct ?? 0}%
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {item.metadata_missing_fields?.length
                              ? item.metadata_missing_fields.join(", ")
                              : "Complete"}
                          </Typography>
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Stack spacing={0.5}>
                          <Typography variant="body2">
                            {item.pending_recommendation_count ?? 0} pending
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            SLA {item.latest_sla_status || "-"}
                          </Typography>
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Stack spacing={0.5}>
                          <Typography variant="body2">
                            {item.command_count ?? 0} total
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {item.latest_command_status || "No actions"}
                          </Typography>
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: "wrap" }}>
                          {(item.attention_flags || []).length ? (
                            (item.attention_flags || []).map((flag: string) => (
                              <Chip key={`${item.identity_id}-${flag}`} label={formatLabel(flag)} size="small" />
                            ))
                          ) : (
                            <Chip label="On Track" size="small" color="success" variant="outlined" />
                          )}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <TablePagination
              component="div"
              count={filteredItems.length}
              page={page}
              onPageChange={(_event, nextPage) => setPage(nextPage)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={(event) => {
                setRowsPerPage(Number(event.target.value));
                setPage(0);
              }}
              rowsPerPageOptions={[5, 10, 25]}
            />
          </Stack>
        </Paper>
      </Stack>
    </OutletPage>
  );
}
