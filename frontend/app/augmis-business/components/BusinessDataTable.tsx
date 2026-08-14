"use client";

import type { ReactNode } from "react";

import {
  Alert,
  Box,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  Typography,
} from "@mui/material";

import {
  AdminTableCard,
  ADMIN_TABLE_CARD_PAGINATION_SX,
} from "@/components/data-display/AdminTableCard";

export type BusinessDataTableColumn<RowType> = {
  key: string;
  label: string;
  render: (row: RowType) => ReactNode;
  sortable?: boolean;
  align?: "left" | "right" | "center";
  width?: number | string;
  sx?: Record<string, unknown>;
  cellSx?: Record<string, unknown>;
  headerSx?: Record<string, unknown>;
};

export const BUSINESS_TABLE_SINGLE_LINE_TEXT_SX = {
  display: "block",
  minWidth: 0,
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
} as const;

export const BUSINESS_TABLE_COMPACT_SX = {
  "& .MuiTableCell-root": {
    borderColor: "#D8E1EE",
  },
  "& .MuiTableHead-root .MuiTableCell-root": {
    py: 0.95,
    color: "#334155",
    fontSize: 12.5,
    fontWeight: 700,
    whiteSpace: "nowrap",
    verticalAlign: "middle",
  },
  "& .MuiTableBody-root .MuiTableCell-root": {
    py: 0.82,
    verticalAlign: "middle",
    borderColor: "#E2E8F0",
  },
} as const;

export default function BusinessDataTable<RowType extends { id?: string }>({
  title,
  subtitle,
  icon,
  count,
  headerActions,
  columns,
  rows,
  loading = false,
  error,
  emptyTitle = "No rows found",
  emptyDescription = "No data matches the current filters.",
  emptyContent,
  sortBy,
  sortOrder = "asc",
  onSortChange,
  page,
  pageSize,
  total,
  rowsPerPageOptions = [10, 25, 50, 100],
  onPageChange,
  onRowsPerPageChange,
  rowKey,
  selectedRowKey,
  onRowClick,
  minWidth = 1080,
  tableLayout = "auto",
  getRowSx,
}: {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  count?: string | number;
  headerActions?: ReactNode;
  columns: BusinessDataTableColumn<RowType>[];
  rows: RowType[];
  loading?: boolean;
  error?: string | null;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyContent?: ReactNode;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  onSortChange?: (sortBy: string, sortOrder: "asc" | "desc") => void;
  page?: number;
  pageSize?: number;
  total?: number;
  rowsPerPageOptions?: number[];
  onPageChange?: (page: number) => void;
  onRowsPerPageChange?: (pageSize: number) => void;
  rowKey?: (row: RowType, index: number) => string;
  selectedRowKey?: string | null;
  onRowClick?: (row: RowType) => void;
  minWidth?: number;
  tableLayout?: "auto" | "fixed";
  getRowSx?: (row: RowType, index: number) => Record<string, unknown> | undefined;
}) {
  return (
    <AdminTableCard
      title={
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          {icon ? <Box sx={{ display: "flex", color: "inherit" }}>{icon}</Box> : null}
          <Box sx={{ minWidth: 0 }}>
            <Stack direction="row" spacing={0.8} sx={{ alignItems: "center", flexWrap: "wrap" }}>
              <Box component="span">{title}</Box>
            </Stack>
          </Box>
        </Stack>
      }
      description={subtitle}
      accentLabel={count == null ? undefined : String(count)}
      headerActions={headerActions}
      bodySx={{ bgcolor: "#FFFFFF" }}
      paperSx={{ bgcolor: "#FFFFFF" }}
    >
      {loading ? (
        <Stack sx={{ minHeight: 260, alignItems: "center", justifyContent: "center" }} spacing={1.25}>
          <CircularProgress size={28} />
          <Typography sx={{ color: "#475569" }}>Loading data...</Typography>
        </Stack>
      ) : error ? (
        <Box sx={{ p: 2 }}>
          <Alert severity="error">{error}</Alert>
        </Box>
      ) : rows.length ? (
        <>
          <Box sx={{ overflowX: "auto" }}>
            <Table
              size="small"
              sx={{
                tableLayout,
                minWidth,
                ...BUSINESS_TABLE_COMPACT_SX,
              }}
            >
              <TableHead>
                <TableRow>
                  {columns.map((column) => (
                    <TableCell
                      key={column.key}
                      align={column.align}
                      sx={{
                        width: column.width,
                        ...column.sx,
                        ...column.headerSx,
                      }}
                    >
                      {column.sortable && onSortChange ? (
                        <TableSortLabel
                          active={sortBy === column.key}
                          direction={sortBy === column.key ? sortOrder : "asc"}
                          onClick={() =>
                            onSortChange(
                              column.key,
                              sortBy === column.key && sortOrder === "asc" ? "desc" : "asc"
                            )
                          }
                        >
                          {column.label}
                        </TableSortLabel>
                      ) : (
                        column.label
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row, index) => {
                  const key = rowKey ? rowKey(row, index) : row.id || String(index);
                  const selected = Boolean(selectedRowKey && selectedRowKey === key);
                  return (
                    <TableRow
                      key={key}
                      hover
                      selected={selected}
                      onClick={onRowClick ? () => onRowClick(row) : undefined}
                      sx={{
                        ...(onRowClick ? { cursor: "pointer" } : {}),
                        ...getRowSx?.(row, index),
                      }}
                    >
                      {columns.map((column) => (
                        <TableCell key={column.key} align={column.align} sx={column.cellSx}>
                          {column.render(row)}
                        </TableCell>
                      ))}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Box>
          {typeof page === "number" &&
          typeof pageSize === "number" &&
          typeof total === "number" &&
          onPageChange &&
          onRowsPerPageChange ? (
            <TablePagination
              component="div"
              count={total}
              page={page}
              rowsPerPage={pageSize}
              onPageChange={(_, nextPage) => onPageChange(nextPage)}
              onRowsPerPageChange={(event) => onRowsPerPageChange(Number(event.target.value))}
              rowsPerPageOptions={rowsPerPageOptions}
              sx={ADMIN_TABLE_CARD_PAGINATION_SX}
            />
          ) : null}
        </>
      ) : emptyContent ? (
        emptyContent
      ) : (
        <Box sx={{ p: 2.25 }}>
          <Box sx={{ p: 2.4, borderRadius: "8px", border: "1px dashed #CBD5E1", bgcolor: "#F8FAFC" }}>
            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{emptyTitle}</Typography>
            <Typography sx={{ mt: 0.7, color: "#475569" }}>{emptyDescription}</Typography>
          </Box>
        </Box>
      )}
    </AdminTableCard>
  );
}
