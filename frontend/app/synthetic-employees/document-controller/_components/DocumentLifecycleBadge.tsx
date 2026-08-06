"use client";

import { Chip } from "@mui/material";

const COLOR_MAP: Record<string, "default" | "primary" | "success" | "warning" | "error" | "info"> = {
  PLANNED: "default",
  DRAFT: "default",
  REGISTERED: "info",
  UNDER_REVIEW: "warning",
  APPROVED: "success",
  ISSUED: "primary",
  ACTIVE: "success",
  SUPERSEDED: "warning",
  WITHDRAWN: "error",
  INACTIVE: "default",
  ARCHIVED: "info",
  DISPOSED: "default",
};

export function DocumentLifecycleBadge({
  stage,
}: {
  stage?: string | null;
}) {
  const normalized = String(stage || "UNSET").toUpperCase();

  return (
    <Chip
      size="small"
      variant="outlined"
      label={normalized}
      color={COLOR_MAP[normalized] || "default"}
    />
  );
}
