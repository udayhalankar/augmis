"use client";

import { Chip, Paper, Stack, Typography } from "@mui/material";

import { OutletPage } from "@/components/layout/OutletPage";

export function ModulePlaceholderPage({
  title,
  description,
  scopeItems,
}: {
  title: string;
  description: string;
  scopeItems: string[];
}) {
  return (
    <OutletPage title={title} description={description}>
      <Paper variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
        <Stack spacing={2}>
          <Stack
            direction="row"
            spacing={1}
            useFlexGap
            sx={{ alignItems: "center", flexWrap: "wrap" }}
          >
            <Typography variant="h6" fontWeight={700}>
              Placeholder Page
            </Typography>
            <Chip label="Future module" size="small" variant="outlined" />
          </Stack>

          <Typography variant="body2" color="text.secondary">
            This page is reserved for the dedicated workflow and data model for this area.
          </Typography>

          <Stack spacing={1}>
            {scopeItems.map((item) => (
              <Paper
                key={item}
                variant="outlined"
                sx={{ px: 1.5, py: 1, borderRadius: 1.5 }}
              >
                <Typography variant="body2" fontWeight={500}>
                  {item}
                </Typography>
              </Paper>
            ))}
          </Stack>
        </Stack>
      </Paper>
    </OutletPage>
  );
}
