"use client";

import type { ReactNode } from "react";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
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
  TextField,
} from "@mui/material";

import { AdminStatusCardStrip } from "@/components/data-display/AdminStatusCardStrip";
import { AdminTableCard } from "@/components/data-display/AdminTableCard";
import {
  ADMIN_TOP_MENU_POST_MENU_CONTENT_SX,
  AdminTopMenu,
} from "@/components/data-display/AdminTopMenu";
import { OutletPage } from "@/components/layout/OutletPage";

export type CommunicationsMetricCard = {
  label: string;
  value: number | string;
  caption?: string;
};

export type CommunicationsColumn<RowType> = {
  key: string;
  label: string;
  render: (row: RowType) => ReactNode;
  sortValue?: (row: RowType) => string | number;
  searchableValue?: (row: RowType) => string;
  align?: "left" | "center" | "right";
  disableTruncate?: boolean;
};

type CommunicationsWorkspaceProps<RowType> = {
  activeMenu: string;
  accentLabel: string;
  bodyTopContent?: ReactNode;
  cardDescription: string;
  cardTitle: string;
  columns: CommunicationsColumn<RowType>[];
  countLabel: string;
  emptyMessage: string;
  error?: ReactNode;
  loading?: boolean;
  metrics: CommunicationsMetricCard[];
  pageDescription: string;
  pageTitle: string;
  rows: RowType[];
  searchPlaceholder: string;
};

const TABLE_SX = {
  tableLayout: "fixed",
  "& .MuiTableCell-root": {
    px: 2,
    py: 0.75,
    borderColor: "#D8E1EE",
    verticalAlign: "middle",
  },
  "& .MuiTableHead-root .MuiTableCell-root": {
    py: 0.7,
    fontWeight: 600,
    color: "#243B53",
    whiteSpace: "nowrap",
  },
  "& .MuiTableBody-root .MuiTableRow-root": {
    height: 36,
  },
} as const;

const CELL_CONTENT_SX = {
  display: "block",
  width: "100%",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
  lineHeight: 1.35,
} as const;

const TOP_MENU_ITEMS = [
  { key: "overview", label: "Overview", href: "/synthetic-employees/document-controller/communications" },
  { key: "transmittals", label: "Transmittals", href: "/synthetic-employees/document-controller/transmittals" },
  {
    key: "incoming-transmittals",
    label: "Incoming Transmittals",
    href: "/synthetic-employees/document-controller/communications/incoming-transmittals",
  },
  {
    key: "outgoing-transmittals",
    label: "Outgoing Transmittals",
    href: "/synthetic-employees/document-controller/communications/outgoing-transmittals",
  },
  {
    key: "correspondence",
    label: "Correspondence",
    href: "/synthetic-employees/document-controller/communications/correspondence",
  },
  {
    key: "acknowledgements",
    label: "Acknowledgements",
    href: "/synthetic-employees/document-controller/communications/acknowledgements",
  },
] as const;

function resolveCellTitle<RowType>(column: CommunicationsColumn<RowType>, row: RowType) {
  if (column.searchableValue) {
    return column.searchableValue(row);
  }
  if (column.sortValue) {
    return String(column.sortValue(row));
  }
  const rendered = column.render(row);
  return typeof rendered === "string" || typeof rendered === "number"
    ? String(rendered)
    : undefined;
}

export function CommunicationsWorkspace<RowType>({
  activeMenu,
  accentLabel,
  bodyTopContent,
  cardDescription,
  cardTitle,
  columns,
  countLabel,
  emptyMessage,
  error,
  loading = false,
  metrics,
  pageDescription,
  pageTitle,
  rows,
  searchPlaceholder,
}: CommunicationsWorkspaceProps<RowType>) {
  const router = useRouter();
  const [searchValue, setSearchValue] = useState("");
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState(columns[0]?.key || "");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  useEffect(() => {
    setSearchValue("");
    setPage(0);
    setSortDirection("asc");
    setSortKey(columns[0]?.key || "");
  }, [activeMenu, columns]);

  const filteredRows = useMemo(() => {
    const query = searchValue.trim().toLowerCase();
    if (!query) {
      return rows;
    }

    return rows.filter((row) =>
      columns.some((column) => {
        const source = column.searchableValue
          ? column.searchableValue(row)
          : column.sortValue
            ? column.sortValue(row)
            : column.render(row);
        return String(source || "")
          .toLowerCase()
          .includes(query);
      })
    );
  }, [columns, rows, searchValue]);

  const sortedRows = useMemo(() => {
    const activeColumn = columns.find((column) => column.key === sortKey);
    if (!activeColumn) {
      return filteredRows;
    }

    const resolveValue =
      activeColumn.sortValue || ((row: RowType) => String(activeColumn.render(row)).toLowerCase());

    return [...filteredRows].sort((left, right) => {
      const leftValue = resolveValue(left);
      const rightValue = resolveValue(right);
      const normalizedLeft =
        typeof leftValue === "number" ? leftValue : String(leftValue).toLowerCase();
      const normalizedRight =
        typeof rightValue === "number" ? rightValue : String(rightValue).toLowerCase();

      if (normalizedLeft < normalizedRight) {
        return sortDirection === "asc" ? -1 : 1;
      }
      if (normalizedLeft > normalizedRight) {
        return sortDirection === "asc" ? 1 : -1;
      }
      return 0;
    });
  }, [columns, filteredRows, sortDirection, sortKey]);

  const rowsPerPage = 10;
  const maxPage = Math.max(0, Math.ceil(sortedRows.length / rowsPerPage) - 1);
  const safePage = page > maxPage ? maxPage : page;
  const visibleRows = sortedRows.slice(safePage * rowsPerPage, (safePage + 1) * rowsPerPage);

  return (
    <OutletPage title={pageTitle} description={pageDescription}>
      {loading ? (
        <CircularProgress />
      ) : (
        <Stack spacing={0}>
          <AdminTopMenu
            menuItems={TOP_MENU_ITEMS.map(({ key, label }) => ({ key, label }))}
            value={activeMenu}
            onChange={(value) => {
              const next = TOP_MENU_ITEMS.find((item) => item.key === value);
              if (next) {
                router.push(next.href);
              }
            }}
            fullBleed
            bleedSx={{ mt: -7 }}
          />

          <Stack spacing={3} sx={ADMIN_TOP_MENU_POST_MENU_CONTENT_SX}>
            {error ? error : null}

            {metrics.length ? <AdminStatusCardStrip metrics={metrics} /> : null}

            <AdminTableCard
              title={cardTitle}
              description={cardDescription}
              accentLabel={accentLabel}
              actions={
                <TextField
                  placeholder={searchPlaceholder}
                  value={searchValue}
                  onChange={(event) => {
                    setSearchValue(event.target.value);
                    setPage(0);
                  }}
                  size="small"
                  sx={{
                    minWidth: { xs: "100%", md: 360 },
                    "& .MuiOutlinedInput-root": {
                      borderRadius: "999px",
                      bgcolor: "#FFFFFF",
                    },
                  }}
                />
              }
            >
              {bodyTopContent ? (
                <Box sx={{ px: 3, pt: 2, pb: 1 }}>{bodyTopContent}</Box>
              ) : null}

              <Table size="small" sx={TABLE_SX}>
                <TableHead>
                  <TableRow>
                    {columns.map((column) => {
                      const active = sortKey === column.key;
                      return (
                        <TableCell key={column.key} align={column.align || "left"}>
                          {column.sortValue ? (
                            <TableSortLabel
                              active={active}
                              direction={active ? sortDirection : "asc"}
                              onClick={() => {
                                if (active) {
                                  setSortDirection((value) => (value === "asc" ? "desc" : "asc"));
                                  return;
                                }
                                setSortKey(column.key);
                                setSortDirection("asc");
                              }}
                            >
                              {column.label}
                            </TableSortLabel>
                          ) : (
                            column.label
                          )}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {visibleRows.length ? (
                    visibleRows.map((row, rowIndex) => (
                      <TableRow key={rowIndex}>
                        {columns.map((column) => {
                          const cellValue = column.render(row);
                          const title = resolveCellTitle(column, row) ?? undefined;
                          return (
                            <TableCell
                              key={column.key}
                              align={column.align || "left"}
                              title={title}
                            >
                              {column.disableTruncate ? (
                                cellValue
                              ) : (
                                <Box sx={CELL_CONTENT_SX}>{cellValue}</Box>
                              )}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={columns.length}>{emptyMessage}</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>

              <TablePagination
                component="div"
                count={sortedRows.length}
                page={safePage}
                onPageChange={(_, nextPage) => setPage(nextPage)}
                rowsPerPage={rowsPerPage}
                rowsPerPageOptions={[10]}
                onRowsPerPageChange={() => undefined}
              />
            </AdminTableCard>
          </Stack>
        </Stack>
      )}
    </OutletPage>
  );
}
