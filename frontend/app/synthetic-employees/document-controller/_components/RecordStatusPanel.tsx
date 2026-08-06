"use client";

import { Paper, Stack, Typography } from "@mui/material";

export function RecordStatusPanel({
  items,
}: {
  items: Array<{ label: string; value: string }>;
}) {
  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
      <Stack spacing={1.5}>
        <Typography variant="h6" fontWeight={700}>
          Record Status
        </Typography>
        {items.map((item) => (
          <Stack key={item.label} direction="row" spacing={2} sx={{ justifyContent: "space-between" }}>
            <Typography variant="body2" color="text.secondary">
              {item.label}
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {item.value}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Paper>
  );
}
