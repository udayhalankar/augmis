"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  Grid,
  IconButton,
  InputLabel,
  Menu,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import DeleteOutlineOutlinedIcon from "@mui/icons-material/DeleteOutlineOutlined";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import MoreVertIcon from "@mui/icons-material/MoreVert";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import ConnectorSettingsFields from "@/components/repositories/ConnectorSettingsFields";
import SharePointSetupWizard from "@/components/repositories/SharePointSetupWizard";
import SharedDriveSetupWizard from "@/components/repositories/SharedDriveSetupWizard";
import SyncLogsTable from "@/components/repositories/SyncLogsTable";
import SyncStatusPanel from "@/components/repositories/SyncStatusPanel";
import { sourceTypeLabel } from "@/components/repositories/sourceTypeLabel";
import { getTenantUsers } from "@/services/authService";
import { repositorySyncApi } from "@/services/repositorySyncApi";
import {
  createIntelligencePattern,
  createRepository,
  createWorkArea,
  deleteIntelligencePattern,
  deleteWorkArea,
  deleteRepository,
  disconnectRepository,
  getIntelligencePatterns,
  getRepositories,
  getRepositoryAccess,
  getWorkAreas,
  grantRepositoryAccess,
  syncRepository,
  updateIntelligencePattern,
  updateRepositoryConnection,
  updateWorkArea,
} from "@/services/repositoryService";

const sourceTypes = [
  "sharedrive",
  "sharepoint",
  "otcs",
  "onedrive",
  "s3",
  "manual_upload",
];

const workAreaRuleOperators = [
  { value: "==", label: "Equals" },
  { value: "!=", label: "Does not equal" },
  { value: ">", label: "Greater than" },
  { value: ">=", label: "Greater than or equal" },
  { value: "<", label: "Less than" },
  { value: "<=", label: "Less than or equal" },
  { value: "in", label: "Matches any of" },
  { value: "contains", label: "Contains text" },
];

const workAreaRiskSeverities = ["Low", "Medium", "High", "Critical"];

type WorkAreaRuleRow = {
  label: string;
  field: string;
  operator: string;
  value: string;
  severity?: string;
};

function parseLineList(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function serializeLineList(values?: string[]) {
  return Array.isArray(values) ? values.join("\n") : "";
}

function normalizeRuleValue(value: string, operator: string) {
  const trimmed = String(value || "").trim();
  if (operator === "in") {
    return trimmed
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  if (trimmed === "") {
    return "";
  }

  const numeric = Number(trimmed);
  if (!Number.isNaN(numeric) && trimmed === String(numeric)) {
    return numeric;
  }

  if (!Number.isNaN(numeric) && /^[+-]?\d+(\.\d+)?$/.test(trimmed)) {
    return numeric;
  }

  return trimmed;
}

function normalizeDashboardTypeForUi(value?: string) {
  return value || "generic";
}

function createDefaultDefinitionForm() {
  return {
    name: "",
    description: "",
    intelligence_pattern: "",
    dashboard_type: "generic",
    tags_keywords: "",
    summary_focus: "",
    required_specifics: "",
    entities_to_extract: "",
    enabled_checks: "",
    summary_template: "",
    risk_rules: [] as WorkAreaRuleRow[],
    thresholds: [] as Array<Record<string, any>>,
    threshold_rules: [] as WorkAreaRuleRow[],
    fact_extractors: [] as Array<Record<string, any>>,
  };
}

function buildDefinitionPayload(form: ReturnType<typeof createDefaultDefinitionForm>) {
  return {
    name: form.name,
    description: form.description,
    intelligence_pattern: form.intelligence_pattern,
    dashboard_type: form.dashboard_type,
    tags_keywords: parseLineList(form.tags_keywords),
    summary_focus: parseLineList(form.summary_focus),
    required_specifics: parseLineList(form.required_specifics),
    entities_to_extract: parseLineList(form.entities_to_extract),
    enabled_checks: parseLineList(form.enabled_checks),
    summary_template: form.summary_template.trim(),
    risk_rules: parseRuleRows(form.risk_rules, "Risk Rules"),
    thresholds: form.thresholds,
    threshold_rules: parseRuleRows(form.threshold_rules, "Threshold Rules"),
    fact_extractors: form.fact_extractors,
  };
}

function parseRuleRows(rows: WorkAreaRuleRow[], fieldLabel: string) {
  return rows
    .map((row) => ({
      label: row.label.trim(),
      field: row.field.trim(),
      operator: row.operator.trim(),
      value: normalizeRuleValue(row.value, row.operator),
      severity: row.severity?.trim() || undefined,
    }))
    .filter((row) => row.label || row.field || row.value !== "")
    .map((row) => {
      if (!row.field) {
        throw new Error(`${fieldLabel}: every rule needs a field.`);
      }
      if (!row.operator) {
        throw new Error(`${fieldLabel}: every rule needs a condition.`);
      }
      return row;
    });
}

function serializeRuleValue(value: any) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  return value === undefined || value === null ? "" : String(value);
}

function toRuleRows(value: any, includeSeverity = false): WorkAreaRuleRow[] {
  if (!Array.isArray(value) || !value.length) return [];
  return value
    .filter((item) => item && typeof item === "object")
    .map((item) => ({
      label: String(item.label || item.name || ""),
      field: String(item.field || ""),
      operator: String(item.operator || "=="),
      value: serializeRuleValue(item.value),
      severity: includeSeverity ? String(item.severity || "") : undefined,
    }));
}

export default function RepositoryManagementPage() {
  const router = useRouter();
  function getDefaultWorkAreaName(areas: Array<{ name: string }>) {
    if (!areas.length) return "";
    const generalArea = areas.find((area) => area.name === "general");
    return generalArea?.name || areas[0]?.name || "";
  }

  const [repositories, setRepositories] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [workAreas, setWorkAreas] = useState<any[]>([]);
  const [intelligencePatterns, setIntelligencePatterns] = useState<any[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<any | null>(null);
  const [accessRows, setAccessRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const [repoDialogOpen, setRepoDialogOpen] = useState(false);
  const [accessDialogOpen, setAccessDialogOpen] = useState(false);
  const [grantAccessDialogOpen, setGrantAccessDialogOpen] = useState(false);
  const [connectionDialogOpen, setConnectionDialogOpen] = useState(false);
  const [workAreaDialogOpen, setWorkAreaDialogOpen] = useState(false);
  const [workAreaDialogMode, setWorkAreaDialogMode] = useState<"create" | "edit">("create");
  const [editingWorkAreaName, setEditingWorkAreaName] = useState("");
  const [patternDialogOpen, setPatternDialogOpen] = useState(false);
  const [patternDialogMode, setPatternDialogMode] = useState<"create" | "edit">("create");
  const [editingPatternName, setEditingPatternName] = useState("");

  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [connectionRepo, setConnectionRepo] = useState<any | null>(null);
  const [rootPath, setRootPath] = useState("");
  const [sourcePath, setSourcePath] = useState("");
  const [connectionBusinessArea, setConnectionBusinessArea] = useState("");
  const [connectionDialogConfig, setConnectionDialogConfig] = useState<Record<string, string>>({});
  const [syncing, setSyncing] = useState(false);
  const [connectorCapabilities, setConnectorCapabilities] = useState<Record<string, any>>({});
  const [connectionConfig, setConnectionConfig] = useState<Record<string, string>>({});
  const [schedulerSettings, setSchedulerSettings] = useState<any>(null);
  const [schedulerMode, setSchedulerMode] = useState("embedded");
  const [schedulerInterval, setSchedulerInterval] = useState("5");
  const [schedulerTimezone, setSchedulerTimezone] = useState("UTC");
  const [chunkingSettings, setChunkingSettings] = useState<any>(null);
  const [chunkMaxChars, setChunkMaxChars] = useState("1400");
  const [chunkOverlapChars, setChunkOverlapChars] = useState("150");
  const [repoActionId, setRepoActionId] = useState<string | null>(null);
  const [repoActionType, setRepoActionType] = useState<"disconnect" | "remove" | "reindex" | null>(null);
  const [reindexReportOpen, setReindexReportOpen] = useState(false);
  const [reindexReport, setReindexReport] = useState<any | null>(null);
  const [actionsAnchorEl, setActionsAnchorEl] = useState<null | HTMLElement>(null);
  const [actionsRepo, setActionsRepo] = useState<any | null>(null);
  const [repositorySearch, setRepositorySearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [businessAreaFilter, setBusinessAreaFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [repositoryPage, setRepositoryPage] = useState(0);
  const [workAreaSearch, setWorkAreaSearch] = useState("");
  const [workAreaPage, setWorkAreaPage] = useState(0);
  const [patternSearch, setPatternSearch] = useState("");
  const [patternPage, setPatternPage] = useState(0);
  const [workAreaForm, setWorkAreaForm] = useState(createDefaultDefinitionForm);
  const [patternForm, setPatternForm] = useState(createDefaultDefinitionForm);

  const [repoForm, setRepoForm] = useState({
    repository_name: "",
    source_type: "sharepoint",
    business_area: "",
    status: "ACTIVE",
    source_path: "",
  });

  const [accessForm, setAccessForm] = useState({
    repository_id: "",
    user_id: "",
    can_read: true,
    can_ingest: false,
    can_admin: false,
    business_area: "general",
  });

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [repoResult, userResult, workAreaResult, patternResult] = await Promise.all([
        getRepositories(),
        getTenantUsers(),
        getWorkAreas(),
        getIntelligencePatterns(),
      ]);

      if (repoResult.success) {
        setRepositories(repoResult.data);
      }
      if (userResult.success) {
        setUsers(userResult.data);
      }
      if (workAreaResult.success) {
        setWorkAreas(workAreaResult.data);
      }
      if (patternResult.success) {
        setIntelligencePatterns(patternResult.data);
      }
    } catch (err: any) {
      setRepositories([]);
      setUsers([]);
      setWorkAreas([]);
      setIntelligencePatterns([]);
      setError(err?.response?.data?.detail || "Unable to load repositories");
    } finally {
      setLoading(false);
    }
  }

  async function loadSchedulerSettings() {
    try {
      const data = await repositorySyncApi.getSchedulerSettings();
      setSchedulerSettings(data);
      setSchedulerMode(data.mode || "embedded");
      setSchedulerInterval(String(data.interval_minutes ?? 5));
      setSchedulerTimezone(data.timezone || "UTC");
    } catch (err) {
      console.error("Failed to load scheduler settings", err);
    }
  }

  async function loadChunkingSettings() {
    try {
      const data = await repositorySyncApi.getChunkingSettings();
      setChunkingSettings(data);
      setChunkMaxChars(String(data.max_chars ?? 1400));
      setChunkOverlapChars(String(data.overlap_chars ?? 150));
    } catch (err) {
      console.error("Failed to load chunking settings", err);
    }
  }

  async function loadAccess(repo: any) {
    setSelectedRepo(repo);
    setAccessForm({
      repository_id: repo.repository_id,
      user_id: "",
      can_read: true,
      can_ingest: false,
      can_admin: false,
      business_area: repo.business_area,
    });

    try {
      const result = await getRepositoryAccess(repo.repository_id);
      if (result.success) {
        setAccessRows(result.data);
        setAccessDialogOpen(true);
      }
    } catch (err: any) {
      setAccessRows([]);
      setError(err?.response?.data?.detail || "Unable to load repository access");
    }
  }

  async function handleSaveWorkArea() {
    setError("");
    setSuccessMessage("");

    try {
      const selectedPattern = intelligencePatterns.find(
        (pattern) => pattern.name === workAreaForm.intelligence_pattern
      );
      const payload = {
        ...buildDefinitionPayload(workAreaForm),
        dashboard_type: selectedPattern?.dashboard_type || "generic",
      };
      const result =
        workAreaDialogMode === "edit"
          ? await updateWorkArea(editingWorkAreaName, payload)
          : await createWorkArea(payload);
      if (!result.success) {
        setError(`Unable to ${workAreaDialogMode} business area`);
        return;
      }
      setWorkAreaDialogOpen(false);
      setWorkAreaDialogMode("create");
      setEditingWorkAreaName("");
      setWorkAreaForm(createDefaultDefinitionForm());
      await loadData();
      setSuccessMessage(
        workAreaDialogMode === "edit"
          ? `Work area ${result.data.name} updated successfully.`
          : `Work area ${result.data.name} created successfully.`
      );
    } catch (err: any) {
      setError(
        err?.response?.data?.detail || `Unable to ${workAreaDialogMode} business area`
      );
    }
  }

  function openCreateWorkAreaDialog() {
    setWorkAreaDialogMode("create");
    setEditingWorkAreaName("");
    setWorkAreaForm({
      ...createDefaultDefinitionForm(),
      intelligence_pattern: intelligencePatterns[0]?.name || "",
    });
    setWorkAreaDialogOpen(true);
  }

  function openEditWorkAreaDialog(area: any) {
    setWorkAreaDialogMode("edit");
    setEditingWorkAreaName(area.name);
    setWorkAreaForm({
      ...createDefaultDefinitionForm(),
      name: area.name,
      description: area.description || "",
      intelligence_pattern: area.intelligence_pattern || intelligencePatterns[0]?.name || "",
      dashboard_type: normalizeDashboardTypeForUi(area.dashboard_type),
      tags_keywords: serializeLineList(area.tags_keywords),
      summary_focus: serializeLineList(area.summary_focus),
      required_specifics: serializeLineList(area.required_specifics),
      entities_to_extract: serializeLineList(area.entities_to_extract),
      enabled_checks: serializeLineList(area.enabled_checks),
      summary_template: area.summary_template || "",
      risk_rules: toRuleRows(area.risk_rules, true),
      thresholds: Array.isArray(area.thresholds) ? area.thresholds : [],
      threshold_rules: toRuleRows(area.threshold_rules, false),
      fact_extractors: Array.isArray(area.fact_extractors) ? area.fact_extractors : [],
    });
    setWorkAreaDialogOpen(true);
  }

  async function handleSavePattern() {
    setError("");
    setSuccessMessage("");

    try {
      const payload = buildDefinitionPayload(patternForm);
      const result =
        patternDialogMode === "edit"
          ? await updateIntelligencePattern(editingPatternName, payload)
          : await createIntelligencePattern(payload);

      if (!result.success) {
        setError(`Unable to ${patternDialogMode} intelligence pattern`);
        return;
      }

      setPatternDialogOpen(false);
      setPatternDialogMode("create");
      setEditingPatternName("");
      setPatternForm(createDefaultDefinitionForm());
      await loadData();
      setSuccessMessage(
        patternDialogMode === "edit"
          ? `Intelligence pattern ${result.data.name} updated successfully.`
          : `Intelligence pattern ${result.data.name} created successfully.`
      );
    } catch (err: any) {
      setError(
        err?.response?.data?.detail || `Unable to ${patternDialogMode} intelligence pattern`
      );
    }
  }

  function openCreatePatternDialog() {
    setPatternDialogMode("create");
    setEditingPatternName("");
    setPatternForm(createDefaultDefinitionForm());
    setPatternDialogOpen(true);
  }

  function openEditPatternDialog(pattern: any) {
    setPatternDialogMode("edit");
    setEditingPatternName(pattern.name);
    setPatternForm({
      ...createDefaultDefinitionForm(),
      name: pattern.name,
      description: pattern.description || "",
      dashboard_type: normalizeDashboardTypeForUi(pattern.dashboard_type),
      tags_keywords: serializeLineList(pattern.tags_keywords),
      summary_focus: serializeLineList(pattern.summary_focus),
      required_specifics: serializeLineList(pattern.required_specifics),
      entities_to_extract: serializeLineList(pattern.entities_to_extract),
      enabled_checks: serializeLineList(pattern.enabled_checks),
      summary_template: pattern.summary_template || "",
      risk_rules: toRuleRows(pattern.risk_rules, true),
      thresholds: Array.isArray(pattern.thresholds) ? pattern.thresholds : [],
      threshold_rules: toRuleRows(pattern.threshold_rules, false),
      fact_extractors: Array.isArray(pattern.fact_extractors) ? pattern.fact_extractors : [],
    });
    setPatternDialogOpen(true);
  }

  async function handleDeletePattern(pattern: { name: string }) {
    if (!window.confirm(`Delete intelligence pattern ${pattern.name}?`)) return;

    setError("");
    setSuccessMessage("");
    try {
      const result = await deleteIntelligencePattern(pattern.name);
      await loadData();
      setSuccessMessage(`Intelligence pattern ${result.data.name} deleted successfully.`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to delete intelligence pattern");
    }
  }

  function addThresholdRuleRow() {
    setWorkAreaForm((current) => ({
      ...current,
      threshold_rules: [
        ...current.threshold_rules,
        { label: "", field: "", operator: ">=", value: "" },
      ],
    }));
  }

  function addPatternThresholdRuleRow() {
    setPatternForm((current) => ({
      ...current,
      threshold_rules: [
        ...current.threshold_rules,
        { label: "", field: "", operator: ">=", value: "" },
      ],
    }));
  }

  function updateThresholdRuleRow(index: number, patch: Partial<WorkAreaRuleRow>) {
    setWorkAreaForm((current) => ({
      ...current,
      threshold_rules: current.threshold_rules.map((rule, ruleIndex) =>
        ruleIndex === index ? { ...rule, ...patch } : rule
      ),
    }));
  }

  function updatePatternThresholdRuleRow(index: number, patch: Partial<WorkAreaRuleRow>) {
    setPatternForm((current) => ({
      ...current,
      threshold_rules: current.threshold_rules.map((rule, ruleIndex) =>
        ruleIndex === index ? { ...rule, ...patch } : rule
      ),
    }));
  }

  function removeThresholdRuleRow(index: number) {
    setWorkAreaForm((current) => ({
      ...current,
      threshold_rules: current.threshold_rules.filter((_, ruleIndex) => ruleIndex !== index),
    }));
  }

  function removePatternThresholdRuleRow(index: number) {
    setPatternForm((current) => ({
      ...current,
      threshold_rules: current.threshold_rules.filter((_, ruleIndex) => ruleIndex !== index),
    }));
  }

  function addRiskRuleRow() {
    setWorkAreaForm((current) => ({
      ...current,
      risk_rules: [
        ...current.risk_rules,
        { label: "", field: "", operator: "==", value: "", severity: "High" },
      ],
    }));
  }

  function addPatternRiskRuleRow() {
    setPatternForm((current) => ({
      ...current,
      risk_rules: [
        ...current.risk_rules,
        { label: "", field: "", operator: "==", value: "", severity: "High" },
      ],
    }));
  }

  function updateRiskRuleRow(index: number, patch: Partial<WorkAreaRuleRow>) {
    setWorkAreaForm((current) => ({
      ...current,
      risk_rules: current.risk_rules.map((rule, ruleIndex) =>
        ruleIndex === index ? { ...rule, ...patch } : rule
      ),
    }));
  }

  function updatePatternRiskRuleRow(index: number, patch: Partial<WorkAreaRuleRow>) {
    setPatternForm((current) => ({
      ...current,
      risk_rules: current.risk_rules.map((rule, ruleIndex) =>
        ruleIndex === index ? { ...rule, ...patch } : rule
      ),
    }));
  }

  function removeRiskRuleRow(index: number) {
    setWorkAreaForm((current) => ({
      ...current,
      risk_rules: current.risk_rules.filter((_, ruleIndex) => ruleIndex !== index),
    }));
  }

  function removePatternRiskRuleRow(index: number) {
    setPatternForm((current) => ({
      ...current,
      risk_rules: current.risk_rules.filter((_, ruleIndex) => ruleIndex !== index),
    }));
  }

  async function handleDeleteWorkArea(area: { name: string }) {
    if (!window.confirm(`Delete business area ${area.name}?`)) return;

    setError("");
    setSuccessMessage("");
    try {
      const result = await deleteWorkArea(area.name);
      await loadData();
      setSuccessMessage(`Work area ${result.data.name} deleted successfully.`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to delete business area");
    }
  }

  useEffect(() => {
    loadData();
    loadSchedulerSettings();
    loadChunkingSettings();
  }, []);

  useEffect(() => {
    const loadCapabilities = async () => {
      try {
        const data = await repositorySyncApi.getConnectorCapabilities();
        setConnectorCapabilities(data);
      } catch (err) {
        console.error("Failed to load connector capabilities", err);
      }
    };

    loadCapabilities();
  }, []);

  useEffect(() => {
    setRepositoryPage(0);
  }, [repositorySearch, sourceFilter, businessAreaFilter, statusFilter, repositories.length]);

  useEffect(() => {
    setWorkAreaPage(0);
  }, [workAreaSearch, workAreas.length]);

  useEffect(() => {
    setPatternPage(0);
  }, [patternSearch, intelligencePatterns.length]);

  useEffect(() => {
    if (!repoForm.business_area && workAreas.length) {
      setRepoForm((current) => ({
        ...current,
        business_area: getDefaultWorkAreaName(workAreas),
      }));
    }
  }, [repoForm.business_area, workAreas]);

  async function handleCreateRepository() {
    setError("");

    try {
      const result = await createRepository({
        ...repoForm,
        connection_config: connectionConfig,
      });

      if (!result.success) {
        setError("Unable to create repository");
        return;
      }

      setRepoDialogOpen(false);
      setRepoForm({
        repository_name: "",
        source_type: "sharepoint",
        business_area: getDefaultWorkAreaName(workAreas),
        status: "ACTIVE",
        source_path: "",
      });
      setConnectionConfig({});

      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to create repository");
    }
  }

  async function handleGrantAccess() {
    setError("");
    setSuccessMessage("");

    try {
      const result = await grantRepositoryAccess(accessForm);

      if (!result.success) {
        setError("Unable to grant access");
        return;
      }

      setAccessDialogOpen(false);
      setGrantAccessDialogOpen(false);

      if (selectedRepo) {
        await loadAccess(selectedRepo);
      }

      setSuccessMessage("Repository access granted successfully.");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to grant access");
    }
  }

  function openConnectionDialog(repo: any) {
    setConnectionRepo(repo);
    setRootPath(repo.connection_config?.root_path || repo.source_path || "");
    setSourcePath(repo.source_path || "");
    setConnectionBusinessArea(String(repo.business_area || ""));
    setConnectionDialogConfig(repo.connection_config || {});
    setConnectionDialogOpen(true);
  }

  async function handleSaveConnection() {
    if (!connectionRepo) return;

    const nextConfig =
      connectionRepo.source_type === "sharedrive"
        ? {
            ...connectionDialogConfig,
            root_path: rootPath,
          }
        : connectionDialogConfig;

    const result = await updateRepositoryConnection(connectionRepo.repository_id, {
      source_path:
        connectionRepo.source_type === "sharedrive" ? sourcePath : undefined,
      business_area: connectionBusinessArea,
      connection_config: nextConfig,
    });

    if (result?.data) {
      setSelectedRepo(result.data);
      setConnectionRepo(result.data);
    }

    setConnectionDialogOpen(false);
    await loadData();
  }

  async function handleSync(repo: any) {
    setSyncing(true);
    setError("");

    try {
      const result = await syncRepository(repo.repository_id);

      if (result.success) {
        alert(
          `Sync completed. Found: ${result.files_found}, Indexed: ${result.indexed}, Failed: ${result.failed}`
        );
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Sync failed");
    } finally {
      setSyncing(false);
      await loadData();
    }
  }

  async function handleDisconnect(repo: any) {
    if (!window.confirm(`Disconnect ${repo.repository_name}?`)) return;

    setRepoActionId(repo.repository_id);
    setRepoActionType("disconnect");
    setError("");
    setSuccessMessage("");

    try {
      const result = await disconnectRepository(repo.repository_id);
      if (result?.data) {
        setSelectedRepo(result.data);
      }
      await loadData();
      if (selectedRepo?.repository_id === repo.repository_id) {
        await loadAccess(result?.data || repo);
      }
      setSuccessMessage(`Disconnected ${repo.repository_name}.`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Disconnect failed");
    } finally {
      setRepoActionId(null);
      setRepoActionType(null);
    }
  }

  async function handleRemove(repo: any) {
    if (
      !window.confirm(
        `Remove ${repo.repository_name}? This will delete the repository and its indexed documents.`
      )
    ) {
      return;
    }

    setRepoActionId(repo.repository_id);
    setRepoActionType("remove");
    setError("");
    setSuccessMessage("");

    try {
      await deleteRepository(repo.repository_id);
      setSelectedRepo((current: any | null) =>
        current?.repository_id === repo.repository_id ? null : current
      );
      setAccessRows((current: any[]) =>
        selectedRepo?.repository_id === repo.repository_id ? [] : current
      );
      await loadData();
      setSuccessMessage(`Removed ${repo.repository_name}.`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Remove failed");
    } finally {
      setRepoActionId(null);
      setRepoActionType(null);
    }
  }

  async function handleReindex(repo: any) {
    if (
      !window.confirm(
        `Reindex ${repo.repository_name}? This will clear existing indexed chunks/documents for this repository and rebuild them using the current chunking settings.`
      )
    ) {
      return;
    }

    setRepoActionId(repo.repository_id);
    setRepoActionType("reindex");
    setError("");
    setSuccessMessage("");

    try {
      const result = await repositorySyncApi.reindexRepository(repo.repository_id);
      await loadData();
      setReindexReport({
        repository_name: repo.repository_name,
        repository_id: repo.repository_id,
        chunking: {
          max_chars: Number(chunkMaxChars || "1400"),
          overlap_chars: Number(chunkOverlapChars || "150"),
        },
        reset: result?.reset,
        sync: result?.sync,
      });
      setReindexReportOpen(true);
      setSuccessMessage(
        result?.sync?.success
          ? `Reindex triggered for ${repo.repository_name}. Files found: ${result.sync.files_found}, reprocessed: ${result.sync.indexed}, chunks rebuilt: ${result.sync.chunks_created}.`
          : `Reindex completed with issues for ${repo.repository_name}.`
      );
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Reindex failed");
    } finally {
      setRepoActionId(null);
      setRepoActionType(null);
    }
  }

  function openActionsMenu(event: React.MouseEvent<HTMLElement>, repo: any) {
    setActionsAnchorEl(event.currentTarget);
    setActionsRepo(repo);
  }

  function closeActionsMenu() {
    setActionsAnchorEl(null);
    setActionsRepo(null);
  }

  async function handleRunDueSyncs() {
    try {
      await repositorySyncApi.runDueSyncs();
      await loadData();
    } catch (err) {
      console.error(err);
    }
  }

  async function handleCleanupSyncRecords() {
    try {
      await repositorySyncApi.cleanupSyncRecords();
      await loadData();
    } catch (err) {
      console.error(err);
    }
  }

  async function handleSaveSchedulerSettings() {
    try {
      const data = await repositorySyncApi.updateSchedulerSettings({
        mode: schedulerMode as "embedded" | "external" | "disabled",
        interval_minutes: Number(schedulerInterval || "5"),
        timezone: schedulerTimezone.trim() || "UTC",
      });
      setSchedulerSettings(data);
      setSchedulerMode(data.mode || "embedded");
      setSchedulerInterval(String(data.interval_minutes ?? 5));
      setSchedulerTimezone(data.timezone || "UTC");
    } catch (err) {
      console.error(err);
    }
  }

  async function handleSaveChunkingSettings() {
    try {
      const data = await repositorySyncApi.updateChunkingSettings({
        max_chars: Number(chunkMaxChars || "1400"),
        overlap_chars: Number(chunkOverlapChars || "150"),
      });
      setChunkingSettings(data);
      setChunkMaxChars(String(data.max_chars ?? 1400));
      setChunkOverlapChars(String(data.overlap_chars ?? 150));
      setSuccessMessage(data.message || "Chunking settings saved.");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to save chunking settings");
    }
  }

  const repositoryRowsPerPage = 10;
  const normalizedRepositorySearch = repositorySearch.trim().toLowerCase();
  const sourceFilterOptions = Array.from(
    new Set(repositories.map((repo) => String(repo.source_type || "")))
  ).filter(Boolean);
  const businessAreaFilterOptions = Array.from(
    new Set(repositories.map((repo) => String(repo.business_area || "")))
  ).filter(Boolean);
  const statusFilterOptions = Array.from(
    new Set(repositories.map((repo) => String(repo.status || "")))
  ).filter(Boolean);

  const filteredRepositories = repositories.filter((repo) => {
    const matchesSearch =
      !normalizedRepositorySearch ||
      [
        repo.repository_name,
        repo.repository_id,
        repo.source_type,
        sourceTypeLabel(repo.source_type),
        repo.business_area,
        repo.status,
        repo.source_path,
      ]
        .filter(Boolean)
        .some((value) =>
          String(value).toLowerCase().includes(normalizedRepositorySearch)
        );

    const matchesSource =
      sourceFilter === "all" || String(repo.source_type || "") === sourceFilter;
    const matchesBusinessArea =
      businessAreaFilter === "all" ||
      String(repo.business_area || "") === businessAreaFilter;
    const matchesStatus =
      statusFilter === "all" || String(repo.status || "") === statusFilter;

    return matchesSearch && matchesSource && matchesBusinessArea && matchesStatus;
  });

  const pagedRepositories = filteredRepositories.slice(
    repositoryPage * repositoryRowsPerPage,
    repositoryPage * repositoryRowsPerPage + repositoryRowsPerPage
  );
  const workAreaRowsPerPage = 10;
  const normalizedWorkAreaSearch = workAreaSearch.trim().toLowerCase();
  const filteredWorkAreas = workAreas.filter((area) => {
    if (!normalizedWorkAreaSearch) return true;
    return [
      area.name,
      area.description,
      ...(Array.isArray(area.tags_keywords) ? area.tags_keywords : []),
    ]
      .filter(Boolean)
      .some((value) =>
        String(value).toLowerCase().includes(normalizedWorkAreaSearch)
      );
  });
  const pagedWorkAreas = filteredWorkAreas.slice(
    workAreaPage * workAreaRowsPerPage,
    workAreaPage * workAreaRowsPerPage + workAreaRowsPerPage
  );
  const patternRowsPerPage = 10;
  const normalizedPatternSearch = patternSearch.trim().toLowerCase();
  const filteredPatterns = intelligencePatterns.filter((pattern) => {
    if (!normalizedPatternSearch) return true;
    return [
      pattern.name,
      pattern.description,
      ...(Array.isArray(pattern.tags_keywords) ? pattern.tags_keywords : []),
    ]
      .filter(Boolean)
      .some((value) =>
        String(value).toLowerCase().includes(normalizedPatternSearch)
      );
  });
  const pagedPatterns = filteredPatterns.slice(
    patternPage * patternRowsPerPage,
    patternPage * patternRowsPerPage + patternRowsPerPage
  );

  if (loading) {
    return (
      <ModuleGuard moduleName="settings" permission="admin:users">
        <Box sx={{ p: 4, display: "flex", alignItems: "center", gap: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading repositories...</Typography>
        </Box>
      </ModuleGuard>
    );
  }

  return (
    <ModuleGuard moduleName="settings" permission="admin:users">
      <OutletPage
        title="Repository Management"
        actions={
          <Stack direction="row" spacing={1.5}>
            <Button variant="outlined" onClick={handleRunDueSyncs}>
              Run Due Syncs
            </Button>
            <Button variant="outlined" color="secondary" onClick={handleCleanupSyncRecords}>
              Cleanup Sync Records
            </Button>
          </Stack>
        }
      >
        <Box sx={{ mb: 3 }}>
          <Typography color="text.secondary">
            Add tenant repositories and assign user-level repository access.
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {successMessage && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {successMessage}
          </Alert>
        )}

        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            mb: 2.5,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Stack spacing={2}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                Connector Scheduler
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Controls the in-app scheduler that triggers due repository syncs.
              </Typography>
            </Box>

            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={1}
              sx={{ flexWrap: "wrap" }}
            >
              <Chip
                size="small"
                label={`Mode: ${schedulerSettings?.mode || "embedded"}`}
                color="info"
              />
              <Chip
                size="small"
                label={`Running: ${schedulerSettings?.running ? "Yes" : "No"}`}
                color={schedulerSettings?.running ? "success" : "default"}
              />
              <Chip
                size="small"
                label={`APScheduler: ${schedulerSettings?.apscheduler_available ? "Available" : "Missing"}`}
                color={schedulerSettings?.apscheduler_available ? "success" : "warning"}
              />
            </Stack>

            <Alert severity="warning">
              These scheduler changes are runtime-only for the current app process and are not persisted across restart.
            </Alert>

            <Alert severity="info">
              For multi-replica deployments, disable the embedded scheduler and run due-syncs from a single external scheduler or job runner instead.
            </Alert>

            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={2}
              sx={{ alignItems: "center" }}
            >
              <FormControl size="small" sx={{ minWidth: 220 }}>
                <InputLabel>Scheduler Mode</InputLabel>
                <Select
                  label="Scheduler Mode"
                  value={schedulerMode}
                  onChange={(e) => setSchedulerMode(String(e.target.value))}
                >
                  <MenuItem value="embedded">Embedded</MenuItem>
                  <MenuItem value="external">External</MenuItem>
                  <MenuItem value="disabled">Disabled</MenuItem>
                </Select>
              </FormControl>

              <TextField
                size="small"
                type="number"
                label="Interval minutes"
                value={schedulerInterval}
                onChange={(e) => setSchedulerInterval(e.target.value)}
                sx={{ width: 180 }}
                disabled={schedulerMode === "disabled"}
              />

              <TextField
                size="small"
                label="Timezone"
                value={schedulerTimezone}
                onChange={(e) => setSchedulerTimezone(e.target.value)}
                sx={{ width: 180 }}
                disabled={schedulerMode === "disabled"}
              />

              <Button variant="outlined" onClick={handleSaveSchedulerSettings}>
                Save Scheduler
              </Button>
            </Stack>
          </Stack>
        </Paper>

        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            mb: 2.5,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Stack spacing={2}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                Chunking Settings
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Controls how repository document text is split for embeddings and search retrieval.
              </Typography>
            </Box>

            <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
              <Chip
                size="small"
                label={`Chunk size: ${chunkingSettings?.max_chars ?? chunkMaxChars} chars`}
                color="info"
              />
              <Chip
                size="small"
                label={`Overlap: ${chunkingSettings?.overlap_chars ?? chunkOverlapChars} chars`}
                color="default"
              />
              <Chip
                size="small"
                label={
                  chunkingSettings?.persistent
                    ? "Persists across restart"
                    : "Runtime only"
                }
                color={chunkingSettings?.persistent ? "success" : "warning"}
              />
            </Stack>

            <Alert severity="info">
              Recommended enterprise default: around 1400 characters with 150 characters overlap.
            </Alert>

            <Alert severity="warning">
              These chunking changes are now saved across backend restart. Existing indexed chunks are not rewritten automatically, so run Reindex on a repository to rebuild all chunks with the new settings.
            </Alert>

            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={2}
              sx={{ alignItems: "center" }}
            >
              <TextField
                size="small"
                type="number"
                label="Chunk size (chars)"
                value={chunkMaxChars}
                onChange={(e) => setChunkMaxChars(e.target.value)}
                sx={{ width: 220 }}
              />

              <TextField
                size="small"
                type="number"
                label="Overlap (chars)"
                value={chunkOverlapChars}
                onChange={(e) => setChunkOverlapChars(e.target.value)}
                sx={{ width: 220 }}
              />

              <Button variant="outlined" onClick={handleSaveChunkingSettings}>
                Save Chunking
              </Button>
            </Stack>
          </Stack>
        </Paper>

        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            mb: 2.5,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              gap: 2,
              alignItems: { xs: "flex-start", md: "center" },
              flexDirection: { xs: "column", md: "row" },
            }}
          >
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                Business Area
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Define the governed business areas used in repository setup and access assignment.
              </Typography>
            </Box>

            <Button variant="contained" onClick={openCreateWorkAreaDialog}>
              Add New Business Area
            </Button>
          </Box>

          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={1.5}
            sx={{ mt: 2, mb: 1.5, alignItems: { md: "center" } }}
          >
            <TextField
              size="small"
              label="Search business areas"
              placeholder="Name or description..."
              value={workAreaSearch}
              onChange={(e) => setWorkAreaSearch(e.target.value)}
              sx={{ minWidth: { xs: "100%", md: 320 } }}
            />
            <Typography variant="body2" color="text.secondary">
              Showing {pagedWorkAreas.length} of {filteredWorkAreas.length} business areas
            </Typography>
          </Stack>

          <Table size="small" sx={{ mt: 2 }}>
            <TableHead>
              <TableRow>
                <TableCell>Business Area Name</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Pattern</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {pagedWorkAreas.length ? (
                pagedWorkAreas.map((area) => (
                  <TableRow key={area.name} hover>
                    <TableCell>
                      <Typography sx={{ fontWeight: 700 }}>{area.name}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography color="text.secondary">
                        {area.description || "-"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={String(area.intelligence_pattern || "Not assigned")}
                        color={area.intelligence_pattern ? "info" : "default"}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        aria-label={`Edit ${area.name}`}
                        onClick={() => openEditWorkAreaDialog(area)}
                      >
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        aria-label={`Delete ${area.name}`}
                        onClick={() => handleDeleteWorkArea(area)}
                      >
                        <DeleteOutlineOutlinedIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={4}>
                    <Typography color="text.secondary">
                      No business areas match the current search.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          <TablePagination
            component="div"
            count={filteredWorkAreas.length}
            page={workAreaPage}
            onPageChange={(_, nextPage) => setWorkAreaPage(nextPage)}
            rowsPerPage={workAreaRowsPerPage}
            rowsPerPageOptions={[10]}
          />
        </Paper>

        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            mb: 2.5,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              gap: 2,
              alignItems: { xs: "flex-start", md: "center" },
              flexDirection: { xs: "column", md: "row" },
            }}
          >
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                Intelligence Patterns
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Create reusable intelligence templates for business areas such as General Workspace, Procure to Pay Process, and Supplier Relationship Management.
              </Typography>
            </Box>

            <Button variant="contained" onClick={openCreatePatternDialog}>
              Add Intelligence Pattern
            </Button>
          </Box>

          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={1.5}
            sx={{ mt: 2, mb: 1.5, alignItems: { md: "center" } }}
          >
            <TextField
              size="small"
              label="Search patterns"
              placeholder="Name, description, or tags..."
              value={patternSearch}
              onChange={(e) => setPatternSearch(e.target.value)}
              sx={{ minWidth: { xs: "100%", md: 320 } }}
            />
            <Typography variant="body2" color="text.secondary">
              Showing {pagedPatterns.length} of {filteredPatterns.length} patterns
            </Typography>
          </Stack>

          <Table size="small" sx={{ mt: 2 }}>
            <TableHead>
              <TableRow>
                <TableCell>Pattern Name</TableCell>
                <TableCell>Description</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {pagedPatterns.length ? (
                pagedPatterns.map((pattern) => (
                  <TableRow key={pattern.name} hover>
                    <TableCell>
                      <Typography sx={{ fontWeight: 700 }}>{pattern.name}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography color="text.secondary">
                        {pattern.description || "-"}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        aria-label={`Edit ${pattern.name}`}
                        onClick={() => openEditPatternDialog(pattern)}
                      >
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        aria-label={`Delete ${pattern.name}`}
                        onClick={() => handleDeletePattern(pattern)}
                      >
                        <DeleteOutlineOutlinedIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={3}>
                    <Typography color="text.secondary">
                      No intelligence patterns match the current search.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          <TablePagination
            component="div"
            count={filteredPatterns.length}
            page={patternPage}
            onPageChange={(_, nextPage) => setPatternPage(nextPage)}
            rowsPerPage={patternRowsPerPage}
            rowsPerPageOptions={[patternRowsPerPage]}
          />
        </Paper>

        <Grid container spacing={2.5}>
          <Grid size={{ xs: 12 }}>
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 2,
                  alignItems: { xs: "flex-start", md: "center" },
                  flexDirection: { xs: "column", md: "row" },
                  mb: 2,
                }}
              >
                <Typography variant="h6" sx={{ fontWeight: 800 }}>
                  Tenant Repositories
                </Typography>
                <Button variant="contained" onClick={() => setRepoDialogOpen(true)}>
                  Add Repository
                </Button>
              </Box>

              <Stack
                direction={{ xs: "column", lg: "row" }}
                spacing={1.5}
                sx={{ mb: 2, alignItems: { lg: "center" } }}
              >
                <TextField
                  size="small"
                  label="Search repositories"
                  placeholder="Name, ID, path, source..."
                  value={repositorySearch}
                  onChange={(e) => setRepositorySearch(e.target.value)}
                  sx={{ minWidth: { xs: "100%", lg: 280 } }}
                />

                <FormControl size="small" sx={{ minWidth: { xs: "100%", sm: 180 } }}>
                  <InputLabel>Source</InputLabel>
                  <Select
                    label="Source"
                    value={sourceFilter}
                    onChange={(e) => setSourceFilter(String(e.target.value))}
                  >
                    <MenuItem value="all">All sources</MenuItem>
                    {sourceFilterOptions.map((type) => (
                      <MenuItem key={type} value={type}>
                        {sourceTypeLabel(type)}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <FormControl size="small" sx={{ minWidth: { xs: "100%", sm: 180 } }}>
                  <InputLabel>Business Area</InputLabel>
                  <Select
                    label="Business Area"
                    value={businessAreaFilter}
                    onChange={(e) => setBusinessAreaFilter(String(e.target.value))}
                  >
                    <MenuItem value="all">All business areas</MenuItem>
                    {businessAreaFilterOptions.map((area) => (
                      <MenuItem key={area} value={area}>
                        {area}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <FormControl size="small" sx={{ minWidth: { xs: "100%", sm: 160 } }}>
                  <InputLabel>Status</InputLabel>
                  <Select
                    label="Status"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(String(e.target.value))}
                  >
                    <MenuItem value="all">All statuses</MenuItem>
                    {statusFilterOptions.map((status) => (
                      <MenuItem key={status} value={status}>
                        {status}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Stack>

              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                Showing {pagedRepositories.length} of {filteredRepositories.length} repositories
              </Typography>

              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Repository</TableCell>
                    <TableCell>Source</TableCell>
                    <TableCell>Business Area</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Action</TableCell>
                  </TableRow>
                </TableHead>

                <TableBody>
                  {pagedRepositories.length ? (
                    pagedRepositories.map((repo) => (
                      <TableRow key={repo.repository_id} hover>
                        <TableCell>
                          <Typography sx={{ fontWeight: 700 }}>
                            {repo.repository_name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {repo.repository_id}
                          </Typography>
                          {repo.source_type === "sharedrive" && repo.source_path && (
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{ display: "block" }}
                            >
                              {repo.source_path}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>{sourceTypeLabel(repo.source_type)}</TableCell>
                        <TableCell>
                          <Chip size="small" label={repo.business_area} />
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={repo.status}
                            color={repo.status === "ACTIVE" ? "success" : "default"}
                          />
                          {repo.sync_status && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                              Sync: {repo.sync_status}
                            </Typography>
                          )}
                          {(repo.last_sync_error || repo.sync_metadata?.discovery_warning?.message) && (
                            <Typography
                              variant="caption"
                              color="warning.main"
                              sx={{ display: "block", mt: 0.5, maxWidth: 280 }}
                            >
                              {repo.last_sync_error || repo.sync_metadata?.discovery_warning?.message}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Button
                            size="small"
                            variant="outlined"
                            endIcon={<MoreVertIcon />}
                            onClick={(event) => openActionsMenu(event, repo)}
                          >
                            Actions
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={5}>
                        <Typography color="text.secondary">
                          No repositories match the current search and filters.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>

              <TablePagination
                component="div"
                count={filteredRepositories.length}
                page={repositoryPage}
                onPageChange={(_, nextPage) => setRepositoryPage(nextPage)}
                rowsPerPage={repositoryRowsPerPage}
                rowsPerPageOptions={[10]}
              />
            </Paper>
          </Grid>

          {selectedRepo && (
            <Grid size={{ xs: 12 }}>
              <SyncStatusPanel repository={selectedRepo} />
              <SyncLogsTable repository={selectedRepo} />
            </Grid>
          )}
        </Grid>

        <Dialog
          open={repoDialogOpen}
          onClose={() => setRepoDialogOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle sx={{ fontWeight: 800 }}>Add Repository</DialogTitle>

          <DialogContent>
            <TextField
              fullWidth
              label="Repository Name"
              value={repoForm.repository_name}
              onChange={(e) =>
                setRepoForm({
                  ...repoForm,
                  repository_name: e.target.value,
                })
              }
              sx={{ mt: 1, mb: 2 }}
            />

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Source Type</InputLabel>
              <Select
                label="Source Type"
                value={repoForm.source_type}
                onChange={(e) =>
                  setRepoForm({
                    ...repoForm,
                    source_type: e.target.value,
                    source_path:
                      e.target.value === "sharedrive" ? repoForm.source_path : "",
                  })
                }
              >
                {sourceTypes.map((type) => (
                  <MenuItem key={type} value={type}>
                    {sourceTypeLabel(type)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {repoForm.source_type === "sharepoint" ? (
              <SharePointSetupWizard
                config={connectionConfig}
                setConfig={setConnectionConfig}
              />
            ) : repoForm.source_type === "sharedrive" ? (
              <SharedDriveSetupWizard
                rootPath={connectionConfig.root_path || ""}
                setRootPath={(value) =>
                  setConnectionConfig({
                    ...connectionConfig,
                    root_path: value,
                  })
                }
                sourcePath={repoForm.source_path}
                setSourcePath={(value) =>
                  setRepoForm({ ...repoForm, source_path: value })
                }
              />
            ) : (
              <ConnectorSettingsFields
                sourceType={repoForm.source_type}
                capabilities={connectorCapabilities}
                config={connectionConfig}
                setConfig={setConnectionConfig}
              />
            )}

            {repoForm.source_type === "sharepoint" && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Configure the Microsoft Graph application fields below to enable SharePoint sync.
              </Alert>
            )}

            {repoForm.source_type === "otcs" && (
              <Alert severity="info" sx={{ mb: 2 }}>
                This connector is scaffolded. Full OTCS connection settings will be enabled later.
              </Alert>
            )}

            <FormControl fullWidth sx={{ mt: 2 }}>
              <InputLabel>Business Area</InputLabel>
              <Select
                label="Business Area"
                value={repoForm.business_area}
                onChange={(e) =>
                  setRepoForm({
                    ...repoForm,
                    business_area: String(e.target.value),
                  })
                }
              >
                {workAreas.map((area) => (
                  <MenuItem key={area.name} value={area.name}>
                    {area.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {!workAreas.length && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                Create at least one Business Area before adding a repository.
              </Alert>
            )}

          </DialogContent>

          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setRepoDialogOpen(false)}>Cancel</Button>
            <Button
              variant="contained"
              disabled={
                !repoForm.repository_name ||
                !repoForm.business_area ||
                (repoForm.source_type === "sharedrive" &&
                  (!repoForm.source_path.trim() || !connectionConfig.root_path?.trim()))
              }
              onClick={handleCreateRepository}
            >
              Create Repository
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog
          open={connectionDialogOpen}
          onClose={() => setConnectionDialogOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle sx={{ fontWeight: 800 }}>Repository Connection</DialogTitle>

          <DialogContent>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Update the connector-specific connection settings for this repository.
            </Typography>

            {connectionRepo?.source_type === "sharepoint" ? (
              <SharePointSetupWizard
                config={connectionDialogConfig}
                setConfig={setConnectionDialogConfig}
              />
            ) : connectionRepo?.source_type === "sharedrive" ? (
              <SharedDriveSetupWizard
                rootPath={rootPath}
                setRootPath={setRootPath}
                sourcePath={sourcePath}
                setSourcePath={setSourcePath}
              />
            ) : (
              connectionRepo?.source_type &&
              connectionRepo.source_type !== "sharedrive" && (
                <ConnectorSettingsFields
                  sourceType={connectionRepo.source_type}
                  capabilities={connectorCapabilities}
                  config={connectionDialogConfig}
                  setConfig={setConnectionDialogConfig}
                />
              )
            )}

            <FormControl fullWidth sx={{ mt: 2 }}>
              <InputLabel>Business Area</InputLabel>
              <Select
                label="Business Area"
                value={connectionBusinessArea}
                onChange={(e) => setConnectionBusinessArea(String(e.target.value))}
              >
                {workAreas.map((area) => (
                  <MenuItem key={area.name} value={area.name}>
                    {area.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {!workAreas.length && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                Create at least one Business Area before editing repository business area.
              </Alert>
            )}
          </DialogContent>

          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setConnectionDialogOpen(false)}>Cancel</Button>
            <Button
              variant="contained"
              disabled={!connectionBusinessArea}
              onClick={handleSaveConnection}
            >
              Save Connection
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog
          open={accessDialogOpen}
          onClose={() => setAccessDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle sx={{ fontWeight: 800 }}>
            Repository Access
          </DialogTitle>

          <DialogContent>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                {selectedRepo
                  ? `Manage access for ${selectedRepo.repository_name}.`
                  : "Select a repository to manage access."}
              </Typography>
            </Box>

            {!selectedRepo ? (
              <Alert severity="info">No repository selected.</Alert>
            ) : accessRows.length === 0 ? (
              <Alert severity="info">
                No access rows exist yet for this repository.
              </Alert>
            ) : (
              <Stack gap={1.2}>
                {accessRows.map((row) => {
                  const user = users.find((u) => u.user_id === row.user_id);

                  return (
                    <Paper
                      key={row.access_id}
                      elevation={0}
                      sx={{
                        p: 1.5,
                        borderRadius: 2,
                        border: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Typography sx={{ fontWeight: 700 }}>
                        {user?.name || row.user_id}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {user?.email}
                      </Typography>

                      <Stack direction="row" gap={1} sx={{ mt: 1, flexWrap: "wrap" }}>
                        {row.can_read && <Chip size="small" label="Read" />}
                        {row.can_ingest && <Chip size="small" label="Ingest" />}
                        {row.can_admin && <Chip size="small" label="Admin" />}
                        <Chip size="small" label={row.business_area} />
                      </Stack>
                    </Paper>
                  );
                })}
              </Stack>
            )}
          </DialogContent>

          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setAccessDialogOpen(false)}>Cancel</Button>
            <Button
              variant="contained"
              disabled={!selectedRepo}
              onClick={() => setGrantAccessDialogOpen(true)}
            >
              Grant Access
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog
          open={grantAccessDialogOpen}
          onClose={() => setGrantAccessDialogOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle sx={{ fontWeight: 800 }}>
            Grant Repository Access
          </DialogTitle>

          <DialogContent>
            <FormControl fullWidth sx={{ mt: 1, mb: 2 }}>
              <InputLabel>User</InputLabel>
              <Select
                label="User"
                value={accessForm.user_id}
                onChange={(e) =>
                  setAccessForm({ ...accessForm, user_id: e.target.value })
                }
              >
                {users.map((user) => (
                  <MenuItem key={user.user_id} value={user.user_id}>
                    {user.name} — {user.email}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Business Area</InputLabel>
              <Select
                label="Business Area"
                value={accessForm.business_area}
                onChange={(e) =>
                  setAccessForm({ ...accessForm, business_area: e.target.value })
                }
              >
                {workAreas.map((area) => (
                  <MenuItem key={area.name} value={area.name}>
                    {area.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControlLabel
              control={
                <Checkbox
                  checked={accessForm.can_read}
                  onChange={(e) =>
                    setAccessForm({ ...accessForm, can_read: e.target.checked })
                  }
                />
              }
              label="Can Read"
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={accessForm.can_ingest}
                  onChange={(e) =>
                    setAccessForm({ ...accessForm, can_ingest: e.target.checked })
                  }
                />
              }
              label="Can Ingest"
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={accessForm.can_admin}
                  onChange={(e) =>
                    setAccessForm({ ...accessForm, can_admin: e.target.checked })
                  }
                />
              }
              label="Can Admin"
            />
          </DialogContent>

          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setGrantAccessDialogOpen(false)}>Cancel</Button>
            <Button
              variant="contained"
              disabled={!accessForm.user_id}
              onClick={handleGrantAccess}
            >
              Grant Access
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog
          open={workAreaDialogOpen}
          onClose={() => setWorkAreaDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle sx={{ fontWeight: 800 }}>
            {workAreaDialogMode === "edit" ? "Edit Business Area" : "Add New Business Area"}
          </DialogTitle>

          <DialogContent>
            <TextField
              fullWidth
              label="Business Area Name"
              value={workAreaForm.name}
              onChange={(e) =>
                setWorkAreaForm({ ...workAreaForm, name: e.target.value })
              }
              sx={{ mt: 1, mb: 2 }}
            />

            <TextField
              fullWidth
              multiline
              minRows={3}
              label="Business Area Description"
              value={workAreaForm.description}
              onChange={(e) =>
                setWorkAreaForm({ ...workAreaForm, description: e.target.value })
              }
              sx={{ mb: 2 }}
            />

            <FormControl fullWidth sx={{ mb: 1 }}>
              <InputLabel>Intelligence Pattern</InputLabel>
              <Select
                label="Intelligence Pattern"
                value={workAreaForm.intelligence_pattern}
                onChange={(e) =>
                  setWorkAreaForm({
                    ...workAreaForm,
                    intelligence_pattern: String(e.target.value),
                  })
                }
              >
                {intelligencePatterns.map((pattern) => (
                  <MenuItem key={pattern.name} value={pattern.name}>
                    {pattern.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 2 }}>
              {intelligencePatterns.find(
                (pattern) => pattern.name === workAreaForm.intelligence_pattern
              )?.description || "Choose the reusable pattern that best fits this business area."}
            </Typography>

            <TextField
              fullWidth
              multiline
              minRows={3}
              label="Tags / Keywords"
              helperText="Enter one keyword per line. These are used as work-area guidance for search, document intelligence, and summary routing."
              value={workAreaForm.tags_keywords}
              onChange={(e) =>
                setWorkAreaForm({ ...workAreaForm, tags_keywords: e.target.value })
              }
              sx={{ mb: 2 }}
            />

          </DialogContent>

          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setWorkAreaDialogOpen(false)}>Cancel</Button>
            <Button
              variant="contained"
              disabled={!workAreaForm.name.trim()}
              onClick={handleSaveWorkArea}
            >
              {workAreaDialogMode === "edit" ? "Update Business Area" : "Save Business Area"}
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog
          open={patternDialogOpen}
          onClose={() => setPatternDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle sx={{ fontWeight: 800 }}>
            {patternDialogMode === "edit" ? "Edit Intelligence Pattern" : "Add Intelligence Pattern"}
          </DialogTitle>

          <DialogContent>
            <TextField
              fullWidth
              label="Pattern Name"
              value={patternForm.name}
              onChange={(e) =>
                setPatternForm({ ...patternForm, name: e.target.value })
              }
              sx={{ mt: 1, mb: 2 }}
            />

            <TextField
              fullWidth
              multiline
              minRows={3}
              label="Pattern Description"
              value={patternForm.description}
              onChange={(e) =>
                setPatternForm({ ...patternForm, description: e.target.value })
              }
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              multiline
              minRows={3}
              label="Tags / Keywords"
              helperText="Enter one keyword per line. These guide search, document intelligence, and summary behavior."
              value={patternForm.tags_keywords}
              onChange={(e) =>
                setPatternForm({ ...patternForm, tags_keywords: e.target.value })
              }
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              multiline
              minRows={3}
              label="Summary Focus"
              helperText="One item per line, for example: contract expiry, invoice variance, delivery delay."
              value={patternForm.summary_focus}
              onChange={(e) =>
                setPatternForm({ ...patternForm, summary_focus: e.target.value })
              }
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              multiline
              minRows={3}
              label="Required Specifics"
              helperText="One item per line, for example: contract number, expiry date, utilization percent, PO value, invoice value."
              value={patternForm.required_specifics}
              onChange={(e) =>
                setPatternForm({
                  ...patternForm,
                  required_specifics: e.target.value,
                })
              }
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              multiline
              minRows={3}
              label="Entities To Extract"
              helperText="One field per line. Example: reference_no, counterparty_name, document_no, effective_date."
              value={patternForm.entities_to_extract}
              onChange={(e) =>
                setPatternForm({
                  ...patternForm,
                  entities_to_extract: e.target.value,
                })
              }
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              multiline
              minRows={3}
              label="Enabled Checks"
              helperText="One check per line. Example: expiring contract, invoice greater than po, missing grn, compliance lapse."
              value={patternForm.enabled_checks}
              onChange={(e) =>
                setPatternForm({
                  ...patternForm,
                  enabled_checks: e.target.value,
                })
              }
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              multiline
              minRows={4}
              label="Summary Template"
              helperText="Optional AI instruction template for this pattern."
              value={patternForm.summary_template}
              onChange={(e) =>
                setPatternForm({
                  ...patternForm,
                  summary_template: e.target.value,
                })
              }
              sx={{ mb: 2 }}
            />

            <Paper
              elevation={0}
              sx={{ p: 2, mb: 2, borderRadius: 2, border: "1px solid", borderColor: "divider" }}
            >
              <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 1.5 }}>
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                    Threshold Rules
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Define measurable conditions like expiring in 30 days, utilization above 80, or value greater than a threshold.
                  </Typography>
                </Box>
                <Button variant="outlined" onClick={addPatternThresholdRuleRow}>
                  Add Threshold
                </Button>
              </Stack>

              {patternForm.threshold_rules.length ? (
                <Stack spacing={1.5}>
                  {patternForm.threshold_rules.map((rule, index) => (
                    <Paper
                      key={`pattern-threshold-rule-${index}`}
                      elevation={0}
                      sx={{ p: 1.5, borderRadius: 2, border: "1px solid", borderColor: "divider" }}
                    >
                      <Grid container spacing={1.5}>
                        <Grid size={{ xs: 12, md: 4 }}>
                          <TextField fullWidth size="small" label="Rule Name" value={rule.label} onChange={(e) => updatePatternThresholdRuleRow(index, { label: e.target.value })} />
                        </Grid>
                        <Grid size={{ xs: 12, md: 3 }}>
                          <TextField fullWidth size="small" label="Field" value={rule.field} onChange={(e) => updatePatternThresholdRuleRow(index, { field: e.target.value })} />
                        </Grid>
                        <Grid size={{ xs: 12, md: 3 }}>
                          <FormControl fullWidth size="small">
                            <InputLabel>Condition</InputLabel>
                            <Select label="Condition" value={rule.operator} onChange={(e) => updatePatternThresholdRuleRow(index, { operator: String(e.target.value) })}>
                              {workAreaRuleOperators.map((operator) => (
                                <MenuItem key={operator.value} value={operator.value}>
                                  {operator.label}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </Grid>
                        <Grid size={{ xs: 10, md: 2 }}>
                          <TextField fullWidth size="small" label="Value" value={rule.value} onChange={(e) => updatePatternThresholdRuleRow(index, { value: e.target.value })} />
                        </Grid>
                        <Grid size={{ xs: 2, md: 12 }}>
                          <Box sx={{ display: "flex", justifyContent: { xs: "flex-end", md: "flex-start" } }}>
                            <Button color="error" onClick={() => removePatternThresholdRuleRow(index)}>Remove</Button>
                          </Box>
                        </Grid>
                      </Grid>
                    </Paper>
                  ))}
                </Stack>
              ) : (
                <Alert severity="info">
                  No threshold rules yet. Add rules like "contract utilization &gt;= 80" or "expiry_days &lt;= 30".
                </Alert>
              )}
            </Paper>

            <Paper
              elevation={0}
              sx={{ p: 2, mb: 1, borderRadius: 2, border: "1px solid", borderColor: "divider" }}
            >
              <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 1.5 }}>
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                    Risk Rules
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Define what should be treated as a risk and how serious it is.
                  </Typography>
                </Box>
                <Button variant="outlined" onClick={addPatternRiskRuleRow}>
                  Add Risk Rule
                </Button>
              </Stack>

              {patternForm.risk_rules.length ? (
                <Stack spacing={1.5}>
                  {patternForm.risk_rules.map((rule, index) => (
                    <Paper
                      key={`pattern-risk-rule-${index}`}
                      elevation={0}
                      sx={{ p: 1.5, borderRadius: 2, border: "1px solid", borderColor: "divider" }}
                    >
                      <Grid container spacing={1.5}>
                        <Grid size={{ xs: 12, md: 3 }}>
                          <TextField fullWidth size="small" label="Risk Name" value={rule.label} onChange={(e) => updatePatternRiskRuleRow(index, { label: e.target.value })} />
                        </Grid>
                        <Grid size={{ xs: 12, md: 3 }}>
                          <TextField fullWidth size="small" label="Field" value={rule.field} onChange={(e) => updatePatternRiskRuleRow(index, { field: e.target.value })} />
                        </Grid>
                        <Grid size={{ xs: 12, md: 2 }}>
                          <FormControl fullWidth size="small">
                            <InputLabel>Condition</InputLabel>
                            <Select label="Condition" value={rule.operator} onChange={(e) => updatePatternRiskRuleRow(index, { operator: String(e.target.value) })}>
                              {workAreaRuleOperators.map((operator) => (
                                <MenuItem key={operator.value} value={operator.value}>
                                  {operator.label}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </Grid>
                        <Grid size={{ xs: 12, md: 2 }}>
                          <TextField fullWidth size="small" label="Value" value={rule.value} onChange={(e) => updatePatternRiskRuleRow(index, { value: e.target.value })} />
                        </Grid>
                        <Grid size={{ xs: 12, md: 2 }}>
                          <FormControl fullWidth size="small">
                            <InputLabel>Severity</InputLabel>
                            <Select label="Severity" value={rule.severity || "High"} onChange={(e) => updatePatternRiskRuleRow(index, { severity: String(e.target.value) })}>
                              {workAreaRiskSeverities.map((severity) => (
                                <MenuItem key={severity} value={severity}>
                                  {severity}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </Grid>
                        <Grid size={{ xs: 12 }}>
                          <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
                            <Button color="error" onClick={() => removePatternRiskRuleRow(index)}>Remove</Button>
                          </Box>
                        </Grid>
                      </Grid>
                    </Paper>
                  ))}
                </Stack>
              ) : (
                <Alert severity="info">
                  No risk rules yet. Add rules like "invoice value greater than purchase order value" or "status contains renewal pending".
                </Alert>
              )}
            </Paper>
          </DialogContent>

          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setPatternDialogOpen(false)}>Cancel</Button>
            <Button
              variant="contained"
              disabled={!patternForm.name.trim()}
              onClick={handleSavePattern}
            >
              {patternDialogMode === "edit" ? "Update Intelligence Pattern" : "Save Intelligence Pattern"}
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog
          open={reindexReportOpen}
          onClose={() => setReindexReportOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle sx={{ fontWeight: 800 }}>Reindex Report</DialogTitle>

          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Alert severity={reindexReport?.sync?.success ? "success" : "warning"}>
                {reindexReport?.repository_name
                  ? `Reindex completed for ${reindexReport.repository_name}.`
                  : "Reindex completed."}
              </Alert>

              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  borderRadius: 2,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 1 }}>
                  Repository
                </Typography>
                <Typography variant="body2">
                  {reindexReport?.repository_name || "-"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {reindexReport?.repository_id || "-"}
                </Typography>
              </Paper>

              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper
                    elevation={0}
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      border: "1px solid",
                      borderColor: "divider",
                      height: "100%",
                    }}
                  >
                    <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 1.5 }}>
                      Reset Phase
                    </Typography>
                    <Stack spacing={1}>
                      <Typography variant="body2">
                        Connector files cleared: {reindexReport?.reset?.deleted_connector_files ?? 0}
                      </Typography>
                      <Typography variant="body2">
                        Documents cleared: {reindexReport?.reset?.deleted_documents ?? 0}
                      </Typography>
                      <Typography variant="body2">
                        Chunks cleared: {reindexReport?.reset?.deleted_chunks ?? 0}
                      </Typography>
                      <Typography variant="body2">
                        Sync runs cleared: {reindexReport?.reset?.deleted_sync_runs ?? 0}
                      </Typography>
                      <Typography variant="body2">
                        Failure records cleared: {reindexReport?.reset?.deleted_failures ?? 0}
                      </Typography>
                    </Stack>
                  </Paper>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper
                    elevation={0}
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      border: "1px solid",
                      borderColor: "divider",
                      height: "100%",
                    }}
                  >
                    <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 1.5 }}>
                      Reindex Phase
                    </Typography>
                    <Stack spacing={1}>
                      <Typography variant="body2">
                        Status: {reindexReport?.sync?.status || (reindexReport?.sync?.success ? "completed" : "warning")}
                      </Typography>
                      <Typography variant="body2">
                        Files discovered: {reindexReport?.sync?.files_found ?? 0}
                      </Typography>
                      <Typography variant="body2">
                        Files truly indexed: {reindexReport?.sync?.indexed ?? 0}
                      </Typography>
                      <Typography variant="body2">
                        Files skipped unchanged: {reindexReport?.sync?.skipped ?? 0}
                      </Typography>
                      <Typography variant="body2">
                        Files failed: {reindexReport?.sync?.failed ?? 0}
                      </Typography>
                      <Typography variant="body2">
                        Files deleted from index: {reindexReport?.sync?.deleted ?? 0}
                      </Typography>
                      <Typography variant="body2">
                        Chunks created: {reindexReport?.sync?.chunks_created ?? 0}
                      </Typography>
                      <Typography variant="body2">
                        Embeddings created: {reindexReport?.sync?.embeddings_created ?? 0}
                      </Typography>
                    </Stack>
                  </Paper>
                </Grid>
              </Grid>

              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  borderRadius: 2,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 1.5 }}>
                  Chunking Settings Used
                </Typography>
                <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
                  <Chip
                    size="small"
                    color="info"
                    label={`Chunk size: ${reindexReport?.chunking?.max_chars ?? "-"} chars`}
                  />
                  <Chip
                    size="small"
                    label={`Overlap: ${reindexReport?.chunking?.overlap_chars ?? "-"} chars`}
                  />
                </Stack>
              </Paper>
            </Stack>
          </DialogContent>

          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setReindexReportOpen(false)}>Close</Button>
          </DialogActions>
        </Dialog>

        <Menu
          anchorEl={actionsAnchorEl}
          open={Boolean(actionsAnchorEl)}
          onClose={closeActionsMenu}
        >
          <MenuItem
            onClick={() => {
              if (!actionsRepo) return;
              loadAccess(actionsRepo);
              closeActionsMenu();
            }}
          >
            Manage Access
          </MenuItem>
          <MenuItem
            onClick={() => {
              if (!actionsRepo) return;
              openConnectionDialog(actionsRepo);
              closeActionsMenu();
            }}
          >
            Connection
          </MenuItem>
          <MenuItem
            onClick={() => {
              if (!actionsRepo) return;
              router.push(
                `/reports/repository-report?repositoryId=${encodeURIComponent(
                  actionsRepo.repository_id
                )}`
              );
              closeActionsMenu();
            }}
          >
            Report
          </MenuItem>
          <MenuItem
            disabled={!actionsRepo || syncing || repoActionId === actionsRepo?.repository_id}
            onClick={() => {
              if (!actionsRepo) return;
              handleSync(actionsRepo);
              closeActionsMenu();
            }}
          >
            Sync
          </MenuItem>
          <MenuItem
            disabled={!actionsRepo || repoActionId === actionsRepo?.repository_id}
            onClick={() => {
              if (!actionsRepo) return;
              handleReindex(actionsRepo);
              closeActionsMenu();
            }}
          >
            Reindex
          </MenuItem>
          <MenuItem
            disabled={!actionsRepo || repoActionId === actionsRepo?.repository_id}
            onClick={() => {
              if (!actionsRepo) return;
              handleDisconnect(actionsRepo);
              closeActionsMenu();
            }}
          >
            Disconnect
          </MenuItem>
          <MenuItem
            disabled={!actionsRepo || repoActionId === actionsRepo?.repository_id}
            onClick={() => {
              if (!actionsRepo) return;
              handleRemove(actionsRepo);
              closeActionsMenu();
            }}
          >
            Remove
          </MenuItem>
        </Menu>
      </OutletPage>
    </ModuleGuard>
  );
}

