"use client";

import { Paper, Stack, Typography } from "@mui/material";

import { OutletPage } from "@/components/layout/OutletPage";

export default function SyntheticEmployeesSafetyPage() {
  return (
    <OutletPage
      title="Synthetic Employees Safety"
      description="Placeholder page for future estimation workflows."
    >
      <Paper variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
        <Stack spacing={1}>
          <Typography variant="h6" fontWeight={700}>
            Safety
          </Typography>
          <Typography variant="body2" color="text.secondary">
            This module is reserved for future scope.
          </Typography>
        </Stack>
      </Paper>
    </OutletPage>
  );
}
