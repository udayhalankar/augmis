"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  Box,
  Button,
  CircularProgress,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  TextField,
  Typography,
} from "@mui/material";

import { OutletPage } from "@/components/layout/OutletPage";
import {
  getDocumentControllerApprovals,
  getDocumentControllerDocumentDetail,
  getDocumentControllerDocuments,
  getDocumentControllerRecommendations,
} from "@/services/symployeeService";

function normalize(value?: string | null, fallback = "UNSET") {
  return String(value || fallback).toUpperCase();
}

type ReviewRow = {
  id: string;
  subject: string;
  reviewStatus: string;
  source: string;
  decision: string;
  detail: string;
};

type SortField = "subject" | "reviewStatus" | "source" | "decision" | "detail";

export default function ReviewsPage() {
  const [rows, setRows] = useState<ReviewRow[] | null>(null);
  const [searchValue, setSearchValue] = useState("");
  const [page, setPage] = useState(0);
  const [sortField, setSortField] = useState<SortField>("subject");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  useEffect(() => {
    async function load() {
      const [documentsResult, recommendationsResult, approvalsResult] = await Promise.all([
        getDocumentControllerDocuments(),
        getDocumentControllerRecommendations(),
        getDocumentControllerApprovals(),
      ]);

      const documentItems = documentsResult?.data?.items || [];
      const details = (
        await Promise.all(
          documentItems.map((item: any) =>
            getDocumentControllerDocumentDetail(item.identity_id)
              .then((result) => result?.data || null)
              .catch(() => null)
          )
        )
      ).filter(Boolean);

      const identities = details.map((item: any) => item.identity).filter(Boolean);
      const recommendations = recommendationsResult?.data?.items || [];
      const approvals = approvalsResult?.data?.items || [];

      const reviewRows: ReviewRow[] = [];

      identities.forEach((item: any) => {
        const reviewStatus = normalize(item.review_status);
        if (!["AWAITING_REVIEW", "IN_REVIEW", "REVIEW_COMPLETED"].includes(reviewStatus)) {
          return;
        }

        reviewRows.push({
          id: `doc-${item.identity_id}`,
          subject: item.title || item.identity_id,
          reviewStatus: reviewStatus.replaceAll("_", " "),
          source: "Document Review State",
          decision: reviewStatus === "REVIEW_COMPLETED" ? "Completed" : "Pending",
          detail: `Document lifecycle is ${normalize(
            item.document_lifecycle_stage,
            item.status
          ).replaceAll("_", " ")}.`,
        });
      });

      recommendations
        .filter((item: any) => normalize(item.status) === "NEEDS_REVIEW")
        .forEach((item: any) => {
          reviewRows.push({
            id: `rec-${item.recommendation_id}`,
            subject: item.recommendation_type || item.recommendation_id,
            reviewStatus: "Awaiting Review",
            source: "AI Recommendation",
            decision: "Pending",
            detail: `Recommendation requires reviewer action${item.model_name ? ` from ${item.model_name}` : ""}.`,
          });
        });

      approvals.forEach((item: any) => {
        reviewRows.push({
          id: `apr-${item.approval_id}`,
          subject: item.approval_subject_type || item.approval_id,
          reviewStatus: "Approval Recorded",
          source: "Approval Audit",
          decision: item.decision || "-",
          detail: item.comments || "Approval decision captured without reviewer comments.",
        });
      });

      setRows(reviewRows);
    }

    void load();
  }, []);

  const metrics = useMemo(() => {
    const items = rows || [];
    return {
      total: items.length,
      awaiting: items.filter((item) => item.reviewStatus === "Awaiting Review").length,
      inProgress: items.filter((item) => item.reviewStatus === "IN REVIEW").length,
      completed: items.filter((item) => item.decision === "Completed").length,
    };
  }, [rows]);

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }

    setSortField(field);
    setSortDirection("asc");
  }

  const filteredRows = useMemo(() => {
    const query = searchValue.trim().toLowerCase();
    const items = rows || [];

    if (!query) return items;

    return items.filter((item) =>
      [item.subject, item.reviewStatus, item.source, item.decision, item.detail]
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [rows, searchValue]);

  const sortedRows = useMemo(() => {
    return [...filteredRows].sort((left, right) => {
      const leftValue = String(left[sortField] ?? "").toLowerCase();
      const rightValue = String(right[sortField] ?? "").toLowerCase();

      if (leftValue < rightValue) {
        return sortDirection === "asc" ? -1 : 1;
      }
      if (leftValue > rightValue) {
        return sortDirection === "asc" ? 1 : -1;
      }
      return 0;
    });
  }, [filteredRows, sortDirection, sortField]);

  const rowsPerPage = 10;
  const pagedRows = sortedRows.slice(page * rowsPerPage, (page + 1) * rowsPerPage);

  return (
    <OutletPage
      title="Reviews"
      description="Live review workspace for active document review states, pending recommendations, and approval history."
      actions={
        <Button
          component={Link}
          href="/synthetic-employees/document-controller/control-center"
          variant="outlined"
        >
          Open Control Center
        </Button>
      }
    >
      {rows === null ? (
        <CircularProgress />
      ) : (
        <Stack spacing={3}>
          <Grid container spacing={2}>
            {[
              ["Review Items", metrics.total],
              ["Awaiting Review", metrics.awaiting],
              ["In Progress", metrics.inProgress],
              ["Completed", metrics.completed],
            ].map(([label, value]) => (
              <Grid key={String(label)} size={{ xs: 12, md: 6, xl: 3 }}>
                <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, height: "100%" }}>
                  <Stack spacing={1}>
                    <Typography color="text.secondary">{label}</Typography>
                    <Typography variant="h4" fontWeight={800}>
                      {value as number}
                    </Typography>
                  </Stack>
                </Paper>
              </Grid>
            ))}
          </Grid>

          <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
            <Stack spacing={1.5}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 2,
                  flexWrap: "wrap",
                }}
              >
                <Typography variant="h6" fontWeight={700}>
                  Review Register
                </Typography>
                <TextField
                  size="small"
                  placeholder="Search reviews"
                  value={searchValue}
                  onChange={(event) => {
                    setSearchValue(event.target.value);
                    setPage(0);
                  }}
                  sx={{ width: { xs: "100%", sm: 280 } }}
                />
              </Box>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sortDirection={sortField === "subject" ? sortDirection : false}>
                      <TableSortLabel
                        active={sortField === "subject"}
                        direction={sortField === "subject" ? sortDirection : "asc"}
                        onClick={() => handleSort("subject")}
                      >
                        Subject
                      </TableSortLabel>
                    </TableCell>
                    <TableCell sortDirection={sortField === "reviewStatus" ? sortDirection : false}>
                      <TableSortLabel
                        active={sortField === "reviewStatus"}
                        direction={sortField === "reviewStatus" ? sortDirection : "asc"}
                        onClick={() => handleSort("reviewStatus")}
                      >
                        Review Status
                      </TableSortLabel>
                    </TableCell>
                    <TableCell sortDirection={sortField === "source" ? sortDirection : false}>
                      <TableSortLabel
                        active={sortField === "source"}
                        direction={sortField === "source" ? sortDirection : "asc"}
                        onClick={() => handleSort("source")}
                      >
                        Source
                      </TableSortLabel>
                    </TableCell>
                    <TableCell sortDirection={sortField === "decision" ? sortDirection : false}>
                      <TableSortLabel
                        active={sortField === "decision"}
                        direction={sortField === "decision" ? sortDirection : "asc"}
                        onClick={() => handleSort("decision")}
                      >
                        Decision
                      </TableSortLabel>
                    </TableCell>
                    <TableCell sortDirection={sortField === "detail" ? sortDirection : false}>
                      <TableSortLabel
                        active={sortField === "detail"}
                        direction={sortField === "detail" ? sortDirection : "asc"}
                        onClick={() => handleSort("detail")}
                      >
                        Detail
                      </TableSortLabel>
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pagedRows.length ? (
                    pagedRows.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>{item.subject}</TableCell>
                        <TableCell>{item.reviewStatus}</TableCell>
                        <TableCell>{item.source}</TableCell>
                        <TableCell>{item.decision}</TableCell>
                        <TableCell>{item.detail}</TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={5}>No review items match the current search.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </Stack>
            <TablePagination
              component="div"
              count={filteredRows.length}
              page={page}
              onPageChange={(_, nextPage) => setPage(nextPage)}
              rowsPerPage={rowsPerPage}
              rowsPerPageOptions={[10]}
            />
          </Paper>
        </Stack>
      )}
    </OutletPage>
  );
}
