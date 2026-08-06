"use client";

import { ReactNode, useEffect, useState } from "react";
import {
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

type Column = {
  key: string;
  label: ReactNode;
  align?: "left" | "center" | "right" | "justify" | "inherit";
};

type ProgressiveDataTableProps<T> = {
  columns: Column[];
  rows: T[];
  renderRow: (row: T, index: number) => ReactNode;
  initialRows?: number;
  step?: number;
  tableSize?: "small" | "medium";
};

export default function ProgressiveDataTable<T>({
  columns,
  rows,
  renderRow,
  initialRows = 40,
  step = 40,
  tableSize = "small",
}: ProgressiveDataTableProps<T>) {
  const [visibleCount, setVisibleCount] = useState(initialRows);

  useEffect(() => {
    setVisibleCount(initialRows);
  }, [rows, initialRows]);

  const visibleRows = rows.slice(0, visibleCount);
  const hasMore = rows.length > visibleCount;
  const remaining = Math.max(rows.length - visibleCount, 0);

  return (
    <>
      <Table size={tableSize}>
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableCell key={column.key} align={column.align}>
                {column.label}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>{visibleRows.map((row, index) => renderRow(row, index))}</TableBody>
      </Table>

      {hasMore ? (
        <Box
          sx={{
            mt: 1.5,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 1.5,
            flexWrap: "wrap",
          }}
        >
          <Typography variant="body2" color="text.secondary">
            Showing {visibleRows.length} of {rows.length} rows
          </Typography>
          <Button
            size="small"
            variant="outlined"
            onClick={() => setVisibleCount((current) => current + step)}
          >
            Load {Math.min(step, remaining)} More
          </Button>
        </Box>
      ) : null}
    </>
  );
}
