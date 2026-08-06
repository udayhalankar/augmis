"use client";

import { Paper, Stack, Typography } from "@mui/material";

type LifecycleEvent = {
  id: string;
  title: string;
  detail?: string;
};

export function LifecycleEventTimeline({
  events,
}: {
  events: LifecycleEvent[];
}) {
  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
      <Stack spacing={1.5}>
        <Typography variant="h6" fontWeight={700}>
          Lifecycle Event Timeline
        </Typography>
        {events.length ? (
          events.map((event) => (
            <Paper key={event.id} variant="outlined" sx={{ p: 1.5, borderRadius: 1.5 }}>
              <Stack spacing={0.5}>
                <Typography variant="body2" fontWeight={600}>
                  {event.title}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {event.detail || "Placeholder lifecycle event detail"}
                </Typography>
              </Stack>
            </Paper>
          ))
        ) : (
          <Typography variant="body2" color="text.secondary">
            No lifecycle events available yet.
          </Typography>
        )}
      </Stack>
    </Paper>
  );
}
