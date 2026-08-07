"use client";

import { type ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";

import AutorenewRoundedIcon from "@mui/icons-material/AutorenewRounded";
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
  createAugmisBusinessSearchProfile,
  deleteAugmisBusinessConnectorCredential,
  getAugmisBusinessConnectorCredential,
  getAugmisBusinessDiscovery,
  importAugmisBusinessDiscovery,
  listAugmisBusinessConnectorRuns,
  listAugmisBusinessConnectors,
  listAugmisBusinessDiscoveries,
  listAugmisBusinessSearchProfiles,
  rejectAugmisBusinessDiscovery,
  scanAugmisBusinessConnector,
  saveAugmisBusinessConnectorCredential,
  shortlistAugmisBusinessDiscovery,
  testAugmisBusinessConnectorCredential,
  testAugmisBusinessConnector,
  updateAugmisBusinessConnector,
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

type DiscoverySourceMetadata = {
  provider?: string;
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
};

type ConnectorRunMetadata = {
  provider?: string;
  queries_executed?: string[];
  query_count?: number;
  api_call_count?: number;
  api_result_count?: number;
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
};

const CONNECTOR_TEST_LABEL = "TEST / FIXTURE";
const CONNECTOR_PRODUCTION_LABEL = "PRODUCTION";

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

function connectorCategoryLabel(connector: AugmisBusinessConnector) {
  if (connector.metadata?.is_test_connector) {
    return CONNECTOR_TEST_LABEL;
  }
  return CONNECTOR_PRODUCTION_LABEL;
}

function connectorPrimaryIcon(connector: AugmisBusinessConnector) {
  if (connector.source_category === "search") {
    return <SearchRoundedIcon sx={{ color: "#1D4ED8", fontSize: 18 }} />;
  }
  return <CableOutlinedIcon sx={{ color: "#B45309", fontSize: 18 }} />;
}

function selectedConnectorProvider(connector: AugmisBusinessConnector | null) {
  const configuredProvider = connector?.configuration_json?.provider;
  return typeof configuredProvider === "string" && configuredProvider.trim()
    ? configuredProvider.trim().toLowerCase()
    : connector?.metadata?.default_provider || "tavily";
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
  const [discoveries, setDiscoveries] = useState<AugmisBusinessDiscovery[]>([]);
  const [discoveriesTotal, setDiscoveriesTotal] = useState(0);
  const [discoveryPage, setDiscoveryPage] = useState(0);
  const [discoveryPageSize, setDiscoveryPageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sourceCategoryFilter, setSourceCategoryFilter] = useState("all");
  const [selectedConnector, setSelectedConnector] = useState<AugmisBusinessConnector | null>(null);
  const [selectedDiscovery, setSelectedDiscovery] = useState<AugmisBusinessDiscovery | null>(null);
  const [selectedDiscoveryDuplicates, setSelectedDiscoveryDuplicates] = useState<AugmisBusinessDiscovery[]>([]);
  const [connectorDrawerOpen, setConnectorDrawerOpen] = useState(false);
  const [discoveryDrawerOpen, setDiscoveryDrawerOpen] = useState(false);
  const [profileDialogOpen, setProfileDialogOpen] = useState(false);
  const [profileForm, setProfileForm] = useState<SearchProfileForm | null>(null);
  const [credentialStatuses, setCredentialStatuses] = useState<
    Record<string, AugmisBusinessConnectorCredentialStatus>
  >({});
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

  const showToast = (message: string, severity: ToastSeverity) => {
    setToastMessage(message);
    setToastSeverity(severity);
    setToastOpen(true);
  };

  const loadConnectors = useCallback(async () => {
    const [connectorsResult, profilesResult] = await Promise.all([
      listAugmisBusinessConnectors(),
      listAugmisBusinessSearchProfiles(),
    ]);
    setConnectors(connectorsResult.data);
    setSummary(connectorsResult.summary);
    setProfiles(profilesResult.data);
  }, []);

  const loadDiscoveries = useCallback(async () => {
    const result = await listAugmisBusinessDiscoveries({
      page: discoveryPage + 1,
      page_size: discoveryPageSize,
      search: search.trim() || undefined,
      status: statusFilter === "all" ? undefined : statusFilter,
      source_category: sourceCategoryFilter === "all" ? undefined : sourceCategoryFilter,
    });
    setDiscoveries(result.data);
    setDiscoveriesTotal(result.pagination.total);
  }, [discoveryPage, discoveryPageSize, search, sourceCategoryFilter, statusFilter]);

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
  const selectedProvider = selectedConnectorProvider(selectedConnector);

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
    try {
      const result = await getAugmisBusinessDiscovery(discovery.id);
      setSelectedDiscovery(result.data);
      setSelectedDiscoveryDuplicates(result.duplicates || []);
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to load discovery detail."), "error");
    }
  }

  async function refreshWorkspace() {
    await Promise.all([loadConnectors(), loadDiscoveries()]);
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
      await updateAugmisBusinessConnector(selectedConnector.id, {
        configuration_json: {
          ...selectedConnector.configuration_json,
          provider,
        },
      });
      await loadConnectors();
      const refreshedConnector =
        connectorById.get(selectedConnector.id) ??
        ({
          ...selectedConnector,
          configuration_json: {
            ...selectedConnector.configuration_json,
            provider,
          },
        } as AugmisBusinessConnector);
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
      await updateAugmisBusinessConnector(selectedConnector.id, {
        configuration_json: selectedConnector.configuration_json,
      });
      await loadConnectors();
      await openConnectorDrawer(selectedConnector);
      showToast("Runtime settings saved.", "success");
    } catch (error) {
      showToast(getBackendErrorMessage(error, "Unable to save runtime settings."), "error");
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
    if (!selectedConnector) return;
    const provider = selectedConnectorProvider(selectedConnector);
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
    if (!selectedConnector) return;
    const provider = selectedConnectorProvider(selectedConnector);
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
                    Web Opportunity Search is the live production listener. The fixture connector remains available for regression-safe testing.
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
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Connector</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Category</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Schedule</TableCell>
                      <TableCell>Last Scan</TableCell>
                      <TableCell>Last Success</TableCell>
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
                        <TableCell sx={{ textTransform: "capitalize" }}>
                          {connector.source_category === "search" ? "Web Search" : connector.source_category}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={connector.status}
                            size="small"
                            sx={{ textTransform: "capitalize", border: "1px solid", ...connectorStatusChip(connector.status) }}
                          />
                        </TableCell>
                        <TableCell>
                          {connector.schedule_enabled ? connector.schedule_expression || "Enabled" : "Disabled"}
                        </TableCell>
                        <TableCell>{formatDate(connector.last_scan_at)}</TableCell>
                        <TableCell>{formatDate(connector.last_success_at)}</TableCell>
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
                <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ minWidth: { md: 720 } }}>
                  <TextField
                    size="small"
                    value={search}
                    onChange={(event) => {
                      setSearch(event.target.value);
                      setDiscoveryPage(0);
                    }}
                    placeholder="Search title, organisation, summary"
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
                  >
                    <MenuItem value="all">All sources</MenuItem>
                    <MenuItem value="search">Web Search</MenuItem>
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
                </Stack>
              </Stack>
            </Box>
            <Box sx={{ p: 2 }}>
              {discoveries.length ? (
                <>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Discovered</TableCell>
                        <TableCell>Opportunity</TableCell>
                        <TableCell>Organisation</TableCell>
                        <TableCell>Source</TableCell>
                        <TableCell>Country</TableCell>
                        <TableCell>Closing</TableCell>
                        <TableCell>Preliminary Match</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell align="right">Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {discoveries.map((discovery) => (
                        <TableRow key={discovery.id} hover>
                          <TableCell>{formatDate(discovery.discovered_at)}</TableCell>
                          <TableCell>
                            <Button
                              variant="text"
                              onClick={() => void openDiscoveryDrawer(discovery)}
                              sx={{ px: 0, textTransform: "none", fontWeight: 700 }}
                            >
                              {discovery.title}
                            </Button>
                          </TableCell>
                          <TableCell>{discovery.organization_name || "Not available"}</TableCell>
                          <TableCell>{discovery.source_name}</TableCell>
                          <TableCell>{discovery.country || "Not available"}</TableCell>
                          <TableCell>{formatDate(discovery.closing_date)}</TableCell>
                          <TableCell>
                            <Chip
                              label={
                                discovery.preliminary_relevance_score == null
                                  ? "Not scored"
                                  : `Preliminary ${discovery.preliminary_relevance_score.toFixed(1)}`
                              }
                              size="small"
                              sx={{ bgcolor: "#EFF6FF", color: "#1D4ED8" }}
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={discovery.discovery_status}
                              size="small"
                              sx={{ textTransform: "capitalize", border: "1px solid", ...discoveryStatusChip(discovery.discovery_status) }}
                            />
                          </TableCell>
                          <TableCell align="right">
                            <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end" }}>
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
                    Run Web Opportunity Search for live discovery or use the fixture connector for safe regression testing.
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
                  Category: {selectedConnector.source_category === "search" ? "Web Search" : selectedConnector.source_category}
                </Typography>
                <Typography sx={{ color: "#0F172A" }}>
                  Last success: {formatDate(selectedConnector.last_success_at)}
                </Typography>
                <Typography sx={{ color: "#0F172A" }}>
                  Last error: {selectedConnector.last_error_message || "None"}
                </Typography>
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
                    <MenuItem value="tavily">Tavily</MenuItem>
                    <MenuItem value="brave">Brave</MenuItem>
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
                    <MetadataMetric label="API Results" value={selectedRunMetadata.api_result_count ?? 0} />
                    <MetadataMetric label="Sources" value={selectedRunMetadata.same_scan_unique_sources ?? 0} />
                    <MetadataMetric label="Attempted Fetches" value={selectedRunMetadata.source_pages_attempted ?? 0} />
                    <MetadataMetric label="Fetched" value={selectedRunMetadata.source_pages_fetched ?? 0} />
                    <MetadataMetric label="Skipped by Limit" value={selectedRunMetadata.source_pages_skipped_due_limit ?? 0} />
                    <MetadataMetric label="Fetch Failures" value={selectedRunMetadata.fetch_failures ?? 0} />
                    <MetadataMetric label="Accepted" value={selectedRunMetadata.accepted_candidates ?? 0} />
                    <MetadataMetric label="Filtered" value={selectedRunMetadata.filtered_candidates ?? 0} />
                    <MetadataMetric label="Duplicates" value={selectedConnectorRun?.items_duplicate ?? 0} />
                  </Box>
                  <Typography sx={{ mt: 1.1, color: "#64748B", fontSize: 12 }}>
                    Effective limits: {selectedRunMetadata.maximum_queries_per_scan ?? 0} queries, {selectedRunMetadata.results_per_query ?? 0} results/query, {selectedRunMetadata.max_source_fetches_per_scan ?? 0} source fetches, {formatBytes(selectedRunMetadata.max_fetch_bytes)}
                  </Typography>
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
                          {metadata.query_count != null || metadata.api_result_count != null ? (
                          <Typography sx={{ mt: 0.6, color: "#64748B", fontSize: 12 }}>
                              Provider {metadata.provider || "n/a"} · Queries {metadata.query_count ?? 0} · API results {metadata.api_result_count ?? 0} · Attempted {metadata.source_pages_attempted ?? 0} · Fetched {metadata.source_pages_fetched ?? 0} · Skipped {metadata.source_pages_skipped_due_limit ?? 0}
                            </Typography>
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
                    {selectedDiscovery.title}
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
                <Typography sx={{ color: "#475569" }}>Source: {selectedDiscovery.source_name}</Typography>
                <Typography sx={{ color: "#475569" }}>
                  Provider: {selectedDiscoverySourceMetadata?.provider || "Not available"}
                </Typography>
                <Typography sx={{ color: "#475569" }}>
                  Retrieved: {formatDate(selectedDiscovery.retrieval_timestamp)}
                </Typography>
                <Typography sx={{ color: "#475569" }}>
                  Source trust: {selectedDiscoverySourceMetadata?.source_trust || "Not available"}
                </Typography>
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
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Preliminary Match</Typography>
                <Typography sx={{ mt: 0.8, color: "#475569" }}>
                  Preliminary Match: {selectedDiscovery.preliminary_relevance_score == null ? "Not scored" : selectedDiscovery.preliminary_relevance_score.toFixed(1)}
                </Typography>
                <Alert severity="info" sx={{ mt: 1.2, borderRadius: "8px" }}>
                  Preliminary Match is deterministic listener filtering. It is not the Phase 4 AI Fit score.
                </Alert>
                <Stack spacing={0.8} sx={{ mt: 1.25 }}>
                  {(selectedDiscovery.relevance_reasons_json || []).length ? (
                    selectedDiscovery.relevance_reasons_json.map((reason) => (
                      <Typography key={reason} sx={{ color: "#334155", fontSize: 13 }}>
                        • {reason}
                      </Typography>
                    ))
                  ) : (
                    <Typography sx={{ color: "#475569" }}>No relevance reasons recorded.</Typography>
                  )}
                </Stack>
              </Paper>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Search Evidence</Typography>
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
                  Search Snippet
                </Typography>
                <Typography sx={{ mt: 0.5, color: "#334155", whiteSpace: "pre-wrap" }}>
                  {selectedDiscoveryRawContent?.search_result_snippet || selectedDiscovery.raw_summary || "Not available"}
                </Typography>
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
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Requirement</Typography>
                <Typography sx={{ mt: 0.8, color: "#475569" }}>
                  {selectedDiscovery.requirement_summary || "Not available"}
                </Typography>
              </Paper>

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
