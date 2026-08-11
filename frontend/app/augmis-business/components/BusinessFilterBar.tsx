"use client";

import { Box, Stack } from "@mui/material";

export default function BusinessFilterBar({
  filters,
  actions,
}: {
  filters: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <Box
      sx={{
        p: 1.5,
        borderRadius: "10px",
        border: "1px solid #E2E8F0",
        bgcolor: "#FFFFFF",
      }}
    >
      <Stack
        direction={{ xs: "column", xl: "row" }}
        spacing={1.2}
        sx={{ justifyContent: "space-between", alignItems: { xl: "center" } }}
      >
        <Box sx={{ minWidth: 0, flex: 1 }}>{filters}</Box>
        {actions ? (
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
            {actions}
          </Stack>
        ) : null}
      </Stack>
    </Box>
  );
}
