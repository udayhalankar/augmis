"use client";

import { useEffect, useState, useTransition } from "react";

import {
  Alert,
  Box,
  Button,
  CircularProgress,
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
  approveDocumentControllerRecommendation,
  getDocumentControllerRecommendations,
  rejectDocumentControllerRecommendation,
} from "@/services/symployeeService";

type RecommendationItem = {
  recommendation_id: string;
  recommendation_type?: string | null;
  status?: string | null;
  confidence_score?: number | null;
  model_name?: string | null;
};

type SortField =
  | "recommendation_type"
  | "status"
  | "confidence_score"
  | "model_name";

export default function DocumentControllerRecommendationsPage() {
  const [items, setItems] = useState<RecommendationItem[]>([]);
  const [message, setMessage] = useState<string>("");
  const [isPending, startTransition] = useTransition();
  const [loading, setLoading] = useState(true);
  const [searchValue, setSearchValue] = useState("");
  const [page, setPage] = useState(0);
  const [sortField, setSortField] = useState<SortField>("recommendation_type");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  function load() {
    getDocumentControllerRecommendations().then((result) => {
      setItems(result?.data?.items || []);
      setLoading(false);
    });
  }

  useEffect(() => {
    load();
  }, []);

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }

    setSortField(field);
    setSortDirection("asc");
  }

  const query = searchValue.trim().toLowerCase();
  const filteredItems = items.filter((item) => {
    if (!query) return true;

    return [
      item.recommendation_type,
      item.status,
      String(item.confidence_score ?? ""),
      item.model_name,
    ]
      .join(" ")
      .toLowerCase()
      .includes(query);
  });

  const sortedItems = [...filteredItems].sort((left, right) => {
    const leftValue =
      sortField === "confidence_score"
        ? Number(left[sortField] ?? 0)
        : String(left[sortField] ?? "").toLowerCase();
    const rightValue =
      sortField === "confidence_score"
        ? Number(right[sortField] ?? 0)
        : String(right[sortField] ?? "").toLowerCase();

    if (leftValue < rightValue) {
      return sortDirection === "asc" ? -1 : 1;
    }
    if (leftValue > rightValue) {
      return sortDirection === "asc" ? 1 : -1;
    }
    return 0;
  });

  const rowsPerPage = 10;
  const pagedItems = sortedItems.slice(page * rowsPerPage, (page + 1) * rowsPerPage);

  return (
    <OutletPage
      title="Recommendations Queue"
      description="Separate queue for Symployee recommendations. Approval here does not double as connector action approval."
    >
      {loading ? (
        <CircularProgress />
      ) : (
        <Stack spacing={2}>
          {message ? <Alert severity="success">{message}</Alert> : null}
          <Typography color="text.secondary">
            {filteredItems.length} recommendations
          </Typography>
          <Paper variant="outlined" sx={{ borderRadius: 2, overflow: "hidden" }}>
            <Stack spacing={2} sx={{ p: 2 }}>
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
                  Recommendations Table
                </Typography>
                <TextField
                  size="small"
                  placeholder="Search recommendations"
                  value={searchValue}
                  onChange={(event) => {
                    setSearchValue(event.target.value);
                    setPage(0);
                  }}
                  sx={{ width: { xs: "100%", sm: 300 } }}
                />
              </Box>

              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sortDirection={sortField === "recommendation_type" ? sortDirection : false}>
                      <TableSortLabel
                        active={sortField === "recommendation_type"}
                        direction={sortField === "recommendation_type" ? sortDirection : "asc"}
                        onClick={() => handleSort("recommendation_type")}
                      >
                        Type
                      </TableSortLabel>
                    </TableCell>
                    <TableCell sortDirection={sortField === "status" ? sortDirection : false}>
                      <TableSortLabel
                        active={sortField === "status"}
                        direction={sortField === "status" ? sortDirection : "asc"}
                        onClick={() => handleSort("status")}
                      >
                        Status
                      </TableSortLabel>
                    </TableCell>
                    <TableCell sortDirection={sortField === "confidence_score" ? sortDirection : false}>
                      <TableSortLabel
                        active={sortField === "confidence_score"}
                        direction={sortField === "confidence_score" ? sortDirection : "asc"}
                        onClick={() => handleSort("confidence_score")}
                      >
                        Confidence
                      </TableSortLabel>
                    </TableCell>
                    <TableCell sortDirection={sortField === "model_name" ? sortDirection : false}>
                      <TableSortLabel
                        active={sortField === "model_name"}
                        direction={sortField === "model_name" ? sortDirection : "asc"}
                        onClick={() => handleSort("model_name")}
                      >
                        Model
                      </TableSortLabel>
                    </TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pagedItems.length ? (
                    pagedItems.map((item) => (
                      <TableRow key={item.recommendation_id}>
                        <TableCell>{item.recommendation_type}</TableCell>
                        <TableCell>{item.status}</TableCell>
                        <TableCell>{item.confidence_score ?? "-"}</TableCell>
                        <TableCell>{item.model_name || "-"}</TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={1}>
                            <Button
                              size="small"
                              variant="contained"
                              disabled={isPending || item.status !== "NEEDS_REVIEW"}
                              onClick={() =>
                                startTransition(async () => {
                                  const result = await approveDocumentControllerRecommendation(item.recommendation_id, {
                                    comments: "Approved from Symployee UI",
                                  });
                                  const commandId = result?.data?.command?.command_id;
                                  setMessage(
                                    commandId
                                      ? `Recommendation approved. Draft connector action ${commandId} created.`
                                      : "Recommendation approved."
                                  );
                                  load();
                                })
                              }
                            >
                              Approve
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              color="error"
                              disabled={isPending || item.status !== "NEEDS_REVIEW"}
                              onClick={() =>
                                startTransition(async () => {
                                  await rejectDocumentControllerRecommendation(item.recommendation_id, {
                                    comments: "Rejected from Symployee UI",
                                  });
                                  setMessage("Recommendation rejected.");
                                  load();
                                })
                              }
                            >
                              Reject
                            </Button>
                          </Stack>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={5}>No recommendations match the current search.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </Stack>

            <TablePagination
              component="div"
              count={filteredItems.length}
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
