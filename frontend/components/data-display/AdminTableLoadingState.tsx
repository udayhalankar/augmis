"use client";

import { Box, Skeleton, Stack } from "@mui/material";

type AdminTableLoadingStateProps = {
  columnCount?: number;
  rowCount?: number;
  showCountLabel?: boolean;
};

export function AdminTableLoadingState({
  columnCount = 5,
  rowCount = 8,
  showCountLabel = true,
}: AdminTableLoadingStateProps) {
  return (
    <Stack spacing={2}>
      {showCountLabel ? <Skeleton variant="text" width={168} height={22} /> : null}
      <Stack spacing={0} sx={{ width: "100%" }}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: `repeat(${columnCount}, minmax(0, 1fr))`,
            gap: 0,
            px: 2,
            py: 1.1,
            borderBottom: "1px solid #D8E1EE",
            backgroundColor: "#F7FAFC",
          }}
        >
          {Array.from({ length: columnCount }).map((_, index) => (
            <Skeleton key={`header-${index}`} variant="text" width="72%" height={20} />
          ))}
        </Box>

        {Array.from({ length: rowCount }).map((_, rowIndex) => (
          <Box
            key={`row-${rowIndex}`}
            sx={{
              display: "grid",
              gridTemplateColumns: `repeat(${columnCount}, minmax(0, 1fr))`,
              gap: 0,
              px: 2,
              py: 1.15,
              borderBottom: "1px solid #D8E1EE",
              backgroundColor: "#F6FAFF",
            }}
          >
            {Array.from({ length: columnCount }).map((__, columnIndex) => (
              <Skeleton
                key={`cell-${rowIndex}-${columnIndex}`}
                variant="text"
                width={columnIndex === columnCount - 1 ? "58%" : "78%"}
                height={20}
              />
            ))}
          </Box>
        ))}
      </Stack>
    </Stack>
  );
}
