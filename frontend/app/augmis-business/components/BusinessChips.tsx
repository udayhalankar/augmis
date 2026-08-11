"use client";

import { Chip } from "@mui/material";

function normalizeLabel(value?: string | null, fallback = "Not available") {
  const normalized = String(value || "").trim();
  return normalized ? normalized.replaceAll("_", " ") : fallback;
}

function sourceChipStyle(label: string, sourceType?: string | null, providerKey?: string | null) {
  let sx = { bgcolor: "#F8FAFC", color: "#475569", borderColor: "#E2E8F0" };
  const normalizedLabel = String(label || "").trim().toLowerCase();
  const normalizedProvider = String(providerKey || "").trim().toLowerCase();
  if (
    normalizedProvider === "augmis_internal" ||
    normalizedLabel === "augmis web" ||
    normalizedLabel === "augmis independent web discovery"
  ) {
    return { bgcolor: "#EEF2FF", color: "#3730A3", borderColor: "#C7D2FE" };
  }
  if (normalizedProvider === "ted" || normalizedLabel === "ted") {
    return { bgcolor: "#ECFEFF", color: "#0F766E", borderColor: "#99F6E4" };
  }
  switch ((sourceType || "").toLowerCase()) {
    case "marketplace_project":
      sx = { bgcolor: "#F5F3FF", color: "#6D28D9", borderColor: "#DDD6FE" };
      break;
    case "employment_contract":
      sx = { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
      break;
    case "web_search":
      sx = { bgcolor: "#FEF3C7", color: "#B45309", borderColor: "#FCD34D" };
      break;
    case "manual":
      sx = { bgcolor: "#EEF2FF", color: "#4338CA", borderColor: "#C7D2FE" };
      break;
    case "fixture":
      sx = { bgcolor: "#FFF7ED", color: "#C2410C", borderColor: "#FED7AA" };
      break;
    case "marketplace_project":
      sx = { bgcolor: "#F5F3FF", color: "#6D28D9", borderColor: "#DDD6FE" };
      break;
  }
  return sx;
}

export function BusinessSourceChip({
  label,
  sourceType,
  providerKey,
}: {
  label: string;
  sourceType?: string | null;
  providerKey?: string | null;
}) {
  return <Chip size="small" label={label} sx={{ border: "1px solid", fontWeight: 700, ...sourceChipStyle(label, sourceType, providerKey) }} />;
}

export function BusinessRecommendationChip({ value }: { value?: string | null }) {
  let sx = { bgcolor: "#FFFBEB", color: "#B45309", borderColor: "#FDE68A" };
  if ((value || "").toLowerCase() === "pursue") {
    sx = { bgcolor: "#DCFCE7", color: "#166534", borderColor: "#86EFAC" };
  } else if ((value || "").toLowerCase() === "skip") {
    sx = { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECACA" };
  } else if ((value || "").toLowerCase() === "review") {
    sx = { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
  } else if ((value || "").toLowerCase() === "partner_required") {
    sx = { bgcolor: "#FFF7ED", color: "#C2410C", borderColor: "#FED7AA" };
  } else if ((value || "").toLowerCase() === "low_priority") {
    sx = { bgcolor: "#F8FAFC", color: "#475569", borderColor: "#CBD5E1" };
  }
  return (
    <Chip
      size="small"
      label={normalizeLabel(value, "watch").toUpperCase()}
      sx={{ border: "1px solid", textTransform: "uppercase", fontWeight: 700, ...sx }}
    />
  );
}

export function BusinessPriorityChip({
  band,
  score,
}: {
  band?: string | null;
  score?: number | null;
}) {
  let sx = { bgcolor: "#F8FAFC", color: "#475569", borderColor: "#E2E8F0" };
  switch ((band || "").toUpperCase()) {
    case "A":
      sx = { bgcolor: "#DBEAFE", color: "#1D4ED8", borderColor: "#93C5FD" };
      break;
    case "B":
      sx = { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
      break;
    case "C":
      sx = { bgcolor: "#FFFBEB", color: "#B45309", borderColor: "#FDE68A" };
      break;
    case "D":
      sx = { bgcolor: "#FFF7ED", color: "#C2410C", borderColor: "#FED7AA" };
      break;
  }
  return (
    <Chip
      size="small"
      label={score == null ? `Priority ${band || "?"}` : `Priority ${band || "?"} · ${Math.round(score)}`}
      sx={{ border: "1px solid", fontWeight: 700, ...sx }}
    />
  );
}

export function BusinessRelevanceChip({ value }: { value?: string | null }) {
  let sx = { bgcolor: "#F8FAFC", color: "#475569", borderColor: "#E2E8F0" };
  switch ((value || "").toLowerCase()) {
    case "strong":
      sx = { bgcolor: "#DCFCE7", color: "#166534", borderColor: "#86EFAC" };
      break;
    case "good":
      sx = { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
      break;
    case "possible":
      sx = { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
      break;
    case "moderate":
      sx = { bgcolor: "#F0FDFA", color: "#0F766E", borderColor: "#99F6E4" };
      break;
    case "weak":
      sx = { bgcolor: "#FFF7ED", color: "#B45309", borderColor: "#FED7AA" };
      break;
    case "low":
      sx = { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
      break;
  }
  return <Chip size="small" label={normalizeLabel(value, "Unknown")} sx={{ border: "1px solid", textTransform: "capitalize", ...sx }} />;
}

export function BusinessStatusChip({ value }: { value: string }) {
  let sx = { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
  switch ((value || "").toLowerCase()) {
    case "new":
    case "received":
      sx = { bgcolor: "#FFFBEB", color: "#B45309", borderColor: "#FDE68A" };
      break;
    case "qualified":
    case "under_review":
    case "proposal":
    case "negotiation":
    case "action_required":
    case "in_progress":
      sx = { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
      break;
    case "shortlisted":
    case "completed":
    case "closed_won":
    case "won":
      sx = { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
      break;
    case "imported":
    case "active":
    case "converted":
      sx = { bgcolor: "#EEF2FF", color: "#4338CA", borderColor: "#C7D2FE" };
      break;
    case "rejected":
    case "closed_lost":
    case "expired":
    case "dismissed":
    case "lost":
    case "archived":
    case "error":
    case "failed":
    case "cancelled":
      sx = { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECACA" };
      break;
    case "duplicate":
    case "pending_review":
    case "watch":
      sx = { bgcolor: "#FFF7ED", color: "#B45309", borderColor: "#FED7AA" };
      break;
    case "ready":
    case "enabled":
      sx = { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
      break;
    case "disabled":
    case "inactive":
      sx = { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
      break;
  }
  return <Chip size="small" label={normalizeLabel(value)} sx={{ border: "1px solid", textTransform: "capitalize", ...sx }} />;
}
