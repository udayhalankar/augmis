"use client";

import { type ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";

import AutorenewRoundedIcon from "@mui/icons-material/AutorenewRounded";
import AccountBalanceOutlinedIcon from "@mui/icons-material/AccountBalanceOutlined";
import CableOutlinedIcon from "@mui/icons-material/CableOutlined";
import CheckCircleOutlineRoundedIcon from "@mui/icons-material/CheckCircleOutlineRounded";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
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
  LinearProgress,
  MenuItem,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";

import { AppNotificationToast } from "@/components/feedback/AppNotificationToast";
import { AdminFormDialog, AdminFormTextField } from "@/components/forms/AdminFormDialog";
import { useAuth } from "@/context/AuthContext";
import { parseApiValidationError } from "@/services/apiErrorParser";
import {
  type AugmisBusinessConnector,
  type AugmisBusinessConnectorCredentialStatus,
  type AugmisBusinessConnectorRun,
  type AugmisBusinessDiscovery,
  type AugmisBusinessDiscoveryCommercialIntelligence,
  type AugmisBusinessDiscoveryDeepAssessment,
  type AugmisBusinessDiscoveryDeepAssessmentHistoryItem,
  type AugmisBusinessSearchProfile,
  type AugmisBusinessSearchProvider,
  type AugmisBusinessWebDomain,
  type AugmisBusinessWebFetchDiagnostic,
  type AugmisBusinessWebPage,
  type AugmisBusinessWebSeed,
  createAugmisBusinessSearchProvider,
  createAugmisBusinessSearchProfile,
  createAugmisBusinessWebSeed,
  deepAssessAugmisBusinessDiscovery,
  deleteAugmisBusinessWebSeed,
  deleteAugmisBusinessConnectorCredential,
  deleteAugmisBusinessSearchProvider,
  getAugmisBusinessConnectorCredential,
  getAugmisBusinessConnectorRun,
  getAugmisBusinessDiscovery,
  getAugmisBusinessDiscoveryCommercialIntelligence,
  getAugmisBusinessDiscoveryDeepAssessment,
  importAugmisBusinessDiscovery,
  listAugmisBusinessWebDomains,
  listAugmisBusinessWebPages,
  listAugmisBusinessWebSeeds,
  listAugmisBusinessConnectorRuns,
  listAugmisBusinessConnectors,
  listAugmisBusinessDiscoveryDeepAssessments,
  listAugmisBusinessDiscoveries,
  listAugmisBusinessSearchProfiles,
  listAugmisBusinessSearchProviders,
  recalculateAugmisBusinessDiscoveryPriorities,
  recalculateAugmisBusinessDiscoveryValidity,
  reprocessAugmisBusinessDiscoveryContent,
  rejectAugmisBusinessDiscovery,
  scanAugmisBusinessConnector,
  saveAugmisBusinessConnectorCredential,
  setAugmisBusinessConnectorSearchProvider,
  shortlistAugmisBusinessDiscovery,
  stopAugmisBusinessConnectorRun,
  testAugmisBusinessWebFetchUrl,
  testAugmisBusinessConnectorCredential,
  testAugmisBusinessConnector,
  testAugmisBusinessSearchProvider,
  translateAugmisBusinessDiscovery,
  updateAugmisBusinessConnector,
  updateAugmisBusinessSearchProvider,
  updateAugmisBusinessSearchProfile,
  updateAugmisBusinessWebDomain,
  updateAugmisBusinessWebSeed,
  recrawlAugmisBusinessWebDomain,
} from "@/services/augmisBusinessService";
import BusinessPageFrame from "../components/BusinessPageFrame";
import BusinessWorkspaceModal from "../components/BusinessWorkspaceModal";

type ToastSeverity = "success" | "error" | "info" | "warning";
const HIDDEN_CONNECTOR_TYPES = new Set([
  "fixture_opportunity_connector",
  "independent_web_discovery",
  "generic_web_search",
  "ted_procurement",
  "remote_job_feed",
]);
const CONNECTOR_REGISTRY_MODAL_WIDTH = 1320;
const CONNECTOR_DETAIL_MODAL_WIDTH = 1180;
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
type CredentialFormState = {
  apiKey: string;
  appId: string;
  appKey: string;
};
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
type WebSeedForm = {
  name: string;
  seed_url: string;
  seed_type: string;
  enabled: boolean;
  crawl_scope: string;
  max_depth: string;
  max_pages: string;
  crawl_frequency: string;
  priority: string;
  country: string;
  industry: string;
  organization_name: string;
  notes: string;
};

type DiscoverySourceMetadata = {
  provider?: string;
  opportunity_class?: string;
  engagement_type?: string;
  employment_type?: string;
  remote?: boolean | null;
  location?: string | null;
  company_name?: string | null;
  company_url?: string | null;
  salary_period?: string | null;
  category?: string | null;
  tags?: string[];
  provider_project_id?: string;
  project_url?: string;
  project_type?: string;
  project_status?: string;
  skills?: string[];
  categories?: string[];
  bid_count?: number;
  bid_avg?: number | null;
  client_country?: string;
  client_location?: string;
  client_rating?: number | null;
  client_review_count?: number | null;
  client_payment_verified?: boolean | null;
  client_projects_posted?: number | null;
  client_projects_completed?: number | null;
  client_username?: string;
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
  fixture_mode?: boolean;
  fixture_version?: string;
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
  crawl_engine?: "augmis_native" | "scrapy";
  crawl_engine_display?: string;
  run_type?: string;
  max_html_response_bytes?: number;
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
  mode?: string;
  fixture_mode?: boolean;
  fixture_version?: string;
  score_bands?: string[];
  countries_searched?: string[];
  item_errors?: string[];
  notices_normalized?: number;
  query_diagnostics?: Array<{
    key?: string;
    label?: string;
    query?: string;
    primary_term?: string;
    cpv_codes?: string[];
    skills?: string[];
    raw_results?: number;
    normalized?: number;
    invalid_items?: number;
    filtered_bids?: number;
    error?: string;
  }>;
  seeds_processed?: number;
  seeds_available?: number;
  seeds_selected?: number;
  seeds_skipped_not_due?: number;
  domains_visited?: number;
  urls_queued?: number;
  requests_scheduled?: number;
  requests_attempted?: number;
  responses_received?: number;
  pages_parsed?: number;
  pages_attempted?: number;
  pages_fetched?: number;
  pages_unchanged?: number;
  pages_changed?: number;
  robots_denied?: number;
  pages_blocked?: number;
  attachments_skipped?: number;
  oversized_html_skipped?: number;
  opportunity_like_pages?: number;
  detail_pages?: number;
  listing_pages?: number;
  unknown_pages?: number;
  stale_or_error_pages?: number;
  dynamic_content_only_pages?: number;
  opportunity_candidates?: number;
  candidates_created?: number;
  candidates_accepted?: number;
  new_discoveries?: number;
  new_discovered_domains?: number;
  contacts_found?: number;
  errors?: number;
  duration_seconds?: number;
  outcome_message?: string;
  skip_summary?: string | null;
  classification_counts?: Record<string, number>;
  candidate_visibility_counts?: Record<string, number>;
  candidate_exclusion_reason_counts?: Record<string, number>;
  filter_reason_counts?: Record<string, number>;
  detail_links_discovered?: number;
  detail_links_queued?: number;
  detail_links_skipped_depth?: number;
  detail_links_skipped_domain_policy?: number;
  detail_links_fetch_failed?: number;
  detail_links_robots_denied?: number;
  skip_reason_counts?: Record<string, number>;
  skip_samples?: Array<{
    error_code?: string;
    url?: string;
    domain?: string;
    depth?: number;
    parent_url?: string | null;
    http_status?: number | null;
    message?: string;
    content_type?: string | null;
    content_length?: number | null;
    response_bytes?: number | null;
    limit_bytes?: number | null;
    resource_kind?: string | null;
    engine?: string | null;
  }>;
  fetch_failure_counts?: Record<string, number>;
  fetch_failure_samples?: Array<{
    error_code?: string;
    url?: string;
    domain?: string;
    depth?: number;
    parent_url?: string | null;
    retryable?: boolean;
    http_status?: number | null;
    message?: string;
    content_type?: string | null;
    content_length?: number | null;
    response_bytes?: number | null;
    limit_bytes?: number | null;
    resource_kind?: string | null;
    engine?: string | null;
  }>;
  candidate_outcomes?: Array<{
    title?: string;
    source_url?: string;
    page_type?: string;
    discovery_status?: string;
    relevance_score?: number;
    reason_codes?: string[];
  }>;
  stage?: string;
  stage_label?: string;
  current_domain?: string | null;
  current_url?: string | null;
  current_depth?: number | null;
  elapsed_seconds?: number;
  pending_frontier_count?: number;
  progress_percent?: number;
  batch_progress_current?: number;
  batch_progress_total?: number;
  current_batch_label?: string;
  batch_outcome?: string;
  outcome_title?: string;
  execution_anomaly?: string;
  failure_message?: string;
  filtered?: number;
  candidate_ingestion_current?: number;
  candidate_ingestion_total?: number;
};

type IndependentCandidateVisibility = {
  eligible?: boolean;
  source_type?: string;
  page_type?: string;
  reason_codes?: string[];
  reason_details?: string[];
  detail_signal_count?: number;
};

type IndependentCandidateDecision = {
  decision?: string;
  page_type?: string;
  reason_codes?: string[];
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

function formatElapsed(seconds: number | null | undefined) {
  const safe = Math.max(0, Math.floor(seconds || 0));
  const minutes = Math.floor(safe / 60);
  const remainder = safe % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

function isConnectorRunActive(status: string | null | undefined) {
  return status === "queued" || status === "running" || status === "retrying";
}

function upsertRunEntry(
  runs: AugmisBusinessConnectorRun[],
  run: AugmisBusinessConnectorRun
): AugmisBusinessConnectorRun[] {
  const next = [run, ...runs.filter((entry) => entry.id !== run.id)];
  return next.sort((left, right) => {
    const leftTime = left.started_at ? new Date(left.started_at).getTime() : 0;
    const rightTime = right.started_at ? new Date(right.started_at).getTime() : 0;
    return rightTime - leftTime;
  });
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

function connectorCrawlEngine(connector: AugmisBusinessConnector | null) {
  const raw = connector?.configuration_json?.crawl_engine;
  return raw === "scrapy" ? "scrapy" : "augmis_native";
}

function crawlEngineDisplay(value: string | null | undefined) {
  return value === "scrapy" ? "Scrapy" : "AUGMIS Native";
}

function getBackendErrorMessage(error: unknown, fallback: string) {
  return parseApiValidationError(error, fallback).message;
}

function getBackendErrorStatus(error: unknown): number | null {
  if (typeof error !== "object" || error === null) {
    return null;
  }
  const response = "response" in error ? (error as { response?: unknown }).response : null;
  if (typeof response !== "object" || response === null) {
    return null;
  }
  const status = "status" in response ? (response as { status?: unknown }).status : null;
  return typeof status === "number" ? status : null;
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

function discoveryPriorityBandChip(band: string | null | undefined) {
  switch ((band || "").toUpperCase()) {
    case "A":
      return { bgcolor: "#DBEAFE", color: "#1D4ED8", borderColor: "#93C5FD" };
    case "B":
      return { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
    case "C":
      return { bgcolor: "#FFFBEB", color: "#B45309", borderColor: "#FDE68A" };
    case "D":
      return { bgcolor: "#FFF7ED", color: "#C2410C", borderColor: "#FED7AA" };
    default:
      return { bgcolor: "#F8FAFC", color: "#475569", borderColor: "#E2E8F0" };
  }
}

function discoveryRecommendationChip(recommendation: string | null | undefined) {
  switch ((recommendation || "").toLowerCase()) {
    case "pursue":
      return { bgcolor: "#DCFCE7", color: "#166534", borderColor: "#86EFAC" };
    case "skip":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECACA" };
    default:
      return { bgcolor: "#FFFBEB", color: "#B45309", borderColor: "#FDE68A" };
  }
}

function discoveryValidityBandChip(band: string | null | undefined) {
  switch ((band || "").toLowerCase()) {
    case "confirmed":
      return { bgcolor: "#DCFCE7", color: "#166534", borderColor: "#86EFAC" };
    case "likely":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "review":
      return { bgcolor: "#FFFBEB", color: "#B45309", borderColor: "#FDE68A" };
    default:
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
  }
}

function actionabilityChip(actionability: string | null | undefined) {
  switch ((actionability || "").toUpperCase()) {
    case "ACTIONABLE":
      return { bgcolor: "#DCFCE7", color: "#166534", borderColor: "#86EFAC" };
    case "PLATFORM_ONLY":
      return { bgcolor: "#EEF2FF", color: "#4338CA", borderColor: "#C7D2FE" };
    case "RESEARCH_REQUIRED":
      return { bgcolor: "#FFF7ED", color: "#B45309", borderColor: "#FED7AA" };
    case "PARTIALLY_ACTIONABLE":
      return { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
    default:
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
  }
}

function formatDiscoveryValidityBand(band: string | null | undefined) {
  switch ((band || "").toLowerCase()) {
    case "confirmed":
      return "Confirmed";
    case "likely":
      return "Likely";
    case "review":
      return "Review";
    case "not_opportunity":
      return "Not Opportunity";
    default:
      return "Unknown";
  }
}

function formatDiscoveryValidityClass(value: string | null | undefined) {
  return (value || "Unknown").replaceAll("_", " ");
}

function formatDiscoveryActionability(value: string | null | undefined) {
  return (value || "Not available").replaceAll("_", " ");
}

function connectorCategoryLabel(connector: AugmisBusinessConnector) {
  if (connector.metadata?.is_test_connector) {
    return CONNECTOR_TEST_LABEL;
  }
  return CONNECTOR_PRODUCTION_LABEL;
}

function connectorPrimaryIcon(connector: AugmisBusinessConnector) {
  if (connector.connector_type === "independent_web_discovery") {
    return <TravelExploreOutlinedIcon sx={{ color: "#1D4ED8", fontSize: 18 }} />;
  }
  if (connector.connector_type === "ted_procurement" || connector.source_category === "procurement") {
    return <AccountBalanceOutlinedIcon sx={{ color: "#0F766E", fontSize: 18 }} />;
  }
  if (connector.connector_type === "freelancer_marketplace" || connector.source_category === "marketplace") {
    return <TravelExploreOutlinedIcon sx={{ color: "#7C3AED", fontSize: 18 }} />;
  }
  if (["remote_job_feed", "job_board_api", "remote_job_api", "job_search_api"].includes(connector.connector_type)) {
    return <HubOutlinedIcon sx={{ color: "#0F766E", fontSize: 18 }} />;
  }
  if (connector.source_category === "search") {
    return <SearchRoundedIcon sx={{ color: "#1D4ED8", fontSize: 18 }} />;
  }
  return <CableOutlinedIcon sx={{ color: "#B45309", fontSize: 18 }} />;
}

function isFreelancerMockMode(connector: AugmisBusinessConnector | null) {
  return connector?.connector_type === "freelancer_marketplace" && connector.configuration_json?.mode === "mock";
}

function selectedConnectorProvider(connector: AugmisBusinessConnector | null) {
  if (connector?.connector_type === "freelancer_marketplace") {
    return "freelancer";
  }
  if (connector?.connector_type === "remote_job_feed") {
    return "remoteok";
  }
  if (connector?.connector_type === "job_board_api") {
    return "arbeitnow";
  }
  if (connector?.connector_type === "remote_job_api") {
    return "remotive";
  }
  if (connector?.connector_type === "job_search_api") {
    return "adzuna";
  }
  const configuredProvider = connector?.configuration_json?.provider;
  return typeof configuredProvider === "string" && configuredProvider.trim()
    ? configuredProvider.trim().toLowerCase()
    : "tavily";
}

function providerSecretLabel(provider: string) {
  if (provider === "adzuna") return "App Key";
  return provider === "freelancer" ? "Access Token" : "API Key";
}

function connectorUsesCredential(connector: AugmisBusinessConnector | null) {
  if (!connector) return false;
  if (connector.connector_type === "job_search_api") return true;
  if (connector.connector_type === "freelancer_marketplace") return !isFreelancerMockMode(connector);
  return connector.connector_type === "generic_web_search";
}

function connectorCategoryDisplay(connector: AugmisBusinessConnector) {
  if (connector.connector_type === "independent_web_discovery") return "Internal Web Discovery";
  if (connector.connector_type === "ted_procurement") return "Public Procurement";
  if (connector.connector_type === "freelancer_marketplace") return "Freelance Marketplace";
  if (connector.connector_type === "remote_job_feed") return "Remote Work";
  if (connector.connector_type === "job_board_api") return "European Jobs";
  if (connector.connector_type === "remote_job_api") return "Remote Work";
  if (connector.connector_type === "job_search_api") return "Job Search";
  if (connector.source_category === "search") return "Web Search";
  return connector.source_category;
}

function discoveryInboxButtonColor(connector: AugmisBusinessConnector) {
  if (connector.metadata?.is_test_connector) return undefined;
  if (connector.connector_type === "freelancer_marketplace") return "#7C3AED";
  if (connector.connector_type === "job_board_api") return "#15803D";
  if (connector.connector_type === "remote_job_api") return "#4338CA";
  if (connector.connector_type === "job_search_api") return "#C2410C";
  return "#2563EB";
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

function buildWebSeedForm(seed?: AugmisBusinessWebSeed | null): WebSeedForm {
  return {
    name: seed?.name ?? "",
    seed_url: seed?.seed_url ?? "",
    seed_type: seed?.seed_type ?? "url",
    enabled: seed?.enabled ?? true,
    crawl_scope: seed?.crawl_scope ?? "same_domain",
    max_depth: seed ? String(seed.max_depth) : "2",
    max_pages: seed ? String(seed.max_pages) : "25",
    crawl_frequency: seed?.crawl_frequency ?? "weekly",
    priority: seed ? String(seed.priority) : "50",
    country: seed?.country ?? "",
    industry: seed?.industry ?? "",
    organization_name: seed?.organization_name ?? "",
    notes: seed?.notes ?? "",
  };
}

function webSeedFormToPayload(form: WebSeedForm) {
  return {
    name: form.name.trim(),
    seed_url: form.seed_url.trim(),
    seed_type: form.seed_type,
    enabled: form.enabled,
    crawl_scope: form.crawl_scope,
    max_depth: Number(form.max_depth || 0),
    max_pages: Number(form.max_pages || 25),
    crawl_frequency: form.crawl_frequency,
    priority: Number(form.priority || 50),
    country: normalizeOptionalString(form.country),
    industry: normalizeOptionalString(form.industry),
    organization_name: normalizeOptionalString(form.organization_name),
    notes: normalizeOptionalString(form.notes),
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

function extractIndependentCandidateVisibility(page: AugmisBusinessWebPage): IndependentCandidateVisibility {
  const sourceMetadata = (page.source_metadata_json || {}) as Record<string, unknown>;
  const fromSource = sourceMetadata.candidate_visibility as IndependentCandidateVisibility | undefined;
  const fromCandidate = ((page.opportunity_candidate_json || {}) as Record<string, unknown>)
    .candidate_visibility as IndependentCandidateVisibility | undefined;
  return fromSource || fromCandidate || {};
}

function extractIndependentCandidateDecision(page: AugmisBusinessWebPage): IndependentCandidateDecision {
  const sourceMetadata = (page.source_metadata_json || {}) as Record<string, unknown>;
  const sourceDecision = sourceMetadata.candidate_decision as IndependentCandidateDecision | undefined;
  const candidateDecision = ((page.opportunity_candidate_json || {}) as Record<string, unknown>)
    .candidate_decision as IndependentCandidateDecision | undefined;
  return sourceDecision || candidateDecision || {};
}

function recordEntriesDescending(record: Record<string, number> | undefined) {
  return Object.entries(record || {}).sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
}

function formatDiagnosticCode(code: string) {
  return code.replace(/[:_]/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

function discoverySourceDisplay(discovery: AugmisBusinessDiscovery) {
  return discovery.display_source || discovery.source_name || discovery.source_type || "Web Search";
}

function discoverySourceProviderKey(discovery: AugmisBusinessDiscovery) {
  return discovery.source_provider_key || String((discovery.raw_content_json || {}).provider || "").trim().toLowerCase() || null;
}

function discoverySourceChipStyle(discovery: AugmisBusinessDiscovery) {
  const providerKey = discoverySourceProviderKey(discovery);
  if (providerKey === "augmis_internal") {
    return { bgcolor: "#EEF2FF", color: "#3730A3", borderColor: "#C7D2FE" };
  }
  if (providerKey === "ted") {
    return { bgcolor: "#ECFEFF", color: "#0F766E", borderColor: "#99F6E4" };
  }
  if (discovery.source_type === "marketplace_project") {
    return { bgcolor: "#F5F3FF", color: "#6D28D9", borderColor: "#DDD6FE" };
  }
  if (discovery.source_type === "employment_contract") {
    return { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
  }
  return { bgcolor: "#FEF3C7", color: "#B45309", borderColor: "#FCD34D" };
}

function extractDiscoverySourceMetadata(discovery: AugmisBusinessDiscovery): DiscoverySourceMetadata {
  const rawMetadata = discovery.raw_content_json as Record<string, unknown>;
  return {
    provider: typeof rawMetadata.provider === "string" ? rawMetadata.provider : undefined,
    provider_project_id:
      typeof rawMetadata.provider_project_id === "string" ? rawMetadata.provider_project_id : undefined,
    project_url: typeof rawMetadata.project_url === "string" ? rawMetadata.project_url : undefined,
    project_type: typeof rawMetadata.project_type === "string" ? rawMetadata.project_type : undefined,
    project_status: typeof rawMetadata.project_status === "string" ? rawMetadata.project_status : undefined,
    skills: Array.isArray(rawMetadata.skills)
      ? rawMetadata.skills.filter((item): item is string => typeof item === "string")
      : undefined,
    categories: Array.isArray(rawMetadata.categories)
      ? rawMetadata.categories.filter((item): item is string => typeof item === "string")
      : undefined,
    bid_count: typeof rawMetadata.bid_count === "number" ? rawMetadata.bid_count : undefined,
    bid_avg: typeof rawMetadata.bid_avg === "number" ? rawMetadata.bid_avg : null,
    client_country: typeof rawMetadata.client_country === "string" ? rawMetadata.client_country : undefined,
    client_location: typeof rawMetadata.client_location === "string" ? rawMetadata.client_location : undefined,
    client_rating: typeof rawMetadata.client_rating === "number" ? rawMetadata.client_rating : null,
    client_review_count:
      typeof rawMetadata.client_review_count === "number" ? rawMetadata.client_review_count : null,
    client_payment_verified:
      typeof rawMetadata.client_payment_verified === "boolean"
        ? rawMetadata.client_payment_verified
        : null,
    client_projects_posted:
      typeof rawMetadata.client_projects_posted === "number" ? rawMetadata.client_projects_posted : null,
    client_projects_completed:
      typeof rawMetadata.client_projects_completed === "number"
        ? rawMetadata.client_projects_completed
        : null,
    client_username: typeof rawMetadata.client_username === "string" ? rawMetadata.client_username : undefined,
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

type NormalizedContentBlock = {
  plain_text?: string;
  safe_html?: string;
  detected_format?: string;
};

function extractDiscoveryNormalizedContent(
  discovery: AugmisBusinessDiscovery | null
): {
  requirement: NormalizedContentBlock;
  summary: NormalizedContentBlock;
  full_text: NormalizedContentBlock;
} {
  const raw = (discovery?.normalized_content_json || {}) as Record<string, unknown>;
  return {
    requirement: ((raw.requirement as NormalizedContentBlock | undefined) || {}),
    summary: ((raw.summary as NormalizedContentBlock | undefined) || {}),
    full_text: ((raw.full_text as NormalizedContentBlock | undefined) || {}),
  };
}

function renderRelativeClosing(value: string | null | undefined) {
  if (!value) {
    return "No deadline provided";
  }
  const target = new Date(value);
  if (Number.isNaN(target.getTime())) {
    return value;
  }
  const diff = Math.ceil((target.getTime() - Date.now()) / 86400000);
  if (diff < 0) {
    return "Expired";
  }
  if (diff === 0) {
    return "Closing today";
  }
  if (diff === 1) {
    return "Closing in 1 day";
  }
  return `Closing in ${diff} days`;
}

function requirementDisplayContent(
  discovery: AugmisBusinessDiscovery | null,
  view: "english" | "original"
) {
  const normalized = extractDiscoveryNormalizedContent(discovery);
  if (!discovery) {
    return {
      title: "Requirement",
      subtitle: "Source-provided description",
      text: "Not available",
      safeHtml: "",
      mode: "original" as const,
    };
  }
  if (view === "english" && discovery.active_translation) {
    return {
      title: "Requirement",
      subtitle: "English translation for operator review",
      text:
        translatedDiscoveryDescription(discovery) ||
        translatedDiscoverySummary(discovery) ||
        "Not available",
      safeHtml: "",
      mode: "english" as const,
    };
  }
  return {
    title: "Requirement",
    subtitle: "Source-provided description",
    text:
      normalized.requirement.plain_text ||
      normalized.summary.plain_text ||
      discovery.requirement_summary ||
      discovery.raw_summary ||
      "Not available",
    safeHtml: normalized.requirement.safe_html || normalized.summary.safe_html || "",
    mode: "original" as const,
  };
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

function AugmisBusinessDiscoveryWorkspace() {
  const pathname = usePathname();
  const isControlCentre = pathname === "/augmis-business/control-centre";
  const pageTitle = isControlCentre ? "Control Centre" : "Discovry Inbox";
  const pageDescription = isControlCentre
    ? "Manage connector registry controls, scan operations, and governed discovery configuration within AUGMIS Business."
    : "Review staged discoveries, inspect source evidence, and run available discovery scans within AUGMIS Business.";
  const showRegistry = isControlCentre;
  const showDiscoveryInbox = !isControlCentre;
  const { hasPermission } = useAuth();
  const canRead = hasPermission("business_development:read");
  const canAdmin = hasPermission("business_development:admin");
  const canUpdate = hasPermission("business_development:update");
  const canScan = hasPermission("business_development:scan");
  const canCreate = hasPermission("business_development:create");
  const canQualify = hasPermission("business_development:qualify");

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
  const [webSeeds, setWebSeeds] = useState<AugmisBusinessWebSeed[]>([]);
  const [webDomains, setWebDomains] = useState<AugmisBusinessWebDomain[]>([]);
  const [webPages, setWebPages] = useState<AugmisBusinessWebPage[]>([]);
  const [webPagesTotal, setWebPagesTotal] = useState(0);
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
  const [independentDiagnosticsTab, setIndependentDiagnosticsTab] = useState(0);
  const [selectedDiscovery, setSelectedDiscovery] = useState<AugmisBusinessDiscovery | null>(null);
  const [selectedDiscoveryDuplicates, setSelectedDiscoveryDuplicates] = useState<AugmisBusinessDiscovery[]>([]);
  const [selectedDiscoveryIntelligence, setSelectedDiscoveryIntelligence] =
    useState<AugmisBusinessDiscoveryCommercialIntelligence | null>(null);
  const [selectedDiscoveryDeepAssessment, setSelectedDiscoveryDeepAssessment] =
    useState<AugmisBusinessDiscoveryDeepAssessment | null>(null);
  const [selectedDiscoveryDeepAssessmentHistory, setSelectedDiscoveryDeepAssessmentHistory] =
    useState<AugmisBusinessDiscoveryDeepAssessmentHistoryItem[]>([]);
  const [showFullRequirement, setShowFullRequirement] = useState(false);
  const [showSourceDetails, setShowSourceDetails] = useState(false);
  const [discoveryTranslationView, setDiscoveryTranslationView] = useState<"english" | "original">("original");
  const [translatingDiscoveryId, setTranslatingDiscoveryId] = useState<string | null>(null);
  const [registryDialogOpen, setRegistryDialogOpen] = useState(false);
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
  const [credentialForm, setCredentialForm] = useState<CredentialFormState>({
    apiKey: "",
    appId: "",
    appKey: "",
  });
  const [credentialShowValue, setCredentialShowValue] = useState(false);
  const [credentialTestMessage, setCredentialTestMessage] = useState<string | null>(null);
  const [credentialTestSeverity, setCredentialTestSeverity] =
    useState<ToastSeverity>("info");
  const [clearCredentialDialogOpen, setClearCredentialDialogOpen] = useState(false);
  const [seedDialogOpen, setSeedDialogOpen] = useState(false);
  const [manualScanDialogOpen, setManualScanDialogOpen] = useState(false);
  const [manualScanConnector, setManualScanConnector] = useState<AugmisBusinessConnector | null>(null);
  const [manualScanEngine, setManualScanEngine] = useState<"augmis_native" | "scrapy">("augmis_native");
  const [seedForm, setSeedForm] = useState<WebSeedForm>(buildWebSeedForm());
  const [editingSeed, setEditingSeed] = useState<AugmisBusinessWebSeed | null>(null);
  const [webFetchTestResult, setWebFetchTestResult] = useState<AugmisBusinessWebFetchDiagnostic | null>(null);
  const [activeScan, setActiveScan] = useState<{ connectorId: string; runId: string } | null>(null);
  const [toastOpen, setToastOpen] = useState(false);
  const [toastSeverity, setToastSeverity] = useState<ToastSeverity>("info");
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const defaultProfile = profiles[0] ?? null;
  const visibleConnectors = useMemo(
    () => connectors.filter((connector) => !HIDDEN_CONNECTOR_TYPES.has(connector.connector_type)),
    [connectors]
  );
  const discoveryInboxConnectors = useMemo(
    () =>
      visibleConnectors.filter(
        (connector) =>
          connector.enabled &&
          (connector.metadata?.is_test_connector ||
            connector.source_category === "search" ||
            connector.source_category === "procurement" ||
            connector.source_category === "marketplace" ||
            ["job_board_api", "remote_job_api", "job_search_api"].includes(connector.connector_type))
      ),
    [visibleConnectors]
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

  const loadIndependentConnectorData = useCallback(async (connectorId: string) => {
    const [seedsResult, domainsResult, pagesResult] = await Promise.all([
      listAugmisBusinessWebSeeds(connectorId),
      listAugmisBusinessWebDomains(connectorId),
      listAugmisBusinessWebPages(connectorId, { page: 1, page_size: 10 }),
    ]);
    setWebSeeds(seedsResult.data);
    setWebDomains(domainsResult.data);
    setWebPages(pagesResult.data);
    setWebPagesTotal(pagesResult.total);
  }, []);

  useEffect(() => {
    if (!activeScan) return;
    let cancelled = false;
    let timerId: number | null = null;
    const poll = async () => {
      try {
        const result = await getAugmisBusinessConnectorRun(activeScan.connectorId, activeScan.runId);
        if (cancelled) return;
        const run = result.data;
        setRuns((current) => upsertRunEntry(current, run));
        if (!isConnectorRunActive(run.status)) {
          setActiveScan((current) =>
            current?.connectorId === activeScan.connectorId && current?.runId === activeScan.runId ? null : current
          );
          await Promise.all([loadConnectors(), loadDiscoveries()]);
          if (selectedConnector?.id === activeScan.connectorId && selectedConnector.connector_type === "independent_web_discovery") {
            await loadIndependentConnectorData(activeScan.connectorId);
          }
          const metadata = extractRunMetadata(run);
          showToast(
            metadata.outcome_message || run.error_summary || (run.status === "failed" ? "Scan failed." : "Scan completed."),
            run.status === "failed" ? "error" : "success"
          );
          return;
        }
      } catch (error) {
        if (!cancelled) {
          if (getBackendErrorStatus(error) === 404) {
            await Promise.all([loadConnectors(), loadDiscoveries()]);
            if (selectedConnector?.id === activeScan.connectorId && selectedConnector.connector_type === "independent_web_discovery") {
              await loadIndependentConnectorData(activeScan.connectorId);
            }
            showToast("Active connector run could not be found. Connector state was refreshed.", "warning");
          } else {
            showToast(getBackendErrorMessage(error, "Unable to refresh scan progress."), "error");
          }
          setActiveScan(null);
        }
        return;
      }
      if (!cancelled) {
        timerId = window.setTimeout(poll, 2000);
      }
    };
    timerId = window.setTimeout(poll, 2000);
    return () => {
      cancelled = true;
      if (timerId !== null) {
        window.clearTimeout(timerId);
      }
    };
  }, [activeScan, loadConnectors, loadDiscoveries, loadIndependentConnectorData, selectedConnector]);

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

  function resetCredentialForm() {
    setCredentialForm({ apiKey: "", appId: "", appKey: "" });
    setCredentialShowValue(false);
    setCredentialTestMessage(null);
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
    setWebFetchTestResult(null);
    setConnectorDrawerOpen(true);
    try {
      const tasks: Promise<unknown>[] = [
        listAugmisBusinessConnectorRuns(connector.id, { page: 1, page_size: 10 }).then((result) => {
          setRuns(result.data);
          const activeRun = result.data.find((run) => isConnectorRunActive(run.status));
          if (connector.active_run_id) {
            setActiveScan({ connectorId: connector.id, runId: connector.active_run_id });
          } else if (activeRun) {
            setActiveScan({ connectorId: connector.id, runId: activeRun.id });
          }
        }),
      ];
      if (connectorUsesCredential(connector)) {
        tasks.push(loadCredentialStatus(selectedConnectorProvider(connector)));
      }
      if (connector.connector_type === "independent_web_discovery") {
        tasks.push(loadIndependentConnectorData(connector.id));
      } else {
        setWebSeeds([]);
        setWebDomains([]);
        setWebPages([]);
        setWebPagesTotal(0);
      }
      await Promise.all(tasks);
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to load connector run history."), "error");
    }
  }

  async function openDiscoveryDrawer(discovery: AugmisBusinessDiscovery) {
    setSelectedDiscovery(discovery);
    setDiscoveryDrawerOpen(true);
    setShowFullRequirement(false);
    setShowSourceDetails(false);
    setDiscoveryTranslationView(discovery.active_translation ? "english" : "original");
    try {
      const [result, intelligenceResult, deepAssessmentResult, historyResult] = await Promise.all([
        getAugmisBusinessDiscovery(discovery.id),
        getAugmisBusinessDiscoveryCommercialIntelligence(discovery.id),
        getAugmisBusinessDiscoveryDeepAssessment(discovery.id),
        listAugmisBusinessDiscoveryDeepAssessments(discovery.id),
      ]);
      setSelectedDiscovery(result.data);
      setSelectedDiscoveryDuplicates(result.duplicates || []);
      setSelectedDiscoveryIntelligence(intelligenceResult.data);
      setSelectedDiscoveryDeepAssessment(deepAssessmentResult.data);
      setSelectedDiscoveryDeepAssessmentHistory(historyResult.data || []);
      setDiscoveryTranslationView(result.data.active_translation ? "english" : "original");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to load discovery detail."), "error");
    }
  }

  async function handleTranslateDiscovery(discovery: AugmisBusinessDiscovery, force = false) {
    setTranslatingDiscoveryId(discovery.id);
    try {
      const result = await translateAugmisBusinessDiscovery(discovery.id, { force });
      const [latest, intelligenceResult, deepAssessmentResult, historyResult] = await Promise.all([
        getAugmisBusinessDiscovery(discovery.id),
        getAugmisBusinessDiscoveryCommercialIntelligence(discovery.id),
        getAugmisBusinessDiscoveryDeepAssessment(discovery.id),
        listAugmisBusinessDiscoveryDeepAssessments(discovery.id),
      ]);
      setSelectedDiscovery(latest.data);
      setSelectedDiscoveryDuplicates(latest.duplicates || []);
      setSelectedDiscoveryIntelligence(intelligenceResult.data);
      setSelectedDiscoveryDeepAssessment(deepAssessmentResult.data);
      setSelectedDiscoveryDeepAssessmentHistory(historyResult.data || []);
      setDiscoveryTranslationView("english");
      await loadDiscoveries();
      showToast(result.cached ? "Saved English translation reused." : "Discovery translated to English.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Translation could not be generated."), "error");
    } finally {
      setTranslatingDiscoveryId(null);
    }
  }

  async function handleDeepAssessDiscovery(discovery: AugmisBusinessDiscovery) {
    setBusy(true);
    setActiveActionLabel(`Assessing ${discovery.title}`);
    try {
      const result = await deepAssessAugmisBusinessDiscovery(discovery.id);
      const [intelligenceResult, historyResult] = await Promise.all([
        getAugmisBusinessDiscoveryCommercialIntelligence(discovery.id),
        listAugmisBusinessDiscoveryDeepAssessments(discovery.id),
      ]);
      setSelectedDiscoveryDeepAssessment(result.data);
      setSelectedDiscoveryDeepAssessmentHistory(historyResult.data || []);
      setSelectedDiscoveryIntelligence(intelligenceResult.data);
      await loadDiscoveries();
      showToast("Deep assessment completed.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Deep assessment failed."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function refreshWorkspace() {
    await Promise.all([loadConnectors(), loadDiscoveries()]);
  }

  async function handleReprocessDiscoveryContent() {
    setBusy(true);
    setActiveActionLabel("Reprocessing discovery content");
    try {
      const result = await reprocessAugmisBusinessDiscoveryContent(100);
      await loadDiscoveries();
      if (selectedDiscovery) {
        await openDiscoveryDrawer(selectedDiscovery);
      }
      showToast(
        `Reprocessed ${result.data.count} discovery item${result.data.count === 1 ? "" : "s"}.`,
        "success"
      );
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to reprocess discovery content."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleRecalculateDiscoveryValidity() {
    setBusy(true);
    setActiveActionLabel("Recalculating opportunity validity");
    try {
      const result = await recalculateAugmisBusinessDiscoveryValidity(100);
      await loadDiscoveries();
      if (selectedDiscovery) {
        await openDiscoveryDrawer(selectedDiscovery);
      }
      showToast(
        `Recalculated validity for ${result.data.count} AUGMIS Web discovery item${result.data.count === 1 ? "" : "s"}.`,
        "success"
      );
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to recalculate opportunity validity."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
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
    if (connector.connector_type === "independent_web_discovery") {
      setManualScanConnector(connector);
      setManualScanEngine(connectorCrawlEngine(connector));
      setManualScanDialogOpen(true);
      return;
    }
    await runConnectorScan(connector);
  }

  async function runConnectorScan(
    connector: AugmisBusinessConnector,
    crawlEngine?: "augmis_native" | "scrapy"
  ) {
    setBusy(true);
    setActiveActionLabel(`Scanning ${connector.name}`);
    try {
      const result = await scanAugmisBusinessConnector(connector.id, {
        run_type: "manual",
        ...(crawlEngine ? { crawl_engine: crawlEngine } : {}),
      });
      const startedRun = result.data.run;
      const startedConnector = result.data.connector;
      setRuns((current) => upsertRunEntry(current, startedRun));
      setActiveScan({ connectorId: connector.id, runId: startedRun.id });
      await refreshWorkspace();
      await openConnectorDrawer((connectorById.get(connector.id) as AugmisBusinessConnector | undefined) ?? startedConnector);
      showToast(
        startedRun.status === "queued" || startedRun.status === "running"
          ? "Scan started. Live progress is now available."
          : extractRunMetadata(startedRun).outcome_message || "Connector scan completed.",
        "info"
      );
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to run connector scan."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleStartManualIndependentScan() {
    if (!manualScanConnector) return;
    setManualScanDialogOpen(false);
    await runConnectorScan(manualScanConnector, manualScanEngine);
  }

  async function handleStopScan(connector: AugmisBusinessConnector, run: AugmisBusinessConnectorRun | null) {
    if (!run) return;
    setBusy(true);
    setActiveActionLabel(`Stopping ${connector.name}`);
    try {
      const result = await stopAugmisBusinessConnectorRun(connector.id, run.id);
      setActiveScan(null);
      setRuns((current) => upsertRunEntry(current, result.data.run));
      await refreshWorkspace();
      await openConnectorDrawer((connectorById.get(connector.id) as AugmisBusinessConnector | undefined) ?? result.data.connector);
      const metadata = extractRunMetadata(result.data.run);
      showToast(metadata.outcome_message || "Scan stopped.", "warning");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to stop connector scan."), "error");
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

  function openSeedDialog(seed?: AugmisBusinessWebSeed | null) {
    setEditingSeed(seed ?? null);
    setSeedForm(buildWebSeedForm(seed ?? null));
    setSeedDialogOpen(true);
  }

  async function handleSaveWebSeed() {
    if (!selectedConnector) return;
    setBusy(true);
    setActiveActionLabel(editingSeed ? `Updating ${seedForm.name}` : `Adding ${seedForm.name}`);
    try {
      if (editingSeed) {
        await updateAugmisBusinessWebSeed(selectedConnector.id, editingSeed.id, webSeedFormToPayload(seedForm));
      } else {
        await createAugmisBusinessWebSeed(selectedConnector.id, webSeedFormToPayload(seedForm));
      }
      await loadIndependentConnectorData(selectedConnector.id);
      setSeedDialogOpen(false);
      setEditingSeed(null);
      showToast(editingSeed ? "Seed updated." : "Seed added.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to save web seed."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleDeleteWebSeed(seed: AugmisBusinessWebSeed) {
    if (!selectedConnector) return;
    setBusy(true);
    setActiveActionLabel(`Removing ${seed.name}`);
    try {
      await deleteAugmisBusinessWebSeed(selectedConnector.id, seed.id);
      await loadIndependentConnectorData(selectedConnector.id);
      showToast("Seed removed.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to delete web seed."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleTestWebSeed(seed: AugmisBusinessWebSeed) {
    if (!selectedConnector) return;
    setBusy(true);
    setActiveActionLabel(`Testing ${seed.name}`);
    try {
      const result = await testAugmisBusinessWebFetchUrl(selectedConnector.id, {
        url: seed.seed_url,
      });
      setWebFetchTestResult(result.data);
      showToast(
        result.data.failure_code
          ? `Seed test completed: ${formatDiagnosticCode(result.data.failure_code)}`
          : `Seed test completed: ${result.data.fetch_decision || "FETCHABLE"}`,
        result.data.failure_code ? "warning" : "success"
      );
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to test seed URL."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleDomainApproval(domain: AugmisBusinessWebDomain, approval_status: string) {
    if (!selectedConnector) return;
    setBusy(true);
    setActiveActionLabel(`Updating ${domain.domain}`);
    try {
      await updateAugmisBusinessWebDomain(selectedConnector.id, domain.id, { approval_status });
      await loadIndependentConnectorData(selectedConnector.id);
      showToast("Domain policy updated.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to update domain policy."), "error");
    } finally {
      setBusy(false);
      setActiveActionLabel(null);
    }
  }

  async function handleDomainRecrawl(domain: AugmisBusinessWebDomain) {
    if (!selectedConnector) return;
    setBusy(true);
    setActiveActionLabel(`Queueing ${domain.domain}`);
    try {
      await recrawlAugmisBusinessWebDomain(selectedConnector.id, domain.id);
      await loadIndependentConnectorData(selectedConnector.id);
      showToast("Domain re-crawl queued.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to queue domain re-crawl."), "error");
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

  async function handleTestCredential(
    provider: string,
    transientCredential?: { apiKey?: string; appId?: string; appKey?: string }
  ) {
    setBusy(true);
    setActiveActionLabel(`Testing ${provider} credential`);
    try {
      const result = await testAugmisBusinessConnectorCredential(
        provider,
        transientCredential
          ? {
              api_key: transientCredential.apiKey || undefined,
              app_id: transientCredential.appId || undefined,
              app_key: transientCredential.appKey || undefined,
            }
          : {}
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
        api_key: credentialForm.apiKey || undefined,
        app_id: credentialForm.appId || undefined,
        app_key: credentialForm.appKey || undefined,
      });
      setCredentialStatuses((current) => ({
        ...current,
        [provider]: result.data,
      }));
      setCredentialDialogOpen(false);
      resetCredentialForm();
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
      <BusinessPageFrame
        title={pageTitle}
        description={pageDescription}
      >
        <Alert severity="warning">
          You do not currently have permission to view listener connectors or discoveries.
        </Alert>
      </BusinessPageFrame>
    );
  }

  const selectedConnectorRun =
    (selectedConnector?.active_run_id
      ? runs.find((run) => run.id === selectedConnector.active_run_id)
      : null) ??
    (activeScan && selectedConnector?.id === activeScan.connectorId
      ? runs.find((run) => run.id === activeScan.runId)
      : null) ??
    runs[0] ??
    null;
  const selectedRunMetadata = selectedConnectorRun ? extractRunMetadata(selectedConnectorRun) : null;
  const selectedConnectorRunActive = isConnectorRunActive(selectedConnectorRun?.status);
  const selectedCredentialStatus = credentialStatuses[selectedProvider] || null;
  const selectedDiscoverySourceMetadata = selectedDiscovery
    ? extractDiscoverySourceMetadata(selectedDiscovery)
    : null;
  const selectedDiscoveryRawContent = selectedDiscovery
    ? extractDiscoveryRawContent(selectedDiscovery)
    : null;
  const selectedDiscoveryNormalizedContent = extractDiscoveryNormalizedContent(selectedDiscovery);
  const selectedRequirementContent = requirementDisplayContent(
    selectedDiscovery,
    discoveryTranslationView
  );

  return (
    <>
      <BusinessPageFrame
        title={pageTitle}
        description={pageDescription}
      >
        <Stack spacing={2.25}>
          {!isControlCentre ? (
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
          ) : null}

          {busy && activeActionLabel ? (
            <Alert
              severity="info"
              icon={<CircularProgress size={16} />}
              sx={{ borderRadius: "8px" }}
            >
              {activeActionLabel}
            </Alert>
          ) : null}

          {showRegistry ? (
            <>
              <Box
                sx={{
                  display: "grid",
                  gap: 1.5,
                  gridTemplateColumns: { xs: "1fr", sm: "minmax(240px, 280px)" },
                  alignItems: "start",
                }}
              >
                <Paper elevation={0} sx={{ borderRadius: "12px", border: "1px solid #D9E2EC", overflow: "hidden", boxShadow: "0 8px 22px rgba(15, 23, 42, 0.08)" }}>
                  <Box sx={{ p: 2, background: "linear-gradient(180deg, #F8FAFC 0%, #EFF6FF 100%)" }}>
                    <Stack spacing={1.6} sx={{ minHeight: 164, justifyContent: "space-between" }}>
                      <Box>
                        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                          <HubOutlinedIcon sx={{ color: "#1D4ED8", fontSize: 22 }} />
                          <Typography sx={{ fontWeight: 800, color: "#0F172A" }}>Connector Registry</Typography>
                        </Stack>
                        <Typography sx={{ mt: 1, color: "#475569", fontSize: 13, lineHeight: 1.45 }}>
                          Open the governed connector workspace, review live connector rows, and update runtime controls from one modal.
                        </Typography>
                      </Box>
                      <Stack direction="row" spacing={1} sx={{ alignItems: "center", justifyContent: "space-between" }}>
                        <Chip
                          label={`${visibleConnectors.length} visible`}
                          size="small"
                          sx={{ borderRadius: "999px", bgcolor: "#EFF6FF", color: "#1D4ED8", border: "1px solid #BFDBFE" }}
                        />
                        <Button
                          variant="contained"
                          onClick={() => setRegistryDialogOpen(true)}
                          disabled={busy}
                          sx={{ borderRadius: "9px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                        >
                          Open Registry
                        </Button>
                      </Stack>
                    </Stack>
                  </Box>
                </Paper>
              </Box>

              <BusinessWorkspaceModal
                open={registryDialogOpen}
                onClose={() => setRegistryDialogOpen(false)}
                title="Connector Registry"
                subtitle="Governed connector operations with single-line rows, runtime actions, and no hidden wrapping."
                maxWidth={CONNECTOR_REGISTRY_MODAL_WIDTH}
                actions={
                  <>
                    <Button
                      variant="outlined"
                      startIcon={<RuleFolderOutlinedIcon />}
                      onClick={() => {
                        setProfileForm(defaultProfile ? profileToForm(defaultProfile) : buildDefaultProfileForm());
                        setProfileDialogOpen(true);
                      }}
                      disabled={!canAdmin || busy}
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, color: "#F8FAFC", borderColor: "rgba(255,255,255,0.35)" }}
                    >
                      Edit Search Profile
                    </Button>
                    <Button
                      variant="contained"
                      startIcon={<RefreshRoundedIcon />}
                      onClick={() => void refreshWorkspace()}
                      disabled={loading || busy}
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "rgba(255,255,255,0.14)" }}
                    >
                      Refresh
                    </Button>
                  </>
                }
                contentSx={{ pt: 2.1 }}
              >
                {loading ? (
                  <Stack sx={{ py: 7, alignItems: "center" }} spacing={1.2}>
                    <CircularProgress size={30} />
                    <Typography sx={{ color: "#475569" }}>Loading registry...</Typography>
                  </Stack>
                ) : (
                  <Paper elevation={0} sx={{ borderRadius: "12px", border: "1px solid #D9E2EC", overflow: "hidden" }}>
                    <Box sx={{ overflowX: "auto" }}>
                      <Table
                        size="small"
                        sx={{
                          minWidth: 1420,
                          tableLayout: "auto",
                          "& th": {
                            px: 1.35,
                            py: 1.2,
                            fontSize: 12,
                            fontWeight: 800,
                            color: "#334155",
                            whiteSpace: "nowrap",
                          },
                          "& td": {
                            px: 1.35,
                            py: 1.15,
                            verticalAlign: "middle",
                            borderColor: "#E2E8F0",
                            whiteSpace: "nowrap",
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
                          {visibleConnectors.map((connector) => (
                            <TableRow key={connector.id} hover>
                              <TableCell>
                                <Stack spacing={0.55}>
                                  <Stack direction="row" spacing={0.8} sx={{ alignItems: "center" }}>
                                    {connectorPrimaryIcon(connector)}
                                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }} noWrap>
                                      {connector.name}
                                    </Typography>
                                  </Stack>
                                  <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
                                    <Chip
                                      label={connectorCategoryLabel(connector)}
                                      size="small"
                                      sx={
                                        connector.metadata?.is_test_connector
                                          ? { bgcolor: "#FFF7ED", color: "#B45309", border: "1px solid #FED7AA" }
                                          : { bgcolor: "#EFF6FF", color: "#1D4ED8", border: "1px solid #BFDBFE" }
                                      }
                                    />
                                    <Typography sx={{ fontSize: 12, color: "#64748B", maxWidth: 260 }} noWrap>
                                      {connector.id}
                                    </Typography>
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
                                ) : connector.connector_type === "freelancer_marketplace" ? (
                                  <Chip
                                    label={connector.configuration_json.mode === "mock" ? "Freelancer / Mock" : "Freelancer"}
                                    size="small"
                                    sx={{ borderRadius: "8px", bgcolor: "#F5F3FF", color: "#6D28D9", border: "1px solid #DDD6FE" }}
                                  />
                                ) : connector.connector_type === "ted_procurement" ? (
                                  <Chip
                                    label="TED"
                                    size="small"
                                    sx={{ borderRadius: "8px", bgcolor: "#ECFDF3", color: "#0F766E", border: "1px solid #A7F3D0" }}
                                  />
                                ) : connector.connector_type === "remote_job_feed" ? (
                                  <Chip label="Remote OK" size="small" sx={{ borderRadius: "8px", bgcolor: "#ECFEFF", color: "#0F766E", border: "1px solid #A5F3FC" }} />
                                ) : connector.connector_type === "job_board_api" ? (
                                  <Chip label="Arbeitnow" size="small" sx={{ borderRadius: "8px", bgcolor: "#F0FDF4", color: "#15803D", border: "1px solid #BBF7D0" }} />
                                ) : connector.connector_type === "remote_job_api" ? (
                                  <Chip label="Remotive" size="small" sx={{ borderRadius: "8px", bgcolor: "#EEF2FF", color: "#4338CA", border: "1px solid #C7D2FE" }} />
                                ) : connector.connector_type === "job_search_api" ? (
                                  <Chip label="Adzuna" size="small" sx={{ borderRadius: "8px", bgcolor: "#FFF7ED", color: "#C2410C", border: "1px solid #FED7AA" }} />
                                ) : (
                                  "—"
                                )}
                              </TableCell>
                              <TableCell sx={{ textTransform: "capitalize" }}>{connectorCategoryDisplay(connector)}</TableCell>
                              <TableCell>
                                <Chip
                                  label={connector.status}
                                  size="small"
                                  sx={{ textTransform: "capitalize", border: "1px solid", ...connectorStatusChip(connector.status) }}
                                />
                              </TableCell>
                              <TableCell>
                                <Stack spacing={0.25}>
                                  <Typography sx={{ fontSize: 13, fontWeight: 600, color: "#0F172A" }} noWrap>
                                    {formatSchedule(connector)}
                                  </Typography>
                                  {connector.schedule_enabled ? (
                                    <Typography sx={{ fontSize: 12, color: "#64748B" }} noWrap>
                                      Next: {formatDate(connector.next_run_at)}
                                    </Typography>
                                  ) : null}
                                </Stack>
                              </TableCell>
                              <TableCell>{formatDate(connector.last_scan_at)}</TableCell>
                              <TableCell align="right">
                                <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end" }}>
                                  <Tooltip title="Update">
                                    <span>
                                      <IconButton
                                        size="small"
                                        onClick={() => {
                                          setRegistryDialogOpen(false);
                                          void openConnectorDrawer(connector);
                                        }}
                                        sx={{ borderRadius: "10px", bgcolor: "#EFF6FF", border: "1px solid #BFDBFE" }}
                                      >
                                        <EditOutlinedIcon fontSize="small" sx={{ color: "#2563EB" }} />
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
                    </Box>
                  </Paper>
                )}
              </BusinessWorkspaceModal>
            </>
          ) : null}

          {showDiscoveryInbox ? (
            <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
            <Box
              sx={{
                px: 2.2,
                py: 0.72,
                background: "linear-gradient(90deg, #DCFCE7 0%, #F8FAFC 100%)",
                borderBottom: "1px solid #E2E8F0",
              }}
            >
              <Stack
                direction={{ xs: "column", lg: "row" }}
                spacing={1.5}
                sx={{ justifyContent: "space-between", alignItems: { lg: "center" } }}
              >
                <Stack spacing={0.1}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                    <TravelExploreOutlinedIcon sx={{ color: "#15803D", fontSize: 18 }} />
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Discovery Inbox</Typography>
                  </Stack>
                  <Typography sx={{ color: "#475569", fontSize: 12, lineHeight: 1.25 }}>
                    Review search-driven discoveries, inspect source evidence, and import only verified opportunities.
                  </Typography>
                </Stack>
              </Stack>
            </Box>
            <Box sx={{ p: 2 }}>
              {discoveries.length ? (
                <>
                  <Box
                    sx={{
                      mb: 1.25,
                      pb: 1.25,
                      borderBottom: "1px solid #E2E8F0",
                    }}
                  >
                    <Stack
                      direction={{ xs: "column", md: "row" }}
                      spacing={1}
                      sx={{
                        width: "100%",
                        minWidth: 0,
                        flexWrap: "wrap",
                        justifyContent: { md: "space-between" },
                        alignItems: { md: "center" },
                        "& .MuiTextField-root": {
                          minWidth: { xs: "100%", md: 0 },
                        },
                      }}
                    >
                      <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ flex: { md: "1 1 auto" }, minWidth: 0 }}>
                        {canAdmin ? (
                          <Button
                            variant="outlined"
                            size="small"
                            startIcon={<AutorenewRoundedIcon />}
                            disabled={busy}
                            onClick={() => void handleReprocessDiscoveryContent()}
                            sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                          >
                            Reprocess Content
                          </Button>
                        ) : null}
                        {canAdmin ? (
                          <Button
                            variant="outlined"
                            size="small"
                            startIcon={<RuleFolderOutlinedIcon />}
                            disabled={busy}
                            onClick={() => void handleRecalculateDiscoveryValidity()}
                            sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                          >
                            Recalculate Validity
                          </Button>
                        ) : null}
                        <TextField
                          size="small"
                          value={search}
                          onChange={(event) => {
                            setSearch(event.target.value);
                            setDiscoveryPage(0);
                          }}
                          placeholder="Search title, organisation, summary"
                          sx={{ flex: { md: "1 1 340px" }, minWidth: 0 }}
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
                      </Stack>
                      <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ minWidth: 0 }}>
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
                          <MenuItem value="company_source">AUGMIS Web</MenuItem>
                          <MenuItem value="search">Web Opportunity Search</MenuItem>
                          <MenuItem value="procurement">TED</MenuItem>
                          <MenuItem value="marketplace">Freelancer</MenuItem>
                          <MenuItem value="remoteok">Remote OK</MenuItem>
                          <MenuItem value="arbeitnow">Arbeitnow</MenuItem>
                          <MenuItem value="remotive">Remotive</MenuItem>
                          <MenuItem value="adzuna">Adzuna</MenuItem>
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
                      "& thead th": {
                        py: 0.8,
                        verticalAlign: "middle",
                        lineHeight: 1.2,
                      },
                    }}
                  >
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ width: { md: 520 } }}>Opportunity</TableCell>
                        <TableCell sx={{ width: { md: 132 } }}>Source</TableCell>
                        <TableCell sx={{ width: { md: 250 } }}>Closing</TableCell>
                        <TableCell sx={{ width: { md: 104 } }}>Match</TableCell>
                        <TableCell sx={{ width: { md: 118 } }}>Commercial</TableCell>
                        <TableCell sx={{ width: { md: 104 } }}>Recommendation</TableCell>
                        <TableCell sx={{ width: { md: 90 } }}>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {discoveries.map((discovery) => (
                        <TableRow
                          key={discovery.id}
                          hover
                          selected={selectedDiscovery?.id === discovery.id}
                          sx={{
                            "&.Mui-selected": { bgcolor: "#F8FBFF" },
                            "&.Mui-selected:hover": { bgcolor: "#EFF6FF" },
                          }}
                        >
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
                              <Typography sx={{ fontSize: 12.5, color: "#0F172A", fontWeight: 600 }}>
                                {discovery.organization_name || "Not available"}
                              </Typography>
                              <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap", rowGap: 0.5 }}>
                                <Chip
                                  size="small"
                                  label={
                                    discovery.validity_score == null
                                      ? "Validity unknown"
                                      : `${Math.round(discovery.validity_score)} · ${formatDiscoveryValidityBand(discovery.validity_band)}`
                                  }
                                  sx={{
                                    maxWidth: "100%",
                                    border: "1px solid",
                                    ...discoveryValidityBandChip(discovery.validity_band),
                                  }}
                                />
                                {discovery.actionability ? (
                                  <Chip
                                    size="small"
                                    label={formatDiscoveryActionability(discovery.actionability)}
                                    sx={{
                                      maxWidth: "100%",
                                      border: "1px solid",
                                      ...actionabilityChip(discovery.actionability),
                                    }}
                                  />
                                ) : null}
                              </Stack>
                              <Typography sx={{ fontSize: 12, color: "#64748B" }}>
                                {discovery.country || "Not available"}
                              </Typography>
                              <Stack direction="row" spacing={0.35} sx={{ flexWrap: "wrap", rowGap: 0.5, pt: 0.45 }}>
                                {discovery.source_url ? (
                                  <Tooltip title="Open Source">
                                    <span>
                                      <IconButton
                                        size="small"
                                        component="a"
                                        href={discovery.source_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        sx={{ border: "1px solid #E2E8F0", bgcolor: "#FFFFFF" }}
                                      >
                                        <OpenInNewRoundedIcon fontSize="small" sx={{ color: "#475569" }} />
                                      </IconButton>
                                    </span>
                                  </Tooltip>
                                ) : null}
                                <Tooltip title="View">
                                  <span>
                                    <IconButton
                                      size="small"
                                      onClick={() => void openDiscoveryDrawer(discovery)}
                                      sx={{ border: "1px solid #DBEAFE", bgcolor: "#F8FBFF" }}
                                    >
                                      <PreviewOutlinedIcon fontSize="small" sx={{ color: "#2563EB" }} />
                                    </IconButton>
                                  </span>
                                </Tooltip>
                                <Tooltip title="Shortlist">
                                  <span>
                                    <IconButton
                                      size="small"
                                      disabled={!canAdmin || busy || discovery.discovery_status === "imported"}
                                      onClick={() => void handleDiscoveryAction("shortlist", discovery)}
                                      sx={{ border: "1px solid #D1FADF", bgcolor: "#F6FEF9" }}
                                    >
                                      <TaskAltOutlinedIcon fontSize="small" sx={{ color: "#15803D" }} />
                                    </IconButton>
                                  </span>
                                </Tooltip>
                                <Tooltip title="Reject">
                                  <span>
                                    <IconButton
                                      size="small"
                                      disabled={!canAdmin || busy || discovery.discovery_status === "imported"}
                                      onClick={() => void handleDiscoveryAction("reject", discovery)}
                                      sx={{ border: "1px solid #FECACA", bgcolor: "#FEF2F2" }}
                                    >
                                      <ErrorOutlineRoundedIcon fontSize="small" sx={{ color: "#B42318" }} />
                                    </IconButton>
                                  </span>
                                </Tooltip>
                                <Tooltip title="Import as Opportunity">
                                  <span>
                                    <IconButton
                                      size="small"
                                      disabled={!canCreate || busy || discovery.discovery_status === "duplicate" || discovery.discovery_status === "imported"}
                                      onClick={() => void handleDiscoveryAction("import", discovery)}
                                      sx={{ border: "1px solid #C7D2FE", bgcolor: "#EEF2FF" }}
                                    >
                                      <ImportExportOutlinedIcon fontSize="small" sx={{ color: "#4338CA" }} />
                                    </IconButton>
                                  </span>
                                </Tooltip>
                              </Stack>
                            </Stack>
                          </TableCell>
                          <TableCell sx={{ color: "#475569" }}>
                            <Chip
                              size="small"
                              label={discoverySourceDisplay(discovery)}
                              sx={{
                                maxWidth: "100%",
                                border: "1px solid",
                                fontWeight: 700,
                                ...discoverySourceChipStyle(discovery),
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ color: "#475569", fontSize: 12, whiteSpace: "normal", overflowWrap: "anywhere" }}>
                            <Stack spacing={0.5}>
                              <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: ".04em" }}>
                                Discovered
                              </Typography>
                              <Typography sx={{ fontSize: 11.5, color: "#64748B" }}>
                                {formatDate(discovery.discovered_at)}
                              </Typography>
                              <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#0F172A" }}>
                                {renderRelativeClosing(discovery.closing_date)}
                              </Typography>
                              <Typography sx={{ fontSize: 11.5, color: "#64748B" }}>
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
                            <Stack spacing={0.35}>
                              <Typography sx={{ fontSize: 13, fontWeight: 800, color: "#0F172A" }}>
                                {discovery.preliminary_relevance_score == null
                                  ? "N/A"
                                  : Math.round(discovery.preliminary_relevance_score)}
                              </Typography>
                              <Chip
                                label={discovery.relevance_band || "Unknown"}
                                size="small"
                                sx={{ textTransform: "capitalize", border: "1px solid", maxWidth: "100%", ...discoveryRelevanceBandChip(discovery.relevance_band) }}
                              />
                            </Stack>
                          </TableCell>
                          <TableCell>
                            <Stack spacing={0.35}>
                              <Typography sx={{ fontSize: 13, fontWeight: 800, color: "#0F172A" }}>
                                {discovery.commercial_priority_score == null
                                  ? "N/A"
                                  : Math.round(discovery.commercial_priority_score)}
                              </Typography>
                              <Chip
                                label={`Priority ${discovery.commercial_priority_band || "?"}`}
                                size="small"
                                sx={{
                                  textTransform: "capitalize",
                                  border: "1px solid",
                                  maxWidth: "100%",
                                  ...discoveryPriorityBandChip(discovery.commercial_priority_band),
                                }}
                              />
                            </Stack>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={(discovery.commercial_recommendation || "watch").toUpperCase()}
                              size="small"
                              sx={{
                                textTransform: "uppercase",
                                border: "1px solid",
                                maxWidth: "100%",
                                ...discoveryRecommendationChip(discovery.commercial_recommendation),
                              }}
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={discovery.discovery_status}
                              size="small"
                              sx={{ textTransform: "capitalize", border: "1px solid", maxWidth: "100%", ...discoveryStatusChip(discovery.discovery_status) }}
                            />
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
                    Run any available connector scan to start populating the discovery inbox.
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 2, justifyContent: "center", flexWrap: "wrap" }}>
                    {discoveryInboxConnectors.map((connector) => (
                      <Button
                        key={connector.id}
                        variant={connector.metadata?.is_test_connector ? "outlined" : "contained"}
                        startIcon={<PlayCircleOutlineRoundedIcon />}
                        onClick={() => void handleScan(connector)}
                        disabled={!canScan || busy || connector.status === "running"}
                        sx={{
                          borderRadius: "8px",
                          textTransform: "none",
                          fontWeight: 700,
                          bgcolor: discoveryInboxButtonColor(connector),
                        }}
                      >
                        {`Scan ${connector.name}`}
                      </Button>
                    ))}
                  </Stack>
                </Paper>
              )}
            </Box>
            </Paper>
          ) : null}
        </Stack>
      </BusinessPageFrame>

      <BusinessWorkspaceModal
        open={connectorDrawerOpen}
        onClose={() => setConnectorDrawerOpen(false)}
        title={
          selectedConnector ? (
            <Stack direction="row" spacing={1.1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
              {connectorPrimaryIcon(selectedConnector)}
              <span>{selectedConnector.name}</span>
            </Stack>
          ) : (
            "Connector"
          )
        }
        subtitle="Connector runtime, schedule, credentials, and governed scan controls."
        chips={
          selectedConnector ? (
            <>
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
            </>
          ) : null
        }
        actions={
          selectedConnector ? (
            <>
              <Button
                variant="outlined"
                size="small"
                startIcon={<CheckCircleOutlineRoundedIcon />}
                onClick={() => void handleTest(selectedConnector)}
                disabled={!canAdmin || busy}
                sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, color: "#F8FAFC", borderColor: "rgba(255,255,255,0.35)" }}
              >
                Test
              </Button>
              <Button
                variant="contained"
                size="small"
                startIcon={selectedConnectorRunActive ? <CircularProgress size={16} color="inherit" /> : <PlayCircleOutlineRoundedIcon />}
                onClick={() => void handleScan(selectedConnector)}
                disabled={!canScan || busy || selectedConnector.status === "running" || Boolean(selectedConnector.active_run_id)}
                sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "rgba(255,255,255,0.14)" }}
              >
                {selectedConnectorRunActive ? "Scanning..." : "Scan Now"}
              </Button>
              {selectedConnector.connector_type === "independent_web_discovery" && selectedConnectorRunActive ? (
                <Button
                  variant="outlined"
                  size="small"
                  color="error"
                  onClick={() => void handleStopScan(selectedConnector, selectedConnectorRun)}
                  disabled={!canScan || busy || !selectedConnectorRun}
                  sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, borderColor: "rgba(254, 202, 202, 0.55)", color: "#FECACA" }}
                >
                  Stop Scan
                </Button>
              ) : null}
            </>
          ) : null
        }
        maxWidth={CONNECTOR_DETAIL_MODAL_WIDTH}
        contentSx={{ maxHeight: "calc(90vh - 190px)", overflowY: "auto" }}
      >
        {selectedConnector ? (
          <Stack spacing={2}>
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

              {connectorUsesCredential(selectedConnector) ? (
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={1.2}
                    sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                        {selectedConnector.connector_type === "freelancer_marketplace"
                          ? "Freelancer Credential"
                          : selectedConnector.connector_type === "job_search_api"
                            ? "Adzuna Credential"
                            : "Search Provider"}
                      </Typography>
                      <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 13 }}>
                        {selectedConnector.connector_type === "freelancer_marketplace"
                          ? "Official Freelancer API access uses a tenant-scoped encrypted access token."
                          : selectedConnector.connector_type === "job_search_api"
                            ? "Adzuna uses a tenant-scoped encrypted App ID and App Key."
                          : "Choose which provider powers Web Opportunity Search. No fallback is applied automatically."}
                      </Typography>
                    </Box>
                    {selectedConnector.connector_type === "generic_web_search" ? (
                      <Button
                        variant="contained"
                        size="small"
                        onClick={() => void handleSaveConnectorProvider()}
                        disabled={!canAdmin || busy}
                        sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                      >
                        Save Provider
                      </Button>
                    ) : null}
                  </Stack>
                  {selectedConnector.connector_type === "generic_web_search" ? (
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
                  ) : null}
                  <Stack direction="row" spacing={1} sx={{ mt: 1.1, alignItems: "center", flexWrap: "wrap" }}>
                    <Chip
                      label={selectedConnector.connector_type === "freelancer_marketplace" ? "FREELANCER" : selectedProvider.toUpperCase()}
                      size="small"
                      sx={{
                        borderRadius: "8px",
                        bgcolor: selectedConnector.connector_type === "freelancer_marketplace" ? "#F5F3FF" : "#EFF6FF",
                        color: selectedConnector.connector_type === "freelancer_marketplace" ? "#6D28D9" : "#1D4ED8",
                        border: selectedConnector.connector_type === "freelancer_marketplace" ? "1px solid #DDD6FE" : "1px solid #BFDBFE",
                      }}
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
                      {providerSecretLabel(selectedProvider)}: {selectedCredentialStatus.masked_hint}
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
                        resetCredentialForm();
                      }}
                      disabled={!canAdmin || busy || !selectedCredentialStatus?.storage_available}
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                    >
                      {selectedCredentialStatus?.configured ? `Replace ${providerSecretLabel(selectedProvider)}` : `Configure ${providerSecretLabel(selectedProvider)}`}
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
                      {`Clear Stored ${providerSecretLabel(selectedProvider)}`}
                    </Button>
                  </Stack>
                </Paper>
              ) : null}

              {selectedConnector.connector_type === "independent_web_discovery" ? (
                <Stack spacing={1.5}>
                  <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                    <Stack
                      direction={{ xs: "column", sm: "row" }}
                      spacing={1.2}
                      sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}
                    >
                      <Box sx={{ minWidth: 0 }}>
                        <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Independent Engine Settings</Typography>
                        <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 13 }}>
                          First-party AUGMIS crawl and index configuration. No Tavily, Brave, or other external search-provider credential is required.
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
                    <Box sx={{ mt: 1.2, display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
                      <TextField size="small" label="Credential" value="None Required" disabled />
                      <TextField size="small" label="Provider" value="AUGMIS Internal" disabled />
                      <TextField
                        select
                        size="small"
                        label="Default Crawl Engine"
                        value={connectorCrawlEngine(selectedConnector)}
                        onChange={(event) =>
                          setSelectedConnector((current) =>
                            current
                              ? {
                                  ...current,
                                  configuration_json: {
                                    ...current.configuration_json,
                                    crawl_engine: event.target.value,
                                  },
                                }
                              : current
                          )
                        }
                      >
                        <MenuItem value="augmis_native">AUGMIS Native</MenuItem>
                        <MenuItem value="scrapy">Scrapy</MenuItem>
                      </TextField>
                      <TextField
                        select
                        size="small"
                        label="Allowed Domain Mode"
                        value={String(selectedConnector.configuration_json.allowed_domain_mode || "approved_only")}
                        onChange={(event) =>
                          setSelectedConnector((current) =>
                            current
                              ? { ...current, configuration_json: { ...current.configuration_json, allowed_domain_mode: event.target.value } }
                              : current
                          )
                        }
                      >
                        <MenuItem value="approved_only">Approved domains only</MenuItem>
                        <MenuItem value="cross_domain_trusted">Trusted cross-domain links</MenuItem>
                      </TextField>
                      <TextField
                        select
                        size="small"
                        label="Maximum Domains / Run"
                        value={String(connectorNumberConfig(selectedConnector, "maximum_domains_per_run", 5))}
                        onChange={(event) =>
                          setSelectedConnector((current) =>
                            current
                              ? { ...current, configuration_json: { ...current.configuration_json, maximum_domains_per_run: Number(event.target.value) } }
                              : current
                          )
                        }
                      >
                        <MenuItem value="1">1</MenuItem>
                        <MenuItem value="3">3</MenuItem>
                        <MenuItem value="5">5</MenuItem>
                        <MenuItem value="10">10</MenuItem>
                      </TextField>
                      <TextField
                        select
                        size="small"
                        label="Maximum Pages / Domain"
                        value={String(connectorNumberConfig(selectedConnector, "maximum_pages_per_domain", 25))}
                        onChange={(event) =>
                          setSelectedConnector((current) =>
                            current
                              ? { ...current, configuration_json: { ...current.configuration_json, maximum_pages_per_domain: Number(event.target.value) } }
                              : current
                          )
                        }
                      >
                        <MenuItem value="10">10</MenuItem>
                        <MenuItem value="25">25</MenuItem>
                        <MenuItem value="50">50</MenuItem>
                      </TextField>
                      <TextField
                        select
                        size="small"
                        label="Maximum Total Pages / Run"
                        value={String(connectorNumberConfig(selectedConnector, "maximum_total_pages_per_run", 100))}
                        onChange={(event) =>
                          setSelectedConnector((current) =>
                            current
                              ? { ...current, configuration_json: { ...current.configuration_json, maximum_total_pages_per_run: Number(event.target.value) } }
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
                        label="Maximum Depth"
                        value={String(connectorNumberConfig(selectedConnector, "maximum_depth", 2))}
                        onChange={(event) =>
                          setSelectedConnector((current) =>
                            current
                              ? { ...current, configuration_json: { ...current.configuration_json, maximum_depth: Number(event.target.value) } }
                              : current
                          )
                        }
                      >
                        <MenuItem value="0">0</MenuItem>
                        <MenuItem value="1">1</MenuItem>
                        <MenuItem value="2">2</MenuItem>
                        <MenuItem value="3">3</MenuItem>
                      </TextField>
                      <TextField
                        select
                        size="small"
                        label="Per-Domain Delay"
                        value={String(connectorNumberConfig(selectedConnector, "per_domain_delay_seconds", 2))}
                        onChange={(event) =>
                          setSelectedConnector((current) =>
                            current
                              ? { ...current, configuration_json: { ...current.configuration_json, per_domain_delay_seconds: Number(event.target.value) } }
                              : current
                          )
                        }
                      >
                        <MenuItem value="2">2 sec</MenuItem>
                        <MenuItem value="5">5 sec</MenuItem>
                        <MenuItem value="10">10 sec</MenuItem>
                        <MenuItem value="15">15 sec</MenuItem>
                      </TextField>
                      <TextField
                        select
                        size="small"
                        label="Request Timeout"
                        value={String(connectorNumberConfig(selectedConnector, "request_timeout_seconds", 15))}
                        onChange={(event) =>
                          setSelectedConnector((current) =>
                            current
                              ? { ...current, configuration_json: { ...current.configuration_json, request_timeout_seconds: Number(event.target.value) } }
                              : current
                          )
                        }
                      >
                        <MenuItem value="10">10 sec</MenuItem>
                        <MenuItem value="15">15 sec</MenuItem>
                        <MenuItem value="20">20 sec</MenuItem>
                        <MenuItem value="30">30 sec</MenuItem>
                      </TextField>
                      <TextField
                        select
                        size="small"
                        label="Maximum HTML Page Size"
                        value={String(connectorNumberConfig(selectedConnector, "max_html_response_bytes", 2000000))}
                        onChange={(event) =>
                          setSelectedConnector((current) =>
                            current
                              ? { ...current, configuration_json: { ...current.configuration_json, max_html_response_bytes: Number(event.target.value) } }
                              : current
                          )
                        }
                        helperText="Applies to both AUGMIS Native and Scrapy. Attachments are skipped separately."
                      >
                        <MenuItem value="500000">500 KB</MenuItem>
                        <MenuItem value="1000000">1 MB</MenuItem>
                        <MenuItem value="2000000">2 MB</MenuItem>
                        <MenuItem value="5000000">5 MB</MenuItem>
                      </TextField>
                    </Box>
                  </Paper>

                  <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                    <Stack direction={{ xs: "column", sm: "row" }} spacing={1.2} sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}>
                      <Box sx={{ minWidth: 0 }}>
                        <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Seeds</Typography>
                        <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 13 }}>
                          Tenant-scoped crawl entry points that bootstrap the internal index.
                        </Typography>
                      </Box>
                      <Button
                        variant="contained"
                        size="small"
                        onClick={() => openSeedDialog()}
                        disabled={!canAdmin || busy}
                        sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                      >
                        Add Seed
                      </Button>
                    </Stack>
                    <Box sx={{ mt: 1, width: "100%", overflowX: "auto" }}>
                      <Table size="small" sx={{ width: "100%", minWidth: 420, tableLayout: "fixed" }}>
                        <TableHead>
                          <TableRow>
                            <TableCell sx={{ width: "82%" }}>Name</TableCell>
                            <TableCell align="right" sx={{ width: "18%" }}>Actions</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {webSeeds.length ? (
                            webSeeds.map((seed) => (
                              <TableRow key={seed.id} hover>
                                <TableCell>
                                  <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13, overflowWrap: "anywhere" }}>{seed.name}</Typography>
                                  <Typography sx={{ fontSize: 12, color: "#64748B", overflowWrap: "anywhere" }}>
                                    {seed.organization_name || seed.country || "Not tagged"}
                                  </Typography>
                                  <Typography
                                    sx={{
                                      mt: 0.4,
                                      fontSize: 12,
                                      color: "#1D4ED8",
                                      overflow: "hidden",
                                      textOverflow: "ellipsis",
                                      whiteSpace: "nowrap",
                                    }}
                                  >
                                    {seed.seed_url}
                                  </Typography>
                                  <Typography sx={{ mt: 0.4, fontSize: 12, color: "#475569" }}>
                                    Type: {seed.seed_type}
                                  </Typography>
                                  <Typography sx={{ fontSize: 12, color: "#475569" }}>
                                    Depth: {seed.max_depth} | Max Pages: {seed.max_pages}
                                  </Typography>
                                  <Typography sx={{ fontSize: 12, color: "#475569", overflowWrap: "anywhere" }}>
                                    Last Crawled: {formatDate(seed.last_crawled_at)}
                                  </Typography>
                                  <Typography sx={{ fontSize: 12, color: "#475569", overflowWrap: "anywhere" }}>
                                    Next Crawl: {formatDate(seed.next_crawl_at)}
                                  </Typography>
                                </TableCell>
                                <TableCell align="right">
                                  <Stack direction="row" spacing={0.25} sx={{ justifyContent: "flex-end", flexWrap: "wrap" }}>
                                    <Tooltip title="Edit Seed">
                                      <IconButton size="small" onClick={() => openSeedDialog(seed)}>
                                        <SettingsSuggestOutlinedIcon sx={{ fontSize: 18, color: "#1D4ED8" }} />
                                      </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Test Seed">
                                      <IconButton size="small" disabled={!canScan || busy} onClick={() => void handleTestWebSeed(seed)}>
                                        <FindInPageOutlinedIcon sx={{ fontSize: 18, color: "#0F766E" }} />
                                      </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Delete Seed">
                                      <IconButton size="small" disabled={!canAdmin || busy} onClick={() => void handleDeleteWebSeed(seed)}>
                                        <VisibilityOffOutlinedIcon sx={{ fontSize: 18, color: "#B42318" }} />
                                      </IconButton>
                                    </Tooltip>
                                  </Stack>
                                </TableCell>
                              </TableRow>
                            ))
                          ) : (
                            <TableRow>
                              <TableCell colSpan={2}>
                                <Typography sx={{ color: "#64748B", fontSize: 13 }}>
                                  No independent web seeds have been configured yet.
                                </Typography>
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </Box>
                    {webFetchTestResult ? (
                      <Alert severity={webFetchTestResult.failure_code ? "warning" : "success"} sx={{ mt: 1.2, borderRadius: "8px" }}>
                        <Typography sx={{ fontWeight: 700, fontSize: 13 }}>
                          {webFetchTestResult.fetch_decision || (webFetchTestResult.failure_code ? "FAILED" : "FETCHABLE")}
                          {webFetchTestResult.http_status != null ? ` · HTTP ${webFetchTestResult.http_status}` : ""}
                          {webFetchTestResult.content_type ? ` · ${webFetchTestResult.content_type}` : ""}
                          {webFetchTestResult.response_bytes != null ? ` · ${formatBytes(webFetchTestResult.response_bytes)}` : ""}
                        </Typography>
                        <Typography sx={{ mt: 0.45, fontSize: 12 }}>
                          Robots: {webFetchTestResult.robots_status}
                          {webFetchTestResult.final_url ? ` · Final URL: ${webFetchTestResult.final_url}` : ""}
                        </Typography>
                        {webFetchTestResult.failure_code ? (
                          <Typography sx={{ mt: 0.45, fontSize: 12 }}>
                            {formatDiagnosticCode(webFetchTestResult.failure_code)}
                            {webFetchTestResult.failure_reason ? ` · ${webFetchTestResult.failure_reason}` : ""}
                          </Typography>
                        ) : null}
                        {webFetchTestResult.page_title || webFetchTestResult.page_type ? (
                          <Typography sx={{ mt: 0.45, fontSize: 12 }}>
                            {webFetchTestResult.page_title || "Untitled page"}{webFetchTestResult.page_type ? ` · ${webFetchTestResult.page_type}` : ""}
                          </Typography>
                        ) : null}
                      </Alert>
                    ) : null}
                  </Paper>

                  <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Domain Registry</Typography>
                    <Box sx={{ mt: 1, width: "100%", overflowX: "auto" }}>
                      <Table size="small" sx={{ width: "100%", minWidth: 420, tableLayout: "fixed" }}>
                        <TableHead>
                          <TableRow>
                            <TableCell sx={{ width: "72%" }}>Domain</TableCell>
                            <TableCell align="right" sx={{ width: "28%" }}>Actions</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {webDomains.length ? (
                            webDomains.slice(0, 12).map((domain) => (
                              <TableRow key={domain.id} hover>
                                <TableCell>
                                  <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13, overflowWrap: "anywhere" }}>{domain.domain}</Typography>
                                  <Typography sx={{ fontSize: 12, color: "#64748B", overflowWrap: "anywhere" }}>
                                    {domain.trust_source_type || "public_web"}
                                  </Typography>
                                  <Typography sx={{ mt: 0.4, fontSize: 12, color: "#475569", textTransform: "lowercase" }}>
                                    Robots: {domain.robots_status}
                                  </Typography>
                                  <Typography sx={{ fontSize: 12, color: "#475569" }}>
                                    Indexed: {domain.pages_indexed} | Opportunities: {domain.opportunities_found}
                                  </Typography>
                                  <Typography sx={{ fontSize: 12, color: "#475569", textTransform: "lowercase" }}>
                                    Status: {domain.status} | Approval: {domain.approval_status}
                                  </Typography>
                                </TableCell>
                                <TableCell align="right">
                                  <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end", flexWrap: "wrap", rowGap: 0.5 }}>
                                    <Button size="small" variant="outlined" disabled={!canAdmin || busy} onClick={() => void handleDomainApproval(domain, "approved")} sx={{ borderRadius: "8px", textTransform: "none", px: 1 }}>
                                      Approve
                                    </Button>
                                    <Button size="small" variant="outlined" color="warning" disabled={!canAdmin || busy} onClick={() => void handleDomainApproval(domain, "ignored")} sx={{ borderRadius: "8px", textTransform: "none", px: 1 }}>
                                      Ignore
                                    </Button>
                                    <Button size="small" variant="outlined" disabled={!canAdmin || busy} onClick={() => void handleDomainRecrawl(domain)} sx={{ borderRadius: "8px", textTransform: "none", px: 1 }}>
                                      Re-crawl
                                    </Button>
                                  </Stack>
                                </TableCell>
                              </TableRow>
                            ))
                        ) : (
                          <TableRow>
                            <TableCell colSpan={2}>
                              <Typography sx={{ color: "#64748B", fontSize: 13 }}>
                                No domains have been registered yet. Add a seed and run the connector to bootstrap discovery.
                              </Typography>
                            </TableCell>
                          </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </Box>
                  </Paper>

                  <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Page Store</Typography>
                    <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 13 }}>
                      Indexed pages stored in the first-party AUGMIS corpus. Showing the latest {webPages.length} of {webPagesTotal}.
                    </Typography>
                    <Tabs
                      value={independentDiagnosticsTab}
                      onChange={(_, value: number) => setIndependentDiagnosticsTab(value)}
                      variant="scrollable"
                      allowScrollButtonsMobile
                      sx={{ mt: 1.2, minHeight: 36, "& .MuiTab-root": { minHeight: 36, textTransform: "none", fontWeight: 700 } }}
                    >
                      <Tab label="Pages" />
                      <Tab label="Run Diagnostics" />
                      <Tab label="Domains" />
                    </Tabs>
                    {independentDiagnosticsTab === 1 ? (
                      <Box sx={{ mt: 1 }}>
                        <Typography sx={{ color: "#475569", fontSize: 13 }}>
                          Candidate visibility and filter-reason diagnostics persisted from the latest independent run.
                        </Typography>
                        <Stack direction="row" spacing={0.75} sx={{ mt: 1, flexWrap: "wrap", rowGap: 0.75 }}>
                          {recordEntriesDescending(selectedRunMetadata?.candidate_visibility_counts).map(([code, count]) => (
                            <Chip key={`visibility-${code}`} size="small" label={`${formatDiagnosticCode(code)} · ${count}`} sx={{ bgcolor: "#F8FAFC", borderRadius: "8px" }} />
                          ))}
                          {!recordEntriesDescending(selectedRunMetadata?.candidate_visibility_counts).length ? (
                            <Chip size="small" label="No persisted visibility counts" sx={{ bgcolor: "#F8FAFC", borderRadius: "8px" }} />
                          ) : null}
                        </Stack>
                        <Stack direction="row" spacing={0.75} sx={{ mt: 1, flexWrap: "wrap", rowGap: 0.75 }}>
                          {recordEntriesDescending(selectedRunMetadata?.candidate_exclusion_reason_counts).map(([code, count]) => (
                            <Chip key={`excluded-${code}`} size="small" label={`${formatDiagnosticCode(code)} · ${count}`} sx={{ bgcolor: "#FEF2F2", color: "#991B1B", borderRadius: "8px" }} />
                          ))}
                        </Stack>
                      </Box>
                    ) : null}
                    {independentDiagnosticsTab === 2 ? (
                      <Box sx={{ mt: 1, width: "100%", overflowX: "auto" }}>
                        <Table size="small" sx={{ width: "100%", minWidth: 420, tableLayout: "fixed" }}>
                          <TableHead>
                            <TableRow>
                              <TableCell sx={{ width: "66%" }}>Domain</TableCell>
                              <TableCell sx={{ width: "34%" }}>Policy</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {webDomains.length ? (
                              webDomains.map((domain) => (
                                <TableRow key={`diagnostic-domain-${domain.id}`} hover>
                                  <TableCell>
                                    <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13 }}>{domain.domain}</Typography>
                                    <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12 }}>
                                      Source: {domain.source || "n/a"} · Trust: {domain.trust_source_type || "n/a"}
                                    </Typography>
                                  </TableCell>
                                  <TableCell sx={{ fontSize: 12, color: "#475569" }}>
                                    {domain.approval_status} · {domain.status}
                                  </TableCell>
                                </TableRow>
                              ))
                            ) : (
                              <TableRow>
                                <TableCell colSpan={2}>
                                  <Typography sx={{ color: "#64748B", fontSize: 13 }}>No domains have been discovered yet.</Typography>
                                </TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </Box>
                    ) : null}
                    {independentDiagnosticsTab === 0 ? (
                    <Box sx={{ mt: 1, width: "100%", overflowX: "auto" }}>
                      <Table size="small" sx={{ width: "100%", minWidth: 1080, tableLayout: "fixed" }}>
                        <TableHead>
                          <TableRow>
                            <TableCell sx={{ width: "28%" }}>Title</TableCell>
                            <TableCell sx={{ width: "14%" }}>Domain</TableCell>
                            <TableCell sx={{ width: "12%" }}>Page Type</TableCell>
                            <TableCell sx={{ width: "14%" }}>Crawl Status</TableCell>
                            <TableCell sx={{ width: "12%" }}>Decision</TableCell>
                            <TableCell sx={{ width: "12%" }}>Reason</TableCell>
                            <TableCell sx={{ width: "8%" }}>Last Seen</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {webPages.length ? (
                            webPages.map((page) => {
                              const visibility = extractIndependentCandidateVisibility(page);
                              const decision = extractIndependentCandidateDecision(page);
                              const sourceMetadata = (page.source_metadata_json || {}) as Record<string, unknown>;
                              return (
                              <TableRow key={page.id} hover>
                                <TableCell>
                                  <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                    {page.title || "Untitled page"}
                                  </Typography>
                                  <Typography sx={{ fontSize: 12, color: "#64748B", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                    {page.canonical_url}
                                  </Typography>
                                </TableCell>
                                <TableCell>
                                  <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13, overflowWrap: "anywhere" }}>
                                    {page.domain}
                                  </Typography>
                                  <Typography sx={{ mt: 0.4, fontSize: 12, color: "#64748B" }}>
                                    HTTP {page.http_status ?? "n/a"}
                                  </Typography>
                                </TableCell>
                                <TableCell sx={{ fontSize: 12, color: "#475569", textTransform: "lowercase" }}>
                                  {page.page_type}
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    size="small"
                                    label={String(sourceMetadata.crawl_status || "stored")}
                                    sx={{ borderRadius: "8px", bgcolor: "#F8FAFC" }}
                                  />
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    size="small"
                                    label={decision.decision || (visibility.eligible ? "candidate_visible" : "excluded")}
                                    sx={{
                                      borderRadius: "8px",
                                      bgcolor: decision.decision === "new" ? "#ECFDF5" : decision.decision === "duplicate" ? "#FFF7ED" : "#FEF2F2",
                                      color: decision.decision === "new" ? "#166534" : decision.decision === "duplicate" ? "#B45309" : "#991B1B",
                                    }}
                                  />
                                </TableCell>
                                <TableCell>
                                  <Typography sx={{ fontSize: 12, color: "#475569" }}>
                                    {(decision.reason_codes || visibility.reason_codes || []).slice(0, 2).map(formatDiagnosticCode).join(" · ") || "No reason codes"}
                                  </Typography>
                                </TableCell>
                                <TableCell sx={{ fontSize: 12, color: "#475569", overflowWrap: "anywhere" }}>
                                  {formatDate(page.last_seen_at)}
                                </TableCell>
                              </TableRow>
                              );
                            })
                          ) : (
                            <TableRow>
                              <TableCell colSpan={7}>
                                <Typography sx={{ color: "#64748B", fontSize: 13 }}>
                                  No pages have been indexed yet.
                                </Typography>
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </Box>
                    ) : null}
                  </Paper>
                </Stack>
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

              {selectedConnector.connector_type === "freelancer_marketplace" ? (
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={1.2}
                    sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Freelancer Settings</Typography>
                      <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 13 }}>
                        Bounded marketplace discovery using the shared AUGMIS search profile. Mock mode reuses realistic local Freelancer API fixtures and performs no external HTTP.
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
                    <TextField
                      select
                      size="small"
                      label="Environment / Mode"
                      value={String(selectedConnector.configuration_json.mode || "production")}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? { ...current, configuration_json: { ...current.configuration_json, mode: event.target.value } }
                            : current
                        )
                      }
                    >
                      <MenuItem value="production">Production</MenuItem>
                      <MenuItem value="mock">Test / Mock</MenuItem>
                    </TextField>
                    <TextField
                      size="small"
                      label="Source"
                      value={selectedConnector.configuration_json.mode === "mock" ? "Local realistic Freelancer fixtures" : "Official Freelancer API"}
                      disabled
                    />
                    <TextField
                      size="small"
                      label="Authentication"
                      value={selectedConnector.configuration_json.mode === "mock" ? "No Credential Required" : "OAuth Access Token"}
                      disabled
                    />
                    <TextField
                      select
                      size="small"
                      label="Lookback Period"
                      value={String(connectorNumberConfig(selectedConnector, "lookback_hours", 24))}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? { ...current, configuration_json: { ...current.configuration_json, lookback_hours: Number(event.target.value) } }
                            : current
                        )
                      }
                    >
                      <MenuItem value="6">6 hours</MenuItem>
                      <MenuItem value="12">12 hours</MenuItem>
                      <MenuItem value="24">24 hours</MenuItem>
                      <MenuItem value="72">3 days</MenuItem>
                      <MenuItem value="168">7 days</MenuItem>
                      <MenuItem value="336">14 days</MenuItem>
                      <MenuItem value="720">30 days</MenuItem>
                    </TextField>
                    <TextField
                      select
                      size="small"
                      label="Maximum Projects Per Scan"
                      value={String(connectorNumberConfig(selectedConnector, "maximum_projects_per_scan", 50))}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? { ...current, configuration_json: { ...current.configuration_json, maximum_projects_per_scan: Number(event.target.value) } }
                            : current
                        )
                      }
                    >
                      <MenuItem value="10">10</MenuItem>
                      <MenuItem value="25">25</MenuItem>
                      <MenuItem value="50">50</MenuItem>
                      <MenuItem value="100">100</MenuItem>
                      <MenuItem value="200">200</MenuItem>
                    </TextField>
                    <TextField
                      select
                      size="small"
                      label="Project Type"
                      value={String(selectedConnector.configuration_json.project_type || "all")}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? { ...current, configuration_json: { ...current.configuration_json, project_type: event.target.value } }
                            : current
                        )
                      }
                    >
                      <MenuItem value="all">All</MenuItem>
                      <MenuItem value="fixed">Fixed Price</MenuItem>
                      <MenuItem value="hourly">Hourly</MenuItem>
                    </TextField>
                    <TextField size="small" label="Project Status" value="Active only" disabled />
                    <AdminFormTextField
                      label="Minimum Budget"
                      value={String(selectedConnector.configuration_json.minimum_budget ?? "")}
                      onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        setSelectedConnector((current) =>
                          current
                            ? { ...current, configuration_json: { ...current.configuration_json, minimum_budget: normalizeOptionalNumber(event.target.value) } }
                            : current
                        )
                      }
                    />
                    <AdminFormTextField
                      label="Maximum Budget"
                      value={String(selectedConnector.configuration_json.maximum_budget ?? "")}
                      onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        setSelectedConnector((current) =>
                          current
                            ? { ...current, configuration_json: { ...current.configuration_json, maximum_budget: normalizeOptionalNumber(event.target.value) } }
                            : current
                        )
                      }
                    />
                    <AdminFormTextField
                      label="Maximum Existing Bids"
                      value={String(selectedConnector.configuration_json.maximum_existing_bids ?? "")}
                      onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        setSelectedConnector((current) =>
                          current
                            ? { ...current, configuration_json: { ...current.configuration_json, maximum_existing_bids: normalizeOptionalNumber(event.target.value) } }
                            : current
                        )
                      }
                    />
                    <TextField size="small" label="Search Scope" value="Default AUGMIS Discovery Profile" disabled />
                  </Box>
                  {selectedConnector.configuration_json.mode === "mock" ? (
                    <Alert severity="info" sx={{ mt: 1.15, borderRadius: "8px" }}>
                      Test / Mock mode uses local realistic Freelancer API fixtures. No requests are sent to Freelancer.com.
                    </Alert>
                  ) : null}
                </Paper>
              ) : null}

              {["remote_job_feed", "job_board_api", "remote_job_api", "job_search_api"].includes(selectedConnector.connector_type) ? (
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={1.2}
                    sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Provider Settings</Typography>
                      <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 13 }}>
                        Bounded external-work discovery using official provider APIs and the shared AUGMIS search profile.
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
                  <Box sx={{ mt: 1.2, display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
                    <TextField size="small" label="Provider" value={selectedConnector.name} disabled />
                    <TextField size="small" label="Authentication" value={selectedConnector.connector_type === "job_search_api" ? "App ID + App Key" : "No API Key Required"} disabled />
                    <TextField
                      select
                      size="small"
                      label="Maximum Results"
                      value={String(connectorNumberConfig(selectedConnector, "maximum_results", selectedConnector.connector_type === "job_search_api" ? 25 : 50))}
                      onChange={(event) =>
                        setSelectedConnector((current) =>
                          current
                            ? { ...current, configuration_json: { ...current.configuration_json, maximum_results: Number(event.target.value) } }
                            : current
                        )
                      }
                    >
                      <MenuItem value="10">10</MenuItem>
                      <MenuItem value="25">25</MenuItem>
                      <MenuItem value="50">50</MenuItem>
                      <MenuItem value="100">100</MenuItem>
                    </TextField>
                    {selectedConnector.connector_type === "job_board_api" ? (
                      <TextField
                        select
                        size="small"
                        label="Remote Only"
                        value={selectedConnector.configuration_json.remote_only === false ? "no" : "yes"}
                        onChange={(event) =>
                          setSelectedConnector((current) =>
                            current
                              ? { ...current, configuration_json: { ...current.configuration_json, remote_only: event.target.value === "yes" } }
                              : current
                          )
                        }
                      >
                        <MenuItem value="yes">Yes</MenuItem>
                        <MenuItem value="no">No</MenuItem>
                      </TextField>
                    ) : (
                      <AdminFormTextField
                        label="Search Keyword"
                        value={String(selectedConnector.configuration_json.search_keyword ?? "")}
                        onChange={(event: ChangeEvent<HTMLInputElement>) =>
                          setSelectedConnector((current) =>
                            current
                              ? { ...current, configuration_json: { ...current.configuration_json, search_keyword: event.target.value } }
                              : current
                          )
                        }
                      />
                    )}
                    {selectedConnector.connector_type === "job_search_api" ? (
                      <AdminFormTextField
                        label="Target Markets"
                        value={Array.isArray(selectedConnector.configuration_json.target_countries_json) ? selectedConnector.configuration_json.target_countries_json.join(", ") : "gb"}
                        onChange={(event: ChangeEvent<HTMLInputElement>) =>
                          setSelectedConnector((current) =>
                            current
                              ? {
                                  ...current,
                                  configuration_json: {
                                    ...current.configuration_json,
                                    target_countries_json: event.target.value
                                      .split(",")
                                      .map((item) => item.trim().toLowerCase())
                                      .filter(Boolean)
                                      .slice(0, 5),
                                  },
                                }
                              : current
                          )
                        }
                      />
                    ) : null}
                  </Box>
                  {selectedConnector.connector_type === "job_search_api" ? (
                    <Alert severity="info" sx={{ mt: 1.15, borderRadius: "8px" }}>
                      Adzuna API usage is subject to Adzuna&apos;s API terms and provider access limits.
                    </Alert>
                  ) : null}
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

              {selectedConnector?.connector_type === "independent_web_discovery" && selectedRunMetadata && selectedConnectorRunActive ? (
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #BFDBFE", bgcolor: "#F8FBFF" }}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
                    <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                      <CircularProgress size={18} />
                      <Box>
                        <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Scan Progress</Typography>
                        <Typography sx={{ color: "#475569", fontSize: 13 }}>
                          {selectedRunMetadata.stage_label || "Scanning"} · {selectedRunMetadata.crawl_engine_display || crawlEngineDisplay(selectedRunMetadata.crawl_engine)} · Elapsed {formatElapsed(selectedRunMetadata.elapsed_seconds)}
                        </Typography>
                      </Box>
                    </Stack>
                    <Chip label={selectedConnectorRun?.status || "running"} size="small" sx={{ textTransform: "capitalize" }} />
                  </Stack>
                  <Stack direction="row" spacing={1} sx={{ mt: 1.1, justifyContent: "flex-end" }}>
                    <Button
                      variant="outlined"
                      size="small"
                      color="error"
                      onClick={() => void handleStopScan(selectedConnector, selectedConnectorRun)}
                      disabled={!canScan || busy || !selectedConnectorRun}
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                    >
                      Stop Scan
                    </Button>
                  </Stack>
                  <Box sx={{ mt: 1.2 }}>
                    <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: ".04em" }}>
                      {selectedRunMetadata.current_batch_label || "Current Batch"}
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={selectedRunMetadata.progress_percent ?? 0}
                      sx={{ mt: 0.7, height: 8, borderRadius: 999, bgcolor: "#DBEAFE" }}
                    />
                    <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 13 }}>
                      {(selectedRunMetadata.batch_progress_current ?? selectedRunMetadata.pages_fetched ?? 0)} / {(selectedRunMetadata.batch_progress_total ?? connectorNumberConfig(selectedConnector, "maximum_total_pages_per_run", 100))} pages
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      mt: 1.2,
                      display: "grid",
                      gap: 1,
                      gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", md: "repeat(4, minmax(0, 1fr))" },
                    }}
                  >
                    <MetadataMetric label="Stage" value={selectedRunMetadata.stage_label || selectedRunMetadata.stage || "Running"} />
                    <MetadataMetric label="Current Domain" value={selectedRunMetadata.current_domain || "Not available"} />
                    <MetadataMetric label="Seeds Selected" value={selectedRunMetadata.seeds_selected ?? selectedRunMetadata.seeds_processed ?? 0} />
                    <MetadataMetric label="Skipped Not Due" value={selectedRunMetadata.seeds_skipped_not_due ?? 0} />
                    <MetadataMetric label="Requests Scheduled" value={selectedRunMetadata.requests_scheduled ?? selectedRunMetadata.urls_queued ?? 0} />
                    <MetadataMetric label="Requests Attempted" value={selectedRunMetadata.requests_attempted ?? selectedRunMetadata.pages_attempted ?? 0} />
                    <MetadataMetric label="Responses Received" value={selectedRunMetadata.responses_received ?? selectedRunMetadata.pages_fetched ?? 0} />
                    <MetadataMetric label="Pages Parsed" value={selectedRunMetadata.pages_parsed ?? selectedRunMetadata.pages_fetched ?? 0} />
                    <MetadataMetric label="Pending Frontier" value={selectedRunMetadata.pending_frontier_count ?? 0} />
                    <MetadataMetric label="Depth" value={selectedRunMetadata.current_depth ?? 0} />
                    <MetadataMetric label="Candidates" value={selectedRunMetadata.candidates_created ?? selectedRunMetadata.opportunity_candidates ?? 0} />
                    <MetadataMetric label="New" value={selectedConnectorRun?.items_new ?? 0} />
                  </Box>
                  {selectedRunMetadata.current_url ? (
                    <Typography sx={{ mt: 1, color: "#475569", fontSize: 12 }}>
                      Current URL: {selectedRunMetadata.current_url}
                    </Typography>
                  ) : null}
                </Paper>
              ) : null}

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
                    {selectedConnector?.connector_type === "independent_web_discovery" ? (
                      <>
                        <MetadataMetric label="Provider" value={selectedRunMetadata.provider || "AUGMIS Internal"} />
                        <MetadataMetric label="Seeds Available" value={selectedRunMetadata.seeds_available ?? 0} />
                        <MetadataMetric label="Seeds Selected" value={selectedRunMetadata.seeds_selected ?? selectedRunMetadata.seeds_processed ?? 0} />
                        <MetadataMetric label="Skipped Not Due" value={selectedRunMetadata.seeds_skipped_not_due ?? 0} />
                        <MetadataMetric label="Domains" value={selectedRunMetadata.domains_visited ?? 0} />
                        <MetadataMetric label="Queued URLs" value={selectedRunMetadata.urls_queued ?? 0} />
                        <MetadataMetric label="Requests Scheduled" value={selectedRunMetadata.requests_scheduled ?? selectedRunMetadata.urls_queued ?? 0} />
                        <MetadataMetric label="Requests Attempted" value={selectedRunMetadata.requests_attempted ?? selectedRunMetadata.pages_attempted ?? 0} />
                        <MetadataMetric label="Responses Received" value={selectedRunMetadata.responses_received ?? selectedRunMetadata.pages_fetched ?? 0} />
                        <MetadataMetric label="Pages Parsed" value={selectedRunMetadata.pages_parsed ?? selectedRunMetadata.pages_fetched ?? 0} />
                        <MetadataMetric label="Pages Attempted" value={selectedRunMetadata.pages_attempted ?? 0} />
                        <MetadataMetric label="Pages Fetched" value={selectedRunMetadata.pages_fetched ?? 0} />
                        <MetadataMetric label="Pages Changed" value={selectedRunMetadata.pages_changed ?? 0} />
                        <MetadataMetric label="Listings" value={selectedRunMetadata.listing_pages ?? 0} />
                        <MetadataMetric label="Detail Pages" value={selectedRunMetadata.detail_pages ?? 0} />
                        <MetadataMetric label="Robots Denied" value={selectedRunMetadata.robots_denied ?? 0} />
                        <MetadataMetric label="Candidates" value={selectedRunMetadata.candidates_created ?? selectedRunMetadata.opportunity_candidates ?? 0} />
                        <MetadataMetric label="Accepted" value={selectedRunMetadata.candidates_accepted ?? 0} />
                        <MetadataMetric label="Filtered" value={selectedConnectorRun?.items_filtered ?? 0} />
                        <MetadataMetric label="Duplicates" value={selectedConnectorRun?.items_duplicate ?? 0} />
                        <MetadataMetric label="New Discoveries" value={selectedConnectorRun?.items_new ?? 0} />
                        <MetadataMetric label="Attachments Skipped" value={selectedRunMetadata.attachments_skipped ?? 0} />
                        <MetadataMetric label="Oversized HTML" value={selectedRunMetadata.oversized_html_skipped ?? 0} />
                        <MetadataMetric label="Stale / Error" value={selectedRunMetadata.stale_or_error_pages ?? 0} />
                        <MetadataMetric label="Unknown Pages" value={selectedRunMetadata.unknown_pages ?? 0} />
                        <MetadataMetric label="Contacts" value={selectedRunMetadata.contacts_found ?? 0} />
                        <MetadataMetric label="Fetch Failures" value={selectedRunMetadata.errors ?? 0} />
                      </>
                    ) : (
                      <>
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
                      </>
                    )}
                  </Box>
                  <Typography sx={{ mt: 1.1, color: "#64748B", fontSize: 12 }}>
                    {selectedConnector?.connector_type === "independent_web_discovery"
                      ? `Effective limits: ${connectorNumberConfig(selectedConnector, "maximum_domains_per_run", 5)} domains/run, ${connectorNumberConfig(selectedConnector, "maximum_pages_per_domain", 25)} pages/domain, ${connectorNumberConfig(selectedConnector, "maximum_total_pages_per_run", 100)} pages/run, depth ${connectorNumberConfig(selectedConnector, "maximum_depth", 2)}, delay ${connectorNumberConfig(selectedConnector, "per_domain_delay_seconds", 2)}s, timeout ${connectorNumberConfig(selectedConnector, "request_timeout_seconds", 15)}s, max HTML ${formatBytes(selectedRunMetadata.max_html_response_bytes ?? connectorNumberConfig(selectedConnector, "max_html_response_bytes", 2000000))}`
                      : `Effective limits: ${selectedRunMetadata.maximum_queries_per_scan ?? 0} queries, ${selectedRunMetadata.results_per_query ?? 0} results/query, ${selectedRunMetadata.max_source_fetches_per_scan ?? 0} source fetches, ${formatBytes(selectedRunMetadata.max_fetch_bytes)}`}
                  </Typography>
                  {selectedConnector?.connector_type === "independent_web_discovery" && selectedRunMetadata.outcome_message ? (
                    <Alert severity="info" sx={{ mt: 1.2, borderRadius: "8px" }}>
                      {selectedRunMetadata.outcome_message}
                    </Alert>
                  ) : null}
                  {selectedConnector?.connector_type === "independent_web_discovery" && selectedRunMetadata.skip_summary ? (
                    <Alert severity="warning" sx={{ mt: 1.2, borderRadius: "8px" }}>
                      {selectedRunMetadata.skip_summary}
                    </Alert>
                  ) : null}
                  {selectedConnector?.connector_type === "independent_web_discovery" && canAdmin ? (
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
                        Crawl Diagnostics
                      </Box>
                      <Stack spacing={1} sx={{ mt: 1 }}>
                        <Box
                          sx={{
                            display: "grid",
                            gap: 1,
                            gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", md: "repeat(4, minmax(0, 1fr))" },
                          }}
                        >
                          <MetadataMetric label="Fetched" value={selectedRunMetadata.pages_fetched ?? 0} />
                          <MetadataMetric label="Opportunity-Like" value={selectedRunMetadata.opportunity_like_pages ?? 0} />
                          <MetadataMetric label="Detail Pages" value={selectedRunMetadata.detail_pages ?? 0} />
                          <MetadataMetric label="Candidates" value={selectedRunMetadata.candidates_created ?? 0} />
                          <MetadataMetric label="Accepted" value={selectedRunMetadata.candidates_accepted ?? 0} />
                          <MetadataMetric label="Filtered" value={selectedConnectorRun?.items_filtered ?? 0} />
                          <MetadataMetric label="Duplicates" value={selectedConnectorRun?.items_duplicate ?? 0} />
                          <MetadataMetric label="New Discoveries" value={selectedConnectorRun?.items_new ?? 0} />
                        </Box>
                        <Box>
                          <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 12 }}>Listing-Link Follow</Typography>
                          <Stack direction="row" spacing={0.75} sx={{ mt: 0.8, flexWrap: "wrap", rowGap: 0.75 }}>
                            <Chip size="small" label={`Discovered ${selectedRunMetadata.detail_links_discovered ?? 0}`} sx={{ bgcolor: "#F8FAFC", borderRadius: "8px" }} />
                            <Chip size="small" label={`Queued ${selectedRunMetadata.detail_links_queued ?? 0}`} sx={{ bgcolor: "#F8FAFC", borderRadius: "8px" }} />
                            <Chip size="small" label={`Skipped Depth ${selectedRunMetadata.detail_links_skipped_depth ?? 0}`} sx={{ bgcolor: "#FFF7ED", color: "#B45309", borderRadius: "8px" }} />
                            <Chip size="small" label={`Skipped Policy ${selectedRunMetadata.detail_links_skipped_domain_policy ?? 0}`} sx={{ bgcolor: "#FFF7ED", color: "#B45309", borderRadius: "8px" }} />
                            <Chip size="small" label={`Fetch Failed ${selectedRunMetadata.detail_links_fetch_failed ?? 0}`} sx={{ bgcolor: "#FEF2F2", color: "#991B1B", borderRadius: "8px" }} />
                            <Chip size="small" label={`Robots Denied ${selectedRunMetadata.detail_links_robots_denied ?? 0}`} sx={{ bgcolor: "#FEF2F2", color: "#991B1B", borderRadius: "8px" }} />
                          </Stack>
                        </Box>
                        {recordEntriesDescending(selectedRunMetadata.skip_reason_counts).length ? (
                          <Box>
                            <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 12 }}>Skipped Pages</Typography>
                            <Stack direction="row" spacing={0.75} sx={{ mt: 0.8, flexWrap: "wrap", rowGap: 0.75 }}>
                              {recordEntriesDescending(selectedRunMetadata.skip_reason_counts).map(([code, count]) => (
                                <Chip key={`skip-${code}`} size="small" label={`${formatDiagnosticCode(code)} · ${count}`} sx={{ bgcolor: "#FFF7ED", color: "#B45309", borderRadius: "8px" }} />
                              ))}
                            </Stack>
                          </Box>
                        ) : null}
                        {selectedRunMetadata.skip_samples?.length ? (
                          <Stack spacing={1}>
                            {selectedRunMetadata.skip_samples.slice(0, 5).map((sample, index) => (
                              <Paper key={`${selectedConnectorRun?.id}-skip-sample-${index}`} elevation={0} sx={{ p: 1, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                                <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13 }}>
                                  {formatDiagnosticCode(sample.error_code || "SKIPPED")}
                                </Typography>
                                <Typography sx={{ mt: 0.35, color: "#475569", fontSize: 12, overflowWrap: "anywhere" }}>
                                  {sample.url || "No URL recorded"}
                                </Typography>
                                <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12 }}>
                                  {(sample.engine ? `${crawlEngineDisplay(sample.engine as "augmis_native" | "scrapy")} · ` : "")}
                                  {(sample.resource_kind ? `${formatDiagnosticCode(sample.resource_kind)} · ` : "")}
                                  Domain: {sample.domain || "n/a"} · Depth: {sample.depth ?? 0}
                                  {sample.http_status != null ? ` · HTTP ${sample.http_status}` : ""}
                                </Typography>
                                {(sample.content_length != null || sample.response_bytes != null || sample.limit_bytes != null) ? (
                                  <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12 }}>
                                    {(sample.content_type || "Unknown type")}
                                    {sample.content_length != null ? ` · Declared ${formatBytes(sample.content_length)}` : ""}
                                    {sample.response_bytes != null ? ` · Read ${formatBytes(sample.response_bytes)}` : ""}
                                    {sample.limit_bytes != null ? ` · Limit ${formatBytes(sample.limit_bytes)}` : ""}
                                  </Typography>
                                ) : null}
                                {sample.parent_url ? (
                                  <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12, overflowWrap: "anywhere" }}>
                                    Parent: {sample.parent_url}
                                  </Typography>
                                ) : null}
                                {sample.message ? (
                                  <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12 }}>
                                    {sample.message}
                                  </Typography>
                                ) : null}
                              </Paper>
                            ))}
                          </Stack>
                        ) : null}
                        {recordEntriesDescending(selectedRunMetadata.fetch_failure_counts).length ? (
                          <Box>
                            <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 12 }}>Fetch Failures</Typography>
                            <Stack direction="row" spacing={0.75} sx={{ mt: 0.8, flexWrap: "wrap", rowGap: 0.75 }}>
                              {recordEntriesDescending(selectedRunMetadata.fetch_failure_counts).map(([code, count]) => (
                                <Chip key={`fetch-${code}`} size="small" label={`${formatDiagnosticCode(code)} · ${count}`} sx={{ bgcolor: "#FEF2F2", color: "#991B1B", borderRadius: "8px" }} />
                              ))}
                            </Stack>
                          </Box>
                        ) : null}
                        {selectedRunMetadata.fetch_failure_samples?.length ? (
                          <Stack spacing={1}>
                            {selectedRunMetadata.fetch_failure_samples.slice(0, 6).map((sample, index) => (
                              <Paper key={`${selectedConnectorRun?.id}-fetch-sample-${index}`} elevation={0} sx={{ p: 1, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                                <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13 }}>
                                  {formatDiagnosticCode(sample.error_code || "UNKNOWN_FETCH_ERROR")}
                                </Typography>
                                <Typography sx={{ mt: 0.35, color: "#475569", fontSize: 12, overflowWrap: "anywhere" }}>
                                  {sample.url || "No URL recorded"}
                                </Typography>
                                <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12 }}>
                                  {(sample.engine ? `${crawlEngineDisplay(sample.engine as "augmis_native" | "scrapy")} · ` : "")}
                                  Domain: {sample.domain || "n/a"} · Depth: {sample.depth ?? 0} · Retryable: {sample.retryable ? "Yes" : "No"}
                                  {sample.http_status != null ? ` · HTTP ${sample.http_status}` : ""}
                                </Typography>
                                {(sample.content_length != null || sample.response_bytes != null || sample.limit_bytes != null) ? (
                                  <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12 }}>
                                    {(sample.content_type || "Unknown type")}
                                    {sample.content_length != null ? ` · Declared ${formatBytes(sample.content_length)}` : ""}
                                    {sample.response_bytes != null ? ` · Read ${formatBytes(sample.response_bytes)}` : ""}
                                    {sample.limit_bytes != null ? ` · Limit ${formatBytes(sample.limit_bytes)}` : ""}
                                  </Typography>
                                ) : null}
                                {sample.parent_url ? (
                                  <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12, overflowWrap: "anywhere" }}>
                                    Parent: {sample.parent_url}
                                  </Typography>
                                ) : null}
                                {sample.message ? (
                                  <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12 }}>
                                    {sample.message}
                                  </Typography>
                                ) : null}
                              </Paper>
                            ))}
                          </Stack>
                        ) : null}
                        {recordEntriesDescending(selectedRunMetadata.filter_reason_counts).length ? (
                          <Box>
                            <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 12 }}>Filter Reasons</Typography>
                            <Stack direction="row" spacing={0.75} sx={{ mt: 0.8, flexWrap: "wrap", rowGap: 0.75 }}>
                              {recordEntriesDescending(selectedRunMetadata.filter_reason_counts).map(([code, count]) => (
                                <Chip key={`filter-${code}`} size="small" label={`${formatDiagnosticCode(code)} · ${count}`} sx={{ bgcolor: "#FEF2F2", color: "#991B1B", borderRadius: "8px" }} />
                              ))}
                            </Stack>
                          </Box>
                        ) : null}
                        {selectedRunMetadata.candidate_outcomes?.length ? (
                          <Stack spacing={1}>
                            {selectedRunMetadata.candidate_outcomes.slice(0, 5).map((outcome, index) => (
                              <Paper key={`${selectedConnectorRun?.id}-independent-outcome-${index}`} elevation={0} sx={{ p: 1, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                                <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13 }}>
                                  {outcome.title || "Untitled candidate"}
                                </Typography>
                                <Typography sx={{ mt: 0.35, color: "#475569", fontSize: 12 }}>
                                  Status: {outcome.discovery_status || "unknown"} · Type: {outcome.page_type || "unknown"} · Score: {outcome.relevance_score ?? "n/a"}
                                </Typography>
                                {outcome.reason_codes?.length ? (
                                  <Stack direction="row" spacing={0.6} sx={{ mt: 0.8, flexWrap: "wrap", rowGap: 0.6 }}>
                                    {outcome.reason_codes.map((code) => (
                                      <Chip key={`${outcome.title}-${code}`} label={formatDiagnosticCode(code)} size="small" sx={{ bgcolor: "#EFF6FF", color: "#1D4ED8", borderRadius: "8px" }} />
                                    ))}
                                  </Stack>
                                ) : null}
                              </Paper>
                            ))}
                          </Stack>
                        ) : (
                          <Typography sx={{ color: "#64748B", fontSize: 12 }}>
                            No independent candidate outcomes were persisted for this run.
                          </Typography>
                        )}
                      </Stack>
                    </Box>
                  ) : null}
                  {canAdmin && selectedRunMetadata.query_diagnostics?.length ? (
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
                              {diagnostic.filtered_bids != null ? ` · Bid-filtered ${diagnostic.filtered_bids}` : ""}
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
                            {diagnostic.skills?.length ? (
                              <Typography sx={{ mt: 0.8, color: "#64748B", fontSize: 12 }}>
                                Skills: {diagnostic.skills.join(", ")}
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
                            <Chip
                              label={isConnectorRunActive(run.status) ? `${run.status} · ${metadata.stage_label || metadata.stage || "Scanning"}` : run.status}
                              size="small"
                              sx={{ textTransform: "capitalize" }}
                            />
                          </Stack>
                          <Typography sx={{ mt: 0.7, color: "#475569", fontSize: 13 }}>
                            {formatDate(run.started_at)} · Found {run.items_found} · New {run.items_new} · Duplicate {run.items_duplicate} · Filtered {run.items_filtered} · Failed {run.items_failed}
                          </Typography>
                          <Typography sx={{ mt: 0.45, color: "#64748B", fontSize: 12 }}>
                            Attempt {run.attempt_number} of {run.max_attempts}
                            {run.next_retry_at ? ` · Retry scheduled ${formatDate(run.next_retry_at)}` : ""}
                          </Typography>
                          {selectedConnector?.connector_type === "independent_web_discovery" ? (
                            <Typography sx={{ mt: 0.45, color: "#64748B", fontSize: 12 }}>
                              Engine: {metadata.crawl_engine_display || crawlEngineDisplay(metadata.crawl_engine)}
                            </Typography>
                          ) : null}
                          {metadata.query_count != null || metadata.api_result_count != null ? (
                          <Typography sx={{ mt: 0.6, color: "#64748B", fontSize: 12 }}>
                              Provider {metadata.provider || "n/a"} · Queries {metadata.query_count ?? 0} · API results {metadata.api_result_count ?? 0} · Attempted {metadata.source_pages_attempted ?? 0} · Fetched {metadata.source_pages_fetched ?? 0} · Skipped {metadata.source_pages_skipped_due_limit ?? 0}
                            </Typography>
                          ) : null}
                          {selectedConnector?.connector_type === "independent_web_discovery" && metadata.outcome_message ? (
                            <Typography sx={{ mt: 0.6, color: "#475569", fontSize: 12 }}>
                              {metadata.outcome_message}
                            </Typography>
                          ) : null}
                          {selectedConnector?.connector_type === "independent_web_discovery" && metadata.skip_summary ? (
                            <Typography sx={{ mt: 0.45, color: "#B45309", fontSize: 12 }}>
                              {metadata.skip_summary}
                            </Typography>
                          ) : null}
                          {selectedConnector?.connector_type === "independent_web_discovery" && recordEntriesDescending(metadata.skip_reason_counts).length ? (
                            <Stack direction="row" spacing={0.6} sx={{ mt: 0.8, flexWrap: "wrap", rowGap: 0.6 }}>
                              {recordEntriesDescending(metadata.skip_reason_counts).slice(0, 4).map(([code, count]) => (
                                <Chip key={`${run.id}-skip-${code}`} size="small" label={`${formatDiagnosticCode(code)} · ${count}`} sx={{ bgcolor: "#FFF7ED", color: "#B45309", borderRadius: "8px" }} />
                              ))}
                            </Stack>
                          ) : null}
                          {selectedConnector?.connector_type === "independent_web_discovery" && recordEntriesDescending(metadata.fetch_failure_counts).length ? (
                            <Stack direction="row" spacing={0.6} sx={{ mt: 0.8, flexWrap: "wrap", rowGap: 0.6 }}>
                              {recordEntriesDescending(metadata.fetch_failure_counts).slice(0, 4).map(([code, count]) => (
                                <Chip key={`${run.id}-${code}`} size="small" label={`${formatDiagnosticCode(code)} · ${count}`} sx={{ bgcolor: "#FEF2F2", color: "#991B1B", borderRadius: "8px" }} />
                              ))}
                            </Stack>
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
      </BusinessWorkspaceModal>

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
                  <Stack direction="row" spacing={0.75} sx={{ mt: 1, flexWrap: "wrap", rowGap: 0.75 }}>
                    <Chip
                      size="small"
                      label={discoverySourceDisplay(selectedDiscovery)}
                      sx={{ border: "1px solid", fontWeight: 700, ...discoverySourceChipStyle(selectedDiscovery) }}
                    />
                    <Chip
                      size="small"
                      label={(selectedDiscoveryIntelligence?.commercial_recommendation || "watch").toUpperCase()}
                      sx={{ textTransform: "uppercase", border: "1px solid", ...discoveryRecommendationChip(selectedDiscoveryIntelligence?.commercial_recommendation) }}
                    />
                    <Chip
                      size="small"
                      label={
                        selectedDiscoveryIntelligence?.commercial_priority_score == null
                          ? "Priority not scored"
                          : `Priority ${selectedDiscoveryIntelligence.commercial_priority_band || "?"} · ${Math.round(selectedDiscoveryIntelligence.commercial_priority_score)}`
                      }
                      sx={{ border: "1px solid", ...discoveryPriorityBandChip(selectedDiscoveryIntelligence?.commercial_priority_band) }}
                    />
                  </Stack>
                </Box>
                <Chip
                  label={selectedDiscovery.discovery_status}
                  size="small"
                  sx={{ textTransform: "capitalize", border: "1px solid", ...discoveryStatusChip(selectedDiscovery.discovery_status) }}
                />
              </Stack>

              <Paper
                elevation={0}
                sx={{
                  p: 1.6,
                  borderRadius: "10px",
                  border: "1px solid #D9E2EC",
                  background: "linear-gradient(135deg, #F8FBFF 0%, #FFFFFF 100%)",
                }}
              >
                <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ justifyContent: "space-between" }}>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Why this matters</Typography>
                    <Stack spacing={0.7} sx={{ mt: 0.9 }}>
                      {(selectedDiscoveryIntelligence?.commercial_recommendation_reasons_json || []).length ? (
                        selectedDiscoveryIntelligence?.commercial_recommendation_reasons_json.map((reason) => (
                          <Typography key={`decision-${reason}`} sx={{ color: "#166534", fontSize: 13 }}>
                            + {reason}
                          </Typography>
                        ))
                      ) : (
                        <Typography sx={{ color: "#475569", fontSize: 13 }}>
                          No deterministic recommendation summary has been recorded yet.
                        </Typography>
                      )}
                    </Stack>
                  </Box>
                  <Box sx={{ minWidth: 0, flex: { md: "0 0 44%" } }}>
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Risks</Typography>
                    <Stack spacing={0.7} sx={{ mt: 0.9 }}>
                      {(selectedDiscoveryIntelligence?.commercial_risks_json || []).length ? (
                        selectedDiscoveryIntelligence?.commercial_risks_json.map((risk) => (
                          <Typography key={`decision-risk-${risk}`} sx={{ color: "#B45309", fontSize: 13 }}>
                            – {risk}
                          </Typography>
                        ))
                      ) : (
                        <Typography sx={{ color: "#475569", fontSize: 13 }}>
                          No additional deterministic risks have been recorded.
                        </Typography>
                      )}
                    </Stack>
                  </Box>
                </Stack>
              </Paper>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
                  <Box>
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Source / Provider</Typography>
                    <Typography sx={{ mt: 0.5, color: "#475569", fontSize: 13 }}>
                      Discovery origin, language, trust, and audit metadata.
                    </Typography>
                  </Box>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => setShowSourceDetails((current) => !current)}
                    sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                  >
                    {showSourceDetails ? "Hide Source Details" : "Show Source Details"}
                  </Button>
                </Stack>
                <Box sx={{ mt: 1.1, display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
                  <MetadataMetric label="Connector" value={connectorById.get(selectedDiscovery.connector_id)?.name || selectedDiscovery.connector_id} />
                  <MetadataMetric label="Provider" value={selectedDiscoverySourceMetadata?.provider?.toUpperCase() || "Not available"} />
                  <MetadataMetric label="Retrieved" value={formatDate(selectedDiscovery.retrieval_timestamp)} />
                  <MetadataMetric label="Original Language" value={selectedDiscovery.source_language_label || "Unknown"} />
                </Box>
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
                      {selectedDiscovery.source_type === "employment_contract" && selectedDiscoverySourceMetadata?.provider === "remotive" ? "Open on Remotive" : "Open Source"}
                    </Button>
                    <Typography sx={{ color: "#2563EB", fontSize: 13, wordBreak: "break-word", alignSelf: "center" }}>
                      <LinkOutlinedIcon sx={{ fontSize: 16, mr: 0.5, verticalAlign: "text-bottom" }} />
                      {selectedDiscovery.source_url}
                    </Typography>
                  </Stack>
                ) : null}
                {showSourceDetails ? (
                  <Stack spacing={0.6} sx={{ mt: 1.2 }}>
                    <Typography sx={{ color: "#475569", fontSize: 13 }}>
                      Source trust: {selectedDiscoverySourceMetadata?.source_trust || "Not available"}
                    </Typography>
                    {selectedDiscovery.source_type === "public_procurement" ? (
                      <>
                        <Typography sx={{ color: "#475569", fontSize: 13 }}>
                          Publication Number: {selectedDiscoverySourceMetadata?.publication_number || "Not available"}
                        </Typography>
                        <Typography sx={{ color: "#475569", fontSize: 13 }}>
                          Notice Identifier: {selectedDiscoverySourceMetadata?.notice_identifier || "Not available"}
                        </Typography>
                        <Typography sx={{ color: "#475569", fontSize: 13 }}>
                          Notice Version: {selectedDiscoverySourceMetadata?.notice_version || "Not available"}
                        </Typography>
                      </>
                    ) : null}
                    {selectedDiscovery.source_type === "marketplace_project" ? (
                      <>
                        <Typography sx={{ color: "#475569", fontSize: 13 }}>
                          Project ID: {selectedDiscoverySourceMetadata?.provider_project_id || selectedDiscovery.external_id || "Not available"}
                        </Typography>
                        <Typography sx={{ color: "#475569", fontSize: 13 }}>
                          Project Type: {selectedDiscoverySourceMetadata?.project_type || "Not available"}
                        </Typography>
                      </>
                    ) : null}
                    {selectedDiscovery.source_type === "employment_contract" ? (
                      <>
                        <Typography sx={{ color: "#475569", fontSize: 13 }}>
                          Provider Job ID: {selectedDiscovery.external_id || "Not available"}
                        </Typography>
                        <Typography sx={{ color: "#475569", fontSize: 13 }}>
                          Engagement Type: {selectedDiscoverySourceMetadata?.engagement_type || "Not available"}
                        </Typography>
                      </>
                    ) : null}
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
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Opportunity Validity</Typography>
                <Typography sx={{ mt: 0.8, color: "#475569" }}>
                  Validity: {selectedDiscovery.validity_score == null ? "Not scored" : `${selectedDiscovery.validity_score.toFixed(1)} · ${formatDiscoveryValidityBand(selectedDiscovery.validity_band)}`}
                </Typography>
                <Stack direction="row" spacing={0.75} sx={{ mt: 1, flexWrap: "wrap", rowGap: 0.75 }}>
                  <Chip
                    label={formatDiscoveryValidityClass(selectedDiscovery.validity_class)}
                    size="small"
                    sx={{ textTransform: "capitalize", border: "1px solid", ...discoveryValidityBandChip(selectedDiscovery.validity_band) }}
                  />
                  <Chip
                    label={formatDiscoveryActionability(selectedDiscovery.actionability)}
                    size="small"
                    sx={{ textTransform: "capitalize", border: "1px solid", ...actionabilityChip(selectedDiscovery.actionability) }}
                  />
                </Stack>
                <Box sx={{ mt: 1.25 }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13 }}>Why considered an opportunity</Typography>
                  <Stack spacing={0.8} sx={{ mt: 0.8 }}>
                    {(selectedDiscovery.validity_positive_evidence || []).length ? (
                      selectedDiscovery.validity_positive_evidence?.map((reason) => (
                        <Typography key={`validity-positive-${reason}`} sx={{ color: "#166534", fontSize: 13 }}>
                          • {reason}
                        </Typography>
                      ))
                    ) : (
                      <Typography sx={{ color: "#475569", fontSize: 13 }}>No positive validity evidence recorded.</Typography>
                    )}
                  </Stack>
                </Box>
                <Box sx={{ mt: 1.25 }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13 }}>Risks</Typography>
                  <Stack spacing={0.8} sx={{ mt: 0.8 }}>
                    {(selectedDiscovery.validity_negative_evidence || []).length ? (
                      selectedDiscovery.validity_negative_evidence?.map((reason) => (
                        <Typography key={`validity-negative-${reason}`} sx={{ color: "#B45309", fontSize: 13 }}>
                          • {reason}
                        </Typography>
                      ))
                    ) : (
                      <Typography sx={{ color: "#475569", fontSize: 13 }}>No validity risks recorded.</Typography>
                    )}
                  </Stack>
                </Box>
              </Paper>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
                  <Box>
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Opportunity Intelligence</Typography>
                    <Typography sx={{ mt: 0.5, color: "#475569", fontSize: 13 }}>
                      Stage 2 commercial ranking plus optional Stage 3 deep assessment.
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={!canAdmin || busy}
                      onClick={async () => {
                        try {
                          setBusy(true);
                          setActiveActionLabel("Recalculating priorities");
                          await recalculateAugmisBusinessDiscoveryPriorities(100);
                          await refreshWorkspace();
                          if (selectedDiscovery) {
                            await openDiscoveryDrawer(selectedDiscovery);
                          }
                          showToast("Commercial priorities recalculated.", "success");
                        } catch (error) {
                          showToast(getBackendErrorMessage(error, "Unable to recalculate priorities."), "error");
                        } finally {
                          setBusy(false);
                          setActiveActionLabel(null);
                        }
                      }}
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                    >
                      Recalculate Priorities
                    </Button>
                    <Button
                      size="small"
                      variant="contained"
                      startIcon={<AutorenewRoundedIcon />}
                      disabled={!canQualify || busy}
                      onClick={() => void handleDeepAssessDiscovery(selectedDiscovery)}
                      sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700, bgcolor: "#2563EB" }}
                    >
                      {selectedDiscoveryDeepAssessment ? "Re-run Deep Assess" : "Deep Assess"}
                    </Button>
                  </Stack>
                </Stack>
                <Stack direction="row" spacing={0.75} sx={{ mt: 1.2, flexWrap: "wrap", rowGap: 0.75 }}>
                  <Chip
                    label={
                      selectedDiscoveryIntelligence?.commercial_priority_score == null
                        ? "Priority not scored"
                        : `Priority ${selectedDiscoveryIntelligence.commercial_priority_band || "?"} • ${Math.round(selectedDiscoveryIntelligence.commercial_priority_score)}`
                    }
                    size="small"
                    sx={{ textTransform: "uppercase", border: "1px solid", ...discoveryPriorityBandChip(selectedDiscoveryIntelligence?.commercial_priority_band) }}
                  />
                  <Chip
                    label={(selectedDiscoveryIntelligence?.commercial_recommendation || "watch").toUpperCase()}
                    size="small"
                    sx={{ textTransform: "uppercase", border: "1px solid", ...discoveryRecommendationChip(selectedDiscoveryIntelligence?.commercial_recommendation) }}
                  />
                  <Chip
                    label={`Feasibility ${selectedDiscoveryIntelligence?.delivery_complexity || "unknown"}`}
                    size="small"
                    sx={{ textTransform: "capitalize", border: "1px solid", bgcolor: "#F8FAFC", color: "#334155", borderColor: "#E2E8F0" }}
                  />
                </Stack>
                <Box sx={{ mt: 1.2, display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
                  <MetadataMetric label="Commercial Priority" value={selectedDiscoveryIntelligence?.commercial_priority_score == null ? "Not available" : Math.round(selectedDiscoveryIntelligence.commercial_priority_score)} />
                  <MetadataMetric label="Delivery Model" value={selectedDiscoveryIntelligence?.delivery_model || "Not available"} />
                  <MetadataMetric label="Data Quality" value={selectedDiscoveryIntelligence?.data_quality_status || "Not available"} />
                  <MetadataMetric label="Urgency" value={selectedDiscoveryIntelligence?.urgency_status || "Not available"} />
                </Box>
                <Box sx={{ mt: 1.25 }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13 }}>Why this is ranked here</Typography>
                  <Stack spacing={0.75} sx={{ mt: 0.8 }}>
                    {(selectedDiscoveryIntelligence?.commercial_recommendation_reasons_json || []).length ? (
                      selectedDiscoveryIntelligence?.commercial_recommendation_reasons_json.map((reason) => (
                        <Typography key={`rank-reason-${reason}`} sx={{ color: "#166534", fontSize: 13 }}>
                          + {reason}
                        </Typography>
                      ))
                    ) : (
                      <Typography sx={{ color: "#475569", fontSize: 13 }}>No deterministic priority reasons recorded yet.</Typography>
                    )}
                  </Stack>
                </Box>
                <Box sx={{ mt: 1.25 }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13 }}>Risks</Typography>
                  <Stack spacing={0.75} sx={{ mt: 0.8 }}>
                    {(selectedDiscoveryIntelligence?.commercial_risks_json || []).length ? (
                      selectedDiscoveryIntelligence?.commercial_risks_json.map((reason) => (
                        <Typography key={`rank-risk-${reason}`} sx={{ color: "#B45309", fontSize: 13 }}>
                          - {reason}
                        </Typography>
                      ))
                    ) : (
                      <Typography sx={{ color: "#475569", fontSize: 13 }}>No additional deterministic risks recorded.</Typography>
                    )}
                  </Stack>
                </Box>
                <Box sx={{ mt: 1.25 }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13 }}>Relevant experience</Typography>
                  <Stack spacing={0.8} sx={{ mt: 0.8 }}>
                    {(selectedDiscoveryIntelligence?.matched_experience_summary_json || []).length ? (
                      selectedDiscoveryIntelligence?.matched_experience_summary_json.map((match) => (
                        <Paper key={match.experience_item_id} elevation={0} sx={{ p: 1, borderRadius: "8px", border: "1px solid #E2E8F0", bgcolor: "#F8FAFC" }}>
                          <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center" }}>
                            <Typography sx={{ fontWeight: 700, color: "#0F172A", fontSize: 13 }}>{match.name}</Typography>
                            <Chip
                              size="small"
                              label={`${match.relevance_label} • ${Math.round(match.match_score)}`}
                              sx={{ textTransform: "capitalize", border: "1px solid", ...discoveryPriorityBandChip(match.relevance_label === "strong" ? "A" : match.relevance_label === "moderate" ? "B" : "C") }}
                            />
                          </Stack>
                          {(match.reasons || []).length ? (
                            <Typography sx={{ mt: 0.55, color: "#475569", fontSize: 12.5 }}>
                              {match.reasons[0]}
                            </Typography>
                          ) : null}
                        </Paper>
                      ))
                    ) : (
                      <Typography sx={{ color: "#475569", fontSize: 13 }}>No relevant experience items matched yet.</Typography>
                    )}
                  </Stack>
                </Box>
                <Divider sx={{ my: 1.5 }} />
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>AI Deep Assessment</Typography>
                {selectedDiscoveryDeepAssessment ? (
                  <Stack spacing={1} sx={{ mt: 1 }}>
                    <Typography sx={{ color: "#334155" }}>{selectedDiscoveryDeepAssessment.executive_summary || selectedDiscoveryDeepAssessment.analysis_json.executive_summary}</Typography>
                    <Stack direction="row" spacing={0.75} sx={{ flexWrap: "wrap", rowGap: 0.75 }}>
                      <Chip label={(selectedDiscoveryDeepAssessment.recommendation || "watch").toUpperCase()} size="small" sx={{ textTransform: "uppercase", border: "1px solid", ...discoveryRecommendationChip(selectedDiscoveryDeepAssessment.recommendation) }} />
                      <Chip label={`Confidence ${selectedDiscoveryDeepAssessment.recommendation_confidence ?? "?"}`} size="small" sx={{ border: "1px solid", bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" }} />
                      <Chip label={`Effort ${selectedDiscoveryDeepAssessment.analysis_json.estimated_effort.level.replaceAll("_", " ")}`} size="small" sx={{ textTransform: "capitalize", border: "1px solid", bgcolor: "#F8FAFC", color: "#334155", borderColor: "#E2E8F0" }} />
                    </Stack>
                    <Box sx={{ display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" } }}>
                      <MetadataMetric label="Solution Fit" value={selectedDiscoveryDeepAssessment.analysis_json.solution_fit.score} />
                      <MetadataMetric label="Commercial" value={selectedDiscoveryDeepAssessment.analysis_json.commercial_attractiveness.score} />
                      <MetadataMetric label="Feasibility" value={selectedDiscoveryDeepAssessment.analysis_json.delivery_feasibility.score} />
                    </Box>
                    {(selectedDiscoveryDeepAssessment.analysis_json.risks || []).length ? (
                      <Typography sx={{ color: "#475569", fontSize: 13 }}>
                        Risks: {selectedDiscoveryDeepAssessment.analysis_json.risks.join(" | ")}
                      </Typography>
                    ) : null}
                    {(selectedDiscoveryDeepAssessment.analysis_json.unknowns || []).length ? (
                      <Typography sx={{ color: "#475569", fontSize: 13 }}>
                        Unknowns: {selectedDiscoveryDeepAssessment.analysis_json.unknowns.join(" | ")}
                      </Typography>
                    ) : null}
                    <Typography sx={{ color: "#0F172A", fontSize: 13, fontWeight: 700 }}>
                      Suggested next action: {selectedDiscoveryDeepAssessment.analysis_json.suggested_next_action}
                    </Typography>
                    <Typography sx={{ color: "#64748B", fontSize: 12 }}>
                      Version {selectedDiscoveryDeepAssessment.analysis_version} • {selectedDiscoveryDeepAssessment.model} • {formatDate(selectedDiscoveryDeepAssessment.created_at)}
                    </Typography>
                    <Typography sx={{ color: "#64748B", fontSize: 12 }}>
                      Saved analyses: {selectedDiscoveryDeepAssessmentHistory.length}
                    </Typography>
                  </Stack>
                ) : (
                  <Alert severity="info" sx={{ mt: 1.1, borderRadius: "8px" }}>
                    No AI deep assessment saved yet. Use Deep Assess for an operator-initiated structured review.
                  </Alert>
                )}
              </Paper>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                  {selectedDiscovery.source_type === "public_procurement"
                    ? "Procurement Details"
                    : selectedDiscovery.source_type === "marketplace_project"
                      ? "Marketplace Summary"
                      : selectedDiscovery.source_type === "employment_contract"
                        ? "Employment / Contract Summary"
                        : "Search Evidence"}
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
                  {selectedDiscovery.source_type === "public_procurement" ? "Structured Summary" : selectedDiscovery.source_type === "employment_contract" ? "Provider Summary" : "Search Snippet"}
                </Typography>
                <Typography sx={{ mt: 0.5, color: "#334155", whiteSpace: "pre-wrap" }}>
                  {discoveryTranslationView === "english" && selectedDiscovery.active_translation
                    ? translatedDiscoverySummary(selectedDiscovery) || "Not available"
                    : selectedDiscovery.source_type === "public_procurement"
                      ? selectedDiscoverySourceMetadata?.ted_summary || selectedDiscoveryNormalizedContent.summary.plain_text || selectedDiscovery.raw_summary || "Not available"
                      : selectedDiscovery.source_type === "marketplace_project"
                        ? selectedDiscoveryNormalizedContent.summary.plain_text || selectedDiscovery.raw_summary || "Not available"
                        : selectedDiscoveryNormalizedContent.summary.plain_text || selectedDiscoveryRawContent?.search_result_snippet || selectedDiscovery.raw_summary || "Not available"}
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
                {selectedDiscovery.source_type === "marketplace_project" ? (
                  <>
                    <Box
                      sx={{
                        mt: 1.2,
                        display: "grid",
                        gap: 1,
                        gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                      }}
                    >
                      <MetadataMetric
                        label="Budget"
                        value={
                          selectedDiscovery.budget_min == null && selectedDiscovery.budget_max == null
                            ? "Not available"
                            : `${selectedDiscovery.budget_min ?? "?"}${selectedDiscovery.budget_max != null ? ` - ${selectedDiscovery.budget_max}` : ""}${selectedDiscovery.currency ? ` ${selectedDiscovery.currency}` : ""}`
                        }
                      />
                      <MetadataMetric label="Bid Count" value={selectedDiscoverySourceMetadata?.bid_count != null ? String(selectedDiscoverySourceMetadata.bid_count) : "Not available"} />
                      <MetadataMetric label="Project Status" value={selectedDiscoverySourceMetadata?.project_status || "Not available"} />
                      <MetadataMetric label="Client Country" value={selectedDiscoverySourceMetadata?.client_country || "Not available"} />
                      <MetadataMetric label="Client Location" value={selectedDiscoverySourceMetadata?.client_location || "Not available"} />
                      <MetadataMetric label="Client Rating" value={selectedDiscoverySourceMetadata?.client_rating != null ? String(selectedDiscoverySourceMetadata.client_rating) : "Not available"} />
                      <MetadataMetric label="Client Reviews" value={selectedDiscoverySourceMetadata?.client_review_count != null ? String(selectedDiscoverySourceMetadata.client_review_count) : "Not available"} />
                      <MetadataMetric label="Payment Verified" value={selectedDiscoverySourceMetadata?.client_payment_verified == null ? "Not available" : selectedDiscoverySourceMetadata.client_payment_verified ? "Yes" : "No"} />
                      <MetadataMetric label="Projects Posted" value={selectedDiscoverySourceMetadata?.client_projects_posted != null ? String(selectedDiscoverySourceMetadata.client_projects_posted) : "Not available"} />
                      <MetadataMetric label="Projects Completed" value={selectedDiscoverySourceMetadata?.client_projects_completed != null ? String(selectedDiscoverySourceMetadata.client_projects_completed) : "Not available"} />
                    </Box>
                    {selectedDiscoverySourceMetadata?.skills?.length ? (
                      <>
                        <Typography sx={{ mt: 1.1, color: "#475569" }}>Skills</Typography>
                        <Stack direction="row" spacing={0.75} sx={{ mt: 0.8, flexWrap: "wrap", rowGap: 0.75 }}>
                          {selectedDiscoverySourceMetadata.skills.map((skill) => (
                            <Chip key={`${selectedDiscovery.id}-${skill}`} label={skill} size="small" sx={{ borderRadius: "8px", bgcolor: "#F8FAFC" }} />
                          ))}
                        </Stack>
                      </>
                    ) : null}
                  </>
                ) : null}
                {selectedDiscovery.source_type === "employment_contract" ? (
                  <>
                    <Box
                      sx={{
                        mt: 1.2,
                        display: "grid",
                        gap: 1,
                        gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                      }}
                    >
                      <MetadataMetric label="Employer" value={selectedDiscovery.organization_name || selectedDiscoverySourceMetadata?.company_name || "Not available"} />
                      <MetadataMetric label="Location" value={selectedDiscoverySourceMetadata?.location || selectedDiscovery.region || "Not available"} />
                      <MetadataMetric label="Remote" value={selectedDiscoverySourceMetadata?.remote == null ? "Not available" : selectedDiscoverySourceMetadata.remote ? "Yes" : "No"} />
                      <MetadataMetric label="Employment Type" value={selectedDiscoverySourceMetadata?.employment_type || "Not available"} />
                      <MetadataMetric label="Engagement Type" value={selectedDiscoverySourceMetadata?.engagement_type || "Not available"} />
                      <MetadataMetric
                        label="Compensation"
                        value={
                          selectedDiscovery.budget_min == null && selectedDiscovery.budget_max == null
                            ? "Not available"
                            : `${selectedDiscovery.budget_min ?? "?"}${selectedDiscovery.budget_max != null ? ` - ${selectedDiscovery.budget_max}` : ""}${selectedDiscovery.currency ? ` ${selectedDiscovery.currency}` : ""}${selectedDiscoverySourceMetadata?.salary_period ? ` / ${selectedDiscoverySourceMetadata.salary_period}` : ""}`
                        }
                      />
                      <MetadataMetric label="Category" value={selectedDiscoverySourceMetadata?.category || "Not available"} />
                      <MetadataMetric label="Posted" value={formatDate(selectedDiscovery.published_date)} />
                    </Box>
                    {(selectedDiscoverySourceMetadata?.skills?.length || selectedDiscoverySourceMetadata?.tags?.length) ? (
                      <>
                        <Typography sx={{ mt: 1.1, color: "#475569" }}>Skills / Tags</Typography>
                        <Stack direction="row" spacing={0.75} sx={{ mt: 0.8, flexWrap: "wrap", rowGap: 0.75 }}>
                          {[...(selectedDiscoverySourceMetadata?.skills || []), ...(selectedDiscoverySourceMetadata?.tags || [])].map((item) => (
                            <Chip key={`${selectedDiscovery.id}-${item}`} label={item} size="small" sx={{ borderRadius: "8px", bgcolor: "#F8FAFC" }} />
                          ))}
                        </Stack>
                      </>
                    ) : null}
                  </>
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
                <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
                  <Box>
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                      {selectedRequirementContent.title}
                    </Typography>
                    <Typography sx={{ mt: 0.5, color: "#475569", fontSize: 13 }}>
                      {selectedRequirementContent.subtitle}
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
                    {!selectedDiscovery.source_language_is_english ? (
                      <>
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
                              Regenerate
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
                            {translatingDiscoveryId === selectedDiscovery.id ? "Translating..." : "English"}
                          </Button>
                        )}
                      </>
                    ) : null}
                    {selectedDiscovery.source_url ? (
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<OpenInNewRoundedIcon />}
                        component="a"
                        href={selectedDiscovery.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
                      >
                        Open Source
                      </Button>
                    ) : null}
                  </Stack>
                </Stack>
                {selectedDiscovery.source_language_is_english ? (
                  <Alert severity="info" sx={{ mt: 1.1, borderRadius: "8px" }}>
                    Original language: English. No translation required.
                  </Alert>
                ) : null}
                {translatingDiscoveryId === selectedDiscovery.id ? (
                  <Stack direction="row" spacing={1} sx={{ mt: 1.1, alignItems: "center" }}>
                    <CircularProgress size={18} />
                    <Typography sx={{ color: "#475569", fontSize: 13 }}>
                      Generating English translation...
                    </Typography>
                  </Stack>
                ) : null}
                <Paper
                  elevation={0}
                  sx={{
                    mt: 1.2,
                    p: 1.5,
                    borderRadius: "10px",
                    border: "1px solid #E2E8F0",
                    bgcolor: "#FCFDFE",
                  }}
                >
                  <Box
                    sx={{
                      maxHeight: showFullRequirement ? "none" : 360,
                      overflow: "hidden",
                      "& p, & ul, & ol": { my: 0.9, color: "#334155", lineHeight: 1.75 },
                      "& li": { mb: 0.55, color: "#334155" },
                      "& h1, & h2, & h3, & h4": { mt: 1.3, mb: 0.8, color: "#0F172A" },
                      "& a": { color: "#2563EB", textDecoration: "none" },
                      "& blockquote": {
                        m: 0,
                        px: 1.2,
                        py: 0.8,
                        borderLeft: "3px solid #BFDBFE",
                        bgcolor: "#F8FBFF",
                        color: "#334155",
                      },
                    }}
                  >
                    {selectedRequirementContent.mode === "original" && selectedRequirementContent.safeHtml ? (
                      <Box dangerouslySetInnerHTML={{ __html: selectedRequirementContent.safeHtml }} />
                    ) : (
                      <Typography sx={{ color: "#334155", whiteSpace: "pre-wrap", lineHeight: 1.8 }}>
                        {selectedRequirementContent.text}
                      </Typography>
                    )}
                  </Box>
                  {(selectedRequirementContent.text || "").length > 900 ? (
                    <Button
                      size="small"
                      onClick={() => setShowFullRequirement((current) => !current)}
                      sx={{ mt: 1, px: 0, textTransform: "none", fontWeight: 700 }}
                    >
                      {showFullRequirement ? "Show less" : "Show more"}
                    </Button>
                  ) : null}
                </Paper>
              </Paper>

              {selectedDiscovery.source_type !== "public_procurement" && selectedDiscovery.source_type !== "marketplace_project" && selectedDiscovery.source_type !== "employment_contract" ? (
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Source Content Excerpt</Typography>
                  {selectedDiscoverySourceMetadata?.partial_source_retrieval ? (
                    <Alert severity="info" sx={{ mt: 1.1, borderRadius: "8px" }}>
                      Partial Source Retrieval
                    </Alert>
                  ) : null}
                  <Typography sx={{ mt: 0.5, color: "#334155", whiteSpace: "pre-wrap" }}>
                    {selectedDiscoveryNormalizedContent.full_text.plain_text ||
                      selectedDiscoveryRawContent?.fetched_source_text ||
                      "Not available"}
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
        open={manualScanDialogOpen}
        onClose={() => {
          setManualScanDialogOpen(false);
          setManualScanConnector(null);
        }}
        title="Start Manual Scan"
        maxWidth={420}
        actions={
          <>
            <Button
              onClick={() => {
                setManualScanDialogOpen(false);
                setManualScanConnector(null);
              }}
              sx={{ textTransform: "none" }}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={() => void handleStartManualIndependentScan()}
              disabled={!manualScanConnector || busy}
              sx={{ textTransform: "none" }}
            >
              Start Scan
            </Button>
          </>
        }
      >
        <Stack spacing={1.2}>
          <TextField
            select
            size="small"
            label="Crawl Engine"
            value={manualScanEngine}
            onChange={(event) => setManualScanEngine(event.target.value as "augmis_native" | "scrapy")}
          >
            <MenuItem value="augmis_native">AUGMIS Native</MenuItem>
            <MenuItem value="scrapy">Scrapy</MenuItem>
          </TextField>
          <TextField size="small" label="Scope" value="Existing/current behavior" disabled />
        </Stack>
      </AdminFormDialog>

      <AdminFormDialog
        open={seedDialogOpen}
        onClose={() => {
          setSeedDialogOpen(false);
          setEditingSeed(null);
          setSeedForm(buildWebSeedForm());
        }}
        title={editingSeed ? "Edit Seed" : "Add Seed"}
        actions={
          <>
            <Button
              onClick={() => {
                setSeedDialogOpen(false);
                setEditingSeed(null);
                setSeedForm(buildWebSeedForm());
              }}
              sx={{ textTransform: "none" }}
            >
              Cancel
            </Button>
            <Button
              onClick={() => void handleSaveWebSeed()}
              variant="contained"
              disabled={busy || !seedForm.name.trim() || !seedForm.seed_url.trim()}
              sx={{ textTransform: "none", bgcolor: "#2563EB" }}
            >
              {editingSeed ? "Save Seed" : "Add Seed"}
            </Button>
          </>
        }
        maxWidth={680}
        stackSx={{ maxWidth: "100%" }}
      >
        <Box
          sx={{
            display: "grid",
            gap: 1.2,
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
          }}
        >
          <AdminFormTextField
            label="Name"
            value={seedForm.name}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSeedForm((current) => ({ ...current, name: event.target.value }))
            }
          />
          <TextField
            select
            size="small"
            label="Seed Type"
            value={seedForm.seed_type}
            onChange={(event) => setSeedForm((current) => ({ ...current, seed_type: event.target.value }))}
          >
            <MenuItem value="url">URL</MenuItem>
            <MenuItem value="domain">Domain</MenuItem>
            <MenuItem value="sitemap">Sitemap</MenuItem>
            <MenuItem value="procurement_portal">Procurement Portal</MenuItem>
            <MenuItem value="career_portal">Career Portal</MenuItem>
            <MenuItem value="government_portal">Government Portal</MenuItem>
            <MenuItem value="public_organization">Public Organization</MenuItem>
            <MenuItem value="target_account">Target Account</MenuItem>
          </TextField>
          <AdminFormTextField
            label="Seed URL"
            value={seedForm.seed_url}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSeedForm((current) => ({ ...current, seed_url: event.target.value }))
            }
            sx={{ gridColumn: { xs: "1 / -1", md: "1 / -1" } }}
          />
          <TextField
            select
            size="small"
            label="Crawl Scope"
            value={seedForm.crawl_scope}
            onChange={(event) => setSeedForm((current) => ({ ...current, crawl_scope: event.target.value }))}
          >
            <MenuItem value="same_domain">Same Domain</MenuItem>
            <MenuItem value="approved_domains">Approved Domains</MenuItem>
            <MenuItem value="cross_domain_trusted">Trusted Cross-Domain</MenuItem>
          </TextField>
          <TextField
            select
            size="small"
            label="Frequency"
            value={seedForm.crawl_frequency}
            onChange={(event) => setSeedForm((current) => ({ ...current, crawl_frequency: event.target.value }))}
          >
            <MenuItem value="daily">Daily</MenuItem>
            <MenuItem value="weekly">Weekly</MenuItem>
            <MenuItem value="monthly">Monthly</MenuItem>
            <MenuItem value="manual">Manual</MenuItem>
          </TextField>
          <AdminFormTextField
            label="Maximum Depth"
            value={seedForm.max_depth}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSeedForm((current) => ({ ...current, max_depth: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Maximum Pages"
            value={seedForm.max_pages}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSeedForm((current) => ({ ...current, max_pages: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Priority"
            value={seedForm.priority}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSeedForm((current) => ({ ...current, priority: event.target.value }))
            }
          />
          <TextField
            select
            size="small"
            label="Enabled"
            value={seedForm.enabled ? "yes" : "no"}
            onChange={(event) => setSeedForm((current) => ({ ...current, enabled: event.target.value === "yes" }))}
          >
            <MenuItem value="yes">Yes</MenuItem>
            <MenuItem value="no">No</MenuItem>
          </TextField>
          <AdminFormTextField
            label="Country"
            value={seedForm.country}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSeedForm((current) => ({ ...current, country: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Industry"
            value={seedForm.industry}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSeedForm((current) => ({ ...current, industry: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Organisation"
            value={seedForm.organization_name}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSeedForm((current) => ({ ...current, organization_name: event.target.value }))
            }
          />
          <AdminFormTextField
            label="Notes"
            value={seedForm.notes}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setSeedForm((current) => ({ ...current, notes: event.target.value }))
            }
            sx={{ gridColumn: { xs: "1 / -1", md: "1 / -1" } }}
          />
        </Box>
      </AdminFormDialog>

      <AdminFormDialog
        open={credentialDialogOpen}
        onClose={() => {
          setCredentialDialogOpen(false);
          resetCredentialForm();
        }}
        title={
          credentialDialogMode === "replace"
            ? `Replace ${providerSecretLabel(selectedProvider)}`
            : `Configure ${providerSecretLabel(selectedProvider)}`
        }
        actions={
          <>
            <Button
              onClick={() => {
                setCredentialDialogOpen(false);
                resetCredentialForm();
              }}
              sx={{ textTransform: "none" }}
            >
              Cancel
            </Button>
            <Button
              onClick={() => void handleSaveCredential()}
              variant="contained"
              disabled={busy || (selectedProvider === "adzuna" ? !(credentialForm.appId.trim() && credentialForm.appKey.trim()) : !credentialForm.apiKey.trim())}
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
          {selectedProvider === "adzuna" ? (
            <>
              <TextField
                size="small"
                label="App ID"
                value={credentialForm.appId}
                onChange={(event) => setCredentialForm((current) => ({ ...current, appId: event.target.value }))}
                autoComplete="off"
              />
              <TextField
                size="small"
                label="App Key"
                type={credentialShowValue ? "text" : "password"}
                value={credentialForm.appKey}
                onChange={(event) => setCredentialForm((current) => ({ ...current, appKey: event.target.value }))}
                autoComplete="off"
                slotProps={{
                  input: {
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton edge="end" onClick={() => setCredentialShowValue((current) => !current)}>
                          {credentialShowValue ? <VisibilityOffOutlinedIcon /> : <VisibilityOutlinedIcon />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  },
                }}
              />
            </>
          ) : (
            <TextField
              size="small"
              label={providerSecretLabel(selectedProvider)}
              type={credentialShowValue ? "text" : "password"}
              value={credentialForm.apiKey}
              onChange={(event) => setCredentialForm((current) => ({ ...current, apiKey: event.target.value }))}
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
          )}
          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              onClick={() =>
                void handleTestCredential(selectedProvider, {
                  apiKey: credentialForm.apiKey,
                  appId: credentialForm.appId,
                  appKey: credentialForm.appKey,
                })
              }
              disabled={busy || (selectedProvider === "adzuna" ? !(credentialForm.appId.trim() && credentialForm.appKey.trim()) : !credentialForm.apiKey.trim())}
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

export default function AugmisBusinessConnectorsPage() {
  return <AugmisBusinessDiscoveryWorkspace />;
}
