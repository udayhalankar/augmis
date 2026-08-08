"use client";

import { type ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";

import AutorenewRoundedIcon from "@mui/icons-material/AutorenewRounded";
import AccountBalanceOutlinedIcon from "@mui/icons-material/AccountBalanceOutlined";
import CableOutlinedIcon from "@mui/icons-material/CableOutlined";
import CheckCircleOutlineRoundedIcon from "@mui/icons-material/CheckCircleOutlineRounded";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import FilterAltOutlinedIcon from "@mui/icons-material/FilterAltOutlined";
import FindInPageOutlinedIcon from "@mui/icons-material/FindInPageOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import ImportExportOutlinedIcon from "@mui/icons-material/ImportExportOutlined";
import LinkOutlinedIcon from "@mui/icons-material/LinkOutlined";
import OpenInNewRoundedIcon from "@mui/icons-material/OpenInNewRounded";
import PlayCircleOutlineRoundedIcon from "@mui/icons-material/PlayCircleOutlineRounded";
import PreviewOutlinedIcon from "@mui/icons-material/PreviewOutlined";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import RuleFolderOutlinedIcon from "@mui/icons-material/RuleFolderOutlined";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import SettingsSuggestOutlinedIcon from "@mui/icons-material/SettingsSuggestOutlined";
import TaskAltOutlinedIcon from "@mui/icons-material/TaskAltOutlined";
import TravelExploreOutlinedIcon from "@mui/icons-material/TravelExploreOutlined";
import TranslateOutlinedIcon from "@mui/icons-material/TranslateOutlined";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Drawer,
  IconButton,
  InputAdornment,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";

import { AppNotificationToast } from "@/components/feedback/AppNotificationToast";
import { AdminFormDialog, AdminFormTextField } from "@/components/forms/AdminFormDialog";
import { OutletPage } from "@/components/layout/OutletPage";
import { useAuth } from "@/context/AuthContext";
import { parseApiValidationError } from "@/services/apiErrorParser";
import {
  type AugmisBusinessConnector,
  type AugmisBusinessConnectorCredentialStatus,
  type AugmisBusinessConnectorRun,
  type AugmisBusinessDiscovery,
  type AugmisBusinessSearchProfile,
  type AugmisBusinessSearchProvider,
  createAugmisBusinessSearchProvider,
  createAugmisBusinessSearchProfile,
  deleteAugmisBusinessConnectorCredential,
  deleteAugmisBusinessSearchProvider,
  getAugmisBusinessConnectorCredential,
  getAugmisBusinessDiscovery,
  importAugmisBusinessDiscovery,
  listAugmisBusinessConnectorRuns,
  listAugmisBusinessConnectors,
  listAugmisBusinessDiscoveries,
  listAugmisBusinessSearchProfiles,
  listAugmisBusinessSearchProviders,
  rejectAugmisBusinessDiscovery,
  scanAugmisBusinessConnector,
  saveAugmisBusinessConnectorCredential,
  setAugmisBusinessConnectorSearchProvider,
  shortlistAugmisBusinessDiscovery,
  testAugmisBusinessConnectorCredential,
  testAugmisBusinessConnector,
  testAugmisBusinessSearchProvider,
  translateAugmisBusinessDiscovery,
  updateAugmisBusinessConnector,
  updateAugmisBusinessSearchProvider,
  updateAugmisBusinessSearchProfile,
} from "@/services/augmisBusinessService";

type ToastSeverity = "success" | "error" | "info" | "warning";
type SearchProfileArrayField =
  | "target_regions_json"
  | "target_countries_json"
  | "target_industries_json"
  | "include_keywords_json"
  | "include_technologies_json"
  | "include_capabilities_json"
  | "exclude_keywords_json"
  | "excluded_domains_json"
  | "excluded_categories_json"
  | "currencies_json";

type SearchProfileForm = {
  name: string;
  target_regions_json: string[];
  target_countries_json: string[];
  target_industries_json: string[];
  include_keywords_json: string[];
  include_technologies_json: string[];
  include_capabilities_json: string[];
  exclude_keywords_json: string[];
  excluded_domains_json: string[];
  excluded_categories_json: string[];
  minimum_budget: string;
  currencies_json: string[];
  allow_budget_unknown: boolean;
  solo_feasibility_preference: string;
  small_team_allowed: boolean;
  max_delivery_months: string;
  max_age_days: string;
};

type SearchProfileArrayEditorProps = {
  label: string;
  helperText: string;
  placeholder: string;
  values: string[];
  onAdd: (value: string) => void;
  onRemove: (value: string) => void;
};

type CredentialDialogMode = "configure" | "replace";
type SearchProviderForm = {
  display_name: string;
  provider_code: string;
  provider_type: "generic_rest";
  enabled: boolean;
  description: string;
  credential_type: "api_key" | "bearer_token";
  base_search_url: string;
  http_method: "get" | "post";
  authentication_type: "api_key_header" | "bearer_token";
  api_key_header_name: string;
  query_parameter_name: string;
  results_path: string;
  title_field: string;
  url_field: string;
  snippet_field: string;
  score_field: string;
  published_date_field: string;
  page_parameter: string;
  page_size_parameter: string;
};

type DiscoverySourceMetadata = {
  provider?: string;
  publication_number?: string;
  notice_identifier?: string;
  notice_version?: string;
  notice_type?: string;
  procedure_type?: string;
  contract_nature?: string;
  cpv_codes?: string[];
  official_language?: string;
  buyer_country?: string;
  place_of_performance?: string[];
  estimated_value?: number | null;
  estimated_currency?: string | null;
  ted_summary?: string;
  queries_matched?: string[];
  best_rank?: number;
  search_snippet?: string;
  fetched_source_available?: boolean;
  partial_source_retrieval?: boolean;
  positive_terms?: string[];
  negative_terms?: string[];
  source_trust?: string;
  fetch_error?: string | null;
  fetch_error_code?: string | null;
};

type DiscoveryRawContent = {
  provider_result?: Record<string, unknown>;
  search_result_title?: string;
  search_result_snippet?: string;
  fetched_source_html?: string | null;
  fetched_source_text?: string | null;
  ted_notice?: Record<string, unknown>;
};

type ConnectorRunMetadata = {
  provider?: string;
  queries_executed?: string[];
  query_count?: number;
  api_call_count?: number;
  api_result_count?: number;
  raw_results_fetched?: number;
  provider_usage?: Record<string, unknown>;
  same_scan_unique_sources?: number;
  source_pages_fetched?: number;
  source_pages_attempted?: number;
  source_pages_skipped_due_limit?: number;
  fetch_failures?: number;
  accepted_candidates?: number;
  filtered_candidates?: number;
  max_candidate_results?: number;
  maximum_queries_per_scan?: number;
  max_source_fetches_per_scan?: number;
  max_fetch_bytes?: number;
  fetch_timeout_seconds?: number;
  max_extracted_text_chars?: number;
  max_redirects?: number;
  fetch_source_page?: boolean;
  results_per_query?: number;
  recency_days?: number;
  item_errors?: string[];
  notices_normalized?: number;
  query_diagnostics?: Array<{
    key?: string;
    label?: string;
    query?: string;
    primary_term?: string;
    cpv_codes?: string[];
    raw_results?: number;
    normalized?: number;
    invalid_items?: number;
    error?: string;
  }>;
};

const CONNECTOR_TEST_LABEL = "TEST / FIXTURE";
const CONNECTOR_PRODUCTION_LABEL = "PRODUCTION";
const SCHEDULE_INTERVAL_OPTIONS = [60, 120, 240, 360, 720];
const SCHEDULE_TIME_OPTIONS = ["06:00", "07:00", "08:00", "09:00", "18:00", "21:00"];
const SCHEDULE_TIMEZONE_OPTIONS = ["UTC", "Asia/Riyadh", "Europe/London", "Europe/Brussels"];
const WEEKDAY_OPTIONS = [
  { value: 0, label: "Monday" },
  { value: 1, label: "Tuesday" },
  { value: 2, label: "Wednesday" },
  { value: 3, label: "Thursday" },
  { value: 4, label: "Friday" },
  { value: 5, label: "Saturday" },
  { value: 6, label: "Sunday" },
];

function formatDate(value: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function normalizeListValues(values: string[]) {
  return values
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item, index, all) => all.findIndex((candidate) => candidate.toLowerCase() === item.toLowerCase()) === index);
}

function normalizeOptionalString(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function slugifyProviderCode(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function normalizeOptionalNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatBytes(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "Not available";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(value % 1_000_000 === 0 ? 0 : 1)} MB`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(value % 1_000 === 0 ? 0 : 1)} KB`;
  return `${value} bytes`;
}

function formatSchedule(connector: AugmisBusinessConnector) {
  if (!connector.schedule_enabled) return "Manual";
  if (connector.schedule_type === "hourly_interval" && connector.schedule_interval_minutes) {
    const hours = Math.max(1, Math.round(connector.schedule_interval_minutes / 60));
    return `Every ${hours} hour${hours === 1 ? "" : "s"}`;
  }
  if (connector.schedule_type === "daily" && connector.schedule_time_local) {
    return `Daily · ${connector.schedule_time_local}`;
  }
  if (
    connector.schedule_type === "weekly" &&
    connector.schedule_time_local &&
    connector.schedule_day_of_week != null &&
    WEEKDAY_OPTIONS[connector.schedule_day_of_week]
  ) {
    return `Weekly · ${WEEKDAY_OPTIONS[connector.schedule_day_of_week].label.slice(0, 3)} · ${connector.schedule_time_local}`;
  }
  return connector.schedule_expression || "Manual";
}

function connectorNumberConfig(connector: AugmisBusinessConnector | null, key: string, fallback: number) {
  const raw = connector?.configuration_json?.[key];
  return typeof raw === "number" && Number.isFinite(raw) ? raw : fallback;
}

function connectorBooleanConfig(connector: AugmisBusinessConnector | null, key: string, fallback: boolean) {
  const raw = connector?.configuration_json?.[key];
  return typeof raw === "boolean" ? raw : fallback;
}

function getBackendErrorMessage(error: unknown, fallback: string) {
  return parseApiValidationError(error, fallback).message;
}

function connectorStatusChip(status: string) {
  switch (status) {
    case "ready":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "running":
      return { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
    case "attention":
      return { bgcolor: "#FFF7ED", color: "#B45309", borderColor: "#FED7AA" };
    case "disabled":
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
    case "error":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
    default:
      return { bgcolor: "#FFF7ED", color: "#C2410C", borderColor: "#FED7AA" };
  }
}

function discoveryStatusChip(status: string) {
  switch (status) {
    case "shortlisted":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "imported":
      return { bgcolor: "#EEF2FF", color: "#4338CA", borderColor: "#C7D2FE" };
    case "duplicate":
      return { bgcolor: "#FFF7ED", color: "#B45309", borderColor: "#FED7AA" };
    case "rejected":
    case "irrelevant":
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
    default:
      return { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
  }
}

function discoveryRelevanceBandChip(band: string | null | undefined) {
  switch ((band || "").toLowerCase()) {
    case "strong":
      return { bgcolor: "#DCFCE7", color: "#166534", borderColor: "#86EFAC" };
    case "good":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "possible":
      return { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
    case "weak":
      return { bgcolor: "#FFF7ED", color: "#B45309", borderColor: "#FED7AA" };
    case "low":
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
    default:
      return { bgcolor: "#F8FAFC", color: "#475569", borderColor: "#E2E8F0" };
  }
}

function discoveryClosingStatusChip(status: string | null | undefined) {
  switch ((status || "").toLowerCase()) {
    case "open":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "closing_soon":
      return { bgcolor: "#FFF7ED", color: "#B45309", borderColor: "#FED7AA" };
    case "expired":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
    default:
      return { bgcolor: "#F8FAFC", color: "#475569", borderColor: "#E2E8F0" };
  }
}

function connectorCategoryLabel(connector: AugmisBusinessConnector) {
  if (connector.metadata?.is_test_connector) {
    return CONNECTOR_TEST_LABEL;
  }
  return CONNECTOR_PRODUCTION_LABEL;
}

function connectorPrimaryIcon(connector: AugmisBusinessConnector) {
  if (connector.connector_type === "ted_procurement" || connector.source_category === "procurement") {
    return <AccountBalanceOutlinedIcon sx={{ color: "#0F766E", fontSize: 18 }} />;
  }
  if (connector.source_category === "search") {
    return <SearchRoundedIcon sx={{ color: "#1D4ED8", fontSize: 18 }} />;
  }
  return <CableOutlinedIcon sx={{ color: "#B45309", fontSize: 18 }} />;
}

function selectedConnectorProvider(connector: AugmisBusinessConnector | null) {
  const configuredProvider = connector?.configuration_json?.provider;
  return typeof configuredProvider === "string" && configuredProvider.trim()
    ? configuredProvider.trim().toLowerCase()
    : "tavily";
}

function credentialStatusChip(status: AugmisBusinessConnectorCredentialStatus | null) {
  if (!status || !status.configured) {
    return { bgcolor: "#FFF7ED", color: "#B45309", borderColor: "#FED7AA" };
  }
  if (status.credential_source === "environment") {
    return { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
  }
  return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
}

function searchProviderStatusChip(provider: AugmisBusinessSearchProvider) {
  if (!provider.enabled) {
    return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
  }
  if (provider.connection_status === "success") {
    return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
  }
  if (provider.connection_status === "failed") {
    return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
  }
  return { bgcolor: "#FFF7ED", color: "#B45309", borderColor: "#FED7AA" };
}

function buildSearchProviderForm(): SearchProviderForm {
  return {
    display_name: "",
    provider_code: "",
    provider_type: "generic_rest",
    enabled: true,
    description: "",
    credential_type: "api_key",
    base_search_url: "",
    http_method: "get",
    authentication_type: "api_key_header",
    api_key_header_name: "X-API-Key",
    query_parameter_name: "q",
    results_path: "results",
    title_field: "title",
    url_field: "url",
    snippet_field: "snippet",
    score_field: "score",
    published_date_field: "",
    page_parameter: "",
    page_size_parameter: "",
  };
}

function buildDefaultProfileForm(): SearchProfileForm {
  return {
    name: "Default AUGMIS Discovery Profile",
    target_regions_json: [],
    target_countries_json: [],
    target_industries_json: [],
    include_keywords_json: [],
    include_technologies_json: [],
    include_capabilities_json: [],
    exclude_keywords_json: [],
    excluded_domains_json: [],
    excluded_categories_json: [],
    minimum_budget: "",
    currencies_json: ["USD", "EUR", "GBP"],
    allow_budget_unknown: true,
    solo_feasibility_preference: "",
    small_team_allowed: true,
    max_delivery_months: "",
    max_age_days: "30",
  };
}

function profileToForm(profile: AugmisBusinessSearchProfile): SearchProfileForm {
  return {
    name: profile.name,
    target_regions_json: profile.target_regions_json,
    target_countries_json: profile.target_countries_json,
    target_industries_json: profile.target_industries_json,
    include_keywords_json: profile.include_keywords_json,
    include_technologies_json: profile.include_technologies_json,
    include_capabilities_json: profile.include_capabilities_json,
    exclude_keywords_json: profile.exclude_keywords_json,
    excluded_domains_json: profile.excluded_domains_json,
    excluded_categories_json: profile.excluded_categories_json,
    minimum_budget: profile.minimum_budget == null ? "" : String(profile.minimum_budget),
    currencies_json: profile.currencies_json,
    allow_budget_unknown: profile.allow_budget_unknown,
    solo_feasibility_preference: profile.solo_feasibility_preference ?? "",
    small_team_allowed: profile.small_team_allowed,
    max_delivery_months:
      profile.max_delivery_months == null ? "" : String(profile.max_delivery_months),
    max_age_days: profile.max_age_days == null ? "" : String(profile.max_age_days),
  };
}

function profileFormToPayload(form: SearchProfileForm) {
  return {
    name: form.name.trim(),
    enabled: true,
    target_regions_json: normalizeListValues(form.target_regions_json),
    target_countries_json: normalizeListValues(form.target_countries_json),
    target_industries_json: normalizeListValues(form.target_industries_json),
    include_keywords_json: normalizeListValues(form.include_keywords_json),
    include_technologies_json: normalizeListValues(form.include_technologies_json),
    include_capabilities_json: normalizeListValues(form.include_capabilities_json),
    exclude_keywords_json: normalizeListValues(form.exclude_keywords_json),
    excluded_domains_json: normalizeListValues(form.excluded_domains_json),
    excluded_categories_json: normalizeListValues(form.excluded_categories_json),
    minimum_budget: normalizeOptionalNumber(form.minimum_budget),
    currencies_json: normalizeListValues(form.currencies_json).map((item) => item.toUpperCase()),
    allow_budget_unknown: form.allow_budget_unknown,
    solo_feasibility_preference: normalizeOptionalString(form.solo_feasibility_preference),
    small_team_allowed: form.small_team_allowed,
    max_delivery_months: normalizeOptionalNumber(form.max_delivery_months),
    max_age_days: normalizeOptionalNumber(form.max_age_days),
  };
}

function extractRunMetadata(run: AugmisBusinessConnectorRun): ConnectorRunMetadata {
  return (run.run_metadata_json || {}) as ConnectorRunMetadata;
}

function extractDiscoverySourceMetadata(discovery: AugmisBusinessDiscovery): DiscoverySourceMetadata {
  const rawMetadata = discovery.raw_content_json as Record<string, unknown>;
  return {
    provider: typeof rawMetadata.provider === "string" ? rawMetadata.provider : undefined,
    publication_number:
      typeof rawMetadata.publication_number === "string" ? rawMetadata.publication_number : undefined,
    notice_identifier:
      typeof rawMetadata.notice_identifier === "string" ? rawMetadata.notice_identifier : undefined,
    notice_version: typeof rawMetadata.notice_version === "string" ? rawMetadata.notice_version : undefined,
    notice_type: typeof rawMetadata.notice_type === "string" ? rawMetadata.notice_type : undefined,
    procedure_type:
      typeof rawMetadata.procedure_type === "string" ? rawMetadata.procedure_type : undefined,
    contract_nature:
      typeof rawMetadata.contract_nature === "string" ? rawMetadata.contract_nature : undefined,
    cpv_codes: Array.isArray(rawMetadata.cpv_codes)
      ? rawMetadata.cpv_codes.filter((item): item is string => typeof item === "string")
      : undefined,
    official_language:
      typeof rawMetadata.official_language === "string" ? rawMetadata.official_language : undefined,
    buyer_country:
      typeof rawMetadata.buyer_country === "string" ? rawMetadata.buyer_country : undefined,
    place_of_performance: Array.isArray(rawMetadata.place_of_performance)
      ? rawMetadata.place_of_performance.filter((item): item is string => typeof item === "string")
      : undefined,
    estimated_value:
      typeof rawMetadata.estimated_value === "number" ? rawMetadata.estimated_value : null,
    estimated_currency:
      typeof rawMetadata.estimated_currency === "string" ? rawMetadata.estimated_currency : null,
    ted_summary: typeof rawMetadata.ted_summary === "string" ? rawMetadata.ted_summary : undefined,
    queries_matched: Array.isArray(rawMetadata.queries_matched)
      ? rawMetadata.queries_matched.filter((item): item is string => typeof item === "string")
      : undefined,
    best_rank: typeof rawMetadata.best_rank === "number" ? rawMetadata.best_rank : undefined,
    search_snippet: typeof rawMetadata.search_snippet === "string" ? rawMetadata.search_snippet : undefined,
    fetched_source_available:
      typeof rawMetadata.fetched_source_available === "boolean"
        ? rawMetadata.fetched_source_available
        : undefined,
    partial_source_retrieval:
      typeof rawMetadata.partial_source_retrieval === "boolean"
        ? rawMetadata.partial_source_retrieval
        : undefined,
    positive_terms: Array.isArray(rawMetadata.positive_terms)
      ? rawMetadata.positive_terms.filter((item): item is string => typeof item === "string")
      : undefined,
    negative_terms: Array.isArray(rawMetadata.negative_terms)
      ? rawMetadata.negative_terms.filter((item): item is string => typeof item === "string")
      : undefined,
    source_trust: typeof rawMetadata.source_trust === "string" ? rawMetadata.source_trust : undefined,
    fetch_error: typeof rawMetadata.fetch_error === "string" ? rawMetadata.fetch_error : undefined,
    fetch_error_code: typeof rawMetadata.fetch_error_code === "string" ? rawMetadata.fetch_error_code : undefined,
  };
}

function discoveryLanguageChip(code: string | null | undefined) {
  if (!code) {
    return { bgcolor: "#F8FAFC", color: "#475569", borderColor: "#E2E8F0" };
  }
  return { bgcolor: "#EEF2FF", color: "#3730A3", borderColor: "#C7D2FE" };
}

function discoveryDisplayTitle(discovery: AugmisBusinessDiscovery) {
  return discovery.active_translation?.translated_title || discovery.title;
}

function discoveryOriginalLabel(discovery: AugmisBusinessDiscovery) {
  return discovery.source_language_label || "Original";
}

function translatedDiscoverySummary(discovery: AugmisBusinessDiscovery) {
  const translatedDetail = discovery.active_translation?.translated_detail_json as
    | Record<string, unknown>
    | undefined;
  return (
    discovery.active_translation?.translated_summary ||
    (typeof translatedDetail?.translated_summary === "string" ? translatedDetail.translated_summary : null) ||
    null
  );
}

function translatedDiscoveryDescription(discovery: AugmisBusinessDiscovery) {
  const translatedDetail = discovery.active_translation?.translated_detail_json as
    | Record<string, unknown>
    | undefined;
  return (
    discovery.active_translation?.translated_description ||
    (typeof translatedDetail?.translated_description === "string"
      ? translatedDetail.translated_description
      : null) ||
    null
  );
}

function extractDiscoveryRawContent(discovery: AugmisBusinessDiscovery): DiscoveryRawContent {
  return (discovery.raw_content_json || {}) as DiscoveryRawContent;
}

function SearchProfileArrayEditor({
  label,
  helperText,
  placeholder,
  values,
  onAdd,
  onRemove,
}: SearchProfileArrayEditorProps) {
  const [draft, setDraft] = useState("");

  function commitDraft() {
    const trimmed = draft.trim();
    if (!trimmed) return;
    onAdd(trimmed);
    setDraft("");
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commitDraft();
    }
  }

  return (
    <Box sx={{ display: "grid", gap: 0.8 }}>
      <TextField
        size="small"
        label={label}
        helperText={helperText}
        placeholder={placeholder}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commitDraft}
        onKeyDown={handleKeyDown}
      />
      <Stack direction="row" spacing={0.75} sx={{ flexWrap: "wrap", rowGap: 0.75 }}>
        {values.length ? (
          values.map((value) => (
            <Chip
              key={`${label}-${value}`}
              label={value}
              onDelete={() => onRemove(value)}
              sx={{ borderRadius: "8px", bgcolor: "#F8FAFC" }}
            />
          ))
        ) : (
          <Typography sx={{ fontSize: 12, color: "#64748B" }}>No values added yet.</Typography>
        )}
      </Stack>
    </Box>
  );
}

function MetricCard({
  icon,
  title,
  value,
  helper,
  accent,
}: {
  icon: React.ReactNode;
  title: string;
  value: React.ReactNode;
  helper: string;
  accent: string;
}) {
  return (
    <Paper elevation={0} sx={{ p: 2, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
      <Stack direction="row" spacing={1.3} sx={{ alignItems: "flex-start" }}>
        <Box
          sx={{
            width: 42,
            height: 42,
            borderRadius: "10px",
            display: "grid",
            placeItems: "center",
            bgcolor: accent,
          }}
        >
          {icon}
        </Box>
        <Box sx={{ minWidth: 0 }}>
          <Typography
            sx={{
              fontSize: 12,
              fontWeight: 700,
              color: "#64748B",
              textTransform: "uppercase",
              letterSpacing: ".05em",
            }}
          >
            {title}
          </Typography>
          <Typography sx={{ mt: 0.65, fontSize: 26, fontWeight: 700, color: "#0F172A" }}>
            {value}
          </Typography>
          <Typography sx={{ mt: 0.35, color: "#475569", fontSize: 13 }}>{helper}</Typography>
        </Box>
      </Stack>
    </Paper>
  );
}

function MetadataMetric({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <Paper elevation={0} sx={{ p: 1.2, borderRadius: "8px", border: "1px solid #E2E8F0", bgcolor: "#F8FAFC" }}>
      <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: ".04em" }}>
        {label}
      </Typography>
      <Typography sx={{ mt: 0.45, fontSize: 18, fontWeight: 700, color: "#0F172A" }}>
        {value}
      </Typography>
    </Paper>
  );
}

export default function AugmisBusinessConnectorsPage() {
  const { hasPermission } = useAuth();
  const canRead = hasPermission("business_development:read");
  const canAdmin = hasPermission("business_development:admin");
  const canUpdate = hasPermission("business_development:update");
  const canScan = hasPermission("business_development:scan");
  const canCreate = hasPermission("business_development:create");

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [activeActionLabel, setActiveActionLabel] = useState<string | null>(null);
  const [connectors, setConnectors] = useState<AugmisBusinessConnector[]>([]);
  const [summary, setSummary] = useState({
    active_connectors: 0,
    last_scan: null as string | null,
    discoveries_today: 0,
    new_discoveries: 0,
    failed_runs: 0,
  });
  const [runs, setRuns] = useState<AugmisBusinessConnectorRun[]>([]);
  const [profiles, setProfiles] = useState<AugmisBusinessSearchProfile[]>([]);
  const [searchProviders, setSearchProviders] = useState<AugmisBusinessSearchProvider[]>([]);
  const [discoveries, setDiscoveries] = useState<AugmisBusinessDiscovery[]>([]);
  const [discoveriesTotal, setDiscoveriesTotal] = useState(0);
  const [discoveryPage, setDiscoveryPage] = useState(0);
  const [discoveryPageSize, setDiscoveryPageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sourceCategoryFilter, setSourceCategoryFilter] = useState("all");
  const [relevanceFilter, setRelevanceFilter] = useState("all");
  const [sortBy, setSortBy] = useState("newest");
  const [selectedConnector, setSelectedConnector] = useState<AugmisBusinessConnector | null>(null);
  const [selectedDiscovery, setSelectedDiscovery] = useState<AugmisBusinessDiscovery | null>(null);
  const [selectedDiscoveryDuplicates, setSelectedDiscoveryDuplicates] = useState<AugmisBusinessDiscovery[]>([]);
  const [discoveryTranslationView, setDiscoveryTranslationView] = useState<"english" | "original">("original");
  const [translatingDiscoveryId, setTranslatingDiscoveryId] = useState<string | null>(null);
  const [connectorDrawerOpen, setConnectorDrawerOpen] = useState(false);
  const [discoveryDrawerOpen, setDiscoveryDrawerOpen] = useState(false);
  const [profileDialogOpen, setProfileDialogOpen] = useState(false);
  const [profileForm, setProfileForm] = useState<SearchProfileForm | null>(null);
  const [searchProviderDialogOpen, setSearchProviderDialogOpen] = useState(false);
  const [searchProviderForm, setSearchProviderForm] = useState<SearchProviderForm>(buildSearchProviderForm());
  const [pendingProviderSelections, setPendingProviderSelections] = useState<Record<string, string>>({});
  const [credentialStatuses, setCredentialStatuses] = useState<
    Record<string, AugmisBusinessConnectorCredentialStatus>
  >({});
  const [activeCredentialProviderCode, setActiveCredentialProviderCode] = useState<string | null>(null);
  const [credentialDialogOpen, setCredentialDialogOpen] = useState(false);
  const [credentialDialogMode, setCredentialDialogMode] =
    useState<CredentialDialogMode>("configure");
  const [credentialFormValue, setCredentialFormValue] = useState("");
  const [credentialShowValue, setCredentialShowValue] = useState(false);
  const [credentialTestMessage, setCredentialTestMessage] = useState<string | null>(null);
  const [credentialTestSeverity, setCredentialTestSeverity] =
    useState<ToastSeverity>("info");
  const [clearCredentialDialogOpen, setClearCredentialDialogOpen] = useState(false);
  const [toastOpen, setToastOpen] = useState(false);
  const [toastSeverity, setToastSeverity] = useState<ToastSeverity>("info");
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const defaultProfile = profiles[0] ?? null;
  const webConnector = useMemo(
    () => connectors.find((connector) => connector.connector_type === "generic_web_search") ?? null,
    [connectors]
  );
  const fixtureConnector = useMemo(
    () => connectors.find((connector) => connector.metadata?.is_test_connector) ?? null,
    [connectors]
  );
  const tedConnector = useMemo(
    () => connectors.find((connector) => connector.connector_type === "ted_procurement") ?? null,
    [connectors]
  );

  const showToast = (message: string, severity: ToastSeverity) => {
    setToastMessage(message);
    setToastSeverity(severity);
    setToastOpen(true);
  };

  const loadConnectors = useCallback(async () => {
    const [connectorsResult, profilesResult, providersResult] = await Promise.all([
      listAugmisBusinessConnectors(),
      listAugmisBusinessSearchProfiles(),
      listAugmisBusinessSearchProviders(),
    ]);
    setConnectors(connectorsResult.data);
    setSummary(connectorsResult.summary);
    setProfiles(profilesResult.data);
    setSearchProviders(providersResult.data);
  }, []);

  const loadDiscoveries = useCallback(async () => {
    const result = await listAugmisBusinessDiscoveries({
      page: discoveryPage + 1,
      page_size: discoveryPageSize,
      search: search.trim() || undefined,
      status: statusFilter === "all" ? undefined : statusFilter,
      source_category: sourceCategoryFilter === "all" ? undefined : sourceCategoryFilter,
      relevance_band: relevanceFilter === "all" ? undefined : relevanceFilter,
      sort_by: sortBy,
    });
    setDiscoveries(result.data);
    setDiscoveriesTotal(result.pagination.total);
  }, [discoveryPage, discoveryPageSize, relevanceFilter, search, sortBy, sourceCategoryFilter, statusFilter]);

  useEffect(() => {
    if (!canRead) return;
    async function bootstrap() {
      setLoading(true);
      try {
        await loadConnectors();
      } catch (error) {
        showToast(getBackendErrorMessage(error, "Unable to load connector workspace."), "error");
      } finally {
        setLoading(false);
      }
    }
    void bootstrap();
  }, [canRead, loadConnectors]);

  useEffect(() => {
    if (!canRead) return;
    async function refreshDiscoveries() {
      try {
        await loadDiscoveries();
      } catch (error) {
        showToast(getBackendErrorMessage(error, "Unable to refresh discovery inbox."), "error");
      }
    }
    void refreshDiscoveries();
  }, [canRead, discoveryPage, discoveryPageSize, search, sourceCategoryFilter, statusFilter, loadDiscoveries]);

  const connectorById = useMemo(
    () => new Map(connectors.map((connector) => [connector.id, connector])),
    [connectors]
  );
  const selectedProvider = activeCredentialProviderCode || selectedConnectorProvider(selectedConnector);

  async function loadCredentialStatus(provider: string) {
    const result = await getAugmisBusinessConnectorCredential(provider);
    setCredentialStatuses((current) => ({
      ...current,
      [provider]: result.data,
    }));
    return result.data;
  }

  function addProfileArrayValue(field: SearchProfileArrayField, value: string) {
    setProfileForm((current) => {
      if (!current) return current;
      return {
        ...current,
        [field]: normalizeListValues([...current[field], value]),
      };
    });
  }

  function removeProfileArrayValue(field: SearchProfileArrayField, value: string) {
    setProfileForm((current) => {
      if (!current) return current;
      return {
        ...current,
        [field]: current[field].filter((item) => item.toLowerCase() !== value.toLowerCase()),
      };
    });
  }

  async function openConnectorDrawer(connector: AugmisBusinessConnector) {
    setActiveCredentialProviderCode(null);
    setSelectedConnector(connector);
    setConnectorDrawerOpen(true);
    try {
      const tasks: Promise<unknown>[] = [
        listAugmisBusinessConnectorRuns(connector.id, { page: 1, page_size: 10 }).then((result) => {
          setRuns(result.data);
        }),
      ];
      if (connector.connector_type === "generic_web_search") {
        tasks.push(loadCredentialStatus(selectedConnectorProvider(connector)));
      }
      await Promise.all(tasks);
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to load connector run history."), "error");
    }
  }

  async function openDiscoveryDrawer(discovery: AugmisBusinessDiscovery) {
    setSelectedDiscovery(discovery);
    setDiscoveryDrawerOpen(true);
    setDiscoveryTranslationView(discovery.active_translation ? "english" : "original");
    try {
      const result = await getAugmisBusinessDiscovery(discovery.id);
      setSelectedDiscovery(result.data);
      setSelectedDiscoveryDuplicates(result.duplicates || []);
      setDiscoveryTranslationView(result.data.active_translation ? "english" : "original");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to load discovery detail."), "error");
    }
  }

  async function handleTranslateDiscovery(discovery: AugmisBusinessDiscovery, force = false) {
    setTranslatingDiscoveryId(discovery.id);
    try {
      const result = await translateAugmisBusinessDiscovery(discovery.id, { force });
      const latest = await getAugmisBusinessDiscovery(discovery.id);
      setSelectedDiscovery(latest.data);
      setSelectedDiscoveryDuplicates(latest.duplicates || []);
      setDiscoveryTranslationView("english");
      await loadDiscoveries();
      showToast(result.cached ? "Saved English translation reused." : "Discovery translated to English.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Translation could not be generated."), "error");
    } finally {
      setTranslatingDiscoveryId(null);
    }
  }

  async function refreshWorkspace() {
    await Promise.all([loadConnectors(), loadDiscoveries()]);
  }

  async function handleInlineProviderSave(connector: AugmisBusinessConnector) {
    const providerCode = pendingProviderSelections[connector.id] || selectedConnectorProvider(connector);
    setBusy(true);
    setActiveActionLabel(`Saving ${connector.name} provider`);
    try {
      await setAugmisBusinessConnectorSearchProvider(connector.id, { provider_code: providerCode });
      setPendingProviderSelections((current) => {
        const next = { ...current };
        delete next[connector.id];
        return next;
      });
      await loadConnectors();
      await loadCredentialStatus(providerCode);
      showToast("Search provider updated.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to update search provider."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleScan(connector: AugmisBusinessConnector) {
    setBusy(true);
    setActiveActionLabel(`Scanning ${connector.name}`);
    try {
      await scanAugmisBusinessConnector(connector.id, { run_type: "manual" });
      await refreshWorkspace();
      const refreshedConnector = connectorById.get(connector.id) ?? connector;
      if (selectedConnector?.id === connector.id) {
        await openConnectorDrawer(refreshedConnector);
      }
      showToast("Connector scan completed.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to run connector scan."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleTest(connector: AugmisBusinessConnector) {
    setBusy(true);
    setActiveActionLabel(`Testing ${connector.name}`);
    try {
      const result = await testAugmisBusinessConnector(connector.id);
      const severity = result.data.result.success ? "success" : "warning";
      showToast(result.data.result.message, severity);
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to test connector."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleToggleConnector(connector: AugmisBusinessConnector) {
    setBusy(true);
    setActiveActionLabel(connector.enabled ? `Disabling ${connector.name}` : `Enabling ${connector.name}`);
    try {
      await updateAugmisBusinessConnector(connector.id, { enabled: !connector.enabled });
      await loadConnectors();
      showToast(connector.enabled ? "Connector disabled." : "Connector enabled.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to update connector."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleSaveConnectorProvider() {
    if (!selectedConnector) return;
    const provider = selectedConnectorProvider(selectedConnector);
    setBusy(true);
    setActiveActionLabel(`Saving ${selectedConnector.name} provider`);
    try {
      await setAugmisBusinessConnectorSearchProvider(selectedConnector.id, { provider_code: provider });
      await loadConnectors();
      await loadCredentialStatus(provider);
      const refreshedConnector = connectorById.get(selectedConnector.id) ?? selectedConnector;
      await openConnectorDrawer(refreshedConnector);
      showToast("Search provider saved.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to save search provider."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleSaveRuntimeSettings() {
    if (!selectedConnector) return;
    setBusy(true);
    setActiveActionLabel(`Saving ${selectedConnector.name} runtime settings`);
    try {
      const result = await updateAugmisBusinessConnector(selectedConnector.id, {
        configuration_json: selectedConnector.configuration_json,
      });
      await loadConnectors();
      await openConnectorDrawer(result.data);
      showToast("Runtime settings saved.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to save runtime settings."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleSaveSchedule() {
    if (!selectedConnector) return;
    setBusy(true);
    setActiveActionLabel(`Saving ${selectedConnector.name} schedule`);
    try {
      const result = await updateAugmisBusinessConnector(selectedConnector.id, {
        schedule_enabled: selectedConnector.schedule_enabled,
        schedule_type: selectedConnector.schedule_type,
        schedule_interval_minutes: selectedConnector.schedule_interval_minutes,
        schedule_day_of_week: selectedConnector.schedule_day_of_week,
        schedule_time_local: selectedConnector.schedule_time_local,
        schedule_timezone: selectedConnector.schedule_timezone,
      });
      await loadConnectors();
      await openConnectorDrawer(result.data);
      showToast("Automatic scanning schedule saved.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to save connector schedule."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleTestCredential(provider: string, transientApiKey?: string) {
    setBusy(true);
    setActiveActionLabel(`Testing ${provider} credential`);
    try {
      const result = await testAugmisBusinessConnectorCredential(
        provider,
        transientApiKey ? { api_key: transientApiKey } : {}
      );
      setCredentialStatuses((current) => ({
        ...current,
        [provider]: result.data,
      }));
      setCredentialTestMessage(result.data.result.message);
      setCredentialTestSeverity(result.data.result.success ? "success" : "warning");
    } catch (error) {
      const message = getBackendErrorMessage(error, "Unable to test provider credential.");
      setCredentialTestMessage(message);
      setCredentialTestSeverity("error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleSaveCredential() {
    const provider = selectedProvider;
    setBusy(true);
    setActiveActionLabel(`Saving ${provider} credential`);
    try {
      const result = await saveAugmisBusinessConnectorCredential(provider, {
        api_key: credentialFormValue,
      });
      setCredentialStatuses((current) => ({
        ...current,
        [provider]: result.data,
      }));
      setCredentialDialogOpen(false);
      setCredentialFormValue("");
      setCredentialShowValue(false);
      setCredentialTestMessage(null);
      showToast("Provider credential saved.", "success");
    } catch (error) {
      const message = getBackendErrorMessage(error, "Unable to save provider credential.");
      setCredentialTestMessage(message);
      setCredentialTestSeverity("error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleClearCredential() {
    const provider = selectedProvider;
    setBusy(true);
    setActiveActionLabel(`Clearing ${provider} credential`);
    try {
      const result = await deleteAugmisBusinessConnectorCredential(provider);
      setCredentialStatuses((current) => ({
        ...current,
        [provider]: result.data,
      }));
      setClearCredentialDialogOpen(false);
      showToast("Stored provider credential cleared.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to clear provider credential."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleDiscoveryAction(
    action: "shortlist" | "reject" | "import",
    discovery: AugmisBusinessDiscovery
  ) {
    setBusy(true);
    setActiveActionLabel(
      action === "import"
        ? `Importing ${discovery.title}`
        : action === "shortlist"
          ? `Shortlisting ${discovery.title}`
          : `Rejecting ${discovery.title}`
    );
    try {
      if (action === "shortlist") {
        await shortlistAugmisBusinessDiscovery(discovery.id);
      } else if (action === "reject") {
        await rejectAugmisBusinessDiscovery(discovery.id);
      } else {
        await importAugmisBusinessDiscovery(discovery.id);
      }
      await refreshWorkspace();
      if (selectedDiscovery?.id === discovery.id) {
        await openDiscoveryDrawer(discovery);
      }
      showToast(
        action === "import"
          ? "Discovery imported as an opportunity."
          : action === "shortlist"
            ? "Discovery shortlisted."
            : "Discovery rejected.",
        "success"
      );
    } catch (error) {
      showToast(
        getBackendErrorMessage(
          error,
          action === "import"
            ? "Unable to import discovery."
            : action === "shortlist"
              ? "Unable to shortlist discovery."
              : "Unable to reject discovery."
        ),
        "error"
      );
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleSaveProfile() {
    if (!profileForm) return;
    setBusy(true);
    setActiveActionLabel("Saving search profile");
    try {
      const payload = profileFormToPayload(profileForm);
      if (defaultProfile) {
        await updateAugmisBusinessSearchProfile(defaultProfile.id, payload);
      } else {
        await createAugmisBusinessSearchProfile(payload);
      }
      await loadConnectors();
      setProfileDialogOpen(false);
      showToast("Search profile saved.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to save search profile."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleCreateSearchProvider() {
    setBusy(true);
    setActiveActionLabel("Creating search provider");
    try {
      await createAugmisBusinessSearchProvider({
        provider_code: searchProviderForm.provider_code || slugifyProviderCode(searchProviderForm.display_name),
        display_name: searchProviderForm.display_name,
        provider_type: "generic_rest",
        enabled: searchProviderForm.enabled,
        description: searchProviderForm.description || null,
        credential_type: searchProviderForm.credential_type,
        configuration_json: {
          base_search_url: searchProviderForm.base_search_url,
          http_method: searchProviderForm.http_method,
          authentication_type: searchProviderForm.authentication_type,
          api_key_header_name: searchProviderForm.api_key_header_name,
          query_parameter_name: searchProviderForm.query_parameter_name,
          results_path: searchProviderForm.results_path,
          title_field: searchProviderForm.title_field,
          url_field: searchProviderForm.url_field,
          snippet_field: searchProviderForm.snippet_field,
          score_field: normalizeOptionalString(searchProviderForm.score_field),
          published_date_field: normalizeOptionalString(searchProviderForm.published_date_field),
          page_parameter: normalizeOptionalString(searchProviderForm.page_parameter),
          page_size_parameter: normalizeOptionalString(searchProviderForm.page_size_parameter),
        },
      });
      await loadConnectors();
      setSearchProviderDialogOpen(false);
      setSearchProviderForm(buildSearchProviderForm());
      showToast("Search provider created.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to create search provider."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleToggleSearchProvider(provider: AugmisBusinessSearchProvider) {
    setBusy(true);
    setActiveActionLabel(`${provider.enabled ? "Disabling" : "Enabling"} ${provider.display_name}`);
    try {
      await updateAugmisBusinessSearchProvider(provider.id, { enabled: !provider.enabled });
      await loadConnectors();
      showToast(provider.enabled ? "Search provider disabled." : "Search provider enabled.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to update search provider."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleTestSearchProvider(provider: AugmisBusinessSearchProvider) {
    setBusy(true);
    setActiveActionLabel(`Testing ${provider.display_name}`);
    try {
      const result = await testAugmisBusinessSearchProvider(provider.id);
      await loadConnectors();
      showToast(result.result.message, result.result.success ? "success" : "warning");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to test search provider."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleDeleteSearchProvider(provider: AugmisBusinessSearchProvider) {
    setBusy(true);
    setActiveActionLabel(`Deleting ${provider.display_name}`);
    try {
      await deleteAugmisBusinessSearchProvider(provider.id);
      await loadConnectors();
      showToast("Search provider deleted.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to delete search provider."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  if (!canRead) {
    return (
      <OutletPage
        title="Connectors"
        description="Discovery connectors, scans, and inbox review remain within your AUGMIS workspace."
      >
        <Alert severity="warning">
          You do not currently have permission to view listener connectors or discoveries.
        </Alert>
      </OutletPage>
    );
  }

  const selectedConnectorRun = runs[0] ?? null;
  const selectedRunMetadata = selectedConnectorRun ? extractRunMetadata(selectedConnectorRun) : null;
  const selectedCredentialStatus = credentialStatuses[selectedProvider] || null;
  const selectedDiscoverySourceMetadata = selectedDiscovery
    ? extractDiscoverySourceMetadata(selectedDiscovery)
    : null;
  const selectedDiscoveryRawContent = selectedDiscovery
    ? extractDiscoveryRawContent(selectedDiscovery)
    : null;

  return (
    <>
      <OutletPage
        title="Connectors"
        description="Manage live web discovery scans, review staged findings, and import verified opportunities into AUGMIS Business."
      >
        <Stack spacing={2.25}>
          <Box
            sx={{
              display: "grid",
              gap: 1.5,
              gridTemplateColumns: {
                xs: "1fr",
                md: "repeat(2, minmax(0, 1fr))",
                xl: "repeat(5, minmax(0, 1fr))",
              },
            }}
          >
            <MetricCard
              icon={<CableOutlinedIcon sx={{ color: "#1D4ED8" }} />}
              title="Active Connectors"
              value={summary.active_connectors}
              helper="Configured and enabled connectors"
              accent="#DBEAFE"
            />
            <MetricCard
              icon={<TravelExploreOutlinedIcon sx={{ color: "#047857" }} />}
              title="Discoveries Today"
              value={summary.discoveries_today}
              helper="Fresh opportunities staged today"
              accent="#D1FAE5"
            />
            <MetricCard
              icon={<FindInPageOutlinedIcon sx={{ color: "#7C3AED" }} />}
              title="New Discoveries"
              value={summary.new_discoveries}
              helper="Awaiting operator review"
              accent="#EDE9FE"
            />
            <MetricCard
              icon={<ErrorOutlineRoundedIcon sx={{ color: "#B42318" }} />}
              title="Failed Runs"
              value={summary.failed_runs}
              helper="Runs that need attention"
              accent="#FEE2E2"
            />
            <MetricCard
              icon={<AutorenewRoundedIcon sx={{ color: "#0F766E" }} />}
              title="Last Scan"
              value={summary.last_scan ? new Date(summary.last_scan).toLocaleDateString() : "None"}
              helper={summary.last_scan ? formatDate(summary.last_scan) : "No scans recorded yet"}
              accent="#CCFBF1"
            />
          </Box>

          {busy && activeActionLabel ? (
            <Alert
              severity="info"
              icon={<CircularProgress size={16} />}
              sx={{ borderRadius: "8px" }}
            >
              {activeActionLabel}
            </Alert>
          ) : null}

          <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
            <Box
              sx={{
                px: 2.2,
                py: 1.5,
                background: "linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)",
                borderBottom: "1px solid #E2E8F0",
              }}
            >
              <Stack
                direction={{ xs: "column", lg: "row" }}
                spacing={1.5}
                sx={{ justifyContent: "space-between", alignItems: { lg: "center" } }}
              >
                <Stack spacing={0.35}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                    <HubOutlinedIcon sx={{ color: "#1D4ED8", fontSize: 20 }} />
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                      Connector Registry
                    </Typography>
                  </Stack>
                  <Typography sx={{ color: "#475569", fontSize: 13 }}>
                    Web Opportunity Search and TED European Procurement are the live production listeners. The fixture connector remains available for regression-safe testing.
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                  <Button
                    variant="outlined"
                    startIcon={<RuleFolderOutlinedIcon />}
                    onClick={() => {
                      setProfileForm(defaultProfile ? profileToForm(defaultProfile) : buildDefaultProfileForm());
                      setProfileDialogOpen(true);
                    }}
                    disabled={!canAdmin || busy}
                    sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                  >
                    Edit Search Profile
                  </Button>
                  <Button
                    variant="contained"
                    startIcon={<RefreshRoundedIcon />}
                    onClick={() => void refreshWorkspace()}
                    disabled={loading || busy}
                    sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                  >
                    Refresh
                  </Button>
                </Stack>
              </Stack>
            </Box>
            <Box sx={{ p: 2 }}>
              {loading ? (
                <Stack sx={{ py: 4, alignItems: "center" }}>
                  <CircularProgress size={30} />
                </Stack>
              ) : (
                <Table
                  size="small"
                  sx={{
                    tableLayout: "fixed",
                    width: "100%",
                    "& th, & td": {
                      px: 1.25,
                      py: 1.1,
                      verticalAlign: "top",
                    },
                  }}
                >
                  <TableHead>
                    <TableRow>
                      <TableCell>Connector</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Provider</TableCell>
                      <TableCell>Category</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Schedule</TableCell>
                      <TableCell>Last Scan</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {connectors.map((connector) => (
                      <TableRow key={connector.id} hover>
                        <TableCell>
                          <Stack spacing={0.4}>
                            <Stack direction="row" spacing={0.8} sx={{ alignItems: "center", flexWrap: "wrap" }}>
                              {connectorPrimaryIcon(connector)}
                              <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                                {connector.name}
                              </Typography>
                            </Stack>
                            <Stack direction="row" spacing={0.75} sx={{ flexWrap: "wrap" }}>
                              <Chip
                                label={connectorCategoryLabel(connector)}
                                size="small"
                                sx={
                                  connector.metadata?.is_test_connector
                                    ? { bgcolor: "#FFF7ED", color: "#B45309", border: "1px solid #FED7AA" }
                                    : { bgcolor: "#EFF6FF", color: "#1D4ED8", border: "1px solid #BFDBFE" }
                                }
                              />
                              <Typography sx={{ fontSize: 12, color: "#64748B" }}>{connector.id}</Typography>
                            </Stack>
                          </Stack>
                        </TableCell>
                        <TableCell>{connector.connector_type}</TableCell>
                        <TableCell>
                          {connector.connector_type === "generic_web_search" ? (
                            <Stack direction="row" spacing={0.75} sx={{ alignItems: "center", minWidth: 220 }}>
                              <TextField
                                select
                                size="small"
                                value={pendingProviderSelections[connector.id] || selectedConnectorProvider(connector)}
                                disabled={!canAdmin || busy}
                                onChange={(event) =>
                                  setPendingProviderSelections((current) => ({
                                    ...current,
                                    [connector.id]: event.target.value,
                                  }))
                                }
                                sx={{ minWidth: 160 }}
                              >
                                {searchProviders
                                  .filter(
                                    (provider) =>
                                      provider.enabled || provider.provider_code === selectedConnectorProvider(connector)
                                  )
                                  .map((provider) => (
                                    <MenuItem key={provider.id} value={provider.provider_code}>
                                      {provider.display_name}
                                    </MenuItem>
                                  ))}
                              </TextField>
                              {(
                                (pendingProviderSelections[connector.id] || selectedConnectorProvider(connector)) !==
                                selectedConnectorProvider(connector)
                              ) ? (
                                <Button
                                  variant="contained"
                                  size="small"
                                  disabled={!canAdmin || busy}
                                  onClick={() => void handleInlineProviderSave(connector)}
                                  sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                                >
                                  Save
                                </Button>
                              ) : null}
                            </Stack>
                          ) : connector.connector_type === "ted_procurement" ? (
                            <Chip
                              label="TED"
                              size="small"
                              sx={{ borderRadius: "8px", bgcolor: "#ECFDF3", color: "#0F766E", border: "1px solid #A7F3D0" }}
                            />
                          ) : (
                            "—"
                          )}
                        </TableCell>
                        <TableCell sx={{ textTransform: "capitalize" }}>
                          {connector.source_category === "search"
                            ? "Web Search"
                            : connector.source_category === "procurement"
                              ? "Public Procurement"
                              : connector.source_category}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={connector.status}
                            size="small"
                            sx={{ textTransform: "capitalize", border: "1px solid", ...connectorStatusChip(connector.status) }}
                          />
                        </TableCell>
                        <TableCell>
                          <Stack spacing={0.25}>
                            <Typography sx={{ fontSize: 13, fontWeight: 600, color: "#0F172A" }}>
                              {formatSchedule(connector)}
                            </Typography>
                            {connector.schedule_enabled ? (
                              <Typography sx={{ fontSize: 12, color: "#64748B" }}>
                                Next: {formatDate(connector.next_run_at)}
                              </Typography>
                            ) : null}
                          </Stack>
                        </TableCell>
                        <TableCell>{formatDate(connector.last_scan_at)}</TableCell>
                        <TableCell align="right">
                          <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end" }}>
                            <Tooltip title="View">
                              <span>
                                <IconButton size="small" onClick={() => void openConnectorDrawer(connector)}>
                                  <PreviewOutlinedIcon fontSize="small" sx={{ color: "#2563EB" }} />
                                </IconButton>
                              </span>
                            </Tooltip>
                            <Tooltip title="Test Connection">
                              <span>
                                <IconButton size="small" disabled={!canAdmin || busy} onClick={() => void handleTest(connector)}>
                                  <CheckCircleOutlineRoundedIcon fontSize="small" sx={{ color: "#0F766E" }} />
                                </IconButton>
                              </span>
                            </Tooltip>
                            <Tooltip title="Scan Now">
                              <span>
                                <IconButton size="small" disabled={!canScan || busy || connector.status === "running"} onClick={() => void handleScan(connector)}>
                                  <PlayCircleOutlineRoundedIcon fontSize="small" sx={{ color: "#1D4ED8" }} />
                                </IconButton>
                              </span>
                            </Tooltip>
                            <Tooltip title={connector.enabled ? "Disable" : "Enable"}>
                              <span>
                                <IconButton size="small" disabled={!canAdmin || busy} onClick={() => void handleToggleConnector(connector)}>
                                  <SettingsSuggestOutlinedIcon fontSize="small" sx={{ color: "#475569" }} />
                                </IconButton>
                              </span>
                            </Tooltip>
                          </Stack>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Box>
          </Paper>

          <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
            <Box
              sx={{
                px: 2.2,
                py: 1.5,
                background: "linear-gradient(90deg, #E0F2FE 0%, #F8FAFC 100%)",
                borderBottom: "1px solid #E2E8F0",
              }}
            >
              <Stack
                direction={{ xs: "column", lg: "row" }}
                spacing={1.5}
                sx={{ justifyContent: "space-between", alignItems: { lg: "center" } }}
              >
                <Stack spacing={0.35}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                    <SearchRoundedIcon sx={{ color: "#0369A1", fontSize: 20 }} />
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Search Providers</Typography>
                  </Stack>
                  <Typography sx={{ color: "#475569", fontSize: 13 }}>
                    Built-in providers remain available globally. Custom Generic REST providers are tenant-scoped and reusable from the connector provider dropdown.
                  </Typography>
                </Stack>
                {canAdmin ? (
                  <Button
                    variant="contained"
                    onClick={() => {
                      setSearchProviderForm(buildSearchProviderForm());
                      setSearchProviderDialogOpen(true);
                    }}
                    disabled={busy}
                    sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                  >
                    + Add Search Provider
                  </Button>
                ) : null}
              </Stack>
            </Box>
            <Box sx={{ p: 2 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Provider</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Credential</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Last Tested</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {searchProviders.map((provider) => (
                    <TableRow key={provider.id} hover>
                      <TableCell>
                        <Stack spacing={0.35}>
                          <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{provider.display_name}</Typography>
                          <Typography sx={{ fontSize: 12, color: "#64748B" }}>{provider.provider_code}</Typography>
                        </Stack>
                      </TableCell>
                      <TableCell>{provider.provider_type === "builtin" ? "Built-in" : "Generic REST"}</TableCell>
                      <TableCell>
                        {provider.credential_configured
                          ? provider.credential_source === "environment"
                            ? "Configured via Environment"
                            : "Configured"
                          : "Not Configured"}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={!provider.enabled ? "Disabled" : provider.connection_status === "success" ? "Success" : provider.connection_status === "failed" ? "Failed" : "Not Tested"}
                          size="small"
                          sx={{ textTransform: "capitalize", border: "1px solid", ...searchProviderStatusChip(provider) }}
                        />
                      </TableCell>
                      <TableCell>{formatDate(provider.last_tested_at)}</TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end" }}>
                          <Tooltip title="Configure Credential">
                            <span>
                              <IconButton
                                size="small"
                                disabled={!canAdmin || busy}
                                onClick={() => {
                                  setActiveCredentialProviderCode(provider.provider_code);
                                  void loadCredentialStatus(provider.provider_code);
                                  setCredentialDialogMode(provider.credential_configured ? "replace" : "configure");
                                  setCredentialDialogOpen(true);
                                  setCredentialTestMessage(null);
                                  setCredentialShowValue(false);
                                }}
                              >
                                <VisibilityOutlinedIcon fontSize="small" sx={{ color: "#2563EB" }} />
                              </IconButton>
                            </span>
                          </Tooltip>
                          <Tooltip title="Test">
                            <span>
                              <IconButton size="small" disabled={!canAdmin || busy} onClick={() => void handleTestSearchProvider(provider)}>
                                <CheckCircleOutlineRoundedIcon fontSize="small" sx={{ color: "#0F766E" }} />
                              </IconButton>
                            </span>
                          </Tooltip>
                          {provider.provider_type === "generic_rest" ? (
                            <Tooltip title={provider.enabled ? "Disable" : "Enable"}>
                              <span>
                                <IconButton size="small" disabled={!canAdmin || busy} onClick={() => void handleToggleSearchProvider(provider)}>
                                  <SettingsSuggestOutlinedIcon fontSize="small" sx={{ color: "#475569" }} />
                                </IconButton>
                              </span>
                            </Tooltip>
                          ) : null}
                          {provider.provider_type === "generic_rest" ? (
                            <Tooltip title="Delete">
                              <span>
                                <IconButton size="small" disabled={!canAdmin || busy} onClick={() => void handleDeleteSearchProvider(provider)}>
                                  <ErrorOutlineRoundedIcon fontSize="small" sx={{ color: "#B42318" }} />
                                </IconButton>
                              </span>
                            </Tooltip>
                          ) : null}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Paper>

          <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
            <Box
              sx={{
                px: 2.2,
                py: 1.5,
                background: "linear-gradient(90deg, #DCFCE7 0%, #F8FAFC 100%)",
                borderBottom: "1px solid #E2E8F0",
              }}
            >
              <Stack
                direction={{ xs: "column", lg: "row" }}
                spacing={1.5}
                sx={{ justifyContent: "space-between", alignItems: { lg: "center" } }}
              >
                <Stack spacing={0.35}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                    <TravelExploreOutlinedIcon sx={{ color: "#15803D", fontSize: 20 }} />
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Discovery Inbox</Typography>
                  </Stack>
                  <Typography sx={{ color: "#475569", fontSize: 13 }}>
                    Review search-driven discoveries, inspect source evidence, and import only verified opportunities.
                  </Typography>
                </Stack>
                <Stack
                  direction={{ xs: "column", md: "row" }}
                  spacing={1}
                  sx={{
                    width: "100%",
                    minWidth: 0,
                    flexWrap: "wrap",
                    justifyContent: { md: "flex-end" },
                    "& .MuiTextField-root": {
                      minWidth: { xs: "100%", md: 0 },
                    },
                  }}
                >
                  <TextField
                    size="small"
                    value={search}
                    onChange={(event) => {
                      setSearch(event.target.value);
                      setDiscoveryPage(0);
                    }}
                    placeholder="Search title, organisation, summary"
                    sx={{ flex: { md: "1 1 300px" }, minWidth: 0 }}
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
                    label="Source"
                    value={sourceCategoryFilter}
                    onChange={(event) => {
                      setSourceCategoryFilter(event.target.value);
                      setDiscoveryPage(0);
                    }}
                    sx={{ width: { xs: "100%", md: 150 } }}
                  >
                    <MenuItem value="all">All sources</MenuItem>
                    <MenuItem value="search">Web Opportunity Search</MenuItem>
                    <MenuItem value="procurement">TED</MenuItem>
                    <MenuItem value="fixture">Fixture</MenuItem>
                  </TextField>
                  <TextField
                    select
                    size="small"
                    label="Status"
                    value={statusFilter}
                    onChange={(event) => {
                      setStatusFilter(event.target.value);
                      setDiscoveryPage(0);
                    }}
                    sx={{ width: { xs: "100%", md: 150 } }}
                    slotProps={{
                      input: {
                        startAdornment: (
                          <InputAdornment position="start">
                            <FilterAltOutlinedIcon fontSize="small" />
                          </InputAdornment>
                        ),
                      },
                    }}
                  >
                    <MenuItem value="all">All statuses</MenuItem>
                    <MenuItem value="new">New</MenuItem>
                    <MenuItem value="shortlisted">Shortlisted</MenuItem>
                    <MenuItem value="duplicate">Duplicate</MenuItem>
                    <MenuItem value="rejected">Rejected</MenuItem>
                    <MenuItem value="imported">Imported</MenuItem>
                    <MenuItem value="irrelevant">Irrelevant</MenuItem>
                  </TextField>
                  <TextField
                    select
                    size="small"
                    label="Relevance"
                    value={relevanceFilter}
                    onChange={(event) => {
                      setRelevanceFilter(event.target.value);
                      setDiscoveryPage(0);
                    }}
                    sx={{ width: { xs: "100%", md: 150 } }}
                  >
                    <MenuItem value="all">All relevance</MenuItem>
                    <MenuItem value="strong">Strong</MenuItem>
                    <MenuItem value="good">Good</MenuItem>
                    <MenuItem value="possible">Possible</MenuItem>
                    <MenuItem value="weak">Weak</MenuItem>
                    <MenuItem value="low">Low</MenuItem>
                  </TextField>
                  <TextField
                    select
                    size="small"
                    label="Sort"
                    value={sortBy}
                    onChange={(event) => {
                      setSortBy(event.target.value);
                      setDiscoveryPage(0);
                    }}
                    sx={{ width: { xs: "100%", md: 150 } }}
                  >
                    <MenuItem value="newest">Newest</MenuItem>
                    <MenuItem value="highest_match">Highest Match</MenuItem>
                    <MenuItem value="lowest_match">Lowest Match</MenuItem>
                    <MenuItem value="closing_soon">Closing Soon</MenuItem>
                  </TextField>
                </Stack>
              </Stack>
            </Box>
            <Box sx={{ p: 2 }}>
              {discoveries.length ? (
                <>
                  <Table
                    size="small"
                    sx={{
                      tableLayout: "fixed",
                      width: "100%",
                      "& th, & td": {
                        px: { xs: 0.75, md: 1.1 },
                        py: 1.05,
                        verticalAlign: "top",
                      },
                    }}
                  >
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ width: { md: 108 } }}>Discovered</TableCell>
                        <TableCell sx={{ width: { md: 320 } }}>Opportunity</TableCell>
                        <TableCell sx={{ width: { md: 160 } }}>Organisation</TableCell>
                        <TableCell sx={{ width: { md: 112 } }}>Source</TableCell>
                        <TableCell sx={{ width: { md: 92 } }}>Country</TableCell>
                        <TableCell sx={{ width: { md: 112 } }}>Closing</TableCell>
                        <TableCell sx={{ width: { md: 118 } }}>Preliminary Match</TableCell>
                        <TableCell sx={{ width: { md: 104 } }}>Relevance Band</TableCell>
                        <TableCell sx={{ width: { md: 90 } }}>Status</TableCell>
                        <TableCell align="right" sx={{ width: { md: 64 } }}>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {discoveries.map((discovery) => (
                        <TableRow key={discovery.id} hover>
                          <TableCell sx={{ color: "#475569", fontSize: 12, whiteSpace: "normal", overflowWrap: "anywhere" }}>
                            {formatDate(discovery.discovered_at)}
                          </TableCell>
                          <TableCell>
                            <Stack spacing={0.55} sx={{ minWidth: 0 }}>
                              <Button
                                variant="text"
                                onClick={() => void openDiscoveryDrawer(discovery)}
                                sx={{
                                  px: 0,
                                  minWidth: 0,
                                  width: "100%",
                                  justifyContent: "flex-start",
                                  textAlign: "left",
                                  textTransform: "none",
                                  fontWeight: 700,
                                  color: "#1D4ED8",
                                  "& .MuiButton-startIcon": { mr: 0.5 },
                                }}
                              >
                                <Box
                                  component="span"
                                  sx={{
                                    display: "-webkit-box",
                                    WebkitBoxOrient: "vertical",
                                    WebkitLineClamp: 2,
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "normal",
                                    overflowWrap: "anywhere",
                                    width: "100%",
                                  }}
                                >
                                  {discoveryDisplayTitle(discovery)}
                                </Box>
                              </Button>
                              <Stack direction="row" spacing={0.6} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}>
                                {!discovery.source_language_is_english ? (
                                  <Chip
                                    size="small"
                                    label={`${(discovery.source_language_code || "??").toUpperCase()} · ${discovery.source_language_label || "Unknown"}`}
                                    sx={{ height: 22, fontSize: 11, border: "1px solid", ...discoveryLanguageChip(discovery.source_language_code) }}
                                  />
                                ) : null}
                                {discovery.active_translation ? (
                                  <Typography sx={{ fontSize: 11, color: "#64748B" }}>
                                    Original: {discoveryOriginalLabel(discovery)}
                                  </Typography>
                                ) : null}
                              </Stack>
                            </Stack>
                          </TableCell>
                          <TableCell sx={{ color: "#0F172A" }}>
                            <Box
                              sx={{
                                display: "-webkit-box",
                                WebkitBoxOrient: "vertical",
                                WebkitLineClamp: 2,
                                overflow: "hidden",
                                whiteSpace: "normal",
                                overflowWrap: "anywhere",
                              }}
                            >
                              {discovery.organization_name || "Not available"}
                            </Box>
                          </TableCell>
                          <TableCell sx={{ color: "#475569" }}>
                            <Box
                              sx={{
                                display: "-webkit-box",
                                WebkitBoxOrient: "vertical",
                                WebkitLineClamp: 2,
                                overflow: "hidden",
                                whiteSpace: "normal",
                                overflowWrap: "anywhere",
                              }}
                            >
                              {discovery.source_type === "public_procurement"
                                ? "TED / EU Procurement"
                                : discovery.source_name}
                            </Box>
                          </TableCell>
                          <TableCell sx={{ color: "#475569" }}>
                            <Box
                              sx={{
                                display: "-webkit-box",
                                WebkitBoxOrient: "vertical",
                                WebkitLineClamp: 2,
                                overflow: "hidden",
                                whiteSpace: "normal",
                                overflowWrap: "anywhere",
                              }}
                            >
                              {discovery.country || "Not available"}
                            </Box>
                          </TableCell>
                          <TableCell sx={{ color: "#475569", fontSize: 12, whiteSpace: "normal", overflowWrap: "anywhere" }}>
                            <Stack spacing={0.5}>
                              <Typography sx={{ fontSize: 12, color: "#475569" }}>
                                {formatDate(discovery.closing_date)}
                              </Typography>
                              <Chip
                                label={(discovery.closing_status || "unknown").replace("_", " ")}
                                size="small"
                                sx={{ width: "fit-content", textTransform: "capitalize", border: "1px solid", ...discoveryClosingStatusChip(discovery.closing_status) }}
                              />
                            </Stack>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={
                                discovery.preliminary_relevance_score == null
                                  ? "Not scored"
                                  : `Preliminary ${discovery.preliminary_relevance_score.toFixed(1)}`
                              }
                              size="small"
                              sx={{ bgcolor: "#EFF6FF", color: "#1D4ED8", maxWidth: "100%" }}
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={discovery.relevance_band || "Unknown"}
                              size="small"
                              sx={{ textTransform: "capitalize", border: "1px solid", maxWidth: "100%", ...discoveryRelevanceBandChip(discovery.relevance_band) }}
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={discovery.discovery_status}
                              size="small"
                              sx={{ textTransform: "capitalize", border: "1px solid", maxWidth: "100%", ...discoveryStatusChip(discovery.discovery_status) }}
                            />
                          </TableCell>
                          <TableCell align="right">
                            <Stack direction="row" spacing={0.15} sx={{ justifyContent: "flex-end", flexWrap: "nowrap" }}>
                              {discovery.source_url ? (
                                <Tooltip title="Open Source">
                                  <span>
                                    <IconButton
                                      size="small"
                                      component="a"
                                      href={discovery.source_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                    >
                                      <OpenInNewRoundedIcon fontSize="small" sx={{ color: "#475569" }} />
                                    </IconButton>
                                  </span>
                                </Tooltip>
                              ) : null}
                              <Tooltip title="View">
                                <span>
                                  <IconButton size="small" onClick={() => void openDiscoveryDrawer(discovery)}>
                                    <PreviewOutlinedIcon fontSize="small" sx={{ color: "#2563EB" }} />
                                  </IconButton>
                                </span>
                              </Tooltip>
                              <Tooltip title="Shortlist">
                                <span>
                                  <IconButton size="small" disabled={!canAdmin || busy || discovery.discovery_status === "imported"} onClick={() => void handleDiscoveryAction("shortlist", discovery)}>
                                    <TaskAltOutlinedIcon fontSize="small" sx={{ color: "#15803D" }} />
                                  </IconButton>
                                </span>
                              </Tooltip>
                              <Tooltip title="Reject">
                                <span>
                                  <IconButton size="small" disabled={!canAdmin || busy || discovery.discovery_status === "imported"} onClick={() => void handleDiscoveryAction("reject", discovery)}>
                                    <ErrorOutlineRoundedIcon fontSize="small" sx={{ color: "#B42318" }} />
                                  </IconButton>
                                </span>
                              </Tooltip>
                              <Tooltip title="Import as Opportunity">
                                <span>
                                  <IconButton size="small" disabled={!canCreate || busy || discovery.discovery_status === "duplicate" || discovery.discovery_status === "imported"} onClick={() => void handleDiscoveryAction("import", discovery)}>
                                    <ImportExportOutlinedIcon fontSize="small" sx={{ color: "#4338CA" }} />
                                  </IconButton>
                                </span>
                              </Tooltip>
                            </Stack>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <TablePagination
                    component="div"
                    count={discoveriesTotal}
                    page={discoveryPage}
                    onPageChange={(_, page) => setDiscoveryPage(page)}
                    rowsPerPage={discoveryPageSize}
                    onRowsPerPageChange={(event) => {
                      setDiscoveryPageSize(Number(event.target.value));
                      setDiscoveryPage(0);
                    }}
                    rowsPerPageOptions={[10, 25, 50]}
                  />
                </>
              ) : (
                <Paper elevation={0} sx={{ p: 3, borderRadius: "8px", border: "1px dashed #CBD5E1", textAlign: "center" }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                    No discoveries in the inbox yet
                  </Typography>
                  <Typography sx={{ mt: 0.75, color: "#475569" }}>
                    Run Web Opportunity Search or TED for live discovery, or use the fixture connector for safe regression testing.
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 2, justifyContent: "center", flexWrap: "wrap" }}>
                    {webConnector ? (
                      <Button
                        variant="contained"
                        startIcon={<PlayCircleOutlineRoundedIcon />}
                        onClick={() => void handleScan(webConnector)}
                        disabled={!canScan || busy}
                        sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                      >
                        Scan Web Opportunity Search
                      </Button>
                    ) : null}
                    {tedConnector ? (
                      <Button
                        variant="contained"
                        startIcon={<PlayCircleOutlineRoundedIcon />}
                        onClick={() => void handleScan(tedConnector)}
                        disabled={!canScan || busy}
                        sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#0F766E" }}
                      >
                        Scan TED
                      </Button>
                    ) : null}
                    {fixtureConnector ? (
                      <Button
                        variant="outlined"
                        startIcon={<PlayCircleOutlineRoundedIcon />}
                        onClick={() => void handleScan(fixtureConnector)}
                        disabled={!canScan || busy}
                        sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                      >
                        Scan Fixture Connector
                      </Button>
                    ) : null}
                  </Stack>
                </Paper>
              )}
            </Box>
          </Paper>
        </Stack>
      </OutletPage>

      <Drawer anchor="right" open={connectorDrawerOpen} onClose={() => setConnectorDrawerOpen(false)}>
        <Box sx={{ width: { xs: "100vw", sm: 560 }, p: 2.2 }}>
          {selectedConnector ? (
            <Stack spacing={2}>
              <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                <Box>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
                    {connectorPrimaryIcon(selectedConnector)}
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                      {selectedConnector.name}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={0.75} sx={{ mt: 0.7, flexWrap: "wrap" }}>
                    <Chip
                      label={connectorCategoryLabel(selectedConnector)}
                      size="small"
                      sx={
                        selectedConnector.metadata?.is_test_connector
                          ? { bgcolor: "#FFF7ED", color: "#B45309", border: "1px solid #FED7AA" }
                          : { bgcolor: "#EFF6FF", color: "#1D4ED8", border: "1px solid #BFDBFE" }
                      }
                    />
                    <Chip
                      label={selectedConnector.status}
                      size="small"
                      sx={{ textTransform: "capitalize", border: "1px solid", ...connectorStatusChip(selectedConnector.status) }}
                    />
                  </Stack>
                </Box>
                <Stack direction="row" spacing={0.5}>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<CheckCircleOutlineRoundedIcon />}
                    onClick={() => void handleTest(selectedConnector)}
                    disabled={!canAdmin || busy}
                    sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                  >
                    Test
                  </Button>
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={<PlayCircleOutlineRoundedIcon />}
                    onClick={() => void handleScan(selectedConnector)}
                    disabled={!canScan || busy || selectedConnector.status === "running"}
                    sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                  >
                    Scan Now
                  </Button>
                </Stack>
              </Stack>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Overview</Typography>
                <Typography sx={{ mt: 0.7, color: "#475569" }}>
                  {selectedConnector.metadata?.description || "Not available"}
                </Typography>
                <Typography sx={{ mt: 1, color: "#0F172A" }}>
                  Type: {selectedConnector.connector_type}
                </Typography>
                <Typography sx={{ color: "#0F172A" }}>
                  Category: {selectedConnector.source_category === "search"
                    ? "Web Search"
                    : selectedConnector.source_category === "procurement"
                      ? "Public Procurement"
                      : selectedConnector.source_category}
                </Typography>
                <Typography sx={{ color: "#0F172A" }}>
                  Last success: {formatDate(selectedConnector.last_success_at)}
                </Typography>
                <Typography sx={{ color: "#0F172A" }}>
                  Last error: {selectedConnector.last_error_message || "None"}
                </Typography>
              </Paper>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  spacing={1.2}
                  sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}
                >
                  <Box sx={{ minWidth: 0 }}>
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Automatic Scanning</Typography>
                    <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 13 }}>
                      Persisted connector schedule and backend-owned next-run calculation.
                    </Typography>
                  </Box>
                  <Button
                    variant="contained"
                    size="small"
                    onClick={() => void handleSaveSchedule()}
                    disabled={!canAdmin || busy}
                    sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                  >
                    Save Schedule
                  </Button>
                </Stack>
                <Box
                  sx={{
                    mt: 1.2,
                    display: "grid",
                    gap: 1,
                    gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                  }}
                >
                  <TextField
                    select
                    size="small"
                    label="Automatic Scan"
                    value={selectedConnector.schedule_enabled ? "on" : "off"}
                    disabled={!canAdmin || busy}
                    onChange={(event) =>
                      setSelectedConnector((current) =>
                        current
                          ? {
                              ...current,
                              schedule_enabled: event.target.value === "on",
                              schedule_type: event.target.value === "on" && current.schedule_type === "manual" ? "hourly_interval" : current.schedule_type,
                              schedule_interval_minutes:
                                event.target.value === "on" && !current.schedule_interval_minutes
                                  ? 360
                                  : current.schedule_interval_minutes,
                              schedule_timezone: current.schedule_timezone || "UTC",
                            }
                          : current
                      )
                    }
                  >
                    <MenuItem value="off">Off</MenuItem>
                    <MenuItem value="on">On</MenuItem>
                  </TextField>
                  <TextField
                    select
                    size="small"
                    label="Schedule"
                    value={selectedConnector.schedule_type}
                    disabled={!canAdmin || busy || !selectedConnector.schedule_enabled}
                    onChange={(event) =>
                      setSelectedConnector((current) =>
                        current
                          ? {
                              ...current,
                              schedule_type: event.target.value as AugmisBusinessConnector["schedule_type"],
                              schedule_interval_minutes:
                                event.target.value === "hourly_interval" ? current.schedule_interval_minutes || 360 : null,
                              schedule_day_of_week:
                                event.target.value === "weekly" ? current.schedule_day_of_week ?? 0 : null,
                              schedule_time_local:
                                event.target.value === "daily" || event.target.value === "weekly"
                                  ? current.schedule_time_local || "07:00"
                                  : null,
                            }
                          : current
                      )
                    }
                  >
                    <MenuItem value="hourly_interval">Hourly interval</MenuItem>
                    <MenuItem value="daily">Daily</MenuItem>
                    <MenuItem value="weekly">Weekly</MenuItem>
                  </TextField>
                  {selectedConnector.schedule_enabled && selectedConnector.schedule_type === "hourly_interval" ? (
                    <TextField
                      select
                      size="small"
                      label="Every"
                      value={String(selectedConnector.schedule_interval_minutes || 360)}
                      disabled={!canAdmin || busy}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? { ...current, schedule_interval_minutes: Number(event.target.value) }
                            : current
                        )
                      }
                    >
                      {SCHEDULE_INTERVAL_OPTIONS.map((value) => (
                        <MenuItem key={value} value={String(value)}>
                          Every {value / 60} hour{value === 60 ? "" : "s"}
                        </MenuItem>
                      ))}
                    </TextField>
                  ) : null}
                  {selectedConnector.schedule_enabled &&
                  (selectedConnector.schedule_type === "daily" || selectedConnector.schedule_type === "weekly") ? (
                    <TextField
                      select
                      size="small"
                      label="At"
                      value={selectedConnector.schedule_time_local || "07:00"}
                      disabled={!canAdmin || busy}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? { ...current, schedule_time_local: event.target.value }
                            : current
                        )
                      }
                    >
                      {SCHEDULE_TIME_OPTIONS.map((value) => (
                        <MenuItem key={value} value={value}>
                          {value}
                        </MenuItem>
                      ))}
                    </TextField>
                  ) : null}
                  {selectedConnector.schedule_enabled && selectedConnector.schedule_type === "weekly" ? (
                    <TextField
                      select
                      size="small"
                      label="Every"
                      value={String(selectedConnector.schedule_day_of_week ?? 0)}
                      disabled={!canAdmin || busy}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? { ...current, schedule_day_of_week: Number(event.target.value) }
                            : current
                        )
                      }
                    >
                      {WEEKDAY_OPTIONS.map((option) => (
                        <MenuItem key={option.value} value={String(option.value)}>
                          {option.label}
                        </MenuItem>
                      ))}
                    </TextField>
                  ) : null}
                  <TextField
                    select
                    size="small"
                    label="Timezone"
                    value={selectedConnector.schedule_timezone || "UTC"}
                    disabled={!canAdmin || busy}
                    onChange={(event) =>
                      setSelectedConnector((current) =>
                        current
                          ? { ...current, schedule_timezone: event.target.value }
                          : current
                      )
                    }
                  >
                    {SCHEDULE_TIMEZONE_OPTIONS.map((value) => (
                      <MenuItem key={value} value={value}>
                        {value}
                      </MenuItem>
                    ))}
                  </TextField>
                </Box>
                <Box
                  sx={{
                    mt: 1.2,
                    display: "grid",
                    gap: 1,
                    gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                  }}
                >
                  <MetadataMetric label="Current Schedule" value={formatSchedule(selectedConnector)} />
                  <MetadataMetric label="Next Scheduled Run" value={formatDate(selectedConnector.next_run_at)} />
                  <MetadataMetric label="Last Scheduled Run" value={formatDate(selectedConnector.last_scheduled_run_at)} />
                  <MetadataMetric label="Retry State" value={selectedConnector.schedule_retry_count ? `Attempt ${selectedConnector.schedule_retry_count + 1} pending` : "Not waiting"} />
                </Box>
              </Paper>

              {selectedConnector.connector_type === "generic_web_search" ? (
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={1.2}
                    sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Search Provider</Typography>
                      <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 13 }}>
                        Choose which provider powers Web Opportunity Search. No fallback is applied automatically.
                      </Typography>
                    </Box>
                    <Button
                      variant="contained"
                      size="small"
                      onClick={() => void handleSaveConnectorProvider()}
                      disabled={!canAdmin || busy}
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                    >
                      Save Provider
                    </Button>
                  </Stack>
                  <TextField
                    select
                    size="small"
                    label="Search Provider"
                    value={selectedConnectorProvider(selectedConnector)}
                    onChange={(event) => {
                      const nextProvider = event.target.value;
                      setSelectedConnector((current) =>
                        current
                          ? {
                              ...current,
                              configuration_json: {
                                ...current.configuration_json,
                                provider: nextProvider,
                              },
                            }
                          : current
                      );
                      if (!credentialStatuses[nextProvider]) {
                        void loadCredentialStatus(nextProvider).catch((error) => {
                          showToast(getBackendErrorMessage(error, "Unable to load provider credential status."), "error");
                        });
                      }
                    }}
                    sx={{ mt: 1.2, maxWidth: 280 }}
                  >
                    {searchProviders
                      .filter(
                        (provider) =>
                          provider.enabled || provider.provider_code === selectedConnectorProvider(selectedConnector)
                      )
                      .map((provider) => (
                        <MenuItem key={provider.id} value={provider.provider_code}>
                          {provider.display_name}
                        </MenuItem>
                      ))}
                  </TextField>
                  <Stack direction="row" spacing={1} sx={{ mt: 1.1, alignItems: "center", flexWrap: "wrap" }}>
                    <Chip
                      label={selectedProvider.toUpperCase()}
                      size="small"
                      sx={{ borderRadius: "8px", bgcolor: "#EFF6FF", color: "#1D4ED8", border: "1px solid #BFDBFE" }}
                    />
                    <Chip
                      label={
                        selectedCredentialStatus?.configured
                          ? selectedCredentialStatus.credential_source === "environment"
                            ? "Configured via Environment"
                            : "Configured"
                          : "Not Configured"
                      }
                      size="small"
                      sx={{ borderRadius: "8px", border: "1px solid", ...credentialStatusChip(selectedCredentialStatus) }}
                    />
                  </Stack>
                  <Box
                    sx={{
                      mt: 1.2,
                      display: "grid",
                      gap: 1,
                      gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                    }}
                  >
                    <MetadataMetric
                      label="Credential Source"
                      value={
                        selectedCredentialStatus?.credential_source === "tenant_secret"
                          ? "Tenant Credential"
                          : selectedCredentialStatus?.credential_source === "environment"
                            ? "Environment"
                            : "None"
                      }
                    />
                    <MetadataMetric
                      label="Connection Status"
                      value={
                        selectedCredentialStatus?.last_test_status
                          ? selectedCredentialStatus.last_test_status
                          : "Not Tested"
                      }
                    />
                    <MetadataMetric
                      label="Last Updated"
                      value={formatDate(selectedCredentialStatus?.last_updated_at || null)}
                    />
                    <MetadataMetric
                      label="Last Tested"
                      value={formatDate(selectedCredentialStatus?.last_tested_at || null)}
                    />
                  </Box>
                  {selectedCredentialStatus?.masked_hint ? (
                    <Typography sx={{ mt: 1.1, color: "#475569", fontSize: 13 }}>
                      API Key: {selectedCredentialStatus.masked_hint}
                    </Typography>
                  ) : null}
                  {selectedCredentialStatus?.storage_message ? (
                    <Alert
                      severity={selectedCredentialStatus.storage_available ? "info" : "warning"}
                      sx={{ mt: 1.1, borderRadius: "8px" }}
                    >
                      {selectedCredentialStatus.storage_message}
                    </Alert>
                  ) : null}
                  {selectedCredentialStatus?.last_test_error ? (
                    <Alert severity="error" sx={{ mt: 1.1, borderRadius: "8px" }}>
                      {selectedCredentialStatus.last_test_error}
                    </Alert>
                  ) : null}
                  <Stack direction="row" spacing={1} sx={{ mt: 1.2, flexWrap: "wrap" }}>
                    <Button
                      variant="contained"
                      size="small"
                      onClick={() => {
                        setCredentialDialogMode(
                          selectedCredentialStatus?.configured ? "replace" : "configure"
                        );
                        setCredentialDialogOpen(true);
                        setCredentialTestMessage(null);
                        setCredentialShowValue(false);
                      }}
                      disabled={!canAdmin || busy || !selectedCredentialStatus?.storage_available}
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                    >
                      {selectedCredentialStatus?.configured ? "Replace Key" : "Configure Key"}
                    </Button>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => void handleTestCredential(selectedProvider)}
                      disabled={!canAdmin || busy}
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                    >
                      Test Connection
                    </Button>
                    <Button
                      variant="outlined"
                      color="error"
                      size="small"
                      onClick={() => setClearCredentialDialogOpen(true)}
                      disabled={!canAdmin || busy || selectedCredentialStatus?.credential_source !== "tenant_secret"}
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                    >
                      Clear Stored Key
                    </Button>
                  </Stack>
                </Paper>
              ) : null}

              {selectedConnector.connector_type === "ted_procurement" ? (
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={1.2}
                    sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>TED Settings</Typography>
                      <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 13 }}>
                        Official TED search runs without an API key and uses the existing tenant search profile for targeting.
                      </Typography>
                    </Box>
                    <Button
                      variant="contained"
                      size="small"
                      onClick={() => void handleSaveRuntimeSettings()}
                      disabled={!canAdmin || busy}
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                    >
                      Save Settings
                    </Button>
                  </Stack>
                  <Box
                    sx={{
                      mt: 1.2,
                      display: "grid",
                      gap: 1,
                      gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                    }}
                  >
                    <TextField size="small" label="Authentication" value="No API Key Required" disabled />
                    <TextField size="small" label="Source" value="Official EU Publications Office / TED" disabled />
                    <TextField
                      select
                      size="small"
                      label="Lookback Period"
                      value={String(connectorNumberConfig(selectedConnector, "lookback_days", 7))}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  lookback_days: Number(event.target.value),
                                },
                              }
                            : current
                        )
                      }
                    >
                      <MenuItem value="1">1 day</MenuItem>
                      <MenuItem value="3">3 days</MenuItem>
                      <MenuItem value="7">7 days</MenuItem>
                      <MenuItem value="14">14 days</MenuItem>
                      <MenuItem value="30">30 days</MenuItem>
                    </TextField>
                    <TextField
                      select
                      size="small"
                      label="Maximum Notices Per Scan"
                      value={String(connectorNumberConfig(selectedConnector, "maximum_notices_per_scan", 50))}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  maximum_notices_per_scan: Number(event.target.value),
                                },
                              }
                            : current
                        )
                      }
                    >
                      <MenuItem value="25">25</MenuItem>
                      <MenuItem value="50">50</MenuItem>
                      <MenuItem value="100">100</MenuItem>
                      <MenuItem value="200">200</MenuItem>
                    </TextField>
                    <TextField
                      select
                      size="small"
                      label="Notice Type Scope"
                      value={String(selectedConnector.configuration_json.notice_type_mode || "competition_only")}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  notice_type_mode: event.target.value,
                                },
                              }
                            : current
                        )
                      }
                    >
                      <MenuItem value="competition_only">Competition only</MenuItem>
                      <MenuItem value="competition_and_results">Competition and results</MenuItem>
                      <MenuItem value="all_supported">All supported</MenuItem>
                    </TextField>
                    <TextField
                      select
                      size="small"
                      label="Country Scope"
                      value={String(selectedConnector.configuration_json.country_scope_mode || "search_profile")}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  country_scope_mode: event.target.value,
                                },
                              }
                            : current
                        )
                      }
                    >
                      <MenuItem value="search_profile">Use Search Profile</MenuItem>
                      <MenuItem value="eu_eea">All EU / EEA</MenuItem>
                      <MenuItem value="selected">Selected countries</MenuItem>
                    </TextField>
                    <TextField size="small" label="CPV Filtering" value="Auto / broad software-services scope" disabled />
                  </Box>
                </Paper>
              ) : null}

              {selectedConnector.connector_type === "generic_web_search" ? (
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={1.2}
                    sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Source Retrieval</Typography>
                      <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 13 }}>
                        Larger limits improve source extraction but increase bandwidth and processing time.
                      </Typography>
                    </Box>
                    <Button
                      variant="contained"
                      size="small"
                      onClick={() => void handleSaveRuntimeSettings()}
                      disabled={!canAdmin || busy}
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                    >
                      Save Runtime Settings
                    </Button>
                  </Stack>
                  <Box
                    sx={{
                      mt: 1.2,
                      display: "grid",
                      gap: 1,
                      gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                    }}
                  >
                    <TextField
                      select
                      size="small"
                      label="Fetch Source Pages"
                      value={connectorBooleanConfig(selectedConnector, "fetch_source_page", true) ? "yes" : "no"}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  fetch_source_page: event.target.value === "yes",
                                },
                              }
                            : current
                        )
                      }
                    >
                      <MenuItem value="yes">Yes</MenuItem>
                      <MenuItem value="no">No</MenuItem>
                    </TextField>
                    <TextField
                      select
                      size="small"
                      label="Maximum Page Download"
                      value={String(connectorNumberConfig(selectedConnector, "max_fetch_bytes", 100000))}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  max_fetch_bytes: Number(event.target.value),
                                },
                              }
                            : current
                        )
                      }
                      helperText="Larger limits improve source extraction but increase bandwidth and processing time."
                    >
                      <MenuItem value="50000">50 KB</MenuItem>
                      <MenuItem value="100000">100 KB</MenuItem>
                      <MenuItem value="250000">250 KB</MenuItem>
                      <MenuItem value="500000">500 KB</MenuItem>
                      <MenuItem value="1000000">1 MB</MenuItem>
                    </TextField>
                    <AdminFormTextField
                      label="Fetch Timeout (seconds)"
                      value={String(connectorNumberConfig(selectedConnector, "fetch_timeout_seconds", 10))}
                      onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  fetch_timeout_seconds: Number(event.target.value || 0),
                                },
                              }
                            : current
                        )
                      }
                    />
                    <AdminFormTextField
                      label="Maximum Extracted Text (characters)"
                      value={String(connectorNumberConfig(selectedConnector, "max_extracted_text_chars", 30000))}
                      onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  max_extracted_text_chars: Number(event.target.value || 0),
                                },
                              }
                            : current
                        )
                      }
                    />
                    <AdminFormTextField
                      label="Maximum Redirects"
                      value={String(connectorNumberConfig(selectedConnector, "max_redirects", 3))}
                      onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  max_redirects: Number(event.target.value || 0),
                                },
                              }
                            : current
                        )
                      }
                    />
                  </Box>
                  <Typography sx={{ mt: 1.2, fontWeight: 700, color: "#0F172A" }}>Scan Limits</Typography>
                  <Box
                    sx={{
                      mt: 1,
                      display: "grid",
                      gap: 1,
                      gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                    }}
                  >
                    <AdminFormTextField
                      label="Maximum Queries"
                      value={String(connectorNumberConfig(selectedConnector, "maximum_queries_per_scan", 10))}
                      onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  maximum_queries_per_scan: Number(event.target.value || 0),
                                },
                              }
                            : current
                        )
                      }
                    />
                    <AdminFormTextField
                      label="Results Per Query"
                      value={String(connectorNumberConfig(selectedConnector, "results_per_query", 10))}
                      onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  results_per_query: Number(event.target.value || 0),
                                },
                              }
                            : current
                        )
                      }
                    />
                    <AdminFormTextField
                      label="Maximum Candidates"
                      value={String(connectorNumberConfig(selectedConnector, "max_candidate_results", 100))}
                      onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  max_candidate_results: Number(event.target.value || 0),
                                },
                              }
                            : current
                        )
                      }
                    />
                    <AdminFormTextField
                      label="Maximum Source Fetches"
                      value={String(connectorNumberConfig(selectedConnector, "max_source_fetches_per_scan", 30))}
                      onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        setSelectedConnector((current) =>
                          current
                            ? {
                                ...current,
                                configuration_json: {
                                  ...current.configuration_json,
                                  max_source_fetches_per_scan: Number(event.target.value || 0),
                                },
                              }
                            : current
                        )
                      }
                    />
                  </Box>
                </Paper>
              ) : null}

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Search Profile</Typography>
                <Typography sx={{ mt: 0.7, color: "#475569" }}>
                  {profiles.find((profile) => profile.id === selectedConnector.search_profile_id)?.name || "Default profile"}
                </Typography>
              </Paper>

              {selectedRunMetadata ? (
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Latest Run Summary</Typography>
                  <Box
                    sx={{
                      mt: 1.2,
                      display: "grid",
                      gap: 1,
                      gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", md: "repeat(3, minmax(0, 1fr))" },
                    }}
                  >
                    <MetadataMetric label="Provider" value={selectedRunMetadata.provider || "Not available"} />
                    <MetadataMetric label="API Calls" value={selectedRunMetadata.api_call_count ?? 0} />
                    <MetadataMetric label="Queries" value={selectedRunMetadata.query_count ?? 0} />
                    <MetadataMetric label="Raw Results" value={selectedRunMetadata.raw_results_fetched ?? selectedRunMetadata.api_result_count ?? 0} />
                    <MetadataMetric label="Normalized" value={selectedRunMetadata.notices_normalized ?? selectedRunMetadata.accepted_candidates ?? 0} />
                    <MetadataMetric label="Filtered" value={selectedConnectorRun?.items_filtered ?? selectedRunMetadata.filtered_candidates ?? 0} />
                    <MetadataMetric label="Duplicates" value={selectedConnectorRun?.items_duplicate ?? 0} />
                    <MetadataMetric label="New Discoveries" value={selectedConnectorRun?.items_new ?? 0} />
                    <MetadataMetric label="Sources" value={selectedRunMetadata.same_scan_unique_sources ?? 0} />
                    <MetadataMetric label="Attempted Fetches" value={selectedRunMetadata.source_pages_attempted ?? 0} />
                    <MetadataMetric label="Fetched" value={selectedRunMetadata.source_pages_fetched ?? 0} />
                    <MetadataMetric label="Skipped by Limit" value={selectedRunMetadata.source_pages_skipped_due_limit ?? 0} />
                    <MetadataMetric label="Fetch Failures" value={selectedRunMetadata.fetch_failures ?? 0} />
                  </Box>
                  <Typography sx={{ mt: 1.1, color: "#64748B", fontSize: 12 }}>
                    Effective limits: {selectedRunMetadata.maximum_queries_per_scan ?? 0} queries, {selectedRunMetadata.results_per_query ?? 0} results/query, {selectedRunMetadata.max_source_fetches_per_scan ?? 0} source fetches, {formatBytes(selectedRunMetadata.max_fetch_bytes)}
                  </Typography>
                  {selectedConnector?.connector_type === "ted_procurement" && canAdmin && selectedRunMetadata.query_diagnostics?.length ? (
                    <Box
                      component="details"
                      sx={{
                        mt: 1.4,
                        borderRadius: "8px",
                        border: "1px solid #E2E8F0",
                        bgcolor: "#F8FAFC",
                        p: 1.2,
                      }}
                    >
                      <Box component="summary" sx={{ cursor: "pointer", fontWeight: 700, color: "#0F172A" }}>
                        Search Diagnostics
                      </Box>
                      <Stack spacing={1} sx={{ mt: 1 }}>
                        {selectedRunMetadata.query_diagnostics.map((diagnostic, index) => (
                          <Paper key={`${selectedConnectorRun?.id}-ted-diagnostic-${index}`} elevation={0} sx={{ p: 1, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                              {diagnostic.label || `Query ${index + 1}`}
                            </Typography>
                            <Typography sx={{ mt: 0.4, color: "#475569", fontSize: 12 }}>
                              Primary term: {diagnostic.primary_term || "Not available"} · Raw Results: {diagnostic.raw_results ?? 0} · Normalized: {diagnostic.normalized ?? 0}
                            </Typography>
                            {diagnostic.error ? (
                              <Alert severity="warning" sx={{ mt: 0.8, borderRadius: "8px" }}>
                                {diagnostic.error}
                              </Alert>
                            ) : null}
                            {diagnostic.cpv_codes?.length ? (
                              <Typography sx={{ mt: 0.8, color: "#64748B", fontSize: 12 }}>
                                CPV: {diagnostic.cpv_codes.join(", ")}
                              </Typography>
                            ) : null}
                            <Typography sx={{ mt: 0.8, color: "#0F172A", fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                              {diagnostic.query || "Not available"}
                            </Typography>
                          </Paper>
                        ))}
                      </Stack>
                    </Box>
                  ) : null}
                  {selectedRunMetadata.queries_executed?.length ? (
                    <Box sx={{ mt: 1.4 }}>
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Queries Executed</Typography>
                      <Stack direction="row" spacing={0.75} sx={{ mt: 1, flexWrap: "wrap", rowGap: 0.75 }}>
                        {selectedRunMetadata.queries_executed.map((query) => (
                          <Chip
                            key={`${selectedConnectorRun?.id}-${query}`}
                            label={query}
                            size="small"
                            sx={{ maxWidth: "100%", bgcolor: "#F8FAFC", borderRadius: "8px" }}
                          />
                        ))}
                      </Stack>
                    </Box>
                  ) : null}
                  {selectedRunMetadata.item_errors?.length ? (
                    <Alert severity="warning" sx={{ mt: 1.4, borderRadius: "8px" }}>
                      {selectedRunMetadata.item_errors[selectedRunMetadata.item_errors.length - 1]}
                    </Alert>
                  ) : null}
                </Paper>
              ) : null}

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Run History</Typography>
                <Stack spacing={1} sx={{ mt: 1 }}>
                  {runs.length ? (
                    runs.map((run) => {
                      const metadata = extractRunMetadata(run);
                      return (
                        <Paper key={run.id} elevation={0} sx={{ p: 1.2, borderRadius: "8px", border: "1px solid #E2E8F0", bgcolor: "#F8FAFC" }}>
                          <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
                            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                              {run.run_type} scan
                            </Typography>
                            <Chip label={run.status} size="small" sx={{ textTransform: "capitalize" }} />
                          </Stack>
                          <Typography sx={{ mt: 0.7, color: "#475569", fontSize: 13 }}>
                            {formatDate(run.started_at)} · Found {run.items_found} · New {run.items_new} · Duplicate {run.items_duplicate} · Filtered {run.items_filtered} · Failed {run.items_failed}
                          </Typography>
                          <Typography sx={{ mt: 0.45, color: "#64748B", fontSize: 12 }}>
                            Attempt {run.attempt_number} of {run.max_attempts}
                            {run.next_retry_at ? ` · Retry scheduled ${formatDate(run.next_retry_at)}` : ""}
                          </Typography>
                          {metadata.query_count != null || metadata.api_result_count != null ? (
                          <Typography sx={{ mt: 0.6, color: "#64748B", fontSize: 12 }}>
                              Provider {metadata.provider || "n/a"} · Queries {metadata.query_count ?? 0} · API results {metadata.api_result_count ?? 0} · Attempted {metadata.source_pages_attempted ?? 0} · Fetched {metadata.source_pages_fetched ?? 0} · Skipped {metadata.source_pages_skipped_due_limit ?? 0}
                            </Typography>
                          ) : null}
                          {run.error_summary ? (
                            <Alert severity="warning" sx={{ mt: 0.9, borderRadius: "8px" }}>
                              {run.error_summary}
                            </Alert>
                          ) : null}
                        </Paper>
                      );
                    })
                  ) : (
                    <Typography sx={{ color: "#475569" }}>No runs recorded yet.</Typography>
                  )}
                </Stack>
              </Paper>
            </Stack>
          ) : null}
        </Box>
      </Drawer>

      <Drawer anchor="right" open={discoveryDrawerOpen} onClose={() => setDiscoveryDrawerOpen(false)}>
        <Box sx={{ width: { xs: "100vw", sm: 660 }, p: 2.2 }}>
          {selectedDiscovery ? (
            <Stack spacing={2}>
              <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {discoveryTranslationView === "english" && selectedDiscovery.active_translation?.translated_title
                      ? selectedDiscovery.active_translation.translated_title
                      : selectedDiscovery.title}
                  </Typography>
                  <Typography sx={{ mt: 0.5, color: "#475569" }}>
                    {selectedDiscovery.organization_name || "Not available"}
                  </Typography>
                </Box>
                <Chip
                  label={selectedDiscovery.discovery_status}
                  size="small"
                  sx={{ textTransform: "capitalize", border: "1px solid", ...discoveryStatusChip(selectedDiscovery.discovery_status) }}
                />
              </Stack>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Source</Typography>
                <Typography sx={{ mt: 0.8, color: "#475569" }}>
                  Connector: {connectorById.get(selectedDiscovery.connector_id)?.name || selectedDiscovery.connector_id}
                </Typography>
                <Typography sx={{ color: "#475569" }}>
                  Source: {selectedDiscovery.source_type === "public_procurement"
                    ? "TED — Tenders Electronic Daily"
                    : selectedDiscovery.source_name}
                </Typography>
                <Typography sx={{ color: "#475569" }}>
                  Provider: {selectedDiscoverySourceMetadata?.provider?.toUpperCase() || "Not available"}
                </Typography>
                <Typography sx={{ color: "#475569" }}>
                  Retrieved: {formatDate(selectedDiscovery.retrieval_timestamp)}
                </Typography>
                <Typography sx={{ color: "#475569" }}>
                  Source trust: {selectedDiscoverySourceMetadata?.source_trust || "Not available"}
                </Typography>
                <Typography sx={{ color: "#475569" }}>
                  Original language: {selectedDiscovery.source_language_label || "Unknown"}
                </Typography>
                {selectedDiscovery.source_type === "public_procurement" ? (
                  <>
                    <Typography sx={{ color: "#475569" }}>
                      Publication Number: {selectedDiscoverySourceMetadata?.publication_number || "Not available"}
                    </Typography>
                    <Typography sx={{ color: "#475569" }}>
                      Notice Identifier: {selectedDiscoverySourceMetadata?.notice_identifier || "Not available"}
                    </Typography>
                    <Typography sx={{ color: "#475569" }}>
                      Notice Version: {selectedDiscoverySourceMetadata?.notice_version || "Not available"}
                    </Typography>
                  </>
                ) : null}
                {selectedDiscovery.source_url ? (
                  <Stack direction="row" spacing={1} sx={{ mt: 1.2, flexWrap: "wrap" }}>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<OpenInNewRoundedIcon />}
                      component="a"
                      href={selectedDiscovery.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                    >
                      Open Source
                    </Button>
                    <Typography sx={{ color: "#2563EB", fontSize: 13, wordBreak: "break-word", alignSelf: "center" }}>
                      <LinkOutlinedIcon sx={{ fontSize: 16, mr: 0.5, verticalAlign: "text-bottom" }} />
                      {selectedDiscovery.source_url}
                    </Typography>
                  </Stack>
                ) : null}
              </Paper>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
                  <Box>
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Translation</Typography>
                    <Typography sx={{ mt: 0.5, color: "#475569", fontSize: 13 }}>
                      AI Translation — Review Against Original
                    </Typography>
                  </Box>
                  {!selectedDiscovery.source_language_is_english ? (
                    <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
                      {selectedDiscovery.active_translation ? (
                        <>
                          <Button
                            size="small"
                            variant={discoveryTranslationView === "english" ? "contained" : "outlined"}
                            onClick={() => setDiscoveryTranslationView("english")}
                            sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                          >
                            English
                          </Button>
                          <Button
                            size="small"
                            variant={discoveryTranslationView === "original" ? "contained" : "outlined"}
                            onClick={() => setDiscoveryTranslationView("original")}
                            sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                          >
                            Original
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<TranslateOutlinedIcon />}
                            disabled={!canUpdate || translatingDiscoveryId === selectedDiscovery.id}
                            onClick={() => void handleTranslateDiscovery(selectedDiscovery, true)}
                            sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                          >
                            Regenerate Translation
                          </Button>
                        </>
                      ) : (
                        <Button
                          size="small"
                          variant="contained"
                          startIcon={<TranslateOutlinedIcon />}
                          disabled={!canUpdate || translatingDiscoveryId === selectedDiscovery.id}
                          onClick={() => void handleTranslateDiscovery(selectedDiscovery)}
                          sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                        >
                          {translatingDiscoveryId === selectedDiscovery.id ? "Translating..." : "Translate to English"}
                        </Button>
                      )}
                    </Stack>
                  ) : null}
                </Stack>
                {selectedDiscovery.source_language_is_english ? (
                  <Alert severity="info" sx={{ mt: 1.2, borderRadius: "8px" }}>
                    Original language: English. No translation required.
                  </Alert>
                ) : null}
                {translatingDiscoveryId === selectedDiscovery.id ? (
                  <Stack direction="row" spacing={1} sx={{ mt: 1.2, alignItems: "center" }}>
                    <CircularProgress size={18} />
                    <Typography sx={{ color: "#475569", fontSize: 13 }}>
                      Generating English translation...
                    </Typography>
                  </Stack>
                ) : null}
              </Paper>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Why this matched</Typography>
                <Typography sx={{ mt: 0.8, color: "#475569" }}>
                  Preliminary Match: {selectedDiscovery.preliminary_relevance_score == null ? "Not scored" : selectedDiscovery.preliminary_relevance_score.toFixed(1)}
                </Typography>
                <Stack direction="row" spacing={0.75} sx={{ mt: 1, flexWrap: "wrap", rowGap: 0.75 }}>
                  <Chip
                    label={`Band: ${selectedDiscovery.relevance_band || "Unknown"}`}
                    size="small"
                    sx={{ textTransform: "capitalize", border: "1px solid", ...discoveryRelevanceBandChip(selectedDiscovery.relevance_band) }}
                  />
                  <Chip
                    label={`Closing: ${(selectedDiscovery.closing_status || "unknown").replace("_", " ")}`}
                    size="small"
                    sx={{ textTransform: "capitalize", border: "1px solid", ...discoveryClosingStatusChip(selectedDiscovery.closing_status) }}
                  />
                </Stack>
                <Alert severity="info" sx={{ mt: 1.2, borderRadius: "8px" }}>
                  Preliminary Match is deterministic listener filtering. It is not the Phase 4 AI Fit score.
                </Alert>
                <Box sx={{ mt: 1.25 }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13 }}>Matched signals</Typography>
                  <Stack spacing={0.8} sx={{ mt: 0.8 }}>
                    {(selectedDiscovery.positive_relevance_reasons || []).length ? (
                      selectedDiscovery.positive_relevance_reasons?.map((reason) => (
                        <Typography key={`positive-${reason}`} sx={{ color: "#166534", fontSize: 13 }}>
                          ✓ {reason}
                        </Typography>
                      ))
                    ) : (
                      <Typography sx={{ color: "#475569", fontSize: 13 }}>No positive match reasons recorded.</Typography>
                    )}
                  </Stack>
                </Box>
                <Box sx={{ mt: 1.25 }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13 }}>Negative signals</Typography>
                  <Stack spacing={0.8} sx={{ mt: 0.8 }}>
                    {(selectedDiscovery.negative_relevance_reasons || []).length ? (
                      selectedDiscovery.negative_relevance_reasons?.map((reason) => (
                        <Typography key={`negative-${reason}`} sx={{ color: "#B42318", fontSize: 13 }}>
                          – {reason}
                        </Typography>
                      ))
                    ) : (
                      <Typography sx={{ color: "#475569", fontSize: 13 }}>No negative signals recorded.</Typography>
                    )}
                  </Stack>
                </Box>
              </Paper>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                  {selectedDiscovery.source_type === "public_procurement" ? "Procurement Details" : "Search Evidence"}
                </Typography>
                {selectedDiscoverySourceMetadata?.queries_matched?.length ? (
                  <>
                    <Typography sx={{ mt: 0.8, color: "#475569" }}>Queries matched</Typography>
                    <Stack direction="row" spacing={0.75} sx={{ mt: 0.8, flexWrap: "wrap", rowGap: 0.75 }}>
                      {selectedDiscoverySourceMetadata.queries_matched.map((query) => (
                        <Chip key={`${selectedDiscovery.id}-${query}`} label={query} size="small" sx={{ borderRadius: "8px", bgcolor: "#F8FAFC" }} />
                      ))}
                    </Stack>
                  </>
                ) : null}
                <Typography sx={{ mt: 1.1, color: "#475569" }}>
                  {selectedDiscovery.source_type === "public_procurement" ? "Structured Summary" : "Search Snippet"}
                </Typography>
                <Typography sx={{ mt: 0.5, color: "#334155", whiteSpace: "pre-wrap" }}>
                  {discoveryTranslationView === "english" && selectedDiscovery.active_translation
                    ? translatedDiscoverySummary(selectedDiscovery) || "Not available"
                    : selectedDiscovery.source_type === "public_procurement"
                      ? selectedDiscoverySourceMetadata?.ted_summary || selectedDiscovery.raw_summary || "Not available"
                      : selectedDiscoveryRawContent?.search_result_snippet || selectedDiscovery.raw_summary || "Not available"}
                </Typography>
                {selectedDiscovery.source_type === "public_procurement" ? (
                  <Box
                    sx={{
                      mt: 1.2,
                      display: "grid",
                      gap: 1,
                      gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                    }}
                  >
                    <MetadataMetric label="Buyer Country" value={selectedDiscoverySourceMetadata?.buyer_country || "Not available"} />
                    <MetadataMetric label="Place of Performance" value={selectedDiscoverySourceMetadata?.place_of_performance?.join(", ") || "Not available"} />
                    <MetadataMetric label="Notice Type" value={selectedDiscoverySourceMetadata?.notice_type || "Not available"} />
                    <MetadataMetric label="Procedure Type" value={selectedDiscoverySourceMetadata?.procedure_type || "Not available"} />
                    <MetadataMetric label="Contract Nature" value={selectedDiscoverySourceMetadata?.contract_nature || "Not available"} />
                    <MetadataMetric label="Language" value={selectedDiscoverySourceMetadata?.official_language || "Not available"} />
                    <MetadataMetric
                      label="Estimated Value"
                      value={
                        selectedDiscoverySourceMetadata?.estimated_value == null
                          ? "Not available"
                          : `${selectedDiscoverySourceMetadata.estimated_value}${selectedDiscoverySourceMetadata.estimated_currency ? ` ${selectedDiscoverySourceMetadata.estimated_currency}` : ""}`
                      }
                    />
                    <MetadataMetric label="CPV Codes" value={selectedDiscoverySourceMetadata?.cpv_codes?.join(", ") || "Not available"} />
                  </Box>
                ) : null}
                {selectedDiscovery.evidence_json.length ? (
                  <>
                    <Divider sx={{ my: 1.2 }} />
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Recorded Evidence</Typography>
                    <Stack spacing={1} sx={{ mt: 1 }}>
                      {selectedDiscovery.evidence_json.map((entry, index) => (
                        <Paper key={`${selectedDiscovery.id}-evidence-${index}`} elevation={0} sx={{ p: 1.1, borderRadius: "8px", border: "1px solid #E2E8F0", bgcolor: "#F8FAFC" }}>
                          {Object.entries(entry).map(([key, value]) => (
                            <Typography key={key} sx={{ color: "#475569", fontSize: 13 }}>
                              <Box component="span" sx={{ fontWeight: 700, color: "#0F172A" }}>
                                {key}:
                              </Box>{" "}
                              {typeof value === "string" ? value : JSON.stringify(value)}
                            </Typography>
                          ))}
                        </Paper>
                      ))}
                    </Stack>
                  </>
                ) : null}
              </Paper>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                  {discoveryTranslationView === "english" && selectedDiscovery.active_translation
                    ? "English Description"
                    : "Requirement"}
                </Typography>
                <Typography sx={{ mt: 0.8, color: "#475569" }}>
                  {discoveryTranslationView === "english" && selectedDiscovery.active_translation
                    ? translatedDiscoveryDescription(selectedDiscovery) || "Not available"
                    : selectedDiscovery.requirement_summary || "Not available"}
                </Typography>
              </Paper>

              {selectedDiscovery.source_type !== "public_procurement" ? (
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Fetched Source Content</Typography>
                  {selectedDiscoverySourceMetadata?.partial_source_retrieval ? (
                    <Alert severity="info" sx={{ mt: 1.1, borderRadius: "8px" }}>
                      Partial Source Retrieval
                    </Alert>
                  ) : null}
                  <Typography sx={{ mt: 0.5, color: "#334155", whiteSpace: "pre-wrap" }}>
                    {selectedDiscoveryRawContent?.fetched_source_text || "Not available"}
                  </Typography>
                  {selectedDiscoverySourceMetadata?.fetch_error ? (
                    <Alert severity="warning" sx={{ mt: 1.2, borderRadius: "8px" }}>
                      Source fetch note: {selectedDiscoverySourceMetadata.fetch_error}
                    </Alert>
                  ) : null}
                </Paper>
              ) : null}

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Duplicates</Typography>
                <Stack spacing={1} sx={{ mt: 1 }}>
                  {selectedDiscoveryDuplicates.length ? (
                    selectedDiscoveryDuplicates.map((item) => (
                      <Paper key={item.id} elevation={0} sx={{ p: 1.1, borderRadius: "8px", border: "1px solid #FED7AA", bgcolor: "#FFF7ED" }}>
                        <Typography sx={{ fontWeight: 700, color: "#9A3412" }}>{item.title}</Typography>
                        <Typography sx={{ mt: 0.5, color: "#9A3412", fontSize: 13 }}>
                          Status {item.discovery_status} · {item.organization_name || "Not available"}
                        </Typography>
                      </Paper>
                    ))
                  ) : (
                    <Typography sx={{ color: "#475569" }}>No duplicate links recorded.</Typography>
                  )}
                </Stack>
              </Paper>

              <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                <Button
                  variant="outlined"
                  startIcon={<TaskAltOutlinedIcon />}
                  disabled={!canAdmin || busy || selectedDiscovery.discovery_status === "imported"}
                  onClick={() => void handleDiscoveryAction("shortlist", selectedDiscovery)}
                  sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                >
                  Shortlist
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<ErrorOutlineRoundedIcon />}
                  disabled={!canAdmin || busy || selectedDiscovery.discovery_status === "imported"}
                  onClick={() => void handleDiscoveryAction("reject", selectedDiscovery)}
                  sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                >
                  Reject
                </Button>
                <Button
                  variant="contained"
                  startIcon={<ImportExportOutlinedIcon />}
                  disabled={!canCreate || busy || selectedDiscovery.discovery_status === "duplicate" || selectedDiscovery.discovery_status === "imported"}
                  onClick={() => void handleDiscoveryAction("import", selectedDiscovery)}
                  sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                >
                  Import as Opportunity
                </Button>
              </Stack>
            </Stack>
          ) : null}
        </Box>
      </Drawer>

      <AdminFormDialog
        open={profileDialogOpen}
        onClose={() => setProfileDialogOpen(false)}
        title="Default Search Profile"
        actions={
          <>
            <Button onClick={() => setProfileDialogOpen(false)} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button onClick={() => void handleSaveProfile()} variant="contained" disabled={busy} sx={{ textTransform: "none", bgcolor: "#2563EB" }}>
              Save Profile
            </Button>
          </>
        }
        maxWidth={820}
        stackSx={{ maxWidth: "100%" }}
      >
        {profileForm ? (
          <Box
            sx={{
              display: "grid",
              gap: 1.15,
              gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
            }}
          >
            <AdminFormTextField
              label="Profile Name"
              value={profileForm.name}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setProfileForm((current) => (current ? { ...current, name: event.target.value } : current))
              }
            />
            <SearchProfileArrayEditor
              label="Target Regions"
              helperText='Add regions one by one. Use "GLOBAL" to keep geography open.'
              placeholder="Type a region and press Enter"
              values={profileForm.target_regions_json}
              onAdd={(value) => addProfileArrayValue("target_regions_json", value)}
              onRemove={(value) => removeProfileArrayValue("target_regions_json", value)}
            />
            <SearchProfileArrayEditor
              label="Target Countries"
              helperText="Optional. Add focused markets only."
              placeholder="Type a country and press Enter"
              values={profileForm.target_countries_json}
              onAdd={(value) => addProfileArrayValue("target_countries_json", value)}
              onRemove={(value) => removeProfileArrayValue("target_countries_json", value)}
            />
            <SearchProfileArrayEditor
              label="Industries"
              helperText="Use industries that should influence discovery relevance."
              placeholder="Type an industry and press Enter"
              values={profileForm.target_industries_json}
              onAdd={(value) => addProfileArrayValue("target_industries_json", value)}
              onRemove={(value) => removeProfileArrayValue("target_industries_json", value)}
            />
            <Box sx={{ gridColumn: "1 / -1" }}>
              <SearchProfileArrayEditor
                label="Include Keywords"
                helperText="Core commercial and solution terms that should drive search intent."
                placeholder="Type a keyword and press Enter"
                values={profileForm.include_keywords_json}
                onAdd={(value) => addProfileArrayValue("include_keywords_json", value)}
                onRemove={(value) => removeProfileArrayValue("include_keywords_json", value)}
              />
            </Box>
            <Box sx={{ gridColumn: "1 / -1" }}>
              <SearchProfileArrayEditor
                label="Include Technologies"
                helperText="Technology terms used to guide query generation."
                placeholder="Type a technology and press Enter"
                values={profileForm.include_technologies_json}
                onAdd={(value) => addProfileArrayValue("include_technologies_json", value)}
                onRemove={(value) => removeProfileArrayValue("include_technologies_json", value)}
              />
            </Box>
            <Box sx={{ gridColumn: "1 / -1" }}>
              <SearchProfileArrayEditor
                label="Include Capabilities"
                helperText="Operational capabilities that should influence concept grouping."
                placeholder="Type a capability and press Enter"
                values={profileForm.include_capabilities_json}
                onAdd={(value) => addProfileArrayValue("include_capabilities_json", value)}
                onRemove={(value) => removeProfileArrayValue("include_capabilities_json", value)}
              />
            </Box>
            <Box sx={{ gridColumn: "1 / -1" }}>
              <SearchProfileArrayEditor
                label="Exclude Keywords"
                helperText="Use this to suppress jobs, training, hardware, and other non-target results."
                placeholder="Type an exclusion keyword and press Enter"
                values={profileForm.exclude_keywords_json}
                onAdd={(value) => addProfileArrayValue("exclude_keywords_json", value)}
                onRemove={(value) => removeProfileArrayValue("exclude_keywords_json", value)}
              />
            </Box>
            <Box sx={{ gridColumn: "1 / -1" }}>
              <SearchProfileArrayEditor
                label="Excluded Domains"
                helperText="Optional. Block noisy domains such as job boards or spam sources."
                placeholder="Type a domain and press Enter"
                values={profileForm.excluded_domains_json}
                onAdd={(value) => addProfileArrayValue("excluded_domains_json", value)}
                onRemove={(value) => removeProfileArrayValue("excluded_domains_json", value)}
              />
            </Box>
            <SearchProfileArrayEditor
              label="Excluded Categories"
              helperText="Optional high-level exclusion categories."
              placeholder="Type a category and press Enter"
              values={profileForm.excluded_categories_json}
              onAdd={(value) => addProfileArrayValue("excluded_categories_json", value)}
              onRemove={(value) => removeProfileArrayValue("excluded_categories_json", value)}
            />
            <AdminFormTextField
              label="Minimum Budget"
              value={profileForm.minimum_budget}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setProfileForm((current) => (current ? { ...current, minimum_budget: event.target.value } : current))
              }
            />
            <SearchProfileArrayEditor
              label="Currencies"
              helperText="Three-letter codes used for budget filtering."
              placeholder="Type a currency code and press Enter"
              values={profileForm.currencies_json}
              onAdd={(value) => addProfileArrayValue("currencies_json", value.toUpperCase())}
              onRemove={(value) => removeProfileArrayValue("currencies_json", value)}
            />
            <AdminFormTextField
              label="Solo Feasibility Preference"
              value={profileForm.solo_feasibility_preference}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setProfileForm((current) => (current ? { ...current, solo_feasibility_preference: event.target.value } : current))
              }
            />
            <AdminFormTextField
              label="Max Delivery Months"
              value={profileForm.max_delivery_months}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setProfileForm((current) => (current ? { ...current, max_delivery_months: event.target.value } : current))
              }
            />
            <AdminFormTextField
              label="Max Age Days"
              value={profileForm.max_age_days}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setProfileForm((current) => (current ? { ...current, max_age_days: event.target.value } : current))
              }
            />
            <TextField
              select
              size="small"
              label="Allow Unknown Budget"
              value={profileForm.allow_budget_unknown ? "yes" : "no"}
              onChange={(event) =>
                setProfileForm((current) => (current ? { ...current, allow_budget_unknown: event.target.value === "yes" } : current))
              }
            >
              <MenuItem value="yes">Yes</MenuItem>
              <MenuItem value="no">No</MenuItem>
            </TextField>
            <TextField
              select
              size="small"
              label="Small Team Allowed"
              value={profileForm.small_team_allowed ? "yes" : "no"}
              onChange={(event) =>
                setProfileForm((current) => (current ? { ...current, small_team_allowed: event.target.value === "yes" } : current))
              }
            >
              <MenuItem value="yes">Yes</MenuItem>
              <MenuItem value="no">No</MenuItem>
            </TextField>
          </Box>
        ) : null}
      </AdminFormDialog>

      <AdminFormDialog
        open={searchProviderDialogOpen}
        onClose={() => setSearchProviderDialogOpen(false)}
        title="Add Search Provider"
        actions={
          <>
            <Button onClick={() => setSearchProviderDialogOpen(false)} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              onClick={() => void handleCreateSearchProvider()}
              variant="contained"
              disabled={busy || !searchProviderForm.display_name.trim() || !searchProviderForm.base_search_url.trim()}
              sx={{ textTransform: "none", bgcolor: "#2563EB" }}
            >
              Save Provider
            </Button>
          </>
        }
        maxWidth={760}
        stackSx={{ maxWidth: "100%" }}
      >
        <Box
          sx={{
            display: "grid",
            gap: 1,
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
          }}
        >
          <AdminFormTextField
            label="Provider Name"
            value={searchProviderForm.display_name}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({
                ...current,
                display_name: event.target.value,
                provider_code: current.provider_code || slugifyProviderCode(event.target.value),
              }))
            }
          />
          <AdminFormTextField
            label="Provider Code"
            value={searchProviderForm.provider_code}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({
                ...current,
                provider_code: slugifyProviderCode(event.target.value),
              }))
            }
          />
          <TextField select size="small" label="Provider Type" value="generic_rest" disabled>
            <MenuItem value="generic_rest">Generic REST Search API</MenuItem>
          </TextField>
          <TextField
            select
            size="small"
            label="Enabled"
            value={searchProviderForm.enabled ? "yes" : "no"}
            onChange={(event) =>
              setSearchProviderForm((current) => ({
                ...current,
                enabled: event.target.value === "yes",
              }))
            }
          >
            <MenuItem value="yes">Yes</MenuItem>
            <MenuItem value="no">No</MenuItem>
          </TextField>
          <Box sx={{ gridColumn: "1 / -1" }}>
            <AdminFormTextField
              label="Description"
              value={searchProviderForm.description}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setSearchProviderForm((current) => ({ ...current, description: event.target.value }))
              }
            />
          </Box>
          <AdminFormTextField
            label="Base Search URL"
            value={searchProviderForm.base_search_url}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({ ...current, base_search_url: event.target.value }))
            }
          />
          <TextField
            select
            size="small"
            label="HTTP Method"
            value={searchProviderForm.http_method}
            onChange={(event) =>
              setSearchProviderForm((current) => ({ ...current, http_method: event.target.value as "get" | "post" }))
            }
          >
            <MenuItem value="get">GET</MenuItem>
            <MenuItem value="post">POST</MenuItem>
          </TextField>
          <TextField
            select
            size="small"
            label="Authentication Type"
            value={searchProviderForm.authentication_type}
            onChange={(event) =>
              setSearchProviderForm((current) => ({
                ...current,
                authentication_type: event.target.value as "api_key_header" | "bearer_token",
                credential_type: event.target.value === "bearer_token" ? "bearer_token" : "api_key",
              }))
            }
          >
            <MenuItem value="api_key_header">API Key Header</MenuItem>
            <MenuItem value="bearer_token">Bearer Token</MenuItem>
          </TextField>
          <AdminFormTextField
            label="API Key Header Name"
            value={searchProviderForm.api_key_header_name}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({ ...current, api_key_header_name: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Query Parameter Name"
            value={searchProviderForm.query_parameter_name}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({ ...current, query_parameter_name: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Results Path"
            value={searchProviderForm.results_path}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({ ...current, results_path: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Title Field"
            value={searchProviderForm.title_field}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({ ...current, title_field: event.target.value }))
            }
          />
          <AdminFormTextField
            label="URL Field"
            value={searchProviderForm.url_field}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({ ...current, url_field: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Snippet Field"
            value={searchProviderForm.snippet_field}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({ ...current, snippet_field: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Score Field"
            value={searchProviderForm.score_field}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({ ...current, score_field: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Published Date Field"
            value={searchProviderForm.published_date_field}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({ ...current, published_date_field: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Page Parameter"
            value={searchProviderForm.page_parameter}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({ ...current, page_parameter: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Page Size Parameter"
            value={searchProviderForm.page_size_parameter}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSearchProviderForm((current) => ({ ...current, page_size_parameter: event.target.value }))
            }
          />
        </Box>
      </AdminFormDialog>

      <AdminFormDialog
        open={credentialDialogOpen}
        onClose={() => {
          setCredentialDialogOpen(false);
          setCredentialFormValue("");
          setCredentialShowValue(false);
          setCredentialTestMessage(null);
        }}
        title={credentialDialogMode === "replace" ? "Replace Provider Credential" : "Configure Provider Credential"}
        actions={
          <>
            <Button
              onClick={() => {
                setCredentialDialogOpen(false);
                setCredentialFormValue("");
                setCredentialShowValue(false);
                setCredentialTestMessage(null);
              }}
              sx={{ textTransform: "none" }}
            >
              Cancel
            </Button>
            <Button
              onClick={() => void handleSaveCredential()}
              variant="contained"
              disabled={busy || !credentialFormValue.trim()}
              sx={{ textTransform: "none", bgcolor: "#2563EB" }}
            >
              Save Credential
            </Button>
          </>
        }
        maxWidth={560}
        stackSx={{ maxWidth: "100%" }}
      >
        <Stack spacing={1.15}>
          <TextField
            size="small"
            label="Provider"
            value={selectedProvider.toUpperCase()}
            slotProps={{ input: { readOnly: true } }}
          />
          <TextField
            size="small"
            label="API Key"
            type={credentialShowValue ? "text" : "password"}
            value={credentialFormValue}
            onChange={(event) => setCredentialFormValue(event.target.value)}
            autoComplete="off"
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      edge="end"
                      onClick={() => setCredentialShowValue((current) => !current)}
                    >
                      {credentialShowValue ? <VisibilityOffOutlinedIcon /> : <VisibilityOutlinedIcon />}
                    </IconButton>
                  </InputAdornment>
                ),
              },
            }}
          />
          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              onClick={() => void handleTestCredential(selectedProvider, credentialFormValue)}
              disabled={busy || !credentialFormValue.trim()}
              sx={{ textTransform: "none", fontWeight: 700 }}
            >
              Test
            </Button>
          </Stack>
          {credentialTestMessage ? (
            <Alert severity={credentialTestSeverity} sx={{ borderRadius: "8px" }}>
              {credentialTestMessage}
            </Alert>
          ) : null}
        </Stack>
      </AdminFormDialog>

      <AdminFormDialog
        open={clearCredentialDialogOpen}
        onClose={() => setClearCredentialDialogOpen(false)}
        title="Clear Stored Credential"
        actions={
          <>
            <Button onClick={() => setClearCredentialDialogOpen(false)} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              onClick={() => void handleClearCredential()}
              variant="contained"
              color="error"
              disabled={busy}
              sx={{ textTransform: "none" }}
            >
              Clear Stored Key
            </Button>
          </>
        }
        maxWidth={460}
      >
        <Alert severity="warning" sx={{ borderRadius: "8px" }}>
          Clearing the tenant credential may cause the connector to fall back to the server environment key if one exists.
        </Alert>
      </AdminFormDialog>

      <AppNotificationToast
        open={toastOpen}
        message={toastMessage}
        severity={toastSeverity}
        onClose={() => {
          setToastOpen(false);
          setToastMessage(null);
        }}
      />
    </>
  );
}
