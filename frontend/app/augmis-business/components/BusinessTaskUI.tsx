"use client";

import { Chip, Typography } from "@mui/material";

import type { AugmisBusinessTask } from "@/services/augmisBusinessService";

function taskStatusColors(status: string) {
  switch (status) {
    case "completed":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "cancelled":
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
    case "in_progress":
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
    default:
      return { bgcolor: "#FFFAEB", color: "#B54708", borderColor: "#FEDF89" };
  }
}

function taskPriorityColors(priority: string) {
  switch (priority) {
    case "high":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
    case "medium":
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
    default:
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
  }
}

export function formatTaskLabel(value: string | null | undefined) {
  if (!value) {
    return "Not available";
  }
  return value.replaceAll("_", " ");
}

export function formatTaskDateTime(value: string | null | undefined) {
  if (!value) {
    return "Not available";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export function isTaskOverdue(task: Pick<AugmisBusinessTask, "due_at" | "task_status">) {
  if (!task.due_at || task.task_status === "completed" || task.task_status === "cancelled") {
    return false;
  }
  return new Date(task.due_at).getTime() < Date.now();
}

export function isTaskDueToday(task: Pick<AugmisBusinessTask, "due_at" | "task_status">) {
  if (!task.due_at || task.task_status === "completed" || task.task_status === "cancelled") {
    return false;
  }
  const due = new Date(task.due_at);
  const now = new Date();
  return due.toDateString() === now.toDateString();
}

export function isTaskUpcoming(task: Pick<AugmisBusinessTask, "due_at" | "task_status">) {
  if (!task.due_at || task.task_status === "completed" || task.task_status === "cancelled") {
    return false;
  }
  const due = new Date(task.due_at);
  const tomorrow = new Date();
  tomorrow.setHours(23, 59, 59, 999);
  return due.getTime() > tomorrow.getTime();
}

export function getTaskDueColor(task: Pick<AugmisBusinessTask, "due_at" | "task_status">) {
  if (!task.due_at) {
    return "#475569";
  }
  if (isTaskOverdue(task)) {
    return "#B42318";
  }
  if (isTaskDueToday(task)) {
    return "#B54708";
  }
  if (task.task_status === "completed") {
    return "#067647";
  }
  return "#0F172A";
}

export function getTaskTimingLabel(task: Pick<AugmisBusinessTask, "due_at" | "task_status">) {
  if (task.task_status === "completed") {
    return "Completed";
  }
  if (task.task_status === "cancelled") {
    return "Cancelled";
  }
  if (!task.due_at) {
    return "No due date";
  }
  const due = new Date(task.due_at);
  const dueStart = new Date(due);
  dueStart.setHours(0, 0, 0, 0);
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  const diffDays = Math.round((dueStart.getTime() - todayStart.getTime()) / 86400000);

  if (diffDays < 0) {
    return `Overdue by ${Math.abs(diffDays)} day${Math.abs(diffDays) === 1 ? "" : "s"}`;
  }
  if (diffDays === 0) {
    return "Due today";
  }
  if (diffDays === 1) {
    return "Due tomorrow";
  }
  return `Due in ${diffDays} days`;
}

export function TaskStatusChip({ status }: { status: string }) {
  return (
    <Chip
      size="small"
      label={formatTaskLabel(status)}
      sx={{
        textTransform: "capitalize",
        border: "1px solid",
        fontWeight: 600,
        ...taskStatusColors(status),
      }}
    />
  );
}

export function TaskPriorityChip({ priority }: { priority: string }) {
  return (
    <Chip
      size="small"
      label={formatTaskLabel(priority)}
      sx={{
        textTransform: "capitalize",
        border: "1px solid",
        fontWeight: 600,
        ...taskPriorityColors(priority),
      }}
    />
  );
}

export function TaskDueIndicator({ task }: { task: Pick<AugmisBusinessTask, "due_at" | "task_status"> }) {
  return (
    <Typography sx={{ color: getTaskDueColor(task), fontWeight: 600, fontSize: 12.5 }}>
      {getTaskTimingLabel(task)}
    </Typography>
  );
}
