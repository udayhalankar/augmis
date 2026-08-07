"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import AddTaskOutlinedIcon from "@mui/icons-material/AddTaskOutlined";
import AssignmentTurnedInOutlinedIcon from "@mui/icons-material/AssignmentTurnedInOutlined";
import CloseIcon from "@mui/icons-material/Close";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import EventBusyOutlinedIcon from "@mui/icons-material/EventBusyOutlined";
import EventNoteOutlinedIcon from "@mui/icons-material/EventNoteOutlined";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import TaskAltOutlinedIcon from "@mui/icons-material/TaskAltOutlined";
import TimelineOutlinedIcon from "@mui/icons-material/TimelineOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import WorkOutlineOutlinedIcon from "@mui/icons-material/WorkOutlineOutlined";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
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
import {
  AdminFormDialog,
  AdminFormField,
  AdminFormTextField,
} from "@/components/forms/AdminFormDialog";
import { OutletPage } from "@/components/layout/OutletPage";
import { useAuth } from "@/context/AuthContext";
import { parseApiValidationError } from "@/services/apiErrorParser";
import {
  type AugmisBusinessAssignableUser,
  type AugmisBusinessContact,
  type AugmisBusinessDashboard,
  type AugmisBusinessLead,
  type AugmisBusinessProspect,
  type AugmisBusinessTask,
  completeAugmisBusinessTask,
  createAugmisBusinessTask,
  getAugmisBusinessDashboard,
  getAugmisBusinessLead,
  getAugmisBusinessProspect,
  getAugmisBusinessProspectContacts,
  listAugmisBusinessAssignableUsers,
  listAugmisBusinessLeads,
  listAugmisBusinessTasks,
  updateAugmisBusinessTask,
} from "@/services/augmisBusinessService";
import {
  TaskDueIndicator,
  TaskPriorityChip,
  TaskStatusChip,
  formatTaskDateTime,
  formatTaskLabel,
  getTaskDueColor,
  isTaskDueToday,
  isTaskOverdue,
  isTaskUpcoming,
} from "../components/BusinessTaskUI";

type TimingView = "all" | "overdue" | "due_today" | "upcoming" | "in_progress" | "completed";
type ToastSeverity = "success" | "error" | "info" | "warning";

type TaskFormState = {
  lead_id: string;
  assigned_user_id: string;
  title: string;
  description: string;
  task_type: string;
  priority: string;
  task_status: string;
  due_at: string;
};

type TaskMetrics = {
  total: number;
  inProgress: number;
  completed: number;
  highPriority: number;
};

type TaskDetailState = {
  lead: AugmisBusinessLead | null;
  prospect: AugmisBusinessProspect | null;
  contacts: AugmisBusinessContact[];
};

type ResolvedUserMap = Record<string, AugmisBusinessAssignableUser>;

const TASK_TYPE_OPTIONS = [
  "research",
  "contact",
  "follow_up",
  "discovery",
  "proposal",
  "review",
  "general",
];

const TASK_STATUS_OPTIONS = ["open", "in_progress", "cancelled"];
const TASK_FILTER_STATUS_OPTIONS = ["all", "open", "in_progress", "completed", "cancelled"];
const PRIORITY_OPTIONS = ["low", "medium", "high"];
const TIMING_OPTIONS: Array<{ value: TimingView; label: string }> = [
  { value: "all", label: "All" },
  { value: "overdue", label: "Overdue" },
  { value: "due_today", label: "Due Today" },
  { value: "upcoming", label: "Upcoming" },
  { value: "in_progress", label: "In Progress" },
  { value: "completed", label: "Completed" },
];

const EMPTY_TASK_FORM: TaskFormState = {
  lead_id: "",
  assigned_user_id: "",
  title: "",
  description: "",
  task_type: "follow_up",
  priority: "medium",
  task_status: "open",
  due_at: "",
};

function normalizeOptionalString(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function toDatetimeLocalValue(value: string | null | undefined) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60000);
  return local.toISOString().slice(0, 16);
}

function fromDatetimeLocalValue(value: string) {
  return value ? new Date(value).toISOString() : null;
}

function matchesTimingView(task: AugmisBusinessTask, timingView: TimingView) {
  if (timingView === "all") {
    return true;
  }
  if (timingView === "in_progress") {
    return task.task_status === "in_progress";
  }
  if (timingView === "completed") {
    return task.task_status === "completed";
  }
  if (timingView === "overdue") {
    return isTaskOverdue(task);
  }
  if (timingView === "due_today") {
    return isTaskDueToday(task);
  }
  return isTaskUpcoming(task);
}

function findPrimaryContact(contacts: AugmisBusinessContact[]) {
  return contacts.find((contact) => contact.is_primary) || contacts[0] || null;
}

function findProspectName(
  leadMaps: Record<string, AugmisBusinessLead>,
  task: AugmisBusinessTask
) {
  return leadMaps[task.lead_id]?.prospect?.organization_name || "Not available";
}

function findLeadTitle(
  leadMaps: Record<string, AugmisBusinessLead>,
  task: AugmisBusinessTask
) {
  return leadMaps[task.lead_id]?.title || task.lead_id;
}

function getUserLabel(user: AugmisBusinessAssignableUser | null | undefined) {
  if (!user) {
    return "";
  }
  return user.name || user.email || user.user_id;
}

function getUserSecondary(user: AugmisBusinessAssignableUser | null | undefined) {
  if (!user) {
    return "";
  }
  if (user.email) {
    return `${user.email} • ${user.user_id}`;
  }
  return user.user_id;
}

function formatAssignedUserSummary(user: AugmisBusinessAssignableUser | null | undefined, fallbackId?: string | null) {
  if (!user) {
    return fallbackId || "Unassigned";
  }
  return user.email ? `${getUserLabel(user)} (${user.email})` : getUserLabel(user) || fallbackId || "Unassigned";
}

function MetricCard({
  title,
  value,
  subtitle,
  icon,
  gradient,
}: {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ReactNode;
  gradient: string;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        borderRadius: "8px",
        border: "1px solid #D9E2EC",
        overflow: "hidden",
        minHeight: 126,
      }}
    >
      <Box sx={{ px: 2, py: 1.15, background: gradient, borderBottom: "1px solid #E2E8F0" }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <Box sx={{ color: "#0F4C81", display: "flex" }}>{icon}</Box>
          <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{title}</Typography>
        </Stack>
      </Box>
      <Box sx={{ px: 2, py: 1.8 }}>
        <Typography sx={{ fontSize: 28, fontWeight: 800, color: "#0F172A", lineHeight: 1 }}>
          {value}
        </Typography>
        <Typography sx={{ mt: 1, color: "#64748B", fontSize: 13 }}>{subtitle}</Typography>
      </Box>
    </Paper>
  );
}

function SectionCard({
  title,
  icon,
  action,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Paper
      elevation={0}
      sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}
    >
      <Box
        sx={{
          px: 2,
          py: 1.3,
          background: "linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)",
          borderBottom: "1px solid #E2E8F0",
        }}
      >
        <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between" }}>
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

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <Paper
      elevation={0}
      sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0", minHeight: 82 }}
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
      <Typography sx={{ mt: 0.7, color: "#0F172A", wordBreak: "break-word" }}>{value}</Typography>
    </Paper>
  );
}

export default function TasksWorkspace() {
  const searchParams = useSearchParams();
  const { hasPermission } = useAuth();
  const canRead = hasPermission("business_development:read");
  const canCreate = hasPermission("business_development:create");
  const canUpdate = hasPermission("business_development:update");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dashboard, setDashboard] = useState<AugmisBusinessDashboard | null>(null);
  const [metrics, setMetrics] = useState<TaskMetrics>({
    total: 0,
    inProgress: 0,
    completed: 0,
    highPriority: 0,
  });
  const [tasks, setTasks] = useState<AugmisBusinessTask[]>([]);
  const [leadOptions, setLeadOptions] = useState<AugmisBusinessLead[]>([]);
  const [leadMap, setLeadMap] = useState<Record<string, AugmisBusinessLead>>({});
  const [assignedUserMap, setAssignedUserMap] = useState<ResolvedUserMap>({});
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [leadFilter, setLeadFilter] = useState("all");
  const [timingView, setTimingView] = useState<TimingView>("all");
  const [refreshTick, setRefreshTick] = useState(0);

  const [createOpen, setCreateOpen] = useState(false);
  const [createSaving, setCreateSaving] = useState(false);
  const [createError, setCreateError] = useState("");
  const [createFieldErrors, setCreateFieldErrors] = useState<Record<string, string>>({});
  const [createForm, setCreateForm] = useState<TaskFormState>(EMPTY_TASK_FORM);
  const [createAssignee, setCreateAssignee] = useState<AugmisBusinessAssignableUser | null>(null);
  const [createAssigneeInput, setCreateAssigneeInput] = useState("");

  const [editOpen, setEditOpen] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState("");
  const [editFieldErrors, setEditFieldErrors] = useState<Record<string, string>>({});
  const [editTask, setEditTask] = useState<AugmisBusinessTask | null>(null);
  const [editForm, setEditForm] = useState<TaskFormState>(EMPTY_TASK_FORM);
  const [editAssignee, setEditAssignee] = useState<AugmisBusinessAssignableUser | null>(null);
  const [editAssigneeInput, setEditAssigneeInput] = useState("");

  const [userLookupLoading, setUserLookupLoading] = useState(false);
  const [assigneeOptions, setAssigneeOptions] = useState<AugmisBusinessAssignableUser[]>([]);

  const [completeOpen, setCompleteOpen] = useState(false);
  const [completeSaving, setCompleteSaving] = useState(false);
  const [completeError, setCompleteError] = useState("");
  const [completeTaskTarget, setCompleteTaskTarget] = useState<AugmisBusinessTask | null>(null);
  const [completionNotes, setCompletionNotes] = useState("");

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [selectedTask, setSelectedTask] = useState<AugmisBusinessTask | null>(null);
  const [detailData, setDetailData] = useState<TaskDetailState>({
    lead: null,
    prospect: null,
    contacts: [],
  });

  const [toastOpen, setToastOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState("");
  const [toastSeverity, setToastSeverity] = useState<ToastSeverity>("success");

  const reliableTimingFilters = total <= pageSize;
  const requestedCreate = searchParams.get("create") === "1";
  const activeAssigneeInput = createOpen ? createAssigneeInput : editOpen ? editAssigneeInput : "";
  const activeSelectedAssignee = createOpen ? createAssignee : editOpen ? editAssignee : null;

  useEffect(() => {
    if (requestedCreate && canCreate && !createOpen) {
      const timer = window.setTimeout(() => setCreateOpen(true), 0);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [canCreate, createOpen, requestedCreate]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(0);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (!(createOpen || editOpen)) {
      return;
    }

    if (activeAssigneeInput.trim().length < 2) {
      return;
    }

    let active = true;
    const timer = window.setTimeout(async () => {
      setUserLookupLoading(true);
      try {
        const result = await listAugmisBusinessAssignableUsers({
          search: activeAssigneeInput.trim(),
          limit: 15,
        });
        if (!active) {
          return;
        }
        const mergedOptions = activeSelectedAssignee
          ? [
              activeSelectedAssignee,
              ...result.data.filter((option) => option.user_id !== activeSelectedAssignee.user_id),
            ]
          : result.data;
        setAssigneeOptions(mergedOptions);
      } catch {
        if (active) {
          setAssigneeOptions(activeSelectedAssignee ? [activeSelectedAssignee] : []);
        }
      } finally {
        if (active) {
          setUserLookupLoading(false);
        }
      }
    }, 300);

    return () => {
      active = false;
      window.clearTimeout(timer);
      setUserLookupLoading(false);
    };
  }, [
    createOpen,
    editOpen,
    activeAssigneeInput,
    activeSelectedAssignee,
  ]);

  useEffect(() => {
    if (!canRead) {
      return;
    }
    let active = true;

    async function loadWorkspace() {
      setLoading(true);
      setError("");
      try {
        const baseTaskParams = {
          page: page + 1,
          page_size: pageSize,
          search: search || undefined,
          status: statusFilter !== "all" ? statusFilter : undefined,
          priority: priorityFilter !== "all" ? priorityFilter : undefined,
          lead_id: leadFilter !== "all" ? leadFilter : undefined,
        };

        const [dashboardResult, taskResult, leadListResult, inProgressResult, completedResult, highPriorityResult] =
          await Promise.all([
            getAugmisBusinessDashboard(),
            listAugmisBusinessTasks(baseTaskParams),
            listAugmisBusinessLeads({ page: 1, page_size: 100 }),
            listAugmisBusinessTasks({ page: 1, page_size: 1, status: "in_progress" }),
            listAugmisBusinessTasks({ page: 1, page_size: 1, status: "completed" }),
            listAugmisBusinessTasks({ page: 1, page_size: 1, priority: "high" }),
          ]);

        const taskRows = taskResult.data || [];
        const uniqueLeadIds = Array.from(
          new Set(taskRows.map((task) => task.lead_id).filter((leadId): leadId is string => Boolean(leadId)))
        );
        const uniqueAssignedUserIds = Array.from(
          new Set(
            taskRows
              .map((task) => task.assigned_user_id)
              .filter((userId): userId is string => Boolean(userId))
          )
        );
        const relatedLeads = await Promise.all(
          uniqueLeadIds.map(async (leadId) => {
            try {
              const leadResult = await getAugmisBusinessLead(leadId);
              return leadResult.data;
            } catch {
              return null;
            }
          })
        );
        const assignableUsersResult = uniqueAssignedUserIds.length
          ? await listAugmisBusinessAssignableUsers({
              user_ids: uniqueAssignedUserIds,
              include_inactive: true,
              limit: uniqueAssignedUserIds.length,
            })
          : { data: [] };

        if (!active) {
          return;
        }

        const nextLeadMap = relatedLeads.reduce<Record<string, AugmisBusinessLead>>((acc, lead) => {
          if (lead) {
            acc[lead.id] = lead;
          }
          return acc;
        }, {});
        const nextAssignedUserMap = (assignableUsersResult.data || []).reduce<ResolvedUserMap>(
          (acc, user) => {
            acc[user.user_id] = user;
            return acc;
          },
          {}
        );

        setDashboard(dashboardResult.data);
        setTasks(taskRows);
        setLeadOptions(leadListResult.data || []);
        setLeadMap(nextLeadMap);
        setAssignedUserMap(nextAssignedUserMap);
        setTotal(taskResult.pagination?.total || 0);
        setMetrics({
          total: taskResult.pagination?.total || 0,
          inProgress: inProgressResult.pagination?.total || 0,
          completed: completedResult.pagination?.total || 0,
          highPriority: highPriorityResult.pagination?.total || 0,
        });
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(parseApiValidationError(loadError, "Unable to load tasks workspace.").message);
        setDashboard(null);
        setTasks([]);
        setLeadOptions([]);
        setLeadMap({});
        setAssignedUserMap({});
        setTotal(0);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadWorkspace();

    return () => {
      active = false;
    };
  }, [canRead, leadFilter, page, pageSize, priorityFilter, refreshTick, search, statusFilter]);

  const displayedTasks = useMemo(() => {
    if (timingView === "all" || timingView === "in_progress" || timingView === "completed") {
      return tasks;
    }
    if (!reliableTimingFilters) {
      return tasks;
    }
    return tasks.filter((task) => matchesTimingView(task, timingView));
  }, [reliableTimingFilters, tasks, timingView]);
  const effectiveAssigneeOptions = useMemo(() => {
    if (activeAssigneeInput.trim().length < 2) {
      return activeSelectedAssignee ? [activeSelectedAssignee] : [];
    }
    return assigneeOptions;
  }, [activeAssigneeInput, activeSelectedAssignee, assigneeOptions]);

  const selectedCreateLead =
    leadOptions.find((lead) => lead.id === createForm.lead_id) || leadMap[createForm.lead_id] || null;
  const selectedEditLead =
    leadOptions.find((lead) => lead.id === editForm.lead_id) || leadMap[editForm.lead_id] || null;

  function getAssignedUserDisplay(userId: string | null | undefined) {
    if (!userId) {
      return {
        primary: "Unassigned",
        secondary: "",
      };
    }
    const user = assignedUserMap[userId];
    if (!user) {
      return {
        primary: userId,
        secondary: "",
      };
    }
    return {
      primary: getUserLabel(user) || userId,
      secondary: getUserSecondary(user),
    };
  }

  function getFriendlyTaskErrorMessage(message: string) {
    if (message.includes("Assigned user not found for tenant")) {
      return "The selected user is no longer available. Please select another user.";
    }
    return message;
  }

  function showToast(message: string, severity: ToastSeverity) {
    setToastMessage(message);
    setToastSeverity(severity);
    setToastOpen(true);
  }

  function resetCreateForm() {
    setCreateForm(EMPTY_TASK_FORM);
    setCreateAssignee(null);
    setCreateAssigneeInput("");
    setAssigneeOptions([]);
    setCreateError("");
    setCreateFieldErrors({});
  }

  function openCreateDialog() {
    resetCreateForm();
    setCreateOpen(true);
  }

  function closeCreateDialog() {
    setCreateOpen(false);
    setCreateSaving(false);
    setCreateError("");
    setCreateFieldErrors({});
  }

  function openEditDialog(task: AugmisBusinessTask) {
    const resolvedAssignee = task.assigned_user_id ? assignedUserMap[task.assigned_user_id] || null : null;
    setEditTask(task);
    setEditForm({
      lead_id: task.lead_id,
      assigned_user_id: task.assigned_user_id || "",
      title: task.title,
      description: task.description || "",
      task_type: task.task_type || "follow_up",
      priority: task.priority || "medium",
      task_status: task.task_status === "completed" ? "in_progress" : task.task_status || "open",
      due_at: toDatetimeLocalValue(task.due_at),
    });
    setEditAssignee(resolvedAssignee);
    setEditAssigneeInput(
      resolvedAssignee ? getUserLabel(resolvedAssignee) : task.assigned_user_id || ""
    );
    setAssigneeOptions(resolvedAssignee ? [resolvedAssignee] : []);
    setEditFieldErrors({});
    setEditError("");
    setEditOpen(true);
  }

  function closeEditDialog() {
    setEditOpen(false);
    setEditSaving(false);
    setEditFieldErrors({});
    setEditError("");
    setEditTask(null);
    setEditAssignee(null);
    setEditAssigneeInput("");
    setAssigneeOptions([]);
  }

  function openCompleteDialog(task: AugmisBusinessTask) {
    setCompleteTaskTarget(task);
    setCompletionNotes("");
    setCompleteError("");
    setCompleteOpen(true);
  }

  function closeCompleteDialog() {
    setCompleteOpen(false);
    setCompleteSaving(false);
    setCompleteError("");
    setCompleteTaskTarget(null);
    setCompletionNotes("");
  }

  async function refreshWorkspace() {
    setRefreshTick((value) => value + 1);
  }

  async function openTaskDetail(task: AugmisBusinessTask) {
    setSelectedTask(task);
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailError("");
    try {
      const leadResult = await getAugmisBusinessLead(task.lead_id);
      const lead = leadResult.data;
      let prospect: AugmisBusinessProspect | null = lead.prospect || null;
      let contacts: AugmisBusinessContact[] = [];

      if (lead.prospect_id) {
        const [prospectResult, contactsResult] = await Promise.all([
          getAugmisBusinessProspect(lead.prospect_id),
          getAugmisBusinessProspectContacts(lead.prospect_id),
        ]);
        prospect = prospectResult.data;
        contacts = contactsResult.data || [];
      }

      setDetailData({ lead, prospect, contacts });
    } catch (drawerError) {
      setDetailError(parseApiValidationError(drawerError, "Unable to load task details.").message);
      setDetailData({ lead: null, prospect: null, contacts: [] });
    } finally {
      setDetailLoading(false);
    }
  }

  function closeTaskDetail() {
    setDetailOpen(false);
    setDetailLoading(false);
    setDetailError("");
    setSelectedTask(null);
    setDetailData({ lead: null, prospect: null, contacts: [] });
  }

  function updateCreateField<K extends keyof TaskFormState>(field: K, value: TaskFormState[K]) {
    setCreateForm((current) => ({ ...current, [field]: value }));
    setCreateFieldErrors((current) => ({ ...current, [field]: "" }));
  }

  function updateEditField<K extends keyof TaskFormState>(field: K, value: TaskFormState[K]) {
    setEditForm((current) => ({ ...current, [field]: value }));
    setEditFieldErrors((current) => ({ ...current, [field]: "" }));
  }

  async function submitCreateTask() {
    setCreateSaving(true);
    setCreateError("");
    setCreateFieldErrors({});
    if (createAssigneeInput.trim() && !createAssignee) {
      setCreateSaving(false);
      setCreateFieldErrors({ assigned_user_id: "Select a valid AUGMIS user from the list." });
      return;
    }
    try {
      const result = await createAugmisBusinessTask({
        lead_id: createForm.lead_id,
        assigned_user_id: createAssignee?.user_id || null,
        title: createForm.title.trim(),
        description: normalizeOptionalString(createForm.description),
        task_type: createForm.task_type,
        priority: createForm.priority,
        due_at: fromDatetimeLocalValue(createForm.due_at),
        opportunity_id: selectedCreateLead?.opportunity_id || null,
        prospect_id: selectedCreateLead?.prospect_id || null,
      });
      closeCreateDialog();
      showToast(`Task ${result.data.title} created.`, "success");
      if (page !== 0) {
        setPage(0);
      } else {
        await refreshWorkspace();
      }
    } catch (saveError) {
      const parsed = parseApiValidationError(saveError, "Unable to create task.");
      setCreateError(getFriendlyTaskErrorMessage(parsed.message));
      setCreateFieldErrors(parsed.fieldErrors);
    } finally {
      setCreateSaving(false);
    }
  }

  async function submitEditTask() {
    if (!editTask) {
      return;
    }
    setEditSaving(true);
    setEditError("");
    setEditFieldErrors({});
    if (editAssigneeInput.trim() && !editAssignee) {
      setEditSaving(false);
      setEditFieldErrors({ assigned_user_id: "Select a valid AUGMIS user from the list." });
      return;
    }
    try {
      const result = await updateAugmisBusinessTask(editTask.id, {
        assigned_user_id: editAssignee?.user_id || null,
        title: editForm.title.trim(),
        description: normalizeOptionalString(editForm.description),
        task_type: editForm.task_type,
        task_status: editForm.task_status,
        priority: editForm.priority,
        due_at: fromDatetimeLocalValue(editForm.due_at),
      });
      closeEditDialog();
      showToast(`Task ${result.data.title} updated.`, "success");
      await refreshWorkspace();
      if (detailOpen && selectedTask?.id === result.data.id) {
        await openTaskDetail(result.data);
      }
    } catch (saveError) {
      const parsed = parseApiValidationError(saveError, "Unable to update task.");
      setEditError(getFriendlyTaskErrorMessage(parsed.message));
      setEditFieldErrors(parsed.fieldErrors);
    } finally {
      setEditSaving(false);
    }
  }

  async function submitCompleteTask() {
    if (!completeTaskTarget) {
      return;
    }
    setCompleteSaving(true);
    setCompleteError("");
    try {
      const result = await completeAugmisBusinessTask(completeTaskTarget.id, {
        completion_notes: normalizeOptionalString(completionNotes),
      });
      closeCompleteDialog();
      showToast(`Task ${result.data.title} completed.`, "success");
      await refreshWorkspace();
      if (detailOpen && selectedTask?.id === result.data.id) {
        await openTaskDetail(result.data);
      }
    } catch (completeErrorValue) {
      setCompleteError(
        parseApiValidationError(completeErrorValue, "Unable to complete task.").message
      );
    } finally {
      setCompleteSaving(false);
    }
  }

  const primaryContact = findPrimaryContact(detailData.contacts);

  return (
    <OutletPage
      title="Business Development Tasks"
      description="Manage live follow-up work, due dates, and sales execution tasks across AUGMIS Business."
    >
      <Stack spacing={2.5}>
        {error ? <Alert severity="error">{error}</Alert> : null}

        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: {
              xs: "1fr",
              md: "repeat(2, minmax(0, 1fr))",
              xl: "repeat(5, minmax(0, 1fr))",
            },
          }}
        >
          <MetricCard
            title="Overdue"
            value={dashboard?.overdue_tasks ?? 0}
            subtitle="Open or in-progress tasks past due"
            icon={<EventBusyOutlinedIcon fontSize="small" />}
            gradient="linear-gradient(90deg, #FEE4E2 0%, #FFF5F4 100%)"
          />
          <MetricCard
            title="Due Today"
            value={dashboard?.tasks_due_today ?? 0}
            subtitle="Live tasks due before close of day"
            icon={<ScheduleOutlinedIcon fontSize="small" />}
            gradient="linear-gradient(90deg, #FEF3C7 0%, #FFFBEB 100%)"
          />
          <MetricCard
            title="In Progress"
            value={metrics.inProgress}
            subtitle="Tenant-wide active execution tasks"
            icon={<TaskAltOutlinedIcon fontSize="small" />}
            gradient="linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)"
          />
          <MetricCard
            title="Completed"
            value={metrics.completed}
            subtitle="Tenant-wide completed task records"
            icon={<AssignmentTurnedInOutlinedIcon fontSize="small" />}
            gradient="linear-gradient(90deg, #DCFCE7 0%, #F0FDF4 100%)"
          />
          <MetricCard
            title="High Priority"
            value={metrics.highPriority}
            subtitle="Tenant-wide tasks marked high priority"
            icon={<WorkOutlineOutlinedIcon fontSize="small" />}
            gradient="linear-gradient(90deg, #FEE2E2 0%, #FFF1F2 100%)"
          />
        </Box>

        <SectionCard
          title="Task Filters"
          icon={<EventNoteOutlinedIcon fontSize="small" />}
          action={
            <Stack direction="row" spacing={1}>
              <Button
                variant="outlined"
                startIcon={<RefreshRoundedIcon />}
                onClick={() => void refreshWorkspace()}
                sx={{ borderRadius: "8px", textTransform: "none" }}
              >
                Refresh
              </Button>
              {canCreate ? (
                <Button
                  variant="contained"
                  startIcon={<AddTaskOutlinedIcon />}
                  onClick={openCreateDialog}
                  sx={{
                    borderRadius: "8px",
                    textTransform: "none",
                    bgcolor: "#2563EB",
                    "&:hover": { bgcolor: "#1D4ED8" },
                  }}
                >
                  New Task
                </Button>
              ) : null}
            </Stack>
          }
        >
          <Stack spacing={1.5}>
            <Box
              sx={{
                display: "grid",
                gap: 1.25,
                gridTemplateColumns: {
                  xs: "1fr",
                  md: "repeat(4, minmax(0, 1fr))",
                },
              }}
            >
              <TextField
                label="Search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Search tasks"
                fullWidth
                sx={{
                  "& .MuiOutlinedInput-root": { borderRadius: "8px", backgroundColor: "#FFFFFF" },
                }}
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
                label="Status"
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value);
                  setPage(0);
                  if (event.target.value === "in_progress") {
                    setTimingView("in_progress");
                  } else if (event.target.value === "completed") {
                    setTimingView("completed");
                  } else if (timingView === "in_progress" || timingView === "completed") {
                    setTimingView("all");
                  }
                }}
              >
                {TASK_FILTER_STATUS_OPTIONS.map((status) => (
                  <MenuItem key={status} value={status}>
                    {status === "all" ? "All statuses" : formatTaskLabel(status)}
                  </MenuItem>
                ))}
              </AdminFormTextField>
              <AdminFormTextField
                select
                label="Priority"
                value={priorityFilter}
                onChange={(event) => {
                  setPriorityFilter(event.target.value);
                  setPage(0);
                }}
              >
                <MenuItem value="all">All priorities</MenuItem>
                {PRIORITY_OPTIONS.map((priority) => (
                  <MenuItem key={priority} value={priority}>
                    {formatTaskLabel(priority)}
                  </MenuItem>
                ))}
              </AdminFormTextField>
              <AdminFormTextField
                select
                label="Lead"
                value={leadFilter}
                onChange={(event) => {
                  setLeadFilter(event.target.value);
                  setPage(0);
                }}
              >
                <MenuItem value="all">All leads</MenuItem>
                {leadOptions.map((lead) => (
                  <MenuItem key={lead.id} value={lead.id}>
                    {lead.title}
                  </MenuItem>
                ))}
              </AdminFormTextField>
            </Box>

            <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
              {TIMING_OPTIONS.map((option) => {
                const needsReliableSet =
                  option.value === "overdue" ||
                  option.value === "due_today" ||
                  option.value === "upcoming";
                const disabled = needsReliableSet && !reliableTimingFilters;
                const button = (
                  <Button
                    key={option.value}
                    variant={timingView === option.value ? "contained" : "outlined"}
                    disabled={disabled}
                    onClick={() => setTimingView(option.value)}
                    sx={{
                      borderRadius: 999,
                      textTransform: "none",
                      minWidth: 0,
                      bgcolor: timingView === option.value ? "#0F4C81" : undefined,
                    }}
                  >
                    {option.label}
                  </Button>
                );
                if (disabled) {
                  return (
                    <Tooltip
                      key={option.value}
                      title="Timing views are enabled only when the loaded page contains the full matching dataset."
                    >
                      <span>{button}</span>
                    </Tooltip>
                  );
                }
                return button;
              })}
            </Stack>

            {!reliableTimingFilters ? (
              <Alert severity="info" sx={{ borderRadius: "8px" }}>
                Overdue, Due Today, and Upcoming tabs stay disabled because the current task result is
                paginated and the backend does not yet expose due-date filters.
              </Alert>
            ) : null}
          </Stack>
        </SectionCard>

        <SectionCard
          title="Tasks Workspace"
          icon={<TimelineOutlinedIcon fontSize="small" />}
          action={
            <Typography sx={{ color: "#64748B", fontSize: 13 }}>
              {metrics.total.toLocaleString()} matching tasks
            </Typography>
          }
        >
          {loading ? (
            <Stack sx={{ py: 6, alignItems: "center" }}>
              <CircularProgress size={28} />
            </Stack>
          ) : displayedTasks.length ? (
            <>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Task</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Related Lead</TableCell>
                      <TableCell>Prospect</TableCell>
                      <TableCell>Assigned To</TableCell>
                      <TableCell>Priority</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Due Date</TableCell>
                      <TableCell>Timing</TableCell>
                      <TableCell>Created</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {displayedTasks.map((task) => (
                      <TableRow key={task.id} hover>
                        <TableCell sx={{ minWidth: 220 }}>
                          <Button
                            variant="text"
                            onClick={() => void openTaskDetail(task)}
                            sx={{
                              p: 0,
                              minWidth: 0,
                              justifyContent: "flex-start",
                              textTransform: "none",
                              color: "#0F4C81",
                              fontWeight: 700,
                            }}
                          >
                            {task.title}
                          </Button>
                        </TableCell>
                        <TableCell>{formatTaskLabel(task.task_type)}</TableCell>
                        <TableCell>{findLeadTitle(leadMap, task)}</TableCell>
                        <TableCell>{findProspectName(leadMap, task)}</TableCell>
                        <TableCell sx={{ minWidth: 180 }}>
                          <Typography sx={{ color: "#0F172A", fontWeight: 600, lineHeight: 1.2 }}>
                            {getAssignedUserDisplay(task.assigned_user_id).primary}
                          </Typography>
                          {getAssignedUserDisplay(task.assigned_user_id).secondary ? (
                            <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12 }}>
                              {getAssignedUserDisplay(task.assigned_user_id).secondary}
                            </Typography>
                          ) : null}
                        </TableCell>
                        <TableCell>
                          <TaskPriorityChip priority={task.priority} />
                        </TableCell>
                        <TableCell>
                          <TaskStatusChip status={task.task_status} />
                        </TableCell>
                        <TableCell sx={{ color: getTaskDueColor(task) }}>
                          {formatTaskDateTime(task.due_at)}
                        </TableCell>
                        <TableCell>
                          <TaskDueIndicator task={task} />
                        </TableCell>
                        <TableCell>{formatTaskDateTime(task.created_at)}</TableCell>
                        <TableCell align="right">
                          <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end" }}>
                            <Tooltip title="View task">
                              <span>
                                <IconButton size="small" onClick={() => void openTaskDetail(task)}>
                                  <VisibilityOutlinedIcon fontSize="small" />
                                </IconButton>
                              </span>
                            </Tooltip>
                            {canUpdate ? (
                              <Tooltip title="Edit task">
                                <span>
                                  <IconButton size="small" onClick={() => openEditDialog(task)}>
                                    <EditOutlinedIcon fontSize="small" />
                                  </IconButton>
                                </span>
                              </Tooltip>
                            ) : null}
                            {canUpdate && task.task_status !== "completed" ? (
                              <Tooltip title="Complete task">
                                <span>
                                  <IconButton size="small" onClick={() => openCompleteDialog(task)}>
                                    <AssignmentTurnedInOutlinedIcon fontSize="small" />
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
                rowsPerPageOptions={[25, 50, 100]}
              />
            </>
          ) : (
            <Paper
              elevation={0}
              sx={{ p: 2.5, borderRadius: "8px", border: "1px dashed #CBD5E1", bgcolor: "#F8FAFC" }}
            >
              <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>No tasks found</Typography>
              <Typography sx={{ mt: 0.7, color: "#475569" }}>
                No live tasks match the current filters. Adjust the filters or create a new task.
              </Typography>
            </Paper>
          )}
        </SectionCard>
      </Stack>

      <AdminFormDialog
        open={createOpen}
        onClose={closeCreateDialog}
        title="Create Task"
        actions={
          <>
            <Button onClick={closeCreateDialog} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={() => void submitCreateTask()}
              disabled={createSaving || !createForm.lead_id || !createForm.title.trim()}
              sx={{ textTransform: "none", bgcolor: "#2563EB", "&:hover": { bgcolor: "#1D4ED8" } }}
            >
              {createSaving ? "Creating..." : "Create Task"}
            </Button>
          </>
        }
      >
        {createError ? <Alert severity="error">{createError}</Alert> : null}
        <AdminFormTextField
          select
          label="Lead"
          value={createForm.lead_id}
          onChange={(event) => updateCreateField("lead_id", event.target.value)}
          error={Boolean(createFieldErrors.lead_id)}
          helperText={createFieldErrors.lead_id || "Required"}
        >
          {leadOptions.map((lead) => (
            <MenuItem key={lead.id} value={lead.id}>
              {lead.title}
            </MenuItem>
          ))}
        </AdminFormTextField>
        <AdminFormTextField
          label="Prospect"
          value={selectedCreateLead?.prospect?.organization_name || "Will follow selected lead"}
          disabled
        />
        <AdminFormField
          label="Assigned To"
          helperText={createFieldErrors.assigned_user_id || "Optional. Start typing a user name, email, or user ID."}
        >
          <Autocomplete
            options={effectiveAssigneeOptions}
            loading={userLookupLoading}
            value={createAssignee}
            inputValue={createAssigneeInput}
            onChange={(_, value) => {
              setCreateAssignee(value);
              updateCreateField("assigned_user_id", value?.user_id || "");
              setCreateAssigneeInput(value ? getUserLabel(value) : "");
            }}
            onInputChange={(_, value, reason) => {
              setCreateAssigneeInput(value);
              if (reason === "input") {
                setCreateAssignee(null);
                updateCreateField("assigned_user_id", "");
              }
            }}
            getOptionLabel={(option) => getUserLabel(option)}
            isOptionEqualToValue={(option, value) => option.user_id === value.user_id}
            noOptionsText={
              createAssigneeInput.trim().length < 2 ? "Type at least 2 characters" : "No matching users"
            }
            renderOption={(props, option) => (
              <Box component="li" {...props} key={option.user_id} sx={{ py: 1 }}>
                <Box>
                  <Typography sx={{ fontWeight: 600, color: "#0F172A" }}>{getUserLabel(option)}</Typography>
                  <Typography sx={{ color: "#64748B", fontSize: 12.5 }}>
                    {getUserSecondary(option)}
                  </Typography>
                </Box>
              </Box>
            )}
            renderInput={(params) => (
              <TextField
                {...params}
                placeholder="Start typing a user name, email, or user ID..."
                error={Boolean(createFieldErrors.assigned_user_id)}
                sx={{
                  "& .MuiOutlinedInput-root": {
                    borderRadius: "6px",
                    minHeight: 36,
                    fontSize: "12px",
                    backgroundColor: "#FFFFFF",
                  },
                }}
              />
            )}
          />
        </AdminFormField>
        <AdminFormTextField
          label="Title"
          value={createForm.title}
          onChange={(event) => updateCreateField("title", event.target.value)}
          error={Boolean(createFieldErrors.title)}
          helperText={createFieldErrors.title || "Required"}
        />
        <AdminFormTextField
          label="Description"
          value={createForm.description}
          onChange={(event) => updateCreateField("description", event.target.value)}
          multiline
          minRows={3}
          error={Boolean(createFieldErrors.description)}
          helperText={createFieldErrors.description}
        />
        <AdminFormTextField
          select
          label="Task Type"
          value={createForm.task_type}
          onChange={(event) => updateCreateField("task_type", event.target.value)}
          error={Boolean(createFieldErrors.task_type)}
          helperText={createFieldErrors.task_type}
        >
          {TASK_TYPE_OPTIONS.map((taskType) => (
            <MenuItem key={taskType} value={taskType}>
              {formatTaskLabel(taskType)}
            </MenuItem>
          ))}
        </AdminFormTextField>
        <AdminFormTextField
          label="Due Date"
          type="datetime-local"
          value={createForm.due_at}
          onChange={(event) => updateCreateField("due_at", event.target.value)}
          error={Boolean(createFieldErrors.due_at)}
          helperText={createFieldErrors.due_at || "Optional. Leave blank to use backend working-day defaults."}
          InputLabelProps={{ shrink: true }}
        />
        <AdminFormTextField
          select
          label="Priority"
          value={createForm.priority}
          onChange={(event) => updateCreateField("priority", event.target.value)}
          error={Boolean(createFieldErrors.priority)}
          helperText={createFieldErrors.priority}
        >
          {PRIORITY_OPTIONS.map((priority) => (
            <MenuItem key={priority} value={priority}>
              {formatTaskLabel(priority)}
            </MenuItem>
          ))}
        </AdminFormTextField>
      </AdminFormDialog>

      <AdminFormDialog
        open={editOpen}
        onClose={closeEditDialog}
        title="Edit Task"
        actions={
          <>
            <Button onClick={closeEditDialog} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={() => void submitEditTask()}
              disabled={editSaving || !editTask || !editForm.title.trim()}
              sx={{ textTransform: "none", bgcolor: "#2563EB", "&:hover": { bgcolor: "#1D4ED8" } }}
            >
              {editSaving ? "Saving..." : "Save Changes"}
            </Button>
          </>
        }
      >
        {editError ? <Alert severity="error">{editError}</Alert> : null}
        <AdminFormTextField label="Lead" value={selectedEditLead?.title || editForm.lead_id} disabled />
        <AdminFormTextField
          label="Prospect"
          value={selectedEditLead?.prospect?.organization_name || "Not available"}
          disabled
        />
        <AdminFormField
          label="Assigned To"
          helperText={editFieldErrors.assigned_user_id || "Optional. Start typing a user name, email, or user ID."}
        >
          <Autocomplete
            options={effectiveAssigneeOptions}
            loading={userLookupLoading}
            value={editAssignee}
            inputValue={editAssigneeInput}
            onChange={(_, value) => {
              setEditAssignee(value);
              updateEditField("assigned_user_id", value?.user_id || "");
              setEditAssigneeInput(value ? getUserLabel(value) : "");
            }}
            onInputChange={(_, value, reason) => {
              setEditAssigneeInput(value);
              if (reason === "input") {
                setEditAssignee(null);
                updateEditField("assigned_user_id", "");
              }
            }}
            getOptionLabel={(option) => getUserLabel(option)}
            isOptionEqualToValue={(option, value) => option.user_id === value.user_id}
            noOptionsText={
              editAssigneeInput.trim().length < 2 ? "Type at least 2 characters" : "No matching users"
            }
            renderOption={(props, option) => (
              <Box component="li" {...props} key={option.user_id} sx={{ py: 1 }}>
                <Box>
                  <Typography sx={{ fontWeight: 600, color: "#0F172A" }}>{getUserLabel(option)}</Typography>
                  <Typography sx={{ color: "#64748B", fontSize: 12.5 }}>
                    {getUserSecondary(option)}
                  </Typography>
                </Box>
              </Box>
            )}
            renderInput={(params) => (
              <TextField
                {...params}
                placeholder="Start typing a user name, email, or user ID..."
                error={Boolean(editFieldErrors.assigned_user_id)}
                sx={{
                  "& .MuiOutlinedInput-root": {
                    borderRadius: "6px",
                    minHeight: 36,
                    fontSize: "12px",
                    backgroundColor: "#FFFFFF",
                  },
                }}
              />
            )}
          />
        </AdminFormField>
        <AdminFormTextField
          label="Title"
          value={editForm.title}
          onChange={(event) => updateEditField("title", event.target.value)}
          error={Boolean(editFieldErrors.title)}
          helperText={editFieldErrors.title || "Required"}
        />
        <AdminFormTextField
          label="Description"
          value={editForm.description}
          onChange={(event) => updateEditField("description", event.target.value)}
          multiline
          minRows={3}
          error={Boolean(editFieldErrors.description)}
          helperText={editFieldErrors.description}
        />
        <AdminFormTextField
          select
          label="Task Type"
          value={editForm.task_type}
          onChange={(event) => updateEditField("task_type", event.target.value)}
          error={Boolean(editFieldErrors.task_type)}
          helperText={editFieldErrors.task_type}
        >
          {TASK_TYPE_OPTIONS.map((taskType) => (
            <MenuItem key={taskType} value={taskType}>
              {formatTaskLabel(taskType)}
            </MenuItem>
          ))}
        </AdminFormTextField>
        <AdminFormTextField
          label="Due Date"
          type="datetime-local"
          value={editForm.due_at}
          onChange={(event) => updateEditField("due_at", event.target.value)}
          error={Boolean(editFieldErrors.due_at)}
          helperText={editFieldErrors.due_at}
          InputLabelProps={{ shrink: true }}
        />
        <AdminFormTextField
          select
          label="Priority"
          value={editForm.priority}
          onChange={(event) => updateEditField("priority", event.target.value)}
          error={Boolean(editFieldErrors.priority)}
          helperText={editFieldErrors.priority}
        >
          {PRIORITY_OPTIONS.map((priority) => (
            <MenuItem key={priority} value={priority}>
              {formatTaskLabel(priority)}
            </MenuItem>
          ))}
        </AdminFormTextField>
        <AdminFormTextField
          select
          label="Status"
          value={editForm.task_status}
          onChange={(event) => updateEditField("task_status", event.target.value)}
          error={Boolean(editFieldErrors.task_status)}
          helperText={editFieldErrors.task_status || "Use Complete Task to stamp completion details."}
        >
          {TASK_STATUS_OPTIONS.map((statusValue) => (
            <MenuItem key={statusValue} value={statusValue}>
              {formatTaskLabel(statusValue)}
            </MenuItem>
          ))}
        </AdminFormTextField>
      </AdminFormDialog>

      <AdminFormDialog
        open={completeOpen}
        onClose={closeCompleteDialog}
        title="Complete Task"
        actions={
          <>
            <Button onClick={closeCompleteDialog} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              color="success"
              onClick={() => void submitCompleteTask()}
              disabled={completeSaving || !completeTaskTarget}
              sx={{ textTransform: "none" }}
            >
              {completeSaving ? "Completing..." : "Complete Task"}
            </Button>
          </>
        }
      >
        {completeError ? <Alert severity="error">{completeError}</Alert> : null}
        <Typography sx={{ color: "#475569" }}>
          Mark <strong>{completeTaskTarget?.title || "this task"}</strong> as completed. This will
          stamp the backend completion timestamp and move the task into the completed state.
        </Typography>
        <AdminFormTextField
          label="Completion Notes"
          value={completionNotes}
          onChange={(event) => setCompletionNotes(event.target.value)}
          multiline
          minRows={3}
          helperText="Optional"
        />
      </AdminFormDialog>

      <Drawer
        anchor="right"
        open={detailOpen}
        onClose={closeTaskDetail}
        slotProps={{
          paper: {
            sx: {
              width: { xs: "100%", sm: 520, lg: 640 },
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
              background: "linear-gradient(135deg, #0F4C81 0%, #2563EB 100%)",
              color: "#F8FAFC",
            }}
          >
            <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <Box sx={{ pr: 2 }}>
                <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: ".06em", textTransform: "uppercase", opacity: 0.88 }}>
                  Task Detail
                </Typography>
                <Typography sx={{ mt: 0.8, fontSize: 24, fontWeight: 800, lineHeight: 1.15 }}>
                  {selectedTask?.title || "Task"}
                </Typography>
                <Typography sx={{ mt: 0.8, color: "rgba(248,250,252,0.88)" }}>
                  Live operational task context for the selected lead and prospect.
                </Typography>
              </Box>
              <IconButton onClick={closeTaskDetail} sx={{ color: "#F8FAFC" }}>
                <CloseIcon />
              </IconButton>
            </Stack>
            <Stack direction="row" spacing={1} sx={{ mt: 1.5, flexWrap: "wrap", rowGap: 1 }}>
              {selectedTask ? <TaskPriorityChip priority={selectedTask.priority} /> : null}
              {selectedTask ? <TaskStatusChip status={selectedTask.task_status} /> : null}
            </Stack>
            <Stack direction="row" spacing={1} sx={{ mt: 1.75, flexWrap: "wrap", rowGap: 1 }}>
              {canUpdate && selectedTask?.task_status !== "completed" ? (
                <Button
                  variant="contained"
                  color="inherit"
                  startIcon={<AssignmentTurnedInOutlinedIcon />}
                  onClick={() => selectedTask && openCompleteDialog(selectedTask)}
                  sx={{ textTransform: "none", bgcolor: "#FFFFFF", color: "#0F4C81", "&:hover": { bgcolor: "#E2E8F0" } }}
                >
                  Complete
                </Button>
              ) : null}
              {canUpdate ? (
                <Button
                  variant="outlined"
                  startIcon={<EditOutlinedIcon />}
                  onClick={() => selectedTask && openEditDialog(selectedTask)}
                  sx={{ textTransform: "none", color: "#FFFFFF", borderColor: "rgba(255,255,255,0.45)" }}
                >
                  Edit
                </Button>
              ) : null}
              <Button
                variant="outlined"
                onClick={closeTaskDetail}
                sx={{ textTransform: "none", color: "#FFFFFF", borderColor: "rgba(255,255,255,0.45)" }}
              >
                Close
              </Button>
            </Stack>
          </Box>

          <Box sx={{ p: 2, overflowY: "auto", flex: 1 }}>
            {detailLoading ? (
              <Stack sx={{ py: 6, alignItems: "center" }}>
                <CircularProgress size={28} />
              </Stack>
            ) : detailError ? (
              <Alert severity="error">{detailError}</Alert>
            ) : selectedTask ? (
              <Stack spacing={2}>
                <SectionCard title="Overview" icon={<WorkOutlineOutlinedIcon fontSize="small" />}>
                  <Box
                    sx={{
                      display: "grid",
                      gap: 1.25,
                      gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                    }}
                  >
                    <DetailField label="Title" value={selectedTask.title} />
                    <DetailField label="Task Type" value={formatTaskLabel(selectedTask.task_type)} />
                    <DetailField label="Status" value={formatTaskLabel(selectedTask.task_status)} />
                    <DetailField label="Priority" value={formatTaskLabel(selectedTask.priority)} />
                    <DetailField label="Due Date" value={formatTaskDateTime(selectedTask.due_at)} />
                    <DetailField
                      label="Assigned User"
                      value={formatAssignedUserSummary(
                        assignedUserMap[selectedTask.assigned_user_id || ""],
                        selectedTask.assigned_user_id
                      )}
                    />
                    <DetailField label="Created Date" value={formatTaskDateTime(selectedTask.created_at)} />
                    <DetailField label="Updated Date" value={formatTaskDateTime(selectedTask.updated_at)} />
                    <DetailField label="Completed Date" value={formatTaskDateTime(selectedTask.completed_at)} />
                    <DetailField label="Description" value={selectedTask.description || "Not available"} />
                  </Box>
                </SectionCard>

                <SectionCard title="Related Lead" icon={<TimelineOutlinedIcon fontSize="small" />}>
                  <Box
                    sx={{
                      display: "grid",
                      gap: 1.25,
                      gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                    }}
                  >
                    <DetailField label="Lead Title" value={detailData.lead?.title || "Not available"} />
                    <DetailField label="Lead Stage" value={formatTaskLabel(detailData.lead?.lead_stage)} />
                    <DetailField
                      label="Probability"
                      value={
                        detailData.lead?.probability_pct != null
                          ? `${detailData.lead.probability_pct}%`
                          : "Not available"
                      }
                    />
                    <DetailField label="Next Action" value={selectedTask.title || "Not available"} />
                  </Box>
                </SectionCard>

                <SectionCard title="Related Prospect" icon={<OpenInNewOutlinedIcon fontSize="small" />}>
                  <Box
                    sx={{
                      display: "grid",
                      gap: 1.25,
                      gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                    }}
                  >
                    <DetailField
                      label="Organization"
                      value={detailData.prospect?.organization_name || "Not available"}
                    />
                    <DetailField label="Country" value={detailData.prospect?.country || "Not available"} />
                    <DetailField label="Industry" value={detailData.prospect?.industry || "Not available"} />
                    <DetailField
                      label="Primary Contact"
                      value={
                        primaryContact
                          ? primaryContact.full_name || primaryContact.job_title || primaryContact.email || "Not available"
                          : "Not available"
                      }
                    />
                  </Box>
                </SectionCard>
              </Stack>
            ) : null}
          </Box>
        </Box>
      </Drawer>

      <AppNotificationToast
        open={toastOpen}
        onClose={() => setToastOpen(false)}
        message={toastMessage}
        severity={toastSeverity}
      />
    </OutletPage>
  );
}
