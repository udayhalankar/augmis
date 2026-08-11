"use client";

import { useEffect, useMemo, useState } from "react";

import AddCircleRoundedIcon from "@mui/icons-material/AddCircleRounded";
import ApartmentOutlinedIcon from "@mui/icons-material/ApartmentOutlined";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import CalendarMonthOutlinedIcon from "@mui/icons-material/CalendarMonthOutlined";
import DeleteOutline from "@mui/icons-material/DeleteOutlineOutlined";
import EditOutlined from "@mui/icons-material/EditOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import LanguageOutlinedIcon from "@mui/icons-material/LanguageOutlined";
import PublicOutlinedIcon from "@mui/icons-material/PublicOutlined";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import SourceOutlinedIcon from "@mui/icons-material/SourceOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import MarkEmailReadOutlinedIcon from "@mui/icons-material/MarkEmailReadOutlined";
import LightbulbOutlinedIcon from "@mui/icons-material/LightbulbOutlined";
import WorkOutlineOutlinedIcon from "@mui/icons-material/WorkOutlineOutlined";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  InputAdornment,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { useAuth } from "@/context/AuthContext";
import { AppNotificationToast } from "@/components/feedback/AppNotificationToast";
import { AdminFormDialog, AdminFormTextField } from "@/components/forms/AdminFormDialog";
import { parseApiValidationError } from "@/services/apiErrorParser";
import {
  type AugmisBusinessOpportunity,
  type AugmisBusinessOpportunityAIAssessment,
  type AugmisBusinessOpportunityAIAssessmentSummary,
  type AugmisBusinessOpportunityExperienceMatch,
  getAugmisBusinessOpportunityAIAssessment,
  listAugmisBusinessOpportunityAIAssessments,
  createAugmisBusinessOpportunity,
  deleteAugmisBusinessOpportunity,
  getAugmisBusinessHealth,
  getAugmisBusinessOpportunity,
  listAugmisBusinessOpportunities,
  runAugmisBusinessOpportunityAIAssessment,
  updateAugmisBusinessOpportunity,
} from "@/services/augmisBusinessService";
import BuildLeadDialog from "./BuildLeadDialog";
import OutreachWorkspaceDialog from "../components/OutreachWorkspaceDialog";
import MiniSolutionWorkspaceDrawer from "../components/MiniSolutionWorkspaceDrawer";
import BusinessPageFrame from "../components/BusinessPageFrame";
import BusinessFilterBar from "../components/BusinessFilterBar";
import BusinessDataTable, { type BusinessDataTableColumn } from "../components/BusinessDataTable";
import BusinessDetailDrawer from "../components/BusinessDetailDrawer";
import BusinessRowActionMenu from "../components/BusinessRowActionMenu";
import {
  BusinessRecommendationChip,
  BusinessSourceChip,
  BusinessStatusChip,
} from "../components/BusinessChips";
import type { BusinessMetricItem } from "../components/BusinessMetricCarousel";

type OpportunityFormState = {
  title: string;
  organization_name: string;
  source_type: string;
  source_name: string;
  requirement_summary: string;
  opportunity_status: string;
  source_url: string;
  organization_domain: string;
  country: string;
  region: string;
  industry: string;
  published_at: string;
  closing_at: string;
  raw_summary: string;
  business_problem: string;
  expected_deliverables: string;
  required_technologies: string;
  published_budget: string;
  published_currency: string;
  estimated_value_min: string;
  estimated_value_max: string;
  estimated_currency: string;
  fit_score: string;
  confidence_score: string;
  ai_recommendation: string;
};

type ToastSeverity = "success" | "error" | "info" | "warning";

const DEFAULT_FORM_STATE: OpportunityFormState = {
  title: "",
  organization_name: "",
  source_type: "manual",
  source_name: "Manual Entry",
  requirement_summary: "",
  opportunity_status: "new",
  source_url: "",
  organization_domain: "",
  country: "",
  region: "",
  industry: "",
  published_at: "",
  closing_at: "",
  raw_summary: "",
  business_problem: "",
  expected_deliverables: "",
  required_technologies: "",
  published_budget: "",
  published_currency: "",
  estimated_value_min: "",
  estimated_value_max: "",
  estimated_currency: "",
  fit_score: "",
  confidence_score: "",
  ai_recommendation: "",
};
const DOMAIN_PATTERN =
  /^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$/;

function formatDate(value: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatNumber(value: number | null) {
  return value == null ? "Not available" : value.toString();
}

function formatScore(value: number | null | undefined) {
  return typeof value === "number" ? value.toFixed(1) : "Not available";
}

function statusChipColor(status: string) {
  switch (status) {
    case "qualified":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "under_review":
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
    case "dismissed":
    case "expired":
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
    case "converted":
      return { bgcolor: "#F5F3FF", color: "#6D28D9", borderColor: "#DDD6FE" };
    default:
      return { bgcolor: "#FFFAEB", color: "#B54708", borderColor: "#FEDF89" };
  }
}

function recommendationChipColor(recommendation: string | null | undefined) {
  switch (recommendation) {
    case "pursue":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "review":
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
    case "partner_required":
      return { bgcolor: "#FFFAEB", color: "#B54708", borderColor: "#FEDF89" };
    case "reject":
    case "expired":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
    case "low_priority":
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
    case "insufficient_information":
      return { bgcolor: "#EEF2FF", color: "#4338CA", borderColor: "#C7D2FE" };
    default:
      return { bgcolor: "#F8FAFC", color: "#475467", borderColor: "#CBD5E1" };
  }
}

function formatRecommendation(value: string | null | undefined) {
  return value ? value.replaceAll("_", " ") : "Not assessed";
}

function formatDeliveryModel(value: string | null | undefined) {
  if (!value) return "Not available";
  switch (value) {
    case "solo":
      return "Solo";
    case "solo_with_support":
      return "Solo with support";
    case "small_team":
      return "Small team";
    case "partner_required":
      return "Partner required";
    default:
      return value.replaceAll("_", " ");
  }
}

function clampedTextSx(lines = 2) {
  return {
    display: "-webkit-box",
    WebkitBoxOrient: "vertical",
    WebkitLineClamp: lines,
    overflow: "hidden",
    whiteSpace: "normal",
    textOverflow: "ellipsis",
    overflowWrap: "anywhere",
  } as const;
}

function parseCsvList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeOptionalString(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function normalizeOptionalNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function getBackendErrorMessage(error: unknown, fallback: string) {
  return parseApiValidationError(error, fallback).message;
}

function isNotFoundError(error: unknown) {
  const statusCode =
    typeof error === "object" && error && "response" in error
      ? (error as { response?: { status?: number } }).response?.status
      : undefined;
  return statusCode === 404;
}

function toDatetimeLocalValue(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const normalized = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return normalized.toISOString().slice(0, 16);
}

function opportunityToFormState(opportunity: AugmisBusinessOpportunity): OpportunityFormState {
  return {
    title: opportunity.title,
    organization_name: opportunity.organization_name,
    source_type: opportunity.source_type,
    source_name: opportunity.source_name,
    requirement_summary: opportunity.requirement_summary,
    opportunity_status: opportunity.opportunity_status,
    source_url: opportunity.source_url ?? "",
    organization_domain: opportunity.organization_domain ?? "",
    country: opportunity.country ?? "",
    region: opportunity.region ?? "",
    industry: opportunity.industry ?? "",
    published_at: toDatetimeLocalValue(opportunity.published_at),
    closing_at: toDatetimeLocalValue(opportunity.closing_at),
    raw_summary: opportunity.raw_summary ?? "",
    business_problem: opportunity.business_problem ?? "",
    expected_deliverables: (opportunity.expected_deliverables_json || []).join(", "),
    required_technologies: (opportunity.required_technologies_json || []).join(", "),
    published_budget:
      opportunity.published_budget == null ? "" : String(opportunity.published_budget),
    published_currency: opportunity.published_currency ?? "",
    estimated_value_min:
      opportunity.estimated_value_min == null ? "" : String(opportunity.estimated_value_min),
    estimated_value_max:
      opportunity.estimated_value_max == null ? "" : String(opportunity.estimated_value_max),
    estimated_currency: opportunity.estimated_currency ?? "",
    fit_score: opportunity.fit_score == null ? "" : String(opportunity.fit_score),
    confidence_score:
      opportunity.confidence_score == null ? "" : String(opportunity.confidence_score),
    ai_recommendation: opportunity.ai_recommendation ?? "",
  };
}

function formStateToPayload(form: OpportunityFormState) {
  return {
    title: form.title.trim(),
    organization_name: form.organization_name.trim(),
    source_type: form.source_type.trim(),
    source_name: form.source_name.trim(),
    requirement_summary: form.requirement_summary.trim(),
    opportunity_status: form.opportunity_status,
    source_url: normalizeOptionalString(form.source_url),
    organization_domain: normalizeOptionalString(form.organization_domain),
    country: normalizeOptionalString(form.country),
    region: normalizeOptionalString(form.region),
    industry: normalizeOptionalString(form.industry),
    published_at: normalizeOptionalString(form.published_at),
    closing_at: normalizeOptionalString(form.closing_at),
    raw_summary: normalizeOptionalString(form.raw_summary),
    business_problem: normalizeOptionalString(form.business_problem),
    expected_deliverables_json: parseCsvList(form.expected_deliverables),
    required_technologies_json: parseCsvList(form.required_technologies),
    published_budget: normalizeOptionalNumber(form.published_budget),
    published_currency: normalizeOptionalString(form.published_currency),
    estimated_value_min: normalizeOptionalNumber(form.estimated_value_min),
    estimated_value_max: normalizeOptionalNumber(form.estimated_value_max),
    estimated_currency: normalizeOptionalString(form.estimated_currency),
    fit_score: normalizeOptionalNumber(form.fit_score),
    confidence_score: normalizeOptionalNumber(form.confidence_score),
    ai_recommendation: normalizeOptionalString(form.ai_recommendation),
    source_evidence_json: [],
  };
}

function validateOpportunityForm(form: OpportunityFormState) {
  const fieldErrors: Record<string, string> = {};

  if (!form.title.trim()) {
    fieldErrors.title = "Title is required.";
  }
  if (!form.organization_name.trim()) {
    fieldErrors.organization_name = "Organization name is required.";
  }
  if (!form.source_type.trim()) {
    fieldErrors.source_type = "Source type is required.";
  }
  if (!form.source_name.trim()) {
    fieldErrors.source_name = "Source name is required.";
  }
  if (!form.requirement_summary.trim()) {
    fieldErrors.requirement_summary = "Requirement summary is required.";
  }

  const sourceUrl = normalizeOptionalString(form.source_url);
  if (sourceUrl) {
    try {
      const parsed = new URL(sourceUrl);
      if (!["http:", "https:"].includes(parsed.protocol)) {
        fieldErrors.source_url = "Enter a valid URL including http:// or https://.";
      }
    } catch {
      fieldErrors.source_url = "Enter a valid URL including http:// or https://.";
    }
  }

  const organizationDomain = normalizeOptionalString(form.organization_domain);
  if (organizationDomain && !DOMAIN_PATTERN.test(organizationDomain)) {
    fieldErrors.organization_domain =
      "Enter a valid domain using letters, numbers, dots, and hyphens only.";
  }

  return fieldErrors;
}

function DetailField({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        borderRadius: "8px",
        border: "1px solid #E2E8F0",
        minHeight: 86,
      }}
    >
      <Stack direction="row" spacing={1.1} sx={{ alignItems: "flex-start" }}>
        <Box sx={{ mt: 0.1, color: "#2563EB" }}>{icon}</Box>
        <Box sx={{ minWidth: 0 }}>
          <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: ".05em" }}>
            {label}
          </Typography>
          <Typography sx={{ mt: 0.65, color: "#0F172A", wordBreak: "break-word" }}>
            {value}
          </Typography>
        </Box>
      </Stack>
    </Paper>
  );
}

function DetailList({
  title,
  items,
  emptyLabel = "Not available",
}: {
  title: string;
  items: string[];
  emptyLabel?: string;
}) {
  return (
    <Stack spacing={1}>
      <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: ".04em" }}>
        {title}
      </Typography>
      {items.length ? (
        <Stack direction="row" spacing={0.75} sx={{ flexWrap: "wrap" }}>
          {items.map((item) => (
            <Chip
              key={`${title}-${item}`}
              label={item}
              size="small"
              sx={{ bgcolor: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "8px" }}
            />
          ))}
        </Stack>
      ) : (
        <Typography sx={{ color: "#475569" }}>{emptyLabel}</Typography>
      )}
    </Stack>
  );
}

function OpportunityFormFields({
  form,
  onChange,
  fieldErrors,
}: {
  form: OpportunityFormState;
  onChange: <K extends keyof OpportunityFormState>(field: K, value: OpportunityFormState[K]) => void;
  fieldErrors: Record<string, string>;
}) {
  return (
    <Box
      sx={{
        display: "grid",
        gap: 1.15,
        gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
      }}
    >
      <AdminFormTextField label="Title" value={form.title} onChange={(event) => onChange("title", event.target.value)} required error={Boolean(fieldErrors.title)} helperText={fieldErrors.title} />
      <AdminFormTextField
        label="Organization Name"
        value={form.organization_name}
        onChange={(event) => onChange("organization_name", event.target.value)}
        required
        error={Boolean(fieldErrors.organization_name)}
        helperText={fieldErrors.organization_name}
      />
      <AdminFormTextField select label="Source Type" value={form.source_type} onChange={(event) => onChange("source_type", event.target.value)} required error={Boolean(fieldErrors.source_type)} helperText={fieldErrors.source_type}>
        <MenuItem value="manual">Manual</MenuItem>
        <MenuItem value="portal">Portal</MenuItem>
        <MenuItem value="email">Email</MenuItem>
        <MenuItem value="partner">Partner</MenuItem>
        <MenuItem value="referral">Referral</MenuItem>
        <MenuItem value="other">Other</MenuItem>
      </AdminFormTextField>
      <AdminFormTextField label="Source Name" value={form.source_name} onChange={(event) => onChange("source_name", event.target.value)} required error={Boolean(fieldErrors.source_name)} helperText={fieldErrors.source_name} />
      <AdminFormTextField select label="Opportunity Status" value={form.opportunity_status} onChange={(event) => onChange("opportunity_status", event.target.value)} required>
        <MenuItem value="draft">Draft</MenuItem>
        <MenuItem value="new">New</MenuItem>
        <MenuItem value="under_review">Under Review</MenuItem>
        <MenuItem value="qualified">Qualified</MenuItem>
        <MenuItem value="converted">Converted</MenuItem>
        <MenuItem value="dismissed">Dismissed</MenuItem>
        <MenuItem value="expired">Expired</MenuItem>
      </AdminFormTextField>
      <AdminFormTextField label="Source URL" value={form.source_url} onChange={(event) => onChange("source_url", event.target.value)} error={Boolean(fieldErrors.source_url)} helperText={fieldErrors.source_url} />
      <AdminFormTextField
        label="Organization Domain"
        value={form.organization_domain}
        onChange={(event) => onChange("organization_domain", event.target.value)}
        error={Boolean(fieldErrors.organization_domain)}
        helperText={
          fieldErrors.organization_domain ||
          "Use a valid domain such as example.com. Spaces are not allowed."
        }
      />
      <AdminFormTextField label="Country" value={form.country} onChange={(event) => onChange("country", event.target.value)} />
      <AdminFormTextField label="Region" value={form.region} onChange={(event) => onChange("region", event.target.value)} />
      <AdminFormTextField label="Industry" value={form.industry} onChange={(event) => onChange("industry", event.target.value)} />
      <AdminFormTextField
        label="Published Date"
        type="datetime-local"
        value={form.published_at}
        onChange={(event) => onChange("published_at", event.target.value)}
        slotProps={{ inputLabel: { shrink: true } }}
      />
      <AdminFormTextField
        label="Closing Date"
        type="datetime-local"
        value={form.closing_at}
        onChange={(event) => onChange("closing_at", event.target.value)}
        slotProps={{ inputLabel: { shrink: true } }}
      />
      <Box sx={{ gridColumn: "1 / -1" }}>
        <AdminFormTextField
          label="Requirement Summary"
          multiline
          minRows={3}
          value={form.requirement_summary}
          onChange={(event) => onChange("requirement_summary", event.target.value)}
          required
          error={Boolean(fieldErrors.requirement_summary)}
          helperText={fieldErrors.requirement_summary}
        />
      </Box>
      <Box sx={{ gridColumn: "1 / -1" }}>
        <AdminFormTextField
          label="Raw Summary"
          multiline
          minRows={3}
          value={form.raw_summary}
          onChange={(event) => onChange("raw_summary", event.target.value)}
        />
      </Box>
      <Box sx={{ gridColumn: "1 / -1" }}>
        <AdminFormTextField
          label="Business Problem"
          multiline
          minRows={3}
          value={form.business_problem}
          onChange={(event) => onChange("business_problem", event.target.value)}
        />
      </Box>
      <Box sx={{ gridColumn: "1 / -1" }}>
        <AdminFormTextField
          label="Expected Deliverables"
          value={form.expected_deliverables}
          onChange={(event) => onChange("expected_deliverables", event.target.value)}
          helperText="Enter comma-separated values."
        />
      </Box>
      <Box sx={{ gridColumn: "1 / -1" }}>
        <AdminFormTextField
          label="Required Technologies"
          value={form.required_technologies}
          onChange={(event) => onChange("required_technologies", event.target.value)}
          helperText="Enter comma-separated values."
        />
      </Box>
      <AdminFormTextField
        label="Published Budget"
        type="number"
        value={form.published_budget}
        onChange={(event) => onChange("published_budget", event.target.value)}
      />
      <AdminFormTextField
        label="Published Currency"
        value={form.published_currency}
        onChange={(event) => onChange("published_currency", event.target.value)}
      />
      <AdminFormTextField
        label="Estimated Value Minimum"
        type="number"
        value={form.estimated_value_min}
        onChange={(event) => onChange("estimated_value_min", event.target.value)}
      />
      <AdminFormTextField
        label="Estimated Value Maximum"
        type="number"
        value={form.estimated_value_max}
        onChange={(event) => onChange("estimated_value_max", event.target.value)}
      />
      <AdminFormTextField
        label="Estimated Currency"
        value={form.estimated_currency}
        onChange={(event) => onChange("estimated_currency", event.target.value)}
      />
      <AdminFormTextField
        label="Fit Score"
        type="number"
        value={form.fit_score}
        onChange={(event) => onChange("fit_score", event.target.value)}
      />
      <AdminFormTextField
        label="Confidence Score"
        type="number"
        value={form.confidence_score}
        onChange={(event) => onChange("confidence_score", event.target.value)}
      />
      <Box sx={{ gridColumn: "1 / -1" }}>
        <AdminFormTextField
          label="AI Recommendation"
          multiline
          minRows={3}
          value={form.ai_recommendation}
          onChange={(event) => onChange("ai_recommendation", event.target.value)}
        />
      </Box>
    </Box>
  );
}

export default function AugmisBusinessOpportunitiesPage() {
  const { hasPermission } = useAuth();
  const canRead = hasPermission("business_development:read");
  const canUpdate = hasPermission("business_development:update");
  const canDelete = hasPermission("business_development:delete");
  const canQualify = hasPermission("business_development:qualify");
  const canOutreach = hasPermission("business_development:outreach");

  const [items, setItems] = useState<AugmisBusinessOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dialogMode, setDialogMode] = useState<"create" | "edit">("create");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dialogError, setDialogError] = useState("");
  const [dialogFieldErrors, setDialogFieldErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState<OpportunityFormState>(DEFAULT_FORM_STATE);
  const [editingOpportunityId, setEditingOpportunityId] = useState<string | null>(null);
  const [toastOpen, setToastOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastSeverity, setToastSeverity] = useState<ToastSeverity>("success");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState("closing_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [refreshTick, setRefreshTick] = useState(0);
  const [healthSummary, setHealthSummary] = useState<{
    opportunity_count?: number;
    experience_item_count?: number;
  } | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [selectedOpportunity, setSelectedOpportunity] = useState<AugmisBusinessOpportunity | null>(null);
  const [latestAssessment, setLatestAssessment] =
    useState<AugmisBusinessOpportunityAIAssessment | null>(null);
  const [assessmentHistory, setAssessmentHistory] = useState<
    AugmisBusinessOpportunityAIAssessmentSummary[]
  >([]);
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [assessmentError, setAssessmentError] = useState("");
  const [assessDialogOpen, setAssessDialogOpen] = useState(false);
  const [assessmentTarget, setAssessmentTarget] = useState<AugmisBusinessOpportunity | null>(null);
  const [assessmentRunning, setAssessmentRunning] = useState(false);
  const [assessmentRunError, setAssessmentRunError] = useState("");
  const [outreachOpen, setOutreachOpen] = useState(false);
  const [miniSolutionOpen, setMiniSolutionOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteSaving, setDeleteSaving] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<AugmisBusinessOpportunity | null>(null);
  const [buildLeadOpen, setBuildLeadOpen] = useState(false);
  const [buildLeadOpportunity, setBuildLeadOpportunity] =
    useState<AugmisBusinessOpportunity | null>(null);

  useEffect(() => {
    let active = true;

    Promise.all([
      listAugmisBusinessOpportunities({
        page: page + 1,
        page_size: pageSize,
        search: search.trim() || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
      getAugmisBusinessHealth(),
    ])
      .then(([opportunityResult, healthResult]) => {
        if (!active) return;
        setItems(opportunityResult.data || []);
        setTotal(opportunityResult.pagination?.total || 0);
        setHealthSummary(healthResult.data || null);
        setError("");
      })
      .catch((loadError) => {
        if (!active) return;
        setError("Unable to load opportunities from the AUGMIS Business API.");
        console.error(loadError);
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [page, pageSize, refreshTick, search, sortBy, sortOrder, statusFilter]);

  const selectedOpportunityEvidence = useMemo(() => {
    if (!selectedOpportunity?.source_evidence_json?.length) {
      return [];
    }
    return selectedOpportunity.source_evidence_json.map((entry) => JSON.stringify(entry));
  }, [selectedOpportunity]);

  const metrics = useMemo<BusinessMetricItem[]>(
    () => [
      {
        key: "total-opportunities",
        title: "Total Opportunities",
        value: String(healthSummary?.opportunity_count ?? 0),
        subtitle: "Tenant-scoped opportunity records",
        accent: "linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)",
        icon: <ApartmentOutlinedIcon fontSize="small" />,
      },
      {
        key: "experience-catalogue",
        title: "Experience Catalogue",
        value: String(healthSummary?.experience_item_count ?? 0),
        subtitle: "Reusable qualification references",
        accent: "linear-gradient(90deg, #DCFCE7 0%, #F0FDF4 100%)",
        icon: <HubOutlinedIcon fontSize="small" />,
      },
      {
        key: "open-opportunities",
        title: "Open / Active",
        value: String(
          items.filter((item) => ["new", "under_review", "qualified"].includes(item.opportunity_status))
            .length
        ),
        subtitle: "Rows on the current filtered page",
        accent: "linear-gradient(90deg, #FEF3C7 0%, #FFFBEB 100%)",
        icon: <SourceOutlinedIcon fontSize="small" />,
      },
      {
        key: "converted-opportunities",
        title: "Converted",
        value: String(items.filter((item) => item.opportunity_status === "converted").length),
        subtitle: "Already converted to leads",
        accent: "linear-gradient(90deg, #EDE9FE 0%, #F8FAFC 100%)",
        icon: <WorkOutlineOutlinedIcon fontSize="small" />,
      },
      {
        key: "assessed-opportunities",
        title: "AI Assessed",
        value: String(items.filter((item) => item.ai_recommendation || item.fit_score != null).length),
        subtitle: "Assessment data available on the page",
        accent: "linear-gradient(90deg, #D1FAE5 0%, #F0FDFA 100%)",
        icon: <AutoAwesomeOutlinedIcon fontSize="small" />,
      },
    ],
    [healthSummary, items]
  );

  const tableColumns: BusinessDataTableColumn<AugmisBusinessOpportunity>[] = [
      {
        key: "title",
        label: "Opportunity",
        sortable: true,
        width: 360,
        render: (item) => (
          <Box>
            <Button
              variant="text"
              onClick={() => void openDetailDrawer(item)}
              sx={{
                p: 0,
                minWidth: 0,
                justifyContent: "flex-start",
                textTransform: "none",
                fontWeight: 700,
                color: "#0F172A",
                textAlign: "left",
                ...clampedTextSx(2),
                "&:hover": { bgcolor: "transparent", color: "#1D4ED8" },
              }}
            >
              {item.title}
            </Button>
            <Typography sx={{ mt: 0.35, color: "#475569", fontSize: 13, ...clampedTextSx(2) }}>
              {item.requirement_summary}
            </Typography>
            {(item.requirement_summary || "").length > 140 ? (
              <Button
                size="small"
                onClick={() => void openDetailDrawer(item)}
                sx={{ mt: 0.25, px: 0, minWidth: 0, textTransform: "none", fontWeight: 700 }}
              >
                View requirement
              </Button>
            ) : null}
          </Box>
        ),
      },
      {
        key: "organization_name",
        label: "Organization",
        sortable: true,
        width: 210,
        render: (item) => (
          <Box>
            <Typography sx={{ fontWeight: 600, color: "#0F172A" }}>{item.organization_name}</Typography>
            <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 13 }}>
              {[item.country, item.region].filter(Boolean).join(" / ") || "Location not set"}
            </Typography>
          </Box>
        ),
      },
      {
        key: "source_name",
        label: "Source",
        width: 170,
        render: (item) => (
          <Stack spacing={0.6} sx={{ alignItems: "flex-start" }}>
            <BusinessSourceChip label={item.source_name || item.source_type} sourceType={item.source_type} />
            <Typography sx={{ color: "#64748B", fontSize: 12.5 }}>{item.source_type}</Typography>
          </Stack>
        ),
      },
      {
        key: "opportunity_status",
        label: "Status",
        sortable: true,
        width: 130,
        render: (item) => <BusinessStatusChip value={item.opportunity_status} />,
      },
      {
        key: "closing_at",
        label: "Closing",
        sortable: true,
        width: 150,
        render: (item) => formatDate(item.closing_at),
      },
      {
        key: "fit_score",
        label: "AI Fit",
        sortable: true,
        width: 96,
        render: (item) => (item.fit_score == null ? "Not assessed" : item.fit_score.toFixed(1)),
      },
      {
        key: "ai_recommendation",
        label: "Recommendation",
        width: 148,
        render: (item) => <BusinessRecommendationChip value={item.ai_recommendation || "watch"} />,
      },
      {
        key: "actions",
        label: "Actions",
        align: "right",
        width: 230,
        render: (item) => (
          <BusinessRowActionMenu
            primaryAction={
              canQualify && isBuildLeadEligible(item) ? (
                <Button
                  size="small"
                  variant="contained"
                  startIcon={<HubOutlinedIcon sx={{ color: "#FFFFFF" }} />}
                  onClick={() => openBuildLeadDialog(item)}
                  sx={{
                    minWidth: 0,
                    px: 1.05,
                    py: 0.4,
                    borderRadius: "8px",
                    textTransform: "none",
                    fontSize: 12,
                    fontWeight: 700,
                    bgcolor: "#2563EB",
                    boxShadow: "none",
                    "&:hover": { bgcolor: "#1D4ED8", boxShadow: "none" },
                  }}
                >
                  Build Lead
                </Button>
              ) : undefined
            }
            onView={canRead ? () => void openDetailDrawer(item) : undefined}
            menuItems={[
              ...(canQualify
                ? [
                    {
                      key: "assess",
                      label: item.ai_recommendation ? "Re-run Assessment" : "AI Assess",
                      icon: <AutoAwesomeOutlinedIcon fontSize="small" />,
                      onClick: () => promptAssess(item),
                    },
                  ]
                : []),
              ...(canOutreach
                ? [
                    {
                      key: "outreach",
                      label: "Personalized Outreach",
                      icon: <MarkEmailReadOutlinedIcon fontSize="small" />,
                      onClick: () => openOutreachWorkspace(item),
                    },
                    {
                      key: "mini-solution",
                      label: "Mini Solution",
                      icon: <LightbulbOutlinedIcon fontSize="small" />,
                      onClick: () => openMiniSolutionWorkspace(item),
                    },
                  ]
                : []),
              {
                key: "edit",
                label: "Edit",
                icon: <EditOutlined fontSize="small" />,
                onClick: () => void openEditDialog(item),
                disabled: !canUpdate,
              },
              {
                key: "delete",
                label: "Delete",
                icon: <DeleteOutline fontSize="small" />,
                onClick: () => promptDelete(item),
                disabled: !canDelete,
              },
            ]}
          />
        ),
      },
    ];

  function showToast(message: string, severity: ToastSeverity) {
    setToastMessage(message);
    setToastSeverity(severity);
    setToastOpen(true);
  }

  function updateFormField<K extends keyof OpportunityFormState>(
    field: K,
    value: OpportunityFormState[K]
  ) {
    setDialogFieldErrors((current) => {
      if (!current[field]) {
        return current;
      }
      const next = { ...current };
      delete next[field];
      return next;
    });
    setForm((current) => ({ ...current, [field]: value }));
  }

  function openCreateDialog() {
    setDialogMode("create");
    setEditingOpportunityId(null);
    setForm(DEFAULT_FORM_STATE);
    setDialogError("");
    setDialogFieldErrors({});
    setDialogOpen(true);
  }

  function isBuildLeadEligible(opportunity: AugmisBusinessOpportunity) {
    return opportunity.opportunity_status !== "converted";
  }

  function closeOpportunityDialog() {
    if (saving) return;
    setDialogError("");
    setDialogFieldErrors({});
    setDialogOpen(false);
    setEditingOpportunityId(null);
  }

  function promptAssess(opportunity: AugmisBusinessOpportunity) {
    if (!canQualify) return;
    setAssessmentTarget(opportunity);
    setAssessmentRunError("");
    setAssessDialogOpen(true);
  }

  function closeAssessDialog() {
    if (assessmentRunning) return;
    setAssessDialogOpen(false);
    setAssessmentTarget(null);
    setAssessmentRunError("");
  }

  function openOutreachWorkspace(opportunity: AugmisBusinessOpportunity) {
    setSelectedOpportunity(opportunity);
    setOutreachOpen(true);
  }

  function openMiniSolutionWorkspace(opportunity: AugmisBusinessOpportunity) {
    setSelectedOpportunity(opportunity);
    setMiniSolutionOpen(true);
  }

  function openBuildLeadDialog(opportunity: AugmisBusinessOpportunity) {
    if (!canQualify || !isBuildLeadEligible(opportunity)) return;
    setBuildLeadOpportunity(opportunity);
    setBuildLeadOpen(true);
  }

  function closeBuildLeadDialog() {
    setBuildLeadOpen(false);
    setBuildLeadOpportunity(null);
  }

  async function openDetailDrawer(opportunity: AugmisBusinessOpportunity) {
    if (!canRead) return;
    setDetailOpen(true);
    setDetailLoading(true);
    setAssessmentLoading(true);
    setDetailError("");
    setAssessmentError("");
    setSelectedOpportunity(opportunity);
    setLatestAssessment(null);
    setAssessmentHistory([]);
    try {
      const [opportunityResult, latestResult, historyResult] = await Promise.allSettled([
        getAugmisBusinessOpportunity(opportunity.id),
        getAugmisBusinessOpportunityAIAssessment(opportunity.id),
        listAugmisBusinessOpportunityAIAssessments(opportunity.id),
      ]);

      if (opportunityResult.status === "fulfilled") {
        setSelectedOpportunity(opportunityResult.value.data);
      } else {
        throw opportunityResult.reason;
      }

      if (latestResult.status === "fulfilled") {
        setLatestAssessment(latestResult.value.data);
      } else if (!isNotFoundError(latestResult.reason)) {
        setAssessmentError(
          getBackendErrorMessage(latestResult.reason, "Unable to load AI assessment.")
        );
      }

      if (historyResult.status === "fulfilled") {
        setAssessmentHistory(historyResult.value.data || []);
      } else if (!isNotFoundError(historyResult.reason)) {
        setAssessmentError(
          getBackendErrorMessage(historyResult.reason, "Unable to load assessment history.")
        );
      }
    } catch (drawerError) {
      setDetailError(getBackendErrorMessage(drawerError, "Unable to load opportunity details."));
    } finally {
      setDetailLoading(false);
      setAssessmentLoading(false);
    }
  }

  async function openEditDialog(opportunity: AugmisBusinessOpportunity) {
    if (!canUpdate) return;
    setDialogMode("edit");
    setDialogError("");
    setDialogFieldErrors({});
    setEditingOpportunityId(opportunity.id);
    setSaving(true);
    setDialogOpen(true);
    try {
      const result = await getAugmisBusinessOpportunity(opportunity.id);
      setForm(opportunityToFormState(result.data));
      setSelectedOpportunity(result.data);
    } catch (editError) {
      setDialogError(getBackendErrorMessage(editError, "Unable to load opportunity for editing."));
    } finally {
      setSaving(false);
    }
  }

  function promptDelete(opportunity: AugmisBusinessOpportunity) {
    if (!canDelete) return;
    setDeleteTarget(opportunity);
    setDeleteError("");
    setDeleteDialogOpen(true);
  }

  function closeDeleteDialog() {
    if (deleteSaving) return;
    setDeleteDialogOpen(false);
    setDeleteError("");
  }

  async function handleCreateOpportunity() {
    const fieldErrors = validateOpportunityForm(form);
    if (Object.keys(fieldErrors).length > 0) {
      setDialogFieldErrors(fieldErrors);
      setDialogError("Please correct the highlighted fields.");
      return;
    }

    setSaving(true);
    setDialogError("");
    setDialogFieldErrors({});
    try {
      const result = await createAugmisBusinessOpportunity(formStateToPayload(form));
      const createdRow = result.data;
      setDialogOpen(false);
      setForm(DEFAULT_FORM_STATE);
      setEditingOpportunityId(null);
      setDialogFieldErrors({});
      setItems((current) => [createdRow, ...current].slice(0, pageSize));
      setTotal((current) => current + 1);
      setHealthSummary((current) =>
        current
          ? { ...current, opportunity_count: (current.opportunity_count ?? 0) + 1 }
          : current
      );
      setSearch("");
      setStatusFilter("all");
      setPage(0);
      showToast("Opportunity created successfully.", "success");
      setLoading(true);
      setRefreshTick((value) => value + 1);
    } catch (submitError: unknown) {
      const parsed = parseApiValidationError(
        submitError,
        "Unable to create opportunity."
      );
      setDialogError(parsed.message);
      setDialogFieldErrors(parsed.fieldErrors);
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdateOpportunity() {
    if (!editingOpportunityId) return;
    const fieldErrors = validateOpportunityForm(form);
    if (Object.keys(fieldErrors).length > 0) {
      setDialogFieldErrors(fieldErrors);
      setDialogError("Please correct the highlighted fields.");
      return;
    }

    setSaving(true);
    setDialogError("");
    setDialogFieldErrors({});
    try {
      const result = await updateAugmisBusinessOpportunity(
        editingOpportunityId,
        formStateToPayload(form)
      );
      const updatedRow = result.data;
      setItems((current) => current.map((item) => (item.id === updatedRow.id ? updatedRow : item)));
      setSelectedOpportunity((current) => (current?.id === updatedRow.id ? updatedRow : current));
      setDialogOpen(false);
      setEditingOpportunityId(null);
      setDialogFieldErrors({});
      showToast("Opportunity updated successfully.", "success");
      setLoading(true);
      setRefreshTick((value) => value + 1);
    } catch (submitError: unknown) {
      const parsed = parseApiValidationError(
        submitError,
        "Unable to update opportunity."
      );
      setDialogError(parsed.message);
      setDialogFieldErrors(parsed.fieldErrors);
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteOpportunity() {
    if (!deleteTarget) return;
    setDeleteSaving(true);
    setDeleteError("");
    try {
      await deleteAugmisBusinessOpportunity(deleteTarget.id);
      const nextTotal = Math.max(0, total - 1);
      setItems((current) => current.filter((item) => item.id !== deleteTarget.id));
      setTotal(nextTotal);
      setHealthSummary((current) =>
        current
          ? { ...current, opportunity_count: Math.max(0, (current.opportunity_count ?? 0) - 1) }
          : current
      );
      if (selectedOpportunity?.id === deleteTarget.id) {
        setSelectedOpportunity(null);
        setDetailOpen(false);
      }
      setDeleteDialogOpen(false);
      showToast("Opportunity deleted successfully.", "success");
      if (items.length === 1 && page > 0) {
        setLoading(true);
        setPage(page - 1);
      } else {
        setLoading(true);
        setRefreshTick((value) => value + 1);
      }
    } catch (deleteRequestError) {
      setDeleteError(getBackendErrorMessage(deleteRequestError, "Unable to delete opportunity."));
    } finally {
      setDeleteSaving(false);
    }
  }

  function handleBuildLeadSuccess(result: {
    lead: { title: string; prospect: { organization_name: string } | null };
    first_task: { due_at: string | null };
    opportunity: AugmisBusinessOpportunity;
  }) {
    const updatedOpportunity = result.opportunity;
    setItems((current) =>
      current.map((item) => (item.id === updatedOpportunity.id ? updatedOpportunity : item))
    );
    setSelectedOpportunity((current) =>
      current?.id === updatedOpportunity.id ? updatedOpportunity : current
    );
    setHealthSummary((current) =>
      current
        ? {
            ...current,
            opportunity_count:
              current.opportunity_count == null ? current.opportunity_count : current.opportunity_count,
          }
        : current
    );
    setBuildLeadOpen(false);
    setBuildLeadOpportunity(null);
    setLoading(true);
    setRefreshTick((value) => value + 1);
  }

  async function handleRunAssessment() {
    if (!assessmentTarget) return;
    setAssessmentRunning(true);
    setAssessmentRunError("");
    try {
      const result = await runAugmisBusinessOpportunityAIAssessment(assessmentTarget.id);
      const assessment = result.data;
      setLatestAssessment(assessment);
      setAssessmentHistory((current) => {
        const next = [
          {
            id: assessment.id,
            opportunity_id: assessment.opportunity_id,
            assessment_version: assessment.assessment_version,
            provider: assessment.provider,
            model: assessment.model,
            prompt_bundle_version: assessment.prompt_bundle_version,
            final_fit_score: assessment.final_fit_score,
            confidence_score: assessment.confidence_score,
            recommendation: assessment.recommendation,
            created_at: assessment.created_at,
          },
          ...current.filter((item) => item.id !== assessment.id),
        ];
        return next.sort((a, b) => b.assessment_version - a.assessment_version);
      });
      setItems((current) =>
        current.map((item) =>
          item.id === assessmentTarget.id
            ? {
                ...item,
                fit_score: assessment.final_fit_score,
                confidence_score: assessment.confidence_score,
                ai_recommendation: assessment.recommendation,
              }
            : item
        )
      );
      setSelectedOpportunity((current) =>
        current?.id === assessmentTarget.id
          ? {
              ...current,
              fit_score: assessment.final_fit_score,
              confidence_score: assessment.confidence_score,
              ai_recommendation: assessment.recommendation,
            }
          : current
      );
      setAssessDialogOpen(false);
      setAssessmentTarget(null);
      showToast("AI assessment completed successfully.", "success");
      setLoading(true);
      setRefreshTick((value) => value + 1);
    } catch (runError) {
      setAssessmentRunError(
        getBackendErrorMessage(runError, "Unable to complete the AI assessment.")
      );
    } finally {
      setAssessmentRunning(false);
    }
  }

  return (
    <>
      <BusinessPageFrame
        title="Opportunities"
        description="Live tenant-scoped opportunity records from PostgreSQL, filtered through the existing AUGMIS authentication and SaaS access model."
        metrics={metrics}
        toolbar={
          <BusinessFilterBar
            filters={
              <Stack direction={{ xs: "column", lg: "row" }} spacing={1.1}>
                <TextField
                  size="small"
                  value={search}
                  onChange={(event) => {
                    setLoading(true);
                    setPage(0);
                    setSearch(event.target.value);
                  }}
                  placeholder="Search opportunities"
                  sx={{ minWidth: { lg: 300 } }}
                  slotProps={{
                    input: {
                      startAdornment: (
                        <InputAdornment position="start">
                          <SearchRoundedIcon fontSize="small" />
                        </InputAdornment>
                      ),
                    },
                  }}
                />
                <TextField
                  select
                  size="small"
                  value={statusFilter}
                  onChange={(event) => {
                    setLoading(true);
                    setPage(0);
                    setStatusFilter(event.target.value);
                  }}
                  sx={{ minWidth: 170 }}
                >
                  <MenuItem value="all">All statuses</MenuItem>
                  <MenuItem value="draft">Draft</MenuItem>
                  <MenuItem value="new">New</MenuItem>
                  <MenuItem value="under_review">Under Review</MenuItem>
                  <MenuItem value="qualified">Qualified</MenuItem>
                  <MenuItem value="converted">Converted</MenuItem>
                  <MenuItem value="dismissed">Dismissed</MenuItem>
                  <MenuItem value="expired">Expired</MenuItem>
                </TextField>
              </Stack>
            }
            actions={
              <>
                <Button
                  variant="contained"
                  startIcon={<AddCircleRoundedIcon sx={{ color: "#FFFFFF" }} />}
                  onClick={openCreateDialog}
                  sx={{
                    minWidth: 180,
                    borderRadius: "8px",
                    bgcolor: "#2563EB",
                    textTransform: "none",
                    fontWeight: 700,
                    boxShadow: "none",
                    "&:hover": {
                      bgcolor: "#1D4ED8",
                      boxShadow: "none",
                    },
                  }}
                >
                  + New Opportunity
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<RefreshRoundedIcon />}
                  onClick={() => {
                    setLoading(true);
                    setRefreshTick((value) => value + 1);
                  }}
                >
                  Refresh
                </Button>
                {canQualify ? (
                  <Button
                    variant="contained"
                    startIcon={<AutoAwesomeOutlinedIcon sx={{ color: "#FFFFFF" }} />}
                    onClick={() => {
                      if (selectedOpportunity) {
                        promptAssess(selectedOpportunity);
                        return;
                      }
                      if (items[0]) {
                        promptAssess(items[0]);
                      }
                    }}
                    disabled={assessmentRunning || (!selectedOpportunity && items.length === 0)}
                    sx={{
                      minWidth: 150,
                      borderRadius: "8px",
                      bgcolor: "#0F766E",
                      textTransform: "none",
                      fontWeight: 700,
                      boxShadow: "none",
                      "&:hover": {
                        bgcolor: "#115E59",
                        boxShadow: "none",
                      },
                    }}
                  >
                    AI Assess
                  </Button>
                ) : null}
              </>
            }
          />
        }
      >
        <Stack spacing={2.5}>
          {error ? <Alert severity="error">{error}</Alert> : null}
          <BusinessDataTable
            title="Opportunity Register"
            subtitle="Tenant-scoped opportunities with shared sorting, paging, and row actions."
            icon={<SourceOutlinedIcon fontSize="small" />}
            count={total}
            columns={tableColumns}
            rows={items}
            loading={loading}
            error={error || null}
            emptyTitle="No opportunities yet"
            emptyDescription="PostgreSQL is connected, but this tenant does not currently have opportunity rows. Use the shared manual create flow to register the first one."
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSortChange={(nextSortBy, nextSortOrder) => {
              setLoading(true);
              setPage(0);
              setSortBy(nextSortBy);
              setSortOrder(nextSortOrder);
            }}
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={(nextPage) => {
              setLoading(true);
              setPage(nextPage);
            }}
            onRowsPerPageChange={(nextPageSize) => {
              setLoading(true);
              setPage(0);
              setPageSize(nextPageSize);
            }}
            selectedRowKey={selectedOpportunity?.id || null}
            rowKey={(item) => item.id}
            minWidth={1320}
          />
        </Stack>
      </BusinessPageFrame>

      <AdminFormDialog
        open={dialogOpen}
        onClose={closeOpportunityDialog}
        title={dialogMode === "create" ? "Create Manual Opportunity" : "Edit Opportunity"}
        maxWidth={760}
        stackSx={{ maxWidth: 640 }}
        actions={
          <>
            <Button onClick={closeOpportunityDialog} disabled={saving} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={dialogMode === "create" ? handleCreateOpportunity : handleUpdateOpportunity}
              disabled={saving}
              sx={{
                textTransform: "none",
                fontWeight: 700,
                borderRadius: "8px",
                bgcolor: "#2563EB",
                "&:hover": { bgcolor: "#1D4ED8" },
              }}
            >
              {saving
                ? dialogMode === "create"
                  ? "Creating..."
                  : "Saving..."
                : dialogMode === "create"
                  ? "Create Opportunity"
                  : "Save Changes"}
            </Button>
          </>
        }
      >
        {dialogError ? <Alert severity="error">{dialogError}</Alert> : null}
        <OpportunityFormFields form={form} onChange={updateFormField} fieldErrors={dialogFieldErrors} />
      </AdminFormDialog>

      <Dialog open={assessDialogOpen} onClose={closeAssessDialog} fullWidth maxWidth="sm">
        <DialogTitle sx={{ fontWeight: 700 }}>
          {assessmentTarget?.ai_recommendation ? "Re-run AI Assessment" : "Run AI Assessment"}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} sx={{ mt: 0.5 }}>
            {assessmentRunError ? <Alert severity="error">{assessmentRunError}</Alert> : null}
            <Typography sx={{ color: "#0F172A" }}>
              This will analyze the selected opportunity using the existing AUGMIS AI service.
            </Typography>
            <Paper elevation={0} sx={{ p: 2, border: "1px solid #CCFBF1", borderRadius: "8px", bgcolor: "#F0FDFA" }}>
              <Typography sx={{ fontWeight: 700, color: "#134E4A" }}>
                {assessmentTarget?.title || "Unknown opportunity"}
              </Typography>
              <Typography sx={{ mt: 0.35, color: "#0F766E" }}>
                {assessmentTarget?.organization_name || "Organization not available"}
              </Typography>
            </Paper>
            <Typography sx={{ color: "#475569" }}>
              The assessment will run requirement extraction, qualification, experience matching,
              and buyer-role identification. Structured results will be validated before they are saved.
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={closeAssessDialog} disabled={assessmentRunning} sx={{ textTransform: "none" }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleRunAssessment}
            disabled={assessmentRunning}
            startIcon={
              assessmentRunning ? <CircularProgress size={16} sx={{ color: "#FFFFFF" }} /> : <AutoAwesomeOutlinedIcon />
            }
            sx={{
              textTransform: "none",
              fontWeight: 700,
              borderRadius: "8px",
              bgcolor: "#0F766E",
              "&:hover": { bgcolor: "#115E59" },
            }}
          >
            {assessmentRunning ? "Running..." : assessmentTarget?.ai_recommendation ? "Re-run Assessment" : "Run Assessment"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteDialogOpen} onClose={closeDeleteDialog} fullWidth maxWidth="sm">
        <DialogTitle sx={{ fontWeight: 700 }}>Delete Opportunity</DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} sx={{ mt: 0.5 }}>
            {deleteError ? <Alert severity="error">{deleteError}</Alert> : null}
            <Typography sx={{ color: "#0F172A" }}>
              You are about to permanently delete this opportunity.
            </Typography>
            <Paper elevation={0} sx={{ p: 2, border: "1px solid #FECACA", borderRadius: "8px", bgcolor: "#FEF2F2" }}>
              <Typography sx={{ fontWeight: 700, color: "#7F1D1D" }}>
                {deleteTarget?.title || "Unknown opportunity"}
              </Typography>
              <Typography sx={{ mt: 0.35, color: "#991B1B" }}>
                {deleteTarget?.organization_name || "Organization not available"}
              </Typography>
            </Paper>
            <Typography sx={{ color: "#7C2D12" }}>
              This action cannot be undone.
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={closeDeleteDialog} disabled={deleteSaving} sx={{ textTransform: "none" }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDeleteOpportunity}
            disabled={deleteSaving}
            sx={{ textTransform: "none", fontWeight: 700, borderRadius: "8px" }}
          >
            {deleteSaving ? "Deleting..." : "Delete Opportunity"}
          </Button>
        </DialogActions>
      </Dialog>

      <BusinessDetailDrawer
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={selectedOpportunity?.title || "Opportunity Details"}
        subtitle={selectedOpportunity?.organization_name || "Review the full tenant-scoped opportunity record."}
        chips={
          selectedOpportunity ? (
            <>
              <BusinessStatusChip value={selectedOpportunity.opportunity_status} />
              <BusinessSourceChip label={selectedOpportunity.source_name || selectedOpportunity.source_type} sourceType={selectedOpportunity.source_type} />
              <BusinessRecommendationChip value={selectedOpportunity.ai_recommendation || "watch"} />
            </>
          ) : undefined
        }
        actions={
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
              <Button
                variant="contained"
                startIcon={<MarkEmailReadOutlinedIcon />}
                disabled={!selectedOpportunity || !canOutreach}
                onClick={() => selectedOpportunity && openOutreachWorkspace(selectedOpportunity)}
                sx={{
                  textTransform: "none",
                  borderRadius: "8px",
                  bgcolor: "rgba(37,99,235,0.88)",
                  color: "#FFFFFF",
                  boxShadow: "none",
                }}
              >
                Personalized Outreach
              </Button>
              <Button
                variant="contained"
                startIcon={<LightbulbOutlinedIcon />}
                disabled={!selectedOpportunity || !canOutreach}
                onClick={() => selectedOpportunity && openMiniSolutionWorkspace(selectedOpportunity)}
                sx={{
                  textTransform: "none",
                  borderRadius: "8px",
                  bgcolor: "rgba(15,118,110,0.9)",
                  color: "#FFFFFF",
                  boxShadow: "none",
                }}
              >
                Mini Solution
              </Button>
              <Button
                variant="contained"
                startIcon={<AutoAwesomeOutlinedIcon />}
                disabled={!selectedOpportunity || !canQualify || assessmentRunning}
                onClick={() => selectedOpportunity && promptAssess(selectedOpportunity)}
                sx={{
                  textTransform: "none",
                  borderRadius: "8px",
                  bgcolor: "rgba(15,118,110,0.9)",
                  color: "#FFFFFF",
                  boxShadow: "none",
                }}
              >
                {latestAssessment ? "Re-run Assessment" : "AI Assess"}
              </Button>
              <Button
                variant="contained"
                startIcon={<HubOutlinedIcon />}
                disabled={
                  !selectedOpportunity || !canQualify || !isBuildLeadEligible(selectedOpportunity)
                }
                onClick={() => selectedOpportunity && openBuildLeadDialog(selectedOpportunity)}
                sx={{
                  textTransform: "none",
                  borderRadius: "8px",
                  bgcolor: "rgba(37,99,235,0.78)",
                  color: "#FFFFFF",
                  boxShadow: "none",
                }}
              >
                Build Lead
              </Button>
              <Button
                variant="contained"
                startIcon={<EditOutlined />}
                disabled={!selectedOpportunity || !canUpdate}
                onClick={() => selectedOpportunity && void openEditDialog(selectedOpportunity)}
                sx={{
                  textTransform: "none",
                  borderRadius: "8px",
                  bgcolor: "rgba(255,255,255,0.16)",
                  color: "#FFFFFF",
                  boxShadow: "none",
                }}
              >
                Edit
              </Button>
              <Button
                variant="contained"
                startIcon={<DeleteOutline />}
                disabled={!selectedOpportunity || !canDelete}
                onClick={() => selectedOpportunity && promptDelete(selectedOpportunity)}
                sx={{
                  textTransform: "none",
                  borderRadius: "8px",
                  bgcolor: "rgba(127,29,29,0.55)",
                  color: "#FFFFFF",
                  boxShadow: "none",
                }}
              >
                Delete
              </Button>
              <Button
                variant="outlined"
                onClick={() => setDetailOpen(false)}
                sx={{ textTransform: "none", borderRadius: "8px" }}
              >
                Close
              </Button>
          </Stack>
        }
        loading={detailLoading}
        error={detailError || null}
        width={780}
      >
            {detailLoading ? (
              <Stack sx={{ minHeight: 280, alignItems: "center", justifyContent: "center" }} spacing={1.5}>
                <CircularProgress />
                <Typography sx={{ color: "#475569" }}>Loading opportunity details...</Typography>
              </Stack>
            ) : detailError ? (
              <Alert severity="error">{detailError}</Alert>
            ) : selectedOpportunity ? (
              <Stack spacing={2}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 2.25,
                    borderRadius: "8px",
                    border: "1px solid #D9E2EC",
                    background:
                      "linear-gradient(180deg, rgba(239,246,255,0.9) 0%, rgba(248,250,252,0.95) 100%)",
                  }}
                >
                  <Typography variant="h5" sx={{ fontWeight: 700, color: "#0F172A" }}>
                    {selectedOpportunity.title}
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 1.25, flexWrap: "wrap" }}>
                    <Chip
                      label={selectedOpportunity.opportunity_status.replaceAll("_", " ")}
                      size="small"
                      sx={{
                        textTransform: "capitalize",
                        border: "1px solid",
                        ...statusChipColor(selectedOpportunity.opportunity_status),
                      }}
                    />
                    <Chip
                      label={selectedOpportunity.organization_name}
                      size="small"
                      sx={{ bgcolor: "#FFFFFF", border: "1px solid #CBD5E1" }}
                    />
                  </Stack>
                </Paper>

                <Box
                  sx={{
                    display: "grid",
                    gap: 1.5,
                    gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                  }}
                >
                  <DetailField icon={<ApartmentOutlinedIcon fontSize="small" />} label="Organization Name" value={selectedOpportunity.organization_name || "Not available"} />
                  <DetailField icon={<LanguageOutlinedIcon fontSize="small" />} label="Organization Domain" value={selectedOpportunity.organization_domain || "Not available"} />
                  <DetailField icon={<SourceOutlinedIcon fontSize="small" />} label="Source Type" value={selectedOpportunity.source_type || "Not available"} />
                  <DetailField icon={<SourceOutlinedIcon fontSize="small" />} label="Source Name" value={selectedOpportunity.source_name || "Not available"} />
                  <DetailField icon={<LanguageOutlinedIcon fontSize="small" />} label="Source URL" value={selectedOpportunity.source_url || "Not available"} />
                  <DetailField icon={<PublicOutlinedIcon fontSize="small" />} label="Country" value={selectedOpportunity.country || "Not available"} />
                  <DetailField icon={<PublicOutlinedIcon fontSize="small" />} label="Region" value={selectedOpportunity.region || "Not available"} />
                  <DetailField icon={<WorkOutlineOutlinedIcon fontSize="small" />} label="Industry" value={selectedOpportunity.industry || "Not available"} />
                  <DetailField icon={<CalendarMonthOutlinedIcon fontSize="small" />} label="Published Date" value={formatDate(selectedOpportunity.published_at)} />
                  <DetailField icon={<CalendarMonthOutlinedIcon fontSize="small" />} label="Closing Date" value={formatDate(selectedOpportunity.closing_at)} />
                  <DetailField icon={<InsightsOutlinedIcon fontSize="small" />} label="Published Budget" value={formatNumber(selectedOpportunity.published_budget)} />
                  <DetailField icon={<InsightsOutlinedIcon fontSize="small" />} label="Published Currency" value={selectedOpportunity.published_currency || "Not available"} />
                  <DetailField icon={<InsightsOutlinedIcon fontSize="small" />} label="Estimated Value Minimum" value={formatNumber(selectedOpportunity.estimated_value_min)} />
                  <DetailField icon={<InsightsOutlinedIcon fontSize="small" />} label="Estimated Value Maximum" value={formatNumber(selectedOpportunity.estimated_value_max)} />
                  <DetailField icon={<InsightsOutlinedIcon fontSize="small" />} label="Estimated Currency" value={selectedOpportunity.estimated_currency || "Not available"} />
                  <DetailField icon={<TuneOutlinedIcon fontSize="small" />} label="Fit Score" value={formatNumber(selectedOpportunity.fit_score)} />
                  <DetailField icon={<TuneOutlinedIcon fontSize="small" />} label="Confidence Score" value={formatNumber(selectedOpportunity.confidence_score)} />
                  <DetailField icon={<CalendarMonthOutlinedIcon fontSize="small" />} label="Created Date" value={formatDate(selectedOpportunity.created_at)} />
                  <DetailField icon={<CalendarMonthOutlinedIcon fontSize="small" />} label="Updated Date" value={formatDate(selectedOpportunity.updated_at)} />
                </Box>

                <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
                  <Box
                    sx={{
                      px: 2,
                      py: 1.4,
                      background: "linear-gradient(90deg, #E0F2FE 0%, #F8FAFC 100%)",
                      borderBottom: "1px solid #E2E8F0",
                    }}
                  >
                    <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                      <WorkOutlineOutlinedIcon sx={{ color: "#2563EB", fontSize: 18 }} />
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                        Opportunity Narrative
                      </Typography>
                    </Stack>
                  </Box>
                  <Stack spacing={2} sx={{ p: 2 }}>
                    <DetailField icon={<WorkOutlineOutlinedIcon fontSize="small" />} label="Requirement Summary" value={selectedOpportunity.requirement_summary || "Not available"} />
                    <DetailField icon={<WorkOutlineOutlinedIcon fontSize="small" />} label="Raw Summary" value={selectedOpportunity.raw_summary || "Not available"} />
                    <DetailField icon={<WorkOutlineOutlinedIcon fontSize="small" />} label="Business Problem" value={selectedOpportunity.business_problem || "Not available"} />
                    <DetailField icon={<AutoAwesomeOutlinedIcon fontSize="small" />} label="AI Recommendation" value={selectedOpportunity.ai_recommendation || "Not available"} />
                  </Stack>
                </Paper>

                <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
                  <Box
                    sx={{
                      px: 2,
                      py: 1.4,
                      background: "linear-gradient(90deg, #CCFBF1 0%, #F8FAFC 100%)",
                      borderBottom: "1px solid #E2E8F0",
                    }}
                  >
                    <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                      <AutoAwesomeOutlinedIcon sx={{ color: "#0F766E", fontSize: 18 }} />
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                        AI Intelligence
                      </Typography>
                    </Stack>
                  </Box>
                  <Box sx={{ p: 2 }}>
                    {assessmentLoading ? (
                      <Stack spacing={1.5} sx={{ alignItems: "center", justifyContent: "center", minHeight: 180 }}>
                        <CircularProgress size={24} />
                        <Typography sx={{ color: "#475569" }}>Loading AI assessment...</Typography>
                      </Stack>
                    ) : assessmentError ? (
                      <Alert severity="error">{assessmentError}</Alert>
                    ) : latestAssessment ? (
                      <Stack spacing={2}>
                        <Box>
                          <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: ".04em" }}>
                            Summary
                          </Typography>
                          <Box
                            sx={{
                              mt: 1,
                              display: "grid",
                              gap: 1.25,
                              gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" },
                            }}
                          >
                            <DetailField
                              icon={<AutoAwesomeOutlinedIcon fontSize="small" />}
                              label="Recommendation"
                              value={
                                <Chip
                                  label={formatRecommendation(latestAssessment.recommendation)}
                                  size="small"
                                  sx={{
                                    textTransform: "capitalize",
                                    border: "1px solid",
                                    ...recommendationChipColor(latestAssessment.recommendation),
                                  }}
                                />
                              }
                            />
                            <DetailField icon={<TuneOutlinedIcon fontSize="small" />} label="Fit Score" value={formatScore(latestAssessment.final_fit_score)} />
                            <DetailField icon={<InsightsOutlinedIcon fontSize="small" />} label="Confidence" value={formatScore(latestAssessment.confidence_score)} />
                            <DetailField icon={<HubOutlinedIcon fontSize="small" />} label="Delivery Model" value={formatDeliveryModel(latestAssessment.qualification_json.delivery_profile.delivery_model)} />
                            <DetailField icon={<InsightsOutlinedIcon fontSize="small" />} label="Complexity Score" value={formatScore(latestAssessment.qualification_json.delivery_profile.complexity_score)} />
                            <DetailField icon={<CalendarMonthOutlinedIcon fontSize="small" />} label="Assessment Date" value={formatDate(latestAssessment.created_at)} />
                            <DetailField icon={<SourceOutlinedIcon fontSize="small" />} label="Model" value={latestAssessment.model || "Not available"} />
                            <DetailField icon={<CalendarMonthOutlinedIcon fontSize="small" />} label="Estimated Delivery" value={latestAssessment.qualification_json.delivery_profile.estimated_delivery_weeks == null ? "Not available" : `${latestAssessment.qualification_json.delivery_profile.estimated_delivery_weeks} weeks`} />
                            <DetailField icon={<WorkOutlineOutlinedIcon fontSize="small" />} label="Assessment Version" value={String(latestAssessment.assessment_version)} />
                          </Box>
                        </Box>

                        <Box>
                          <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: ".04em" }}>
                            Qualification
                          </Typography>
                          <Box
                            sx={{
                              mt: 1,
                              display: "grid",
                              gap: 1.25,
                              gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                            }}
                          >
                            {[
                              { label: "Experience Relevance", component: latestAssessment.qualification_json.experience_relevance },
                              { label: "Technology Match", component: latestAssessment.qualification_json.technology_match },
                              { label: "Budget Attractiveness", component: latestAssessment.qualification_json.budget_attractiveness },
                              { label: "Delivery Feasibility", component: latestAssessment.qualification_json.delivery_feasibility },
                              { label: "Buyer Accessibility", component: latestAssessment.qualification_json.buyer_accessibility },
                              { label: "Deadline Feasibility", component: latestAssessment.qualification_json.deadline_feasibility },
                              { label: "Market / Payment Risk", component: latestAssessment.qualification_json.market_payment_risk },
                            ].map(({ label, component }) => (
                              <Paper key={label} elevation={0} sx={{ p: 1.5, border: "1px solid #D9E2EC", borderRadius: "8px" }}>
                                <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center" }}>
                                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{label}</Typography>
                                  <Chip label={`${component.score.toFixed(1)}`} size="small" sx={{ bgcolor: "#EFF6FF", color: "#1D4ED8" }} />
                                </Stack>
                                <Box sx={{ mt: 1, height: 8, borderRadius: 999, bgcolor: "#E2E8F0", overflow: "hidden" }}>
                                  <Box sx={{ width: `${Math.max(0, Math.min(100, component.score))}%`, height: "100%", bgcolor: "#2563EB" }} />
                                </Box>
                                <Typography sx={{ mt: 1, color: "#475569", fontSize: 13 }}>
                                  {component.explanation}
                                </Typography>
                              </Paper>
                            ))}
                          </Box>
                          <Paper elevation={0} sx={{ mt: 1.25, p: 1.5, border: "1px solid #D9E2EC", borderRadius: "8px", bgcolor: "#F8FAFC" }}>
                            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                              Qualification Summary
                            </Typography>
                            <Typography sx={{ mt: 0.75, color: "#475569" }}>
                              {latestAssessment.qualification_json.explanation}
                            </Typography>
                          </Paper>
                        </Box>

                        <Box>
                          <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: ".04em" }}>
                            Experience Match
                          </Typography>
                          <Stack spacing={1.25} sx={{ mt: 1 }}>
                            {latestAssessment.experience_matches.length ? (
                              latestAssessment.experience_matches.map((match: AugmisBusinessOpportunityExperienceMatch) => (
                                <Paper key={match.experience_item_id} elevation={0} sx={{ p: 1.5, border: "1px solid #D9E2EC", borderRadius: "8px" }}>
                                  <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
                                    <Box>
                                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{match.name}</Typography>
                                      <Typography sx={{ mt: 0.35, color: "#475569", fontSize: 13 }}>{match.category}</Typography>
                                    </Box>
                                    <Chip label={`${match.match_score.toFixed(1)}`} size="small" sx={{ bgcolor: "#ECFDF3", color: "#067647" }} />
                                  </Stack>
                                  <Typography sx={{ mt: 1, color: "#475569" }}>{match.explanation}</Typography>
                                  <Typography sx={{ mt: 1, color: "#334155", fontSize: 13 }}>
                                    {match.business_problem_similarity}
                                  </Typography>
                                  <Box sx={{ mt: 1.25 }}>
                                    <DetailList title="Matching Capabilities" items={match.matching_capabilities} />
                                  </Box>
                                  <Box sx={{ mt: 1.25 }}>
                                    <DetailList title="Matching Technologies" items={match.matching_technologies} />
                                  </Box>
                                </Paper>
                              ))
                            ) : (
                              <Typography sx={{ color: "#475569" }}>Not available</Typography>
                            )}
                          </Stack>
                        </Box>

                        <Box>
                          <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: ".04em" }}>
                            Buyer Roles
                          </Typography>
                          <Typography sx={{ mt: 0.5, color: "#64748B", fontSize: 13 }}>
                            Role recommendation — no named contact identified yet
                          </Typography>
                          <Box
                            sx={{
                              mt: 1,
                              display: "grid",
                              gap: 1.25,
                              gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                            }}
                          >
                            {[
                              { label: "Economic Buyer", role: latestAssessment.buyer_roles_json.economic_buyer },
                              { label: "Operational Owner", role: latestAssessment.buyer_roles_json.operational_owner },
                              { label: "Technical Evaluator", role: latestAssessment.buyer_roles_json.technical_evaluator },
                              { label: "Procurement Contact", role: latestAssessment.buyer_roles_json.procurement_contact },
                            ].map(({ label, role }) => (
                              <Paper key={label} elevation={0} sx={{ p: 1.5, border: "1px solid #D9E2EC", borderRadius: "8px" }}>
                                <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center" }}>
                                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{label}</Typography>
                                  <Chip label={`${role.confidence.toFixed(1)}`} size="small" sx={{ bgcolor: "#EEF2FF", color: "#4338CA" }} />
                                </Stack>
                                <Typography sx={{ mt: 0.85, color: "#0F172A" }}>{role.role}</Typography>
                                <Typography sx={{ mt: 0.75, color: "#475569", fontSize: 13 }}>{role.reason}</Typography>
                              </Paper>
                            ))}
                          </Box>
                        </Box>

                        <Box>
                          <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: ".04em" }}>
                            Risks & Gaps
                          </Typography>
                          <Stack spacing={1.25} sx={{ mt: 1 }}>
                            <DetailList title="Risks" items={latestAssessment.risks_json} />
                            <DetailList title="Missing Information" items={latestAssessment.missing_information_json} />
                            <DetailList title="Requirement Evidence" items={latestAssessment.requirement_extraction_json.source_evidence} />
                            <DetailList title="Delivery Risks" items={latestAssessment.qualification_json.delivery_profile.key_delivery_risks} />
                          </Stack>
                        </Box>

                        <Box>
                          <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: ".04em" }}>
                            Assessment History
                          </Typography>
                          <Stack spacing={1} sx={{ mt: 1 }}>
                            {assessmentHistory.length ? (
                              assessmentHistory.map((entry) => (
                                <Paper key={entry.id} elevation={0} sx={{ p: 1.25, border: "1px solid #D9E2EC", borderRadius: "8px" }}>
                                  <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
                                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                                      Version {entry.assessment_version}
                                    </Typography>
                                    <Chip
                                      label={formatRecommendation(entry.recommendation)}
                                      size="small"
                                      sx={{
                                        textTransform: "capitalize",
                                        border: "1px solid",
                                        ...recommendationChipColor(entry.recommendation),
                                      }}
                                    />
                                  </Stack>
                                  <Typography sx={{ mt: 0.5, color: "#475569", fontSize: 13 }}>
                                    {formatDate(entry.created_at)} · {entry.model} · Fit {formatScore(entry.final_fit_score)}
                                  </Typography>
                                </Paper>
                              ))
                            ) : (
                              <Typography sx={{ color: "#475569" }}>No prior assessment history.</Typography>
                            )}
                          </Stack>
                        </Box>
                      </Stack>
                    ) : (
                      <Alert severity="info">
                        This opportunity has not been assessed yet. Run AI Assess to generate
                        structured qualification, experience matching, buyer-role guidance, and
                        grounded risks.
                      </Alert>
                    )}
                  </Box>
                </Paper>

                <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
                  <Box
                    sx={{
                      px: 2,
                      py: 1.4,
                      background: "linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)",
                      borderBottom: "1px solid #E2E8F0",
                    }}
                  >
                    <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                      <TuneOutlinedIcon sx={{ color: "#1D4ED8", fontSize: 18 }} />
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                        Deliverables and Technology
                      </Typography>
                    </Stack>
                  </Box>
                  <Box sx={{ p: 2 }}>
                    <DetailField
                      icon={<TuneOutlinedIcon fontSize="small" />}
                      label="Expected Deliverables"
                      value={
                        selectedOpportunity.expected_deliverables_json.length
                          ? selectedOpportunity.expected_deliverables_json.join(", ")
                          : "Not available"
                      }
                    />
                    <Box sx={{ mt: 1.5 }}>
                      <DetailField
                        icon={<TuneOutlinedIcon fontSize="small" />}
                        label="Required Technologies"
                        value={
                          selectedOpportunity.required_technologies_json.length
                            ? selectedOpportunity.required_technologies_json.join(", ")
                            : "Not available"
                        }
                      />
                    </Box>
                  </Box>
                </Paper>

                <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
                  <Box
                    sx={{
                      px: 2,
                      py: 1.4,
                      background: "linear-gradient(90deg, #DCFCE7 0%, #F8FAFC 100%)",
                      borderBottom: "1px solid #E2E8F0",
                    }}
                  >
                    <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                      <SourceOutlinedIcon sx={{ color: "#15803D", fontSize: 18 }} />
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                        Source Evidence
                      </Typography>
                    </Stack>
                  </Box>
                  <Box sx={{ p: 2 }}>
                    {selectedOpportunityEvidence.length ? (
                      <Stack spacing={1}>
                        {selectedOpportunityEvidence.map((entry, index) => (
                          <Paper
                            key={`${selectedOpportunity.id}-evidence-${index}`}
                            elevation={0}
                            sx={{
                              p: 1.5,
                              borderRadius: "8px",
                              border: "1px solid #DCFCE7",
                              bgcolor: "#F0FDF4",
                              color: "#14532D",
                              wordBreak: "break-word",
                            }}
                          >
                            {entry}
                          </Paper>
                        ))}
                      </Stack>
                    ) : (
                      <Typography sx={{ color: "#475569" }}>Not available</Typography>
                    )}
                  </Box>
                </Paper>
              </Stack>
            ) : (
              <Typography sx={{ color: "#475569" }}>Not available</Typography>
            )}
      </BusinessDetailDrawer>

      <AppNotificationToast
        open={toastOpen}
        message={toastMessage}
        severity={toastSeverity}
        onClose={() => {
          setToastOpen(false);
          setToastMessage(null);
        }}
      />

      <BuildLeadDialog
        key={`${buildLeadOpportunity?.id ?? "none"}-${buildLeadOpen ? "open" : "closed"}`}
        open={buildLeadOpen}
        opportunity={buildLeadOpportunity}
        onClose={closeBuildLeadDialog}
        onSuccess={handleBuildLeadSuccess}
        showToast={showToast}
      />

      <OutreachWorkspaceDialog
        open={outreachOpen}
        opportunityId={selectedOpportunity?.id || ""}
        title={selectedOpportunity?.title || "Opportunity"}
        organizationName={selectedOpportunity?.organization_name}
        hasAssessment={Boolean(latestAssessment || selectedOpportunity?.ai_recommendation)}
        onClose={() => setOutreachOpen(false)}
        showToast={showToast}
      />

      <MiniSolutionWorkspaceDrawer
        open={miniSolutionOpen}
        opportunityId={selectedOpportunity?.id || ""}
        title={selectedOpportunity?.title || "Opportunity"}
        hasAssessment={Boolean(latestAssessment || selectedOpportunity?.ai_recommendation)}
        onClose={() => setMiniSolutionOpen(false)}
        showToast={showToast}
      />
    </>
  );
}
