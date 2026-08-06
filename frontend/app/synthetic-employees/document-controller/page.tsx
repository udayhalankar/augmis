"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { AdminTableCard } from "@/components/data-display/AdminTableCard";
import {
  Box,
  CircularProgress,
  Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  TextField,
} from "@mui/material";

import { OperationalReadinessCardsGrid } from "./_components/OperationalReadinessCardsGrid";
import { OperationalSummaryTiles } from "./_components/OperationalSummaryTiles";
import { useDocumentControllerOperationalData } from "./_components/useDocumentControllerOperationalData";
import { OutletPage } from "@/components/layout/OutletPage";

function BreakdownTable({
  title,
  rows,
}: {
  title: string;
  rows: Array<{ label: string; count: number }>;
}) {
  return (
    <AdminTableCard
      title={title}
      paperSx={{ height: "100%" }}
    >
      <Stack spacing={1}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Label</TableCell>
              <TableCell align="right">Count</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length ? (
              rows.map((row) => (
                <TableRow key={`${title}-${row.label}`}>
                  <TableCell>{row.label}</TableCell>
                  <TableCell align="right">{row.count}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={2}>No data</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Stack>
    </AdminTableCard>
  );
}

type RecentActivityRow = {
  identity_id?: string | number;
  title?: string | null;
  repository_name?: string | null;
  status?: string | null;
  last_seen_at?: string | null;
  modified_at?: string | null;
};

type RecentActivitySortField = "title" | "repository_name" | "status" | "last_seen_at";

function RecentRegisterActivityCard({
  rows,
}: {
  rows: RecentActivityRow[];
}) {
  const [searchValue, setSearchValue] = useState("");
  const [page, setPage] = useState(0);
  const [sortField, setSortField] = useState<RecentActivitySortField>("last_seen_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const rowsPerPage = 10;

  const filteredRows = useMemo(() => {
    const query = searchValue.trim().toLowerCase();

    if (!query) {
      return rows;
    }

    return rows.filter((row) =>
      [
        row.title,
        row.repository_name,
        row.status,
        row.last_seen_at || row.modified_at,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query)),
    );
  }, [rows, searchValue]);

  const sortedRows = useMemo(() => {
    const resolveValue = (row: RecentActivityRow) => {
      if (sortField === "last_seen_at") {
        return row.last_seen_at || row.modified_at || "";
      }

      return row[sortField] || "";
    };

    return [...filteredRows].sort((left, right) => {
      const leftValue = String(resolveValue(left)).toLowerCase();
      const rightValue = String(resolveValue(right)).toLowerCase();

      if (leftValue < rightValue) {
        return sortDirection === "asc" ? -1 : 1;
      }

      if (leftValue > rightValue) {
        return sortDirection === "asc" ? 1 : -1;
      }

      return 0;
    });
  }, [filteredRows, sortDirection, sortField]);

  const pagedRows = useMemo(
    () => sortedRows.slice(page * rowsPerPage, (page + 1) * rowsPerPage),
    [page, sortedRows],
  );

  const handleSort = (field: RecentActivitySortField) => {
    setPage(0);
    if (sortField === field) {
      setSortDirection((value) => (value === "asc" ? "desc" : "asc"));
      return;
    }

    setSortField(field);
    setSortDirection(field === "last_seen_at" ? "desc" : "asc");
  };

  return (
    <AdminTableCard
      title="Recent Register Activity"
      actions={
        <TextField
          placeholder="Search recent activity"
          value={searchValue}
          onChange={(event) => {
            setSearchValue(event.target.value);
            setPage(0);
          }}
          size="small"
          sx={{ minWidth: { xs: "100%", sm: 260 } }}
        />
      }
    >
      <Stack spacing={1}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sortDirection={sortField === "title" ? sortDirection : false}>
                <TableSortLabel
                  active={sortField === "title"}
                  direction={sortField === "title" ? sortDirection : "asc"}
                  onClick={() => handleSort("title")}
                >
                  Document
                </TableSortLabel>
              </TableCell>
              <TableCell sortDirection={sortField === "repository_name" ? sortDirection : false}>
                <TableSortLabel
                  active={sortField === "repository_name"}
                  direction={sortField === "repository_name" ? sortDirection : "asc"}
                  onClick={() => handleSort("repository_name")}
                >
                  Repository
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
              <TableCell sortDirection={sortField === "last_seen_at" ? sortDirection : false}>
                <TableSortLabel
                  active={sortField === "last_seen_at"}
                  direction={sortField === "last_seen_at" ? sortDirection : "desc"}
                  onClick={() => handleSort("last_seen_at")}
                >
                  Last Seen
                </TableSortLabel>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {pagedRows.length ? (
              pagedRows.map((row, index) => (
                <TableRow key={String(row.identity_id || `${row.title || "row"}-${index}`)}>
                  <TableCell>{row.title || "-"}</TableCell>
                  <TableCell>{row.repository_name || "-"}</TableCell>
                  <TableCell>{row.status || "-"}</TableCell>
                  <TableCell>{row.last_seen_at || row.modified_at || "-"}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={4}>
                  {rows.length ? "No recent activity matches the current search." : "No recent activity"}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        <TablePagination
          component="div"
          count={sortedRows.length}
          page={page}
          onPageChange={(_, nextPage) => setPage(nextPage)}
          rowsPerPage={rowsPerPage}
          rowsPerPageOptions={[10]}
          onRowsPerPageChange={() => {}}
        />
      </Stack>
    </AdminTableCard>
  );
}

export default function DocumentControllerOverviewPage() {
  const data = useDocumentControllerOperationalData();
  const overview = data?.overview;

  return (
    <OutletPage
      title="Overview"
      description="Operational overview for registers, compliance, and analytics."
    >
      {!overview ? (
        <CircularProgress />
      ) : (
        <Box sx={{ mt: -7 }}>
          <Stack spacing={3} sx={{ pt: 2 }}>
            {data ? <OperationalSummaryTiles tiles={data.summaryTiles} /> : null}

            {data ? <OperationalReadinessCardsGrid sections={data.sections} /> : null}

            <RecentRegisterActivityCard rows={overview.analytics?.recent_activity || []} />

            <Grid container spacing={2}>
              <Grid size={{ xs: 12, lg: 4 }}>
                <BreakdownTable
                  title="By Repository"
                  rows={overview.analytics?.breakdowns?.by_repository || []}
                />
              </Grid>
              <Grid size={{ xs: 12, lg: 4 }}>
                <BreakdownTable
                  title="By Document Type"
                  rows={overview.analytics?.breakdowns?.by_document_type || []}
                />
              </Grid>
              <Grid size={{ xs: 12, lg: 4 }}>
                <BreakdownTable
                  title="Action Status"
                  rows={overview.analytics?.breakdowns?.command_status || []}
                />
              </Grid>
            </Grid>
          </Stack>
        </Box>
      )}
    </OutletPage>
  );
}
