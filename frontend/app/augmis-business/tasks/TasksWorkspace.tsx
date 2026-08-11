"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import AddTaskOutlinedIcon from "@mui/icons-material/AddTaskOutlined";
import AssignmentTurnedInOutlinedIcon from "@mui/icons-material/AssignmentTurnedInOutlined";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import EventBusyOutlinedIcon from "@mui/icons-material/EventBusyOutlined";
import EventNoteOutlinedIcon from "@mui/icons-material/EventNoteOutlined";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import TaskAltOutlinedIcon from "@mui/icons-material/TaskAltOutlined";
import TimelineOutlinedIcon from "@mui/icons-material/TimelineOutlined";
import WorkOutlineOutlinedIcon from "@mui/icons-material/WorkOutlineOutlined";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  InputAdornment,
  MenuItem,
  Paper,
  Stack,
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
  TaskPriorityChip,
  TaskStatusChip,
  formatTaskDateTime,
  formatTaskLabel,
  getTaskDueColor,
  isTaskDueToday,
  isTaskOverdue,
  isTaskUpcoming,
} from "../components/BusinessTaskUI";
import BusinessDataTable, { type BusinessDataTableColumn } from "../components/BusinessDataTable";
import BusinessDetailDrawer from "../components/BusinessDetailDrawer";
import BusinessFilterBar from "../components/BusinessFilterBar";
import BusinessMetricCarousel, { type BusinessMetricItem } from "../components/BusinessMetricCarousel";
import BusinessPageFrame from "../components/BusinessPageFrame";
import BusinessRowActionMenu from "../components/BusinessRowActionMenu";
import BusinessTabs, { type BusinessTabItem } from "../components/BusinessTabs";

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

function completedResultCount(tasks: AugmisBusinessTask[], timingView: TimingView, total: number) {
  if (timingView === "completed") {
    return total;
  }
  return tasks.filter((task) => task.task_status === "completed").length;
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
  const [tasks, setTasks] = useState<AugmisBusinessTask[]>([]);
  const [leadOptions, setLeadOptions] = useState<AugmisBusinessLead[]>([]);
  const [leadMap, setLeadMap] = useState<Record<string, AugmisBusinessLead>>({});
  const [assignedUserMap, setAssignedUserMap] = useState<ResolvedUserMap>({});
  const [assignableUserOptions, setAssignableUserOptions] = useState<AugmisBusinessAssignableUser[]>([]);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [leadFilter, setLeadFilter] = useState("all");
  const [assignedUserFilter, setAssignedUserFilter] = useState("all");
  const [timingView, setTimingView] = useState<TimingView>("all");
  const [taskSortBy, setTaskSortBy] = useState("due_at");
  const [taskSortOrder, setTaskSortOrder] = useState<"asc" | "desc">("asc");
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

  const taskStatusFilter =
    timingView === "in_progress" || timingView === "completed" ? timingView : undefined;

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
          status: taskStatusFilter,
          priority: priorityFilter !== "all" ? priorityFilter : undefined,
          lead_id: leadFilter !== "all" ? leadFilter : undefined,
          assigned_user_id: assignedUserFilter !== "all" ? assignedUserFilter : undefined,
          sort_by: taskSortBy,
          sort_order: taskSortOrder,
        };

        const [dashboardResult, taskResult, leadListResult, inProgressResult, completedResult, assignableUsersResult] =
          await Promise.all([
            getAugmisBusinessDashboard(),
            listAugmisBusinessTasks(baseTaskParams),
            listAugmisBusinessLeads({ page: 1, page_size: 100 }),
            listAugmisBusinessTasks({ page: 1, page_size: 1, status: "in_progress" }),
            listAugmisBusinessTasks({ page: 1, page_size: 1, status: "completed" }),
            listAugmisBusinessAssignableUsers({
              include_inactive: true,
              limit: 200,
            }),
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
        const relatedAssignableUsersResult = uniqueAssignedUserIds.length
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
        const nextAssignedUserMap = (relatedAssignableUsersResult.data || []).reduce<ResolvedUserMap>(
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
        setAssignableUserOptions(assignableUsersResult.data || []);
        setTotal(taskResult.pagination?.total || 0);
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
        setAssignableUserOptions([]);
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
  }, [
    assignedUserFilter,
    canRead,
    leadFilter,
    page,
    pageSize,
    priorityFilter,
    refreshTick,
    search,
    taskSortBy,
    taskSortOrder,
    taskStatusFilter,
  ]);

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
  const metricItems = useMemo<BusinessMetricItem[]>(
    () => [
      {
        key: "open",
        title: "Open",
        value: total,
        subtitle: "Matching open task records",
        icon: <TaskAltOutlinedIcon fontSize="small" />,
        accent: "linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)",
      },
      {
        key: "overdue",
        title: "Overdue",
        value: dashboard?.overdue_tasks ?? 0,
        subtitle: "Open or in-progress tasks past due",
        icon: <EventBusyOutlinedIcon fontSize="small" />,
        accent: "linear-gradient(90deg, #FEE4E2 0%, #FFF5F4 100%)",
      },
      {
        key: "due-today",
        title: "Due Today",
        value: dashboard?.tasks_due_today ?? 0,
        subtitle: "Live tasks due before close of day",
        icon: <ScheduleOutlinedIcon fontSize="small" />,
        accent: "linear-gradient(90deg, #FEF3C7 0%, #FFFBEB 100%)",
      },
      {
        key: "upcoming",
        title: "Upcoming",
        value: displayedTasks.filter((task) => isTaskUpcoming(task)).length,
        subtitle: "Loaded tasks due after today",
        icon: <EventNoteOutlinedIcon fontSize="small" />,
        accent: "linear-gradient(90deg, #E0F2FE 0%, #F8FAFC 100%)",
      },
      {
        key: "completed",
        title: "Completed",
        value: completedResultCount(displayedTasks, timingView, total),
        subtitle: "Matching completed tasks",
        icon: <AssignmentTurnedInOutlinedIcon fontSize="small" />,
        accent: "linear-gradient(90deg, #DCFCE7 0%, #F0FDF4 100%)",
      },
    ],
    [dashboard?.overdue_tasks, dashboard?.tasks_due_today, displayedTasks, timingView, total]
  );
  const timingTabItems = useMemo<BusinessTabItem[]>(
    () =>
      TIMING_OPTIONS.map((option) => {
        const disabled =
          (option.value === "overdue" ||
            option.value === "due_today" ||
            option.value === "upcoming") &&
          !reliableTimingFilters;
        return {
          value: option.value,
          label: option.label,
          disabled,
        };
      }),
    [reliableTimingFilters]
  );
  const taskColumns = useMemo<BusinessDataTableColumn<AugmisBusinessTask>[]>(
    () => [
      {
        key: "title",
        label: "Task",
        sortable: true,
        width: 250,
        render: (task) => (
          <Box sx={{ minWidth: 0 }}>
            <Typography
              sx={{
                fontWeight: 700,
                color: "#0F172A",
                display: "-webkit-box",
                WebkitBoxOrient: "vertical",
                WebkitLineClamp: 2,
                overflow: "hidden",
                whiteSpace: "normal",
              }}
            >
              {task.title}
            </Typography>
            <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12.5 }}>
              {formatTaskLabel(task.task_type)}
            </Typography>
          </Box>
        ),
      },
      {
        key: "priority",
        label: "Priority",
        sortable: true,
        width: 110,
        render: (task) => <TaskPriorityChip priority={task.priority} />,
      },
      {
        key: "due_at",
        label: "Due Date",
        sortable: true,
        width: 150,
        render: (task) => (
          <Typography sx={{ color: getTaskDueColor(task), fontWeight: 600 }}>
            {formatTaskDateTime(task.due_at)}
          </Typography>
        ),
      },
      {
        key: "status",
        label: "Status",
        sortable: true,
        width: 120,
        render: (task) => <TaskStatusChip status={task.task_status} />,
      },
      {
        key: "assignee",
        label: "Assignee",
        sortable: true,
        width: 220,
        render: (task) => {
          const assigned = getAssignedUserDisplay(task.assigned_user_id);
          return (
            <Box sx={{ minWidth: 0 }}>
              <Typography sx={{ color: "#0F172A", fontWeight: 600, lineHeight: 1.2 }}>
                {assigned.primary}
              </Typography>
              {assigned.secondary ? (
                <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12 }}>
                  {assigned.secondary}
                </Typography>
              ) : null}
            </Box>
          );
        },
      },
      {
        key: "lead",
        label: "Lead",
        width: 220,
        render: (task) => (
          <Box sx={{ minWidth: 0 }}>
            <Typography
              sx={{
                color: "#0F172A",
                fontWeight: 600,
                display: "-webkit-box",
                WebkitBoxOrient: "vertical",
                WebkitLineClamp: 2,
                overflow: "hidden",
                whiteSpace: "normal",
              }}
            >
              {findLeadTitle(leadMap, task)}
            </Typography>
            <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12.5 }}>
              {findProspectName(leadMap, task)}
            </Typography>
          </Box>
        ),
      },
      {
        key: "actions",
        label: "Actions",
        align: "right",
        width: 130,
        render: (task) => (
          <BusinessRowActionMenu
            onView={() => void openTaskDetail(task)}
            menuItems={[
              {
                key: "edit",
                label: "Edit Task",
                icon: <EditOutlinedIcon fontSize="small" />,
                disabled: !canUpdate,
                onClick: () => openEditDialog(task),
              },
              {
                key: "complete",
                label: "Complete Task",
                icon: <AssignmentTurnedInOutlinedIcon fontSize="small" />,
                disabled: !canUpdate || task.task_status === "completed",
                onClick: () => openCompleteDialog(task),
              },
            ]}
          />
        ),
      },
    ],
    [canUpdate, leadMap]
  );

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
    <BusinessPageFrame
      title="Business Development Tasks"
      description="Manage live follow-up work, due dates, and sales execution tasks across AUGMIS Business."
    >
      <Stack spacing={2.5}>
        {error ? <Alert severity="error">{error}</Alert> : null}
        <BusinessMetricCarousel items={metricItems} />

        <BusinessFilterBar
          filters={
            <Stack spacing={1.2}>
              <Box
                sx={{
                  display: "grid",
                  gap: 1.1,
                  gridTemplateColumns: { xs: "1fr", md: "repeat(4, minmax(0, 1fr))" },
                }}
              >
                <TextField
                  label="Search"
                  size="small"
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="Search tasks"
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
                <AdminFormTextField
                  select
                  label="Assigned To"
                  value={assignedUserFilter}
                  onChange={(event) => {
                    setAssignedUserFilter(event.target.value);
                    setPage(0);
                  }}
                >
                  <MenuItem value="all">All assignees</MenuItem>
                  {assignableUserOptions.map((user) => (
                    <MenuItem key={user.user_id} value={user.user_id}>
                      {getUserLabel(user) || user.user_id}
                    </MenuItem>
                  ))}
                </AdminFormTextField>
              </Box>
              <BusinessTabs
                compact
                value={timingView}
                onChange={(value) => setTimingView(value as TimingView)}
                items={timingTabItems}
              />
              {!reliableTimingFilters ? (
                <Alert severity="info" sx={{ borderRadius: "8px" }}>
                  Overdue, Due Today, and Upcoming views stay disabled when pagination means the
                  loaded page may not contain the full matching set.
                </Alert>
              ) : null}
            </Stack>
          }
          actions={
            <>
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
                  sx={{ borderRadius: "8px", textTransform: "none", bgcolor: "#2563EB", "&:hover": { bgcolor: "#1D4ED8" } }}
                >
                  New Task
                </Button>
              ) : null}
            </>
          }
        />

        <BusinessDataTable
          title="Task Workspace"
          subtitle="Live follow-up work, due dates, assignees, and completion actions."
          icon={<TimelineOutlinedIcon fontSize="small" />}
          count={total.toLocaleString()}
          columns={taskColumns}
          rows={displayedTasks}
          loading={loading}
          error={null}
          emptyTitle="No tasks found"
          emptyDescription="No live tasks match the current filters. Adjust the filters or create a new task."
          sortBy={taskSortBy}
          sortOrder={taskSortOrder}
          onSortChange={(sortBy, sortOrder) => {
            setTaskSortBy(sortBy);
            setTaskSortOrder(sortOrder);
            setPage(0);
          }}
          page={page}
          pageSize={pageSize}
          total={total}
          onPageChange={setPage}
          onRowsPerPageChange={(rows) => {
            setPageSize(rows);
            setPage(0);
          }}
          minWidth={1220}
          tableLayout="fixed"
        />
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

      <BusinessDetailDrawer
        open={detailOpen}
        onClose={closeTaskDetail}
        title={selectedTask?.title || "Task"}
        subtitle="Live operational task context for the selected lead and prospect."
        chips={
          <>
            {selectedTask ? <TaskPriorityChip priority={selectedTask.priority} /> : null}
            {selectedTask ? <TaskStatusChip status={selectedTask.task_status} /> : null}
          </>
        }
        actions={
          <>
            {canUpdate && selectedTask?.task_status !== "completed" ? (
              <Button
                variant="contained"
                startIcon={<AssignmentTurnedInOutlinedIcon />}
                onClick={() => selectedTask && openCompleteDialog(selectedTask)}
                sx={{ textTransform: "none", bgcolor: "#2563EB", "&:hover": { bgcolor: "#1D4ED8" } }}
              >
                Complete
              </Button>
            ) : null}
            {canUpdate ? (
              <Button
                variant="outlined"
                startIcon={<EditOutlinedIcon />}
                onClick={() => selectedTask && openEditDialog(selectedTask)}
                sx={{ textTransform: "none" }}
              >
                Edit
              </Button>
            ) : null}
          </>
        }
        loading={detailLoading}
        error={detailError}
        width={640}
      >
        {selectedTask ? (
          <>
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
          </>
        ) : null}
      </BusinessDetailDrawer>

      <AppNotificationToast
        open={toastOpen}
        onClose={() => setToastOpen(false)}
        message={toastMessage}
        severity={toastSeverity}
      />
    </BusinessPageFrame>
  );
}
