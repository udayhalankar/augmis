"use client";

import { useEffect, useState } from "react";

import {
  Box,
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
import { getDocumentControllerApprovals } from "@/services/symployeeService";

type ApprovalItem = {
  approval_id: string;
  approval_subject_type?: string | null;
  decision?: string | null;
  approver_name?: string | null;
  approver_user_id?: string | null;
  comments?: string | null;
};

type SortField =
  | "approval_subject_type"
  | "decision"
  | "approver"
  | "comments";

export default function DocumentControllerApprovalsPage() {
  const [items, setItems] = useState<ApprovalItem[] | null>(null);
  const [searchValue, setSearchValue] = useState("");
  const [page, setPage] = useState(0);
  const [sortField, setSortField] = useState<SortField>("approval_subject_type");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  useEffect(() => {
    getDocumentControllerApprovals().then((result) => {
      setItems(result?.data?.items || []);
    });
  }, []);

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }

    setSortField(field);
    setSortDirection("asc");
  }

  const filteredItems = (items || []).filter((item) => {
    const query = searchValue.trim().toLowerCase();
    if (!query) return true;

    return [
      item.approval_subject_type,
      item.decision,
      item.approver_name || item.approver_user_id,
      item.comments,
    ]
      .join(" ")
      .toLowerCase()
      .includes(query);
  });

  const sortedItems = [...filteredItems].sort((left, right) => {
    const getValue = (item: ApprovalItem) => {
      if (sortField === "approver") {
        return String(item.approver_name || item.approver_user_id || "").toLowerCase();
      }

      return String(item[sortField] ?? "").toLowerCase();
    };

    const leftValue = getValue(left);
    const rightValue = getValue(right);

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
      title="Approvals Console"
      description="Audit-facing view of recommendation and action approvals."
    >
      {!items ? (
        <CircularProgress />
      ) : (
        <Stack spacing={2}>
          <Typography color="text.secondary">{filteredItems.length} approvals</Typography>
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
                  Approvals Table
                </Typography>
                <TextField
                  size="small"
                  placeholder="Search approvals"
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
                    <TableCell sortDirection={sortField === "approval_subject_type" ? sortDirection : false}>
                      <TableSortLabel
                        active={sortField === "approval_subject_type"}
                        direction={sortField === "approval_subject_type" ? sortDirection : "asc"}
                        onClick={() => handleSort("approval_subject_type")}
                      >
                        Subject Type
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
                    <TableCell sortDirection={sortField === "approver" ? sortDirection : false}>
                      <TableSortLabel
                        active={sortField === "approver"}
                        direction={sortField === "approver" ? sortDirection : "asc"}
                        onClick={() => handleSort("approver")}
                      >
                        Approver
                      </TableSortLabel>
                    </TableCell>
                    <TableCell sortDirection={sortField === "comments" ? sortDirection : false}>
                      <TableSortLabel
                        active={sortField === "comments"}
                        direction={sortField === "comments" ? sortDirection : "asc"}
                        onClick={() => handleSort("comments")}
                      >
                        Comments
                      </TableSortLabel>
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pagedItems.length ? (
                    pagedItems.map((item) => (
                      <TableRow key={item.approval_id}>
                        <TableCell>{item.approval_subject_type}</TableCell>
                        <TableCell>{item.decision}</TableCell>
                        <TableCell>{item.approver_name || item.approver_user_id}</TableCell>
                        <TableCell>{item.comments || "-"}</TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={4}>No approvals match the current search.</TableCell>
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
