"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import AddCommentOutlinedIcon from "@mui/icons-material/AddCommentOutlined";
import BadgeOutlinedIcon from "@mui/icons-material/BadgeOutlined";
import CloseIcon from "@mui/icons-material/Close";
import MarkEmailReadOutlinedIcon from "@mui/icons-material/MarkEmailReadOutlined";
import EditOutlined from "@mui/icons-material/EditOutlined";
import EventNoteOutlinedIcon from "@mui/icons-material/EventNoteOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import LightbulbOutlinedIcon from "@mui/icons-material/LightbulbOutlined";
import MoreVertRoundedIcon from "@mui/icons-material/MoreVertRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import SourceOutlinedIcon from "@mui/icons-material/SourceOutlined";
import SwapHorizOutlinedIcon from "@mui/icons-material/SwapHorizOutlined";
import VisibilityOutlined from "@mui/icons-material/VisibilityOutlined";
import WorkOutlineOutlinedIcon from "@mui/icons-material/WorkOutlineOutlined";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Drawer,
  IconButton,
  InputAdornment,
  Menu,
  MenuItem,
  Paper,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";

import { AppNotificationToast } from "@/components/feedback/AppNotificationToast";
import { AdminFormDialog, AdminFormTextField } from "@/components/forms/AdminFormDialog";
import { useAuth } from "@/context/AuthContext";
import { parseApiValidationError } from "@/services/apiErrorParser";
import {
  type AugmisBusinessActivity,
  type AugmisBusinessContact,
  type AugmisBusinessDashboard,
  type AugmisBusinessExperienceItem,
  type AugmisBusinessLead,
  type AugmisBusinessReply,
  type AugmisBusinessProspect,
  type AugmisBusinessTask,
  createAugmisBusinessLeadActivity,
  getAugmisBusinessDashboard,
  getAugmisBusinessLead,
  getAugmisBusinessProspectContacts,
  listAugmisBusinessExperienceItems,
  listAugmisBusinessLeadActivities,
  listAugmisBusinessLeadTasks,
  listAugmisBusinessLeads,
  listAugmisBusinessReplies,
  listAugmisBusinessProspects,
  updateAugmisBusinessLead,
  updateAugmisBusinessLeadStage,
} from "@/services/augmisBusinessService";
import {
  TaskPriorityChip,
  TaskStatusChip,
  formatTaskDateTime,
  formatTaskLabel,
} from "../components/BusinessTaskUI";
import OutreachWorkspaceDialog from "../components/OutreachWorkspaceDialog";
import MiniSolutionWorkspaceDrawer from "../components/MiniSolutionWorkspaceDrawer";
import BusinessPageFrame from "../components/BusinessPageFrame";

type WorkspaceMode = "table" | "pipeline";
type ToastSeverity = "success" | "error" | "info" | "warning";
type DetailTabValue =
  | "overview"
  | "prospect"
  | "opportunity"
  | "experience"
  | "replies"
  | "activities"
  | "tasks";

type LeadEditFormState = {
  title: string;
  primary_contact_id: string;
  priority: string;
  lead_status: string;
  estimated_value: string;
  probability_pct: string;
  notes: string;
};

type ActivityFormState = {
  activity_type: string;
  subject: string;
  description: string;
  activity_at: string;
  direction: string;
  outcome: string;
  contact_id: string;
};

type LeadRowMeta = {
  activities: AugmisBusinessActivity[];
  tasks: AugmisBusinessTask[];
  error: string | null;
};

const ACTIVE_STAGE_ORDER = ["new", "qualified", "proposal", "negotiation"] as const;
const TERMINAL_STAGE_ORDER = ["closed_won", "closed_lost"] as const;
const PIPELINE_STAGE_ORDER = [...ACTIVE_STAGE_ORDER, ...TERMINAL_STAGE_ORDER] as const;

const DEFAULT_EDIT_FORM: LeadEditFormState = {
  title: "",
  primary_contact_id: "",
  priority: "medium",
  lead_status: "active",
  estimated_value: "",
  probability_pct: "",
  notes: "",
};

const DEFAULT_ACTIVITY_FORM: ActivityFormState = {
  activity_type: "manual_activity",
  subject: "",
  description: "",
  activity_at: "",
  direction: "",
  outcome: "",
  contact_id: "",
};

function formatStageLabel(value: string | null | undefined) {
  if (!value) return "Not available";
  return value.replaceAll("_", " ");
}

function formatDateTime(value: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
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

function formatCurrency(value: number | null, currency?: string | null) {
  if (value == null) return "Not available";
  return `${currency ? `${currency} ` : ""}${value.toLocaleString()}`;
}

function getActivitySummary(activity: AugmisBusinessActivity | null) {
  return activity?.subject || "Not available";
}

function getContactDisplayName(contact: AugmisBusinessContact | null) {
  if (!contact) return "Not available";
  return contact.full_name || contact.job_title || contact.email || contact.phone || "Not available";
}

function getPriorityChip(priority: string) {
  switch (priority) {
    case "high":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
    case "medium":
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
    default:
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
  }
}

function getStageChip(stage: string) {
  switch (stage) {
    case "proposal":
      return { bgcolor: "#F5F3FF", color: "#6D28D9", borderColor: "#DDD6FE" };
    case "negotiation":
      return { bgcolor: "#FFF7ED", color: "#C2410C", borderColor: "#FDBA74" };
    case "closed_won":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "closed_lost":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
    case "qualified":
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
    default:
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
  }
}

function getStatusChip(status: string) {
  switch (status) {
    case "won":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "lost":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
    case "archived":
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
    default:
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
  }
}

function getVerificationChip(status: string | null | undefined) {
  switch (status) {
    case "published_by_buyer":
    case "official_company_website":
    case "provider_verified":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "licensed_enrichment":
      return { bgcolor: "#F0FDFA", color: "#0F766E", borderColor: "#99F6E4" };
    case "public_professional_profile":
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
    case "pattern_inferred":
      return { bgcolor: "#FFFAEB", color: "#B54708", borderColor: "#FEDF89" };
    case "rejected":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
    default:
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
  }
}

function isDueToday(value: string | null) {
  if (!value) return false;
  const date = new Date(value);
  const now = new Date();
  return date.toDateString() === now.toDateString();
}

function isOverdue(value: string | null) {
  if (!value) return false;
  return new Date(value).getTime() < Date.now();
}

function getDueDateColor(value: string | null) {
  if (!value) return "#475569";
  if (isOverdue(value)) return "#B42318";
  if (isDueToday(value)) return "#B54708";
  return "#0F172A";
}

function detailField(label: string, value: string) {
  return { label, value };
}

function DetailFieldCard({ label, value }: { label: string; value: string }) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        borderRadius: "8px",
        border: "1px solid #E2E8F0",
        minHeight: 84,
      }}
    >
      <Typography
        sx={{
          fontSize: 11,
          fontWeight: 700,
          color: "#64748B",
          textTransform: "uppercase",
          letterSpacing: ".05em",
        }}
      >
        {label}
      </Typography>
      <Typography sx={{ mt: 0.7, color: "#0F172A", wordBreak: "break-word" }}>
        {value}
      </Typography>
    </Paper>
  );
}

function SectionPanel({
  title,
  icon,
  gradient,
  children,
  action,
}: {
  title: string;
  icon: React.ReactNode;
  gradient: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <Paper
      elevation={0}
      sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}
    >
      <Box
        sx={{
          px: 2,
          py: 1.35,
          background: gradient,
          borderBottom: "1px solid #E2E8F0",
        }}
      >
        <Stack
          direction="row"
          spacing={1}
          sx={{ alignItems: "center", justifyContent: "space-between" }}
        >
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Box sx={{ color: "#2563EB", display: "flex" }}>{icon}</Box>
            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{title}</Typography>
          </Stack>
          {action}
        </Stack>
      </Box>
      <Box sx={{ p: 2 }}>{children}</Box>
    </Paper>
  );
}

function EmptyPanel({ title, description }: { title: string; description: string }) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.25,
        borderRadius: "8px",
        border: "1px dashed #CBD5E1",
        bgcolor: "#F8FAFC",
      }}
    >
      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{title}</Typography>
      <Typography sx={{ mt: 0.7, color: "#475569" }}>{description}</Typography>
    </Paper>
  );
}

function leadToEditForm(lead: AugmisBusinessLead): LeadEditFormState {
  return {
    title: lead.title,
    primary_contact_id: lead.primary_contact_id || "",
    priority: lead.priority,
    lead_status: lead.lead_status,
    estimated_value: lead.estimated_value == null ? "" : String(lead.estimated_value),
    probability_pct: lead.probability_pct == null ? "" : String(lead.probability_pct),
    notes: lead.notes || "",
  };
}

function editFormToPayload(form: LeadEditFormState) {
  return {
    title: form.title.trim(),
    primary_contact_id: normalizeOptionalString(form.primary_contact_id),
    priority: form.priority,
    lead_status: form.lead_status,
    estimated_value: normalizeOptionalNumber(form.estimated_value),
    probability_pct: normalizeOptionalNumber(form.probability_pct),
    notes: normalizeOptionalString(form.notes),
  };
}

function activityFormToPayload(form: ActivityFormState) {
  return {
    activity_type: form.activity_type,
    subject: form.subject.trim(),
    description: normalizeOptionalString(form.description),
    activity_at: normalizeOptionalString(form.activity_at),
    direction: normalizeOptionalString(form.direction),
    outcome: normalizeOptionalString(form.outcome),
    contact_id: normalizeOptionalString(form.contact_id),
    metadata_json: {},
  };
}

function findNextOpenTask(tasks: AugmisBusinessTask[]) {
  return (
    tasks
      .filter((task) => task.task_status === "open" || task.task_status === "in_progress")
      .sort((left, right) => {
        const leftTime = left.due_at ? new Date(left.due_at).getTime() : Number.MAX_SAFE_INTEGER;
        const rightTime = right.due_at ? new Date(right.due_at).getTime() : Number.MAX_SAFE_INTEGER;
        return leftTime - rightTime;
      })[0] || null
  );
}

function mapStageCounts(dashboard: AugmisBusinessDashboard | null) {
  const counts = new Map<string, number>();
  for (const row of dashboard?.leads_by_stage || []) {
    counts.set(row.lead_stage, row.count);
  }
  return counts;
}

export default function LeadWorkspace({ mode }: { mode: WorkspaceMode }) {
  const isPipeline = mode === "pipeline";
  const { hasPermission } = useAuth();
  const canRead = hasPermission("business_development:read");
  const canCreate = hasPermission("business_development:create");
  const canUpdate = hasPermission("business_development:update");
  const canOutreach = hasPermission("business_development:outreach");

  const [dashboard, setDashboard] = useState<AugmisBusinessDashboard | null>(null);
  const [leads, setLeads] = useState<AugmisBusinessLead[]>([]);
  const [leadMeta, setLeadMeta] = useState<Record<string, LeadRowMeta>>({});
  const [prospects, setProspects] = useState<AugmisBusinessProspect[]>([]);
  const [experienceItems, setExperienceItems] = useState<AugmisBusinessExperienceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [prospectFilter, setProspectFilter] = useState("all");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [refreshTick, setRefreshTick] = useState(0);

  const [menuAnchorEl, setMenuAnchorEl] = useState<HTMLElement | null>(null);
  const [menuLead, setMenuLead] = useState<AugmisBusinessLead | null>(null);

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [detailTab, setDetailTab] = useState<DetailTabValue>("overview");
  const [selectedLead, setSelectedLead] = useState<AugmisBusinessLead | null>(null);
  const [selectedLeadActivities, setSelectedLeadActivities] = useState<AugmisBusinessActivity[]>([]);
  const [selectedLeadTasks, setSelectedLeadTasks] = useState<AugmisBusinessTask[]>([]);
  const [selectedLeadReplies, setSelectedLeadReplies] = useState<AugmisBusinessReply[]>([]);
  const [outreachOpen, setOutreachOpen] = useState(false);
  const [miniSolutionOpen, setMiniSolutionOpen] = useState(false);

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editDialogSaving, setEditDialogSaving] = useState(false);
  const [editDialogError, setEditDialogError] = useState("");
  const [editFieldErrors, setEditFieldErrors] = useState<Record<string, string>>({});
  const [editLeadId, setEditLeadId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<LeadEditFormState>(DEFAULT_EDIT_FORM);
  const [editContacts, setEditContacts] = useState<AugmisBusinessContact[]>([]);

  const [stageDialogOpen, setStageDialogOpen] = useState(false);
  const [stageDialogSaving, setStageDialogSaving] = useState(false);
  const [stageDialogError, setStageDialogError] = useState("");
  const [stageLead, setStageLead] = useState<AugmisBusinessLead | null>(null);
  const [targetStage, setTargetStage] = useState("qualified");

  const [activityDialogOpen, setActivityDialogOpen] = useState(false);
  const [activityDialogSaving, setActivityDialogSaving] = useState(false);
  const [activityDialogError, setActivityDialogError] = useState("");
  const [activityFieldErrors, setActivityFieldErrors] = useState<Record<string, string>>({});
  const [activityLead, setActivityLead] = useState<AugmisBusinessLead | null>(null);
  const [activityContacts, setActivityContacts] = useState<AugmisBusinessContact[]>([]);
  const [activityForm, setActivityForm] = useState<ActivityFormState>(DEFAULT_ACTIVITY_FORM);

  const [toastOpen, setToastOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastSeverity, setToastSeverity] = useState<ToastSeverity>("success");

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(0);
    }, 300);
    return () => window.clearTimeout(timeout);
  }, [searchInput]);

  useEffect(() => {
    if (!canRead) return;
    let active = true;

    async function loadData() {
      setLoading(true);
      setError("");
      try {
        const [dashboardResult, leadsResult, prospectsResult, experienceResult] =
          await Promise.all([
            getAugmisBusinessDashboard(),
            listAugmisBusinessLeads({
              page: isPipeline ? 1 : page + 1,
              page_size: isPipeline ? 100 : pageSize,
              search: search || undefined,
              stage: stageFilter === "all" ? undefined : stageFilter,
              status: statusFilter === "all" ? undefined : statusFilter,
              prospect_id: prospectFilter === "all" ? undefined : prospectFilter,
            }),
            listAugmisBusinessProspects({ page: 1, page_size: 100, status: "active" }),
            listAugmisBusinessExperienceItems(),
          ]);

        if (!active) return;

        setDashboard(dashboardResult.data);
        setLeads(leadsResult.data || []);
        setTotal(leadsResult.pagination?.total || 0);
        setProspects(prospectsResult.data || []);
        setExperienceItems(experienceResult.data || []);

        const metaEntries = await Promise.all(
          (leadsResult.data || []).map(async (lead) => {
            try {
              const [activitiesResult, tasksResult] = await Promise.all([
                listAugmisBusinessLeadActivities(lead.id),
                listAugmisBusinessLeadTasks(lead.id),
              ]);
              return [
                lead.id,
                {
                  activities: activitiesResult.data || [],
                  tasks: tasksResult.data || [],
                  error: null,
                },
              ] as const;
            } catch (metaError) {
              return [
                lead.id,
                {
                  activities: [],
                  tasks: [],
                  error: parseApiValidationError(
                    metaError,
                    "Unable to load lead activity and task metadata."
                  ).message,
                },
              ] as const;
            }
          })
        );

        if (!active) return;
        setLeadMeta(Object.fromEntries(metaEntries));
      } catch (loadError) {
        if (!active) return;
        setError(
          parseApiValidationError(loadError, "Unable to load lead workspace data.").message
        );
        setDashboard(null);
        setLeads([]);
        setLeadMeta({});
        setTotal(0);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadData();
    return () => {
      active = false;
    };
  }, [canRead, isPipeline, page, pageSize, prospectFilter, refreshTick, search, stageFilter, statusFilter]);

  const stageCounts = useMemo(() => mapStageCounts(dashboard), [dashboard]);

  const leadsByStage = useMemo(() => {
    const grouped: Record<string, AugmisBusinessLead[]> = {};
    for (const stage of [...ACTIVE_STAGE_ORDER, ...TERMINAL_STAGE_ORDER]) {
      grouped[stage] = [];
    }
    for (const lead of leads) {
      if (!grouped[lead.lead_stage]) {
        grouped[lead.lead_stage] = [];
      }
      grouped[lead.lead_stage].push(lead);
    }
    return grouped;
  }, [leads]);

  function showToast(message: string, severity: ToastSeverity) {
    setToastMessage(message);
    setToastSeverity(severity);
    setToastOpen(true);
  }

  function closeActionMenu() {
    setMenuAnchorEl(null);
    setMenuLead(null);
  }

  function openActionMenu(
    event: React.MouseEvent<HTMLElement>,
    lead: AugmisBusinessLead
  ) {
    setMenuAnchorEl(event.currentTarget);
    setMenuLead(lead);
  }

  function openOutreachWorkspace(lead: AugmisBusinessLead) {
    closeActionMenu();
    setSelectedLead(lead);
    setOutreachOpen(true);
  }

  function openMiniSolutionWorkspace(lead: AugmisBusinessLead) {
    closeActionMenu();
    setSelectedLead(lead);
    setMiniSolutionOpen(true);
  }

  async function openLeadDetail(leadId: string) {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailError("");
    setDetailTab("overview");
    try {
      const [leadResult, activitiesResult, tasksResult, repliesResult] = await Promise.all([
        getAugmisBusinessLead(leadId),
        listAugmisBusinessLeadActivities(leadId),
        listAugmisBusinessLeadTasks(leadId),
        listAugmisBusinessReplies({ lead_id: leadId, page: 1, page_size: 5 }),
      ]);
      const lead = leadResult.data;
      setSelectedLead(lead);
      setSelectedLeadActivities(activitiesResult.data || []);
      setSelectedLeadTasks(tasksResult.data || []);
      setSelectedLeadReplies(repliesResult.data || []);
    } catch (drawerError) {
      setDetailError(
        parseApiValidationError(drawerError, "Unable to load lead details.").message
      );
    } finally {
      setDetailLoading(false);
    }
  }

  async function refreshLeadData(leadId: string) {
    setRefreshTick((value) => value + 1);
    if (selectedLead?.id === leadId) {
      await openLeadDetail(leadId);
    }
  }

  async function openEditLeadDialog(lead: AugmisBusinessLead) {
    closeActionMenu();
    setEditLeadId(lead.id);
    setEditDialogOpen(true);
    setEditDialogSaving(true);
    setEditDialogError("");
    setEditFieldErrors({});
    try {
      const result = await getAugmisBusinessLead(lead.id);
      setEditForm(leadToEditForm(result.data));
      if (result.data.prospect_id) {
        const contactsResult = await getAugmisBusinessProspectContacts(result.data.prospect_id);
        setEditContacts(contactsResult.data || []);
      } else {
        setEditContacts([]);
      }
    } catch (dialogError) {
      setEditDialogError(
        parseApiValidationError(dialogError, "Unable to load lead for editing.").message
      );
    } finally {
      setEditDialogSaving(false);
    }
  }

  function closeEditLeadDialog() {
    if (editDialogSaving) return;
    setEditDialogOpen(false);
    setEditDialogError("");
    setEditFieldErrors({});
    setEditLeadId(null);
    setEditContacts([]);
  }

  async function handleSaveLead() {
    if (!editLeadId) return;
    const fieldErrors: Record<string, string> = {};
    if (!editForm.title.trim()) {
      fieldErrors.title = "Lead title is required.";
    }
    const probability = normalizeOptionalNumber(editForm.probability_pct);
    if (probability != null && (probability < 0 || probability > 100)) {
      fieldErrors.probability_pct = "Probability must be between 0 and 100.";
    }
    if (Object.keys(fieldErrors).length > 0) {
      setEditFieldErrors(fieldErrors);
      setEditDialogError("Please correct the highlighted fields.");
      return;
    }

    setEditDialogSaving(true);
    setEditDialogError("");
    setEditFieldErrors({});
    try {
      const result = await updateAugmisBusinessLead(editLeadId, editFormToPayload(editForm));
      closeEditLeadDialog();
      await refreshLeadData(editLeadId);
      showToast(`Lead updated: ${result.data.title}.`, "success");
    } catch (saveError) {
      const parsed = parseApiValidationError(saveError, "Unable to update lead.");
      setEditDialogError(parsed.message);
      setEditFieldErrors(parsed.fieldErrors);
    } finally {
      setEditDialogSaving(false);
    }
  }

  function updateEditField<K extends keyof LeadEditFormState>(
    field: K,
    value: LeadEditFormState[K]
  ) {
    setEditFieldErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
    setEditForm((current) => ({ ...current, [field]: value }));
  }

  function openStageDialog(lead: AugmisBusinessLead) {
    closeActionMenu();
    setStageLead(lead);
    setTargetStage(lead.lead_stage === "new" ? "qualified" : lead.lead_stage);
    setStageDialogError("");
    setStageDialogOpen(true);
  }

  function closeStageDialog() {
    if (stageDialogSaving) return;
    setStageDialogOpen(false);
    setStageDialogError("");
  }

  async function handleChangeStage() {
    if (!stageLead) return;
    setStageDialogSaving(true);
    setStageDialogError("");
    try {
      const result = await updateAugmisBusinessLeadStage(stageLead.id, {
        lead_stage: targetStage,
      });
      closeStageDialog();
      await refreshLeadData(stageLead.id);
      showToast(
        `Lead moved to ${formatStageLabel(result.data.lead_stage)}.`,
        "success"
      );
    } catch (updateError) {
      setStageDialogError(
        parseApiValidationError(updateError, "Unable to update lead stage.").message
      );
    } finally {
      setStageDialogSaving(false);
    }
  }

  async function openActivityDialog(lead: AugmisBusinessLead) {
    closeActionMenu();
    setActivityLead(lead);
    setActivityDialogOpen(true);
    setActivityDialogError("");
    setActivityFieldErrors({});
    setActivityForm({
      ...DEFAULT_ACTIVITY_FORM,
      subject: `Manual activity for ${lead.title}`,
      contact_id: lead.primary_contact_id || "",
    });
    try {
      if (lead.prospect_id) {
        const contactsResult = await getAugmisBusinessProspectContacts(lead.prospect_id);
        setActivityContacts(contactsResult.data || []);
      } else {
        setActivityContacts([]);
      }
    } catch {
      setActivityContacts([]);
    }
  }

  function closeActivityDialog() {
    if (activityDialogSaving) return;
    setActivityDialogOpen(false);
    setActivityDialogError("");
    setActivityFieldErrors({});
  }

  function updateActivityField<K extends keyof ActivityFormState>(
    field: K,
    value: ActivityFormState[K]
  ) {
    setActivityFieldErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
    setActivityForm((current) => ({ ...current, [field]: value }));
  }

  async function handleCreateActivity() {
    if (!activityLead) return;
    const fieldErrors: Record<string, string> = {};
    if (!activityForm.activity_type.trim()) {
      fieldErrors.activity_type = "Activity type is required.";
    }
    if (!activityForm.subject.trim()) {
      fieldErrors.subject = "Subject is required.";
    }
    if (Object.keys(fieldErrors).length > 0) {
      setActivityFieldErrors(fieldErrors);
      setActivityDialogError("Please correct the highlighted fields.");
      return;
    }

    setActivityDialogSaving(true);
    setActivityDialogError("");
    setActivityFieldErrors({});
    try {
      const result = await createAugmisBusinessLeadActivity(
        activityLead.id,
        activityFormToPayload(activityForm)
      );
      closeActivityDialog();
      await refreshLeadData(activityLead.id);
      showToast(`Activity added: ${result.data.subject}.`, "success");
    } catch (saveError) {
      const parsed = parseApiValidationError(saveError, "Unable to create activity.");
      setActivityDialogError(parsed.message);
      setActivityFieldErrors(parsed.fieldErrors);
    } finally {
      setActivityDialogSaving(false);
    }
  }

  if (!canRead) {
    return (
      <BusinessPageFrame
        title={isPipeline ? "Pipeline" : "Leads"}
        description="This workspace requires business development read access."
      >
        <Alert severity="warning">
          You do not currently have permission to view tenant lead records.
        </Alert>
      </BusinessPageFrame>
    );
  }

  return (
    <>
      <BusinessPageFrame
        title={isPipeline ? "Pipeline" : "Leads"}
        description={
          isPipeline
            ? "Track live tenant leads through the actual backend sales stages and update stage progression directly from the pipeline board."
            : "Review live converted leads, real pipeline metrics, manual activities, and lead-scoped follow-up tasks."
        }
      >
        <Stack spacing={2.25}>
          <Paper
            elevation={0}
            sx={{
              borderRadius: "10px",
              border: "1px solid #D9E2EC",
              overflow: "hidden",
            }}
          >
            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={1.5}
              sx={{ p: 2, borderBottom: "1px solid #E2E8F0", bgcolor: "#F8FAFC" }}
            >
              <Paper
                elevation={0}
                sx={{ flex: 1, p: 1.75, borderRadius: "8px", border: "1px solid #E2E8F0" }}
              >
                <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: ".05em" }}>
                  Open Leads
                </Typography>
                <Typography sx={{ mt: 0.6, fontSize: 28, fontWeight: 700, color: "#0F172A" }}>
                  {dashboard?.open_leads ?? 0}
                </Typography>
              </Paper>
              <Paper
                elevation={0}
                sx={{ flex: 1, p: 1.75, borderRadius: "8px", border: "1px solid #E2E8F0" }}
              >
                <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: ".05em" }}>
                  Pipeline Value
                </Typography>
                <Typography sx={{ mt: 0.6, fontSize: 28, fontWeight: 700, color: "#0F172A" }}>
                  {formatCurrency(dashboard?.pipeline_value ?? 0)}
                </Typography>
              </Paper>
              <Paper
                elevation={0}
                sx={{ flex: 1, p: 1.75, borderRadius: "8px", border: "1px solid #E2E8F0" }}
              >
                <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: ".05em" }}>
                  Weighted Pipeline
                </Typography>
                <Typography sx={{ mt: 0.6, fontSize: 28, fontWeight: 700, color: "#0F172A" }}>
                  {formatCurrency(dashboard?.weighted_pipeline_value ?? 0)}
                </Typography>
              </Paper>
              <Paper
                elevation={0}
                sx={{ flex: 1, p: 1.75, borderRadius: "8px", border: "1px solid #E2E8F0" }}
              >
                <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: ".05em" }}>
                  Due / Overdue
                </Typography>
                <Typography sx={{ mt: 0.6, fontSize: 28, fontWeight: 700, color: "#0F172A" }}>
                  {(dashboard?.tasks_due_today ?? 0) + (dashboard?.overdue_tasks ?? 0)}
                </Typography>
                <Typography sx={{ mt: 0.25, color: "#64748B", fontSize: 12.5 }}>
                  {dashboard?.tasks_due_today ?? 0} due today • {dashboard?.overdue_tasks ?? 0} overdue
                </Typography>
              </Paper>
              <Paper
                elevation={0}
                sx={{ flex: 1, p: 1.75, borderRadius: "8px", border: "1px solid #E2E8F0" }}
              >
                <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: ".05em" }}>
                  Proposal / Negotiation
                </Typography>
                <Typography sx={{ mt: 0.6, fontSize: 28, fontWeight: 700, color: "#0F172A" }}>
                  {(stageCounts.get("proposal") ?? 0) + (stageCounts.get("negotiation") ?? 0)}
                </Typography>
              </Paper>
            </Stack>

            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={1.25}
              sx={{ p: 2, alignItems: { md: "center" } }}
            >
              <AdminFormTextField
                label="Search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                fieldSx={{ minWidth: { xs: "100%", md: 320 } }}
                placeholder="Search lead title"
                slotProps={{
                  input: {
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchRoundedIcon fontSize="small" sx={{ color: "#64748B" }} />
                      </InputAdornment>
                    ),
                  },
                }}
              />
              <AdminFormTextField
                select
                label="Stage"
                value={stageFilter}
                onChange={(event) => {
                  setStageFilter(event.target.value);
                  setPage(0);
                }}
                fieldSx={{ minWidth: { xs: "100%", md: 180 } }}
              >
                <MenuItem value="all">All stages</MenuItem>
                {[...ACTIVE_STAGE_ORDER, ...TERMINAL_STAGE_ORDER].map((stage) => (
                  <MenuItem key={stage} value={stage}>
                    {formatStageLabel(stage)}
                  </MenuItem>
                ))}
              </AdminFormTextField>
              <AdminFormTextField
                select
                label="Status"
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value);
                  setPage(0);
                }}
                fieldSx={{ minWidth: { xs: "100%", md: 180 } }}
              >
                <MenuItem value="all">All statuses</MenuItem>
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="won">Won</MenuItem>
                <MenuItem value="lost">Lost</MenuItem>
                <MenuItem value="archived">Archived</MenuItem>
              </AdminFormTextField>
              <AdminFormTextField
                select
                label="Prospect"
                value={prospectFilter}
                onChange={(event) => {
                  setProspectFilter(event.target.value);
                  setPage(0);
                }}
                fieldSx={{ minWidth: { xs: "100%", md: 220 } }}
              >
                <MenuItem value="all">All prospects</MenuItem>
                {prospects.map((prospect) => (
                  <MenuItem key={prospect.id} value={prospect.id}>
                    {prospect.organization_name}
                  </MenuItem>
                ))}
              </AdminFormTextField>
              <Button
                variant="outlined"
                startIcon={<RefreshRoundedIcon />}
                onClick={() => setRefreshTick((value) => value + 1)}
                sx={{ textTransform: "none", borderRadius: "8px", alignSelf: { xs: "stretch", md: "flex-end" } }}
              >
                Refresh
              </Button>
            </Stack>

            <Box sx={{ px: 2, pb: 1.5 }}>
              <Alert severity="info">
                Supported backend filters are search, stage, status, and prospect. Priority,
                due-date, and owner filters are not currently exposed server-side.
              </Alert>
            </Box>

            {loading ? (
              <Stack sx={{ minHeight: 280, alignItems: "center", justifyContent: "center" }} spacing={1.5}>
                <CircularProgress />
                <Typography sx={{ color: "#475569" }}>
                  {isPipeline ? "Loading pipeline..." : "Loading leads..."}
                </Typography>
              </Stack>
            ) : error ? (
              <Box sx={{ p: 2 }}>
                <Alert severity="error">{error}</Alert>
              </Box>
            ) : leads.length === 0 ? (
              <Box sx={{ p: 2 }}>
                <EmptyPanel
                  title={isPipeline ? "No pipeline leads found" : "No leads found"}
                  description="No live lead records match the current filters."
                />
              </Box>
            ) : isPipeline ? (
              <Box sx={{ p: 2, overflowX: "auto" }}>
                <Stack direction="row" spacing={1.5} sx={{ minWidth: 1560, alignItems: "flex-start" }}>
                  {PIPELINE_STAGE_ORDER.map((stage) => (
                    <Paper
                      key={stage}
                      elevation={0}
                      sx={{
                        width: 260,
                        flexShrink: 0,
                        borderRadius: "8px",
                        border: "1px solid #E2E8F0",
                        overflow: "hidden",
                      }}
                    >
                      <Box
                        sx={{
                          px: 1.5,
                          py: 1.2,
                          background:
                            stage === "closed_won"
                              ? "linear-gradient(90deg, #DCFCE7 0%, #F8FAFC 100%)"
                              : stage === "closed_lost"
                                ? "linear-gradient(90deg, #FEE2E2 0%, #F8FAFC 100%)"
                                : "linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)",
                          borderBottom: "1px solid #E2E8F0",
                        }}
                      >
                        <Stack direction="row" spacing={1} sx={{ alignItems: "center", justifyContent: "space-between" }}>
                          <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                            {formatStageLabel(stage)}
                          </Typography>
                          <Chip size="small" label={stageCounts.get(stage) ?? 0} />
                        </Stack>
                      </Box>
                      <Stack spacing={1} sx={{ p: 1.25, minHeight: 220 }}>
                        {leadsByStage[stage]?.length ? (
                          leadsByStage[stage].map((lead) => {
                            const meta = leadMeta[lead.id];
                            const nextTask = findNextOpenTask(meta?.tasks || []);
                            return (
                              <Paper
                                key={lead.id}
                                elevation={0}
                                sx={{
                                  p: 1.25,
                                  borderRadius: "8px",
                                  border: "1px solid #D9E2EC",
                                  bgcolor: "#FFFFFF",
                                }}
                              >
                                <Stack spacing={0.9}>
                                  <Button
                                    onClick={() => void openLeadDetail(lead.id)}
                                    sx={{
                                      px: 0,
                                      py: 0,
                                      minWidth: 0,
                                      justifyContent: "flex-start",
                                      textTransform: "none",
                                      fontWeight: 700,
                                      color: "#0F172A",
                                    }}
                                  >
                                    {lead.title}
                                  </Button>
                                  <Typography sx={{ color: "#475569", fontSize: 12.5 }}>
                                    {lead.prospect?.organization_name || "Prospect not available"}
                                  </Typography>
                                  <Typography sx={{ color: "#64748B", fontSize: 12.5 }}>
                                    {getContactDisplayName(lead.primary_contact)}
                                  </Typography>
                                  <Stack direction="row" spacing={0.75} sx={{ flexWrap: "wrap" }}>
                                    <Chip
                                      size="small"
                                      label={lead.priority}
                                      sx={{ textTransform: "capitalize", border: "1px solid", ...getPriorityChip(lead.priority) }}
                                    />
                                    <Chip
                                      size="small"
                                      label={lead.lead_status}
                                      sx={{ textTransform: "capitalize", border: "1px solid", ...getStatusChip(lead.lead_status) }}
                                    />
                                  </Stack>
                                  <Typography sx={{ color: "#0F172A", fontSize: 12.5 }}>
                                    {formatCurrency(lead.estimated_value, lead.opportunity?.estimated_currency)}
                                  </Typography>
                                  <Typography sx={{ color: "#475569", fontSize: 12.5 }}>
                                    Probability: {lead.probability_pct == null ? "Not available" : `${lead.probability_pct}%`}
                                  </Typography>
                                  <Typography sx={{ color: getDueDateColor(nextTask?.due_at || null), fontSize: 12.5 }}>
                                    Due: {formatDateTime(nextTask?.due_at || null)}
                                  </Typography>
                                  <Typography sx={{ color: "#475569", fontSize: 12.5 }}>
                                    Next: {nextTask?.title || "Not available"}
                                  </Typography>
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    startIcon={<SwapHorizOutlinedIcon />}
                                    onClick={() => openStageDialog(lead)}
                                    disabled={!canUpdate}
                                    sx={{ textTransform: "none", borderRadius: "8px", alignSelf: "flex-start" }}
                                  >
                                    Change Stage
                                  </Button>
                                </Stack>
                              </Paper>
                            );
                          })
                        ) : (
                          <Typography sx={{ color: "#64748B", fontSize: 12.5 }}>
                            No leads in this stage.
                          </Typography>
                        )}
                      </Stack>
                    </Paper>
                  ))}
                </Stack>
              </Box>
            ) : (
              <>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Lead</TableCell>
                      <TableCell>Prospect</TableCell>
                      <TableCell>Primary Buyer / Contact</TableCell>
                      <TableCell>Source Opportunity</TableCell>
                      <TableCell>Pipeline Stage</TableCell>
                      <TableCell>Priority</TableCell>
                      <TableCell>Estimated Value</TableCell>
                      <TableCell>Probability</TableCell>
                      <TableCell>Due Date</TableCell>
                      <TableCell>Next Action</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Last Activity</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {leads.map((lead) => {
                      const meta = leadMeta[lead.id];
                      const nextTask = findNextOpenTask(meta?.tasks || []);
                      const lastActivity = meta?.activities?.[0] || null;
                      return (
                        <TableRow key={lead.id} hover>
                          <TableCell sx={{ minWidth: 180 }}>
                            <Button
                              onClick={() => void openLeadDetail(lead.id)}
                              sx={{
                                px: 0,
                                py: 0,
                                minWidth: 0,
                                justifyContent: "flex-start",
                                textTransform: "none",
                                fontWeight: 700,
                                color: "#0F172A",
                              }}
                            >
                              {lead.title}
                            </Button>
                          </TableCell>
                          <TableCell>{lead.prospect?.organization_name || "Not available"}</TableCell>
                          <TableCell>{getContactDisplayName(lead.primary_contact)}</TableCell>
                          <TableCell>{lead.opportunity?.title || "Not available"}</TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={formatStageLabel(lead.lead_stage)}
                              sx={{ textTransform: "capitalize", border: "1px solid", ...getStageChip(lead.lead_stage) }}
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={lead.priority}
                              sx={{ textTransform: "capitalize", border: "1px solid", ...getPriorityChip(lead.priority) }}
                            />
                          </TableCell>
                          <TableCell>{formatCurrency(lead.estimated_value, lead.opportunity?.estimated_currency)}</TableCell>
                          <TableCell>
                            {lead.probability_pct == null ? "Not available" : `${lead.probability_pct}%`}
                          </TableCell>
                          <TableCell sx={{ color: getDueDateColor(nextTask?.due_at || null) }}>
                            {formatDateTime(nextTask?.due_at || null)}
                          </TableCell>
                          <TableCell>{nextTask?.title || "Not available"}</TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={lead.lead_status}
                              sx={{ textTransform: "capitalize", border: "1px solid", ...getStatusChip(lead.lead_status) }}
                            />
                          </TableCell>
                          <TableCell>{getActivitySummary(lastActivity)}</TableCell>
                          <TableCell align="right">
                            <Tooltip title="Actions">
                              <span>
                                <IconButton size="small" onClick={(event) => openActionMenu(event, lead)}>
                                  <MoreVertRoundedIcon fontSize="small" />
                                </IconButton>
                              </span>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>

                <TablePagination
                  component="div"
                  count={total}
                  page={page}
                  onPageChange={(_, nextPage) => setPage(nextPage)}
                  rowsPerPage={pageSize}
                  onRowsPerPageChange={(event) => {
                    setPageSize(Number(event.target.value));
                    setPage(0);
                  }}
                  rowsPerPageOptions={[10, 25, 50]}
                />
              </>
            )}
          </Paper>
        </Stack>
      </BusinessPageFrame>

      <Menu anchorEl={menuAnchorEl} open={Boolean(menuAnchorEl)} onClose={closeActionMenu}>
        <MenuItem
          onClick={() => {
            if (menuLead) {
              openOutreachWorkspace(menuLead);
            }
          }}
          disabled={!canOutreach}
        >
          <MarkEmailReadOutlinedIcon fontSize="small" style={{ marginRight: 10, color: "#2563EB" }} />
          Generate Outreach
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (menuLead) {
              openMiniSolutionWorkspace(menuLead);
            }
          }}
          disabled={!canOutreach}
        >
          <LightbulbOutlinedIcon fontSize="small" style={{ marginRight: 10, color: "#0F766E" }} />
          Generate Mini Solution
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (menuLead) {
              void openLeadDetail(menuLead.id);
            }
            closeActionMenu();
          }}
        >
          <VisibilityOutlined fontSize="small" style={{ marginRight: 10 }} />
          View Details
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (menuLead) {
              void openEditLeadDialog(menuLead);
            }
          }}
          disabled={!canUpdate}
        >
          <EditOutlined fontSize="small" style={{ marginRight: 10 }} />
          Edit Lead
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (menuLead) {
              openStageDialog(menuLead);
            }
          }}
          disabled={!canUpdate}
        >
          <SwapHorizOutlinedIcon fontSize="small" style={{ marginRight: 10 }} />
          Change Stage
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (menuLead) {
              void openActivityDialog(menuLead);
            }
          }}
          disabled={!canCreate}
        >
          <AddCommentOutlinedIcon fontSize="small" style={{ marginRight: 10, color: "#2563EB" }} />
          Add Activity
        </MenuItem>
      </Menu>

      <AdminFormDialog
        open={editDialogOpen}
        onClose={closeEditLeadDialog}
        title="Edit Lead"
        maxWidth={780}
        stackSx={{ maxWidth: 620 }}
        actions={
          <>
            <Button onClick={closeEditLeadDialog} disabled={editDialogSaving} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleSaveLead}
              disabled={editDialogSaving}
              sx={{ textTransform: "none", fontWeight: 700, borderRadius: "8px", bgcolor: "#2563EB", "&:hover": { bgcolor: "#1D4ED8" } }}
            >
              {editDialogSaving ? "Saving..." : "Save Lead"}
            </Button>
          </>
        }
      >
        {editDialogError ? <Alert severity="error">{editDialogError}</Alert> : null}
        <Box sx={{ display: "grid", gap: 1.15, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
          <AdminFormTextField label="Lead Title" value={editForm.title} onChange={(event) => updateEditField("title", event.target.value)} required error={Boolean(editFieldErrors.title)} helperText={editFieldErrors.title} />
          <AdminFormTextField select label="Primary Contact" value={editForm.primary_contact_id} onChange={(event) => updateEditField("primary_contact_id", event.target.value)}>
            <MenuItem value="">No primary contact</MenuItem>
            {editContacts.map((contact) => (
              <MenuItem key={contact.id} value={contact.id}>
                {getContactDisplayName(contact)}
              </MenuItem>
            ))}
          </AdminFormTextField>
          <AdminFormTextField select label="Priority" value={editForm.priority} onChange={(event) => updateEditField("priority", event.target.value)}>
            <MenuItem value="high">High</MenuItem>
            <MenuItem value="medium">Medium</MenuItem>
            <MenuItem value="low">Low</MenuItem>
          </AdminFormTextField>
          <AdminFormTextField select label="Lead Status" value={editForm.lead_status} onChange={(event) => updateEditField("lead_status", event.target.value)}>
            <MenuItem value="active">Active</MenuItem>
            <MenuItem value="won">Won</MenuItem>
            <MenuItem value="lost">Lost</MenuItem>
            <MenuItem value="archived">Archived</MenuItem>
          </AdminFormTextField>
          <AdminFormTextField label="Estimated Value" type="number" value={editForm.estimated_value} onChange={(event) => updateEditField("estimated_value", event.target.value)} />
          <AdminFormTextField label="Probability Percent" type="number" value={editForm.probability_pct} onChange={(event) => updateEditField("probability_pct", event.target.value)} error={Boolean(editFieldErrors.probability_pct)} helperText={editFieldErrors.probability_pct} />
          <Box sx={{ gridColumn: "1 / -1" }}>
            <AdminFormTextField label="Notes" multiline minRows={4} value={editForm.notes} onChange={(event) => updateEditField("notes", event.target.value)} />
          </Box>
        </Box>
      </AdminFormDialog>

      <AdminFormDialog
        open={stageDialogOpen}
        onClose={closeStageDialog}
        title="Change Lead Stage"
        maxWidth={560}
        actions={
          <>
            <Button onClick={closeStageDialog} disabled={stageDialogSaving} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleChangeStage}
              disabled={stageDialogSaving}
              sx={{ textTransform: "none", fontWeight: 700, borderRadius: "8px", bgcolor: "#2563EB", "&:hover": { bgcolor: "#1D4ED8" } }}
            >
              {stageDialogSaving ? "Saving..." : "Update Stage"}
            </Button>
          </>
        }
      >
        {stageDialogError ? <Alert severity="error">{stageDialogError}</Alert> : null}
        <Typography sx={{ color: "#475569" }}>
          {stageLead ? `Current stage: ${formatStageLabel(stageLead.lead_stage)}.` : "Select the next stage for this lead."}
        </Typography>
        {(targetStage === "closed_won" || targetStage === "closed_lost") && stageLead ? (
          <Alert severity={targetStage === "closed_won" ? "success" : "warning"}>
            {targetStage === "closed_won"
              ? "This will mark the lead as won."
              : "This will mark the lead as lost."}
          </Alert>
        ) : null}
        <AdminFormTextField
          select
          label="New Stage"
          value={targetStage}
          onChange={(event) => setTargetStage(event.target.value)}
        >
          {[...ACTIVE_STAGE_ORDER, ...TERMINAL_STAGE_ORDER].map((stage) => (
            <MenuItem key={stage} value={stage}>
              {formatStageLabel(stage)}
            </MenuItem>
          ))}
        </AdminFormTextField>
      </AdminFormDialog>

      <AdminFormDialog
        open={activityDialogOpen}
        onClose={closeActivityDialog}
        title="Add Manual Activity"
        maxWidth={720}
        stackSx={{ maxWidth: 580 }}
        actions={
          <>
            <Button onClick={closeActivityDialog} disabled={activityDialogSaving} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleCreateActivity}
              disabled={activityDialogSaving}
              sx={{ textTransform: "none", fontWeight: 700, borderRadius: "8px", bgcolor: "#2563EB", "&:hover": { bgcolor: "#1D4ED8" } }}
            >
              {activityDialogSaving ? "Saving..." : "Add Activity"}
            </Button>
          </>
        }
      >
        {activityDialogError ? <Alert severity="error">{activityDialogError}</Alert> : null}
        <Box sx={{ display: "grid", gap: 1.15, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
          <AdminFormTextField select label="Activity Type" value={activityForm.activity_type} onChange={(event) => updateActivityField("activity_type", event.target.value)} required error={Boolean(activityFieldErrors.activity_type)} helperText={activityFieldErrors.activity_type}>
            <MenuItem value="manual_activity">Manual Activity</MenuItem>
            <MenuItem value="note_added">Note Added</MenuItem>
            <MenuItem value="contact_attempt">Contact Attempt</MenuItem>
            <MenuItem value="meeting">Meeting</MenuItem>
            <MenuItem value="follow_up">Follow Up</MenuItem>
          </AdminFormTextField>
          <AdminFormTextField label="Subject" value={activityForm.subject} onChange={(event) => updateActivityField("subject", event.target.value)} required error={Boolean(activityFieldErrors.subject)} helperText={activityFieldErrors.subject} />
          <AdminFormTextField label="Activity Timestamp" type="datetime-local" value={activityForm.activity_at} onChange={(event) => updateActivityField("activity_at", event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
          <AdminFormTextField select label="Contact" value={activityForm.contact_id} onChange={(event) => updateActivityField("contact_id", event.target.value)}>
            <MenuItem value="">No linked contact</MenuItem>
            {activityContacts.map((contact) => (
              <MenuItem key={contact.id} value={contact.id}>
                {getContactDisplayName(contact)}
              </MenuItem>
            ))}
          </AdminFormTextField>
          <AdminFormTextField label="Direction" value={activityForm.direction} onChange={(event) => updateActivityField("direction", event.target.value)} />
          <AdminFormTextField label="Outcome" value={activityForm.outcome} onChange={(event) => updateActivityField("outcome", event.target.value)} />
          <Box sx={{ gridColumn: "1 / -1" }}>
            <AdminFormTextField label="Description" multiline minRows={4} value={activityForm.description} onChange={(event) => updateActivityField("description", event.target.value)} />
          </Box>
        </Box>
      </AdminFormDialog>

      <Drawer
        anchor="right"
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        slotProps={{
          paper: {
            sx: {
              width: { xs: "100%", md: 760 },
              bgcolor: "#F8FAFC",
            },
          },
        }}
      >
        <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
          <Box
            sx={{
              px: 2.5,
              py: 2,
              borderBottom: "1px solid #E2E8F0",
              background: "linear-gradient(135deg, rgba(13,45,78,0.98) 0%, rgba(25,93,161,0.95) 58%, rgba(222,239,255,0.92) 100%)",
              color: "#F8FAFC",
            }}
          >
            <Stack direction="row" spacing={1.5} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  Lead Details
                </Typography>
                <Typography sx={{ mt: 0.6, color: "rgba(248,250,252,0.88)" }}>
                  Review the live tenant lead, related prospect and opportunity context, manual activity history, and open task trail.
                </Typography>
              </Box>
              <IconButton onClick={() => setDetailOpen(false)} sx={{ color: "#F8FAFC" }}>
                <CloseIcon />
              </IconButton>
            </Stack>
            <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: "wrap" }}>
              <Button
                variant="contained"
                startIcon={<MarkEmailReadOutlinedIcon />}
                disabled={!selectedLead || !canOutreach}
                onClick={() => selectedLead && openOutreachWorkspace(selectedLead)}
                sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "rgba(37,99,235,0.82)", color: "#FFFFFF", boxShadow: "none" }}
              >
                Generate Outreach
              </Button>
              <Button
                variant="contained"
                startIcon={<LightbulbOutlinedIcon />}
                disabled={!selectedLead || !canOutreach}
                onClick={() => selectedLead && openMiniSolutionWorkspace(selectedLead)}
                sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "rgba(15,118,110,0.82)", color: "#FFFFFF", boxShadow: "none" }}
              >
                Generate Mini Solution
              </Button>
              <Button
                variant="contained"
                startIcon={<EditOutlined />}
                disabled={!selectedLead || !canUpdate}
                onClick={() => selectedLead && void openEditLeadDialog(selectedLead)}
                sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "rgba(255,255,255,0.16)", color: "#FFFFFF", boxShadow: "none" }}
              >
                Edit
              </Button>
              <Button
                variant="contained"
                startIcon={<SwapHorizOutlinedIcon />}
                disabled={!selectedLead || !canUpdate}
                onClick={() => selectedLead && openStageDialog(selectedLead)}
                sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "rgba(37,99,235,0.78)", color: "#FFFFFF", boxShadow: "none" }}
              >
                Change Stage
              </Button>
              <Button
                variant="contained"
                startIcon={<AddCommentOutlinedIcon />}
                disabled={!selectedLead || !canCreate}
                onClick={() => selectedLead && void openActivityDialog(selectedLead)}
                sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "rgba(12,148,136,0.72)", color: "#FFFFFF", boxShadow: "none" }}
              >
                Add Activity
              </Button>
              <Button
                variant="outlined"
                onClick={() => setDetailOpen(false)}
                sx={{ textTransform: "none", borderRadius: "8px", color: "#FFFFFF", borderColor: "rgba(255,255,255,0.4)" }}
              >
                Close
              </Button>
            </Stack>
          </Box>

          <Box sx={{ borderBottom: "1px solid #E2E8F0", bgcolor: "#FFFFFF" }}>
            <Tabs
              value={detailTab}
              onChange={(_, value: DetailTabValue) => setDetailTab(value)}
              variant="scrollable"
              scrollButtons="auto"
            >
              <Tab value="overview" label="Overview" />
              <Tab value="prospect" label="Prospect & Contact" />
              <Tab value="opportunity" label="Source Opportunity" />
              <Tab value="experience" label="Experience Match" />
              <Tab value="replies" label={`Replies (${selectedLeadReplies.length})`} />
              <Tab value="activities" label={`Activities (${selectedLeadActivities.length})`} />
              <Tab value="tasks" label={`Tasks (${selectedLeadTasks.length})`} />
            </Tabs>
          </Box>

          <Box sx={{ p: 2.5, overflowY: "auto", flex: 1 }}>
            {detailLoading ? (
              <Stack sx={{ minHeight: 280, alignItems: "center", justifyContent: "center" }} spacing={1.5}>
                <CircularProgress />
                <Typography sx={{ color: "#475569" }}>Loading lead details...</Typography>
              </Stack>
            ) : detailError ? (
              <Alert severity="error">{detailError}</Alert>
            ) : selectedLead ? (
              <Stack spacing={2}>
                {detailTab === "overview" ? (
                  <>
                    <Paper elevation={0} sx={{ p: 2.25, borderRadius: "8px", border: "1px solid #D9E2EC", background: "linear-gradient(180deg, rgba(239,246,255,0.9) 0%, rgba(248,250,252,0.95) 100%)" }}>
                      <Typography variant="h5" sx={{ fontWeight: 700, color: "#0F172A" }}>
                        {selectedLead.title}
                      </Typography>
                      <Stack direction="row" spacing={1} sx={{ mt: 1.25, flexWrap: "wrap" }}>
                        <Chip size="small" label={formatStageLabel(selectedLead.lead_stage)} sx={{ textTransform: "capitalize", border: "1px solid", ...getStageChip(selectedLead.lead_stage) }} />
                        <Chip size="small" label={selectedLead.lead_status} sx={{ textTransform: "capitalize", border: "1px solid", ...getStatusChip(selectedLead.lead_status) }} />
                        <Chip size="small" label={selectedLead.priority} sx={{ textTransform: "capitalize", border: "1px solid", ...getPriorityChip(selectedLead.priority) }} />
                      </Stack>
                    </Paper>

                    <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
                      {[
                        detailField("Probability", selectedLead.probability_pct == null ? "Not available" : `${selectedLead.probability_pct}%`),
                        detailField("Estimated Value", formatCurrency(selectedLead.estimated_value, selectedLead.opportunity?.estimated_currency)),
                        detailField("Weighted Value", formatCurrency(selectedLead.weighted_value, selectedLead.opportunity?.estimated_currency)),
                        detailField("Source Name", selectedLead.source_name || "Not available"),
                        detailField("Primary Contact", getContactDisplayName(selectedLead.primary_contact)),
                        detailField("Converted At", formatDateTime(selectedLead.converted_at)),
                        detailField("Created", formatDateTime(selectedLead.created_at)),
                        detailField("Updated", formatDateTime(selectedLead.updated_at)),
                        detailField("Notes", selectedLead.notes || "Not available"),
                      ].map((item) => (
                        <DetailFieldCard key={item.label} label={item.label} value={item.value} />
                      ))}
                    </Box>
                  </>
                ) : null}

                {detailTab === "prospect" ? (
                  <SectionPanel
                    title="Prospect & Contact"
                    icon={<BadgeOutlinedIcon fontSize="small" />}
                    gradient="linear-gradient(90deg, #EDE9FE 0%, #F8FAFC 100%)"
                  >
                    <Stack spacing={2}>
                      <Box sx={{ display: "grid", gap: 1.25, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
                        <DetailFieldCard label="Organization" value={selectedLead.prospect?.organization_name || "Not available"} />
                        <DetailFieldCard label="Country" value={selectedLead.prospect?.country || "Not available"} />
                        <DetailFieldCard label="Industry" value={selectedLead.prospect?.industry || "Not available"} />
                        <DetailFieldCard label="Domain / Website" value={selectedLead.prospect?.organization_domain || selectedLead.prospect?.website_url || "Not available"} />
                      </Box>
                      <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                        <Stack spacing={1}>
                          <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                            Primary Contact
                          </Typography>
                          <Typography sx={{ color: "#0F172A" }}>
                            {getContactDisplayName(selectedLead.primary_contact)}
                          </Typography>
                          <Typography sx={{ color: "#475569" }}>
                            {selectedLead.primary_contact?.job_title || "Not available"}
                          </Typography>
                          <Stack direction="row" spacing={0.75} sx={{ flexWrap: "wrap" }}>
                            {selectedLead.primary_contact?.is_primary ? (
                              <Chip size="small" label="Primary" sx={{ bgcolor: "#DBEAFE", color: "#1D4ED8", border: "1px solid #93C5FD" }} />
                            ) : null}
                            <Chip
                              size="small"
                              label={formatStageLabel(selectedLead.primary_contact?.verification_status || "unverified")}
                              sx={{ textTransform: "capitalize", border: "1px solid", ...getVerificationChip(selectedLead.primary_contact?.verification_status) }}
                            />
                          </Stack>
                          <Box sx={{ display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
                            <DetailFieldCard label="Buyer Role" value={selectedLead.primary_contact?.buyer_role ? formatStageLabel(selectedLead.primary_contact.buyer_role) : "Not available"} />
                            <DetailFieldCard label="Email" value={selectedLead.primary_contact?.email || "Not available"} />
                            <DetailFieldCard label="Phone" value={selectedLead.primary_contact?.phone || "Not available"} />
                            <DetailFieldCard label="Department" value={selectedLead.primary_contact?.department || "Not available"} />
                          </Box>
                        </Stack>
                      </Paper>
                    </Stack>
                  </SectionPanel>
                ) : null}

                {detailTab === "opportunity" ? (
                  <SectionPanel
                    title="Source Opportunity"
                    icon={<SourceOutlinedIcon fontSize="small" />}
                    gradient="linear-gradient(90deg, #E0F2FE 0%, #F8FAFC 100%)"
                  >
                    {selectedLead.opportunity ? (
                      <Box sx={{ display: "grid", gap: 1.25, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
                        <DetailFieldCard label="Opportunity Title" value={selectedLead.opportunity.title} />
                        <DetailFieldCard label="Organization" value={selectedLead.opportunity.organization_name} />
                        <DetailFieldCard label="Source" value={selectedLead.opportunity.source_name || selectedLead.opportunity.source_type} />
                        <DetailFieldCard label="Status" value={formatStageLabel(selectedLead.opportunity.opportunity_status)} />
                        <DetailFieldCard label="Requirement Summary" value={selectedLead.opportunity.requirement_summary || "Not available"} />
                        <DetailFieldCard label="Fit Score" value={selectedLead.opportunity.fit_score == null ? "Not available" : String(selectedLead.opportunity.fit_score)} />
                        <DetailFieldCard label="Closing Date" value={formatDateTime(selectedLead.opportunity.closing_at)} />
                      </Box>
                    ) : (
                      <EmptyPanel
                        title="Source opportunity not available"
                        description="This lead does not currently expose a source opportunity payload."
                      />
                    )}
                  </SectionPanel>
                ) : null}

                {detailTab === "experience" ? (
                  <SectionPanel
                    title="Experience Match"
                    icon={<InsightsOutlinedIcon fontSize="small" />}
                    gradient="linear-gradient(90deg, #DCFCE7 0%, #F8FAFC 100%)"
                  >
                    {selectedLead.experience_matches.length ? (
                      <Stack spacing={1.2}>
                        {selectedLead.experience_matches.map((match) => {
                          const item = experienceItems.find(
                            (experienceItem) => experienceItem.id === match.experience_item_id
                          );
                          return (
                            <Paper
                              key={match.id}
                              elevation={0}
                              sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}
                            >
                              <Stack spacing={0.8}>
                                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                                  {item?.name || match.experience_item_id}
                                </Typography>
                                <Typography sx={{ color: "#475569" }}>
                                  {item?.category || "Category not available"}
                                </Typography>
                                <Typography sx={{ color: "#0F172A" }}>
                                  Match score: {match.relevance_score == null ? "Not available" : String(match.relevance_score)}
                                </Typography>
                                <Typography sx={{ color: "#475569" }}>
                                  Matching capabilities: {item?.reusable_capabilities_json.length ? item.reusable_capabilities_json.join(", ") : "Not available"}
                                </Typography>
                                <Typography sx={{ color: "#475569" }}>
                                  Explanation: {match.match_notes || "Not available"}
                                </Typography>
                              </Stack>
                            </Paper>
                          );
                        })}
                      </Stack>
                    ) : (
                      <EmptyPanel
                        title="No experience matches"
                        description="This lead does not currently have recorded experience-match records."
                      />
                    )}
                  </SectionPanel>
                ) : null}

                {detailTab === "replies" ? (
                  <SectionPanel
                    title="Replies"
                    icon={<MarkEmailReadOutlinedIcon fontSize="small" />}
                    gradient="linear-gradient(90deg, #E0F2FE 0%, #F8FAFC 100%)"
                    action={
                      selectedLead ? (
                        <Button
                          component={Link}
                          href={`/augmis-business/replies?lead_id=${encodeURIComponent(selectedLead.id)}`}
                          variant="outlined"
                          sx={{ textTransform: "none", borderRadius: "8px" }}
                        >
                          Open Replies Workspace
                        </Button>
                      ) : null
                    }
                  >
                    {selectedLeadReplies.length ? (
                      <Stack spacing={1.2}>
                        {selectedLeadReplies.map((reply) => (
                          <Paper
                            key={reply.id}
                            elevation={0}
                            sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}
                          >
                            <Stack spacing={0.7}>
                              <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
                                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                                  {reply.subject || "No subject"}
                                </Typography>
                                <Chip
                                  size="small"
                                  label={formatStageLabel(reply.reply_status)}
                                  sx={{ textTransform: "capitalize", border: "1px solid", ...getStatusChip(reply.reply_status) }}
                                />
                                {reply.latest_intent ? (
                                  <Chip
                                    size="small"
                                    label={formatStageLabel(reply.latest_intent)}
                                    sx={{ textTransform: "capitalize", border: "1px solid", ...getStageChip("qualified") }}
                                  />
                                ) : null}
                              </Stack>
                              <Typography sx={{ color: "#475569", fontSize: 13 }}>
                                {formatDateTime(reply.received_at)} • {reply.contact_name || reply.sender_display || "Unknown sender"}
                              </Typography>
                              <Typography sx={{ color: "#334155" }}>
                                {reply.raw_message.length > 180 ? `${reply.raw_message.slice(0, 180)}...` : reply.raw_message}
                              </Typography>
                              <Typography sx={{ color: "#64748B", fontSize: 12.5 }}>
                                Response status: {formatStageLabel(reply.latest_response_status || "not available")}
                              </Typography>
                            </Stack>
                          </Paper>
                        ))}
                      </Stack>
                    ) : (
                      <EmptyPanel
                        title="No replies yet"
                        description="No inbound replies are recorded for this lead yet. Use the Replies workspace to record and analyze inbound responses."
                      />
                    )}
                  </SectionPanel>
                ) : null}

                {detailTab === "activities" ? (
                  <SectionPanel
                    title="Activities"
                    icon={<EventNoteOutlinedIcon fontSize="small" />}
                    gradient="linear-gradient(90deg, #FDE68A 0%, #F8FAFC 100%)"
                    action={
                      canCreate && selectedLead ? (
                        <Button
                          size="small"
                          variant="contained"
                          startIcon={<AddCommentOutlinedIcon />}
                          onClick={() => void openActivityDialog(selectedLead)}
                          sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "#2563EB", "&:hover": { bgcolor: "#1D4ED8" } }}
                        >
                          Add Activity
                        </Button>
                      ) : null
                    }
                  >
                    {selectedLeadActivities.length ? (
                      <Stack spacing={1.2}>
                        {selectedLeadActivities.map((activity) => (
                          <Paper
                            key={activity.id}
                            elevation={0}
                            sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}
                          >
                            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                              {activity.subject}
                            </Typography>
                            <Typography sx={{ mt: 0.3, color: "#475569" }}>
                              {formatStageLabel(activity.activity_type)}
                            </Typography>
                            <Typography sx={{ mt: 0.45, color: "#64748B", fontSize: 12.5 }}>
                              {activity.created_by || "System"} • {formatDateTime(activity.activity_at || activity.created_at)}
                            </Typography>
                            {activity.description ? (
                              <Typography sx={{ mt: 0.75, color: "#334155" }}>
                                {activity.description}
                              </Typography>
                            ) : null}
                          </Paper>
                        ))}
                      </Stack>
                    ) : (
                      <EmptyPanel
                        title="No activities yet"
                        description="No live business activities are currently recorded for this lead."
                      />
                    )}
                  </SectionPanel>
                ) : null}

                {detailTab === "tasks" ? (
                  <SectionPanel
                    title="Tasks"
                    icon={<WorkOutlineOutlinedIcon fontSize="small" />}
                    gradient="linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)"
                  >
                    {selectedLeadTasks.length ? (
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Title</TableCell>
                            <TableCell>Task Type</TableCell>
                            <TableCell>Due Date</TableCell>
                            <TableCell>Priority</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Assigned User</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {selectedLeadTasks.map((task) => (
                            <TableRow key={task.id}>
                              <TableCell>{task.title}</TableCell>
                              <TableCell>{formatTaskLabel(task.task_type)}</TableCell>
                              <TableCell sx={{ color: getDueDateColor(task.due_at) }}>
                                {formatTaskDateTime(task.due_at)}
                              </TableCell>
                              <TableCell>
                                <TaskPriorityChip priority={task.priority} />
                              </TableCell>
                              <TableCell>
                                <TaskStatusChip status={task.task_status} />
                              </TableCell>
                              <TableCell>{task.assigned_user_id || "Not available"}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    ) : (
                      <EmptyPanel
                        title="No tasks for this lead"
                        description="There are no live lead-scoped tasks to display yet."
                      />
                    )}
                  </SectionPanel>
                ) : null}
              </Stack>
            ) : (
              <Typography sx={{ color: "#475569" }}>Not available</Typography>
            )}
          </Box>
        </Box>
      </Drawer>

      <AppNotificationToast
        open={toastOpen}
        message={toastMessage}
        severity={toastSeverity}
        onClose={() => {
          setToastOpen(false);
          setToastMessage(null);
        }}
      />

      <OutreachWorkspaceDialog
        open={outreachOpen}
        opportunityId={selectedLead?.opportunity_id || ""}
        leadId={selectedLead?.id || null}
        title={selectedLead?.title || "Lead"}
        organizationName={selectedLead?.prospect?.organization_name}
        hasAssessment={Boolean(selectedLead?.opportunity?.ai_recommendation)}
        onClose={() => setOutreachOpen(false)}
        showToast={showToast}
      />

      <MiniSolutionWorkspaceDrawer
        open={miniSolutionOpen}
        opportunityId={selectedLead?.opportunity_id || ""}
        leadId={selectedLead?.id || null}
        title={selectedLead?.title || "Lead"}
        hasAssessment={Boolean(selectedLead?.opportunity?.ai_recommendation)}
        onClose={() => setMiniSolutionOpen(false)}
        showToast={showToast}
      />
    </>
  );
}
