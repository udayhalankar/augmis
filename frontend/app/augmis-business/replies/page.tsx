"use client";

import { useEffect, useEffectEvent, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import AddCommentOutlinedIcon from "@mui/icons-material/AddCommentOutlined";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import EmailOutlinedIcon from "@mui/icons-material/EmailOutlined";
import EventNoteOutlinedIcon from "@mui/icons-material/EventNoteOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import LowPriorityOutlinedIcon from "@mui/icons-material/LowPriorityOutlined";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import SendOutlinedIcon from "@mui/icons-material/SendOutlined";
import TaskAltOutlinedIcon from "@mui/icons-material/TaskAltOutlined";
import TimelineOutlinedIcon from "@mui/icons-material/TimelineOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  CircularProgress,
  Drawer,
  IconButton,
  InputAdornment,
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
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";

import { AppNotificationToast } from "@/components/feedback/AppNotificationToast";
import {
  AdminTableCard,
  ADMIN_TABLE_CARD_PAGINATION_SX,
} from "@/components/data-display/AdminTableCard";
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
  type AugmisBusinessLead,
  type AugmisBusinessReply,
  type AugmisBusinessReplyAnalysis,
  type AugmisBusinessReplyAnalysisSummary,
  type AugmisBusinessReplyChannel,
  type AugmisBusinessReplyEngagementLevel,
  type AugmisBusinessReplyIntent,
  type AugmisBusinessReplyResponseDraft,
  type AugmisBusinessReplyResponseDraftSummary,
  type AugmisBusinessReplyResponseStrategy,
  type AugmisBusinessReplyStatus,
  type AugmisBusinessReplyUrgency,
  analyzeAugmisBusinessReply,
  approveAugmisBusinessReplyResponse,
  createAugmisBusinessReply,
  createAugmisBusinessTask,
  generateAugmisBusinessReplyResponse,
  getAugmisBusinessReply,
  getAugmisBusinessReplyAnalysis,
  getAugmisBusinessReplyResponse,
  getAugmisBusinessProspectContacts,
  listAugmisBusinessAssignableUsers,
  listAugmisBusinessLeads,
  listAugmisBusinessReplies,
  listAugmisBusinessReplyAnalyses,
  listAugmisBusinessReplyResponses,
  rejectAugmisBusinessReplyResponse,
  updateAugmisBusinessLead,
  updateAugmisBusinessLeadStage,
  updateAugmisBusinessReplyResponse,
} from "@/services/augmisBusinessService";
import BusinessStatusCardStrip, {
  type BusinessStatusCardItem,
} from "../components/BusinessStatusCardStrip";
import BusinessPageFrame from "../components/BusinessPageFrame";
import {
  BUSINESS_TABLE_COMPACT_SX,
  BUSINESS_TABLE_SINGLE_LINE_TEXT_SX,
} from "../components/BusinessDataTable";

type ToastSeverity = "success" | "error" | "info" | "warning";
type DetailTab = "message" | "analysis" | "response" | "context" | "history";

type RecordReplyForm = {
  lead_id: string;
  contact_id: string;
  channel: AugmisBusinessReplyChannel;
  subject: string;
  raw_message: string;
  sender_display: string;
  received_at: string;
  notes: string;
};

type TaskForm = {
  title: string;
  task_type: string;
  priority: "high" | "medium" | "low";
  description: string;
  due_at: string;
  assigned_user_id: string;
};

const CHANNEL_OPTIONS: Array<{ value: AugmisBusinessReplyChannel; label: string }> = [
  { value: "email", label: "Email" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "phone_summary", label: "Phone Summary" },
  { value: "meeting_note", label: "Meeting Note" },
  { value: "website_message", label: "Website Message" },
  { value: "procurement_portal", label: "Procurement Portal" },
  { value: "other", label: "Other" },
];

const STATUS_OPTIONS: Array<{ value: AugmisBusinessReplyStatus | "all"; label: string }> = [
  { value: "all", label: "All Statuses" },
  { value: "received", label: "Received" },
  { value: "analyzed", label: "Analyzed" },
  { value: "action_required", label: "Action Required" },
  { value: "responded", label: "Responded" },
  { value: "archived", label: "Archived" },
];

const INTENT_OPTIONS: Array<{ value: AugmisBusinessReplyIntent | "all"; label: string }> = [
  { value: "all", label: "All Intents" },
  { value: "interested", label: "Interested" },
  { value: "needs_more_information", label: "Needs Information" },
  { value: "meeting_requested", label: "Meeting Requested" },
  { value: "demo_requested", label: "Demo Requested" },
  { value: "proposal_requested", label: "Proposal Requested" },
  { value: "pricing_requested", label: "Pricing Requested" },
  { value: "technical_questions", label: "Technical Questions" },
  { value: "procurement_process", label: "Procurement Process" },
  { value: "legal_compliance", label: "Legal / Compliance" },
  { value: "objection", label: "Objection" },
  { value: "defer", label: "Defer" },
  { value: "not_interested", label: "Not Interested" },
  { value: "wrong_contact", label: "Wrong Contact" },
  { value: "referral", label: "Referral" },
  { value: "out_of_office", label: "Out of Office" },
  { value: "neutral", label: "Neutral" },
  { value: "unclear", label: "Unclear" },
];

const RESPONSE_STRATEGIES: Array<{
  value: AugmisBusinessReplyResponseStrategy;
  label: string;
}> = [
  { value: "consultative", label: "Consultative" },
  { value: "concise", label: "Concise" },
  { value: "technical", label: "Technical" },
  { value: "executive", label: "Executive" },
  { value: "objection_handling", label: "Objection Handling" },
  { value: "procurement", label: "Procurement" },
];

const EMPTY_RECORD_FORM: RecordReplyForm = {
  lead_id: "",
  contact_id: "",
  channel: "email",
  subject: "",
  raw_message: "",
  sender_display: "",
  received_at: "",
  notes: "",
};

const EMPTY_TASK_FORM: TaskForm = {
  title: "",
  task_type: "follow_up",
  priority: "medium",
  description: "",
  due_at: "",
  assigned_user_id: "",
};

function formatDateTime(value: string | null | undefined) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatLabel(value: string | null | undefined) {
  if (!value) return "Not available";
  return value.replaceAll("_", " ");
}

function toDatetimeLocalValue(value: string | null | undefined) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 16);
}

function fromDatetimeLocalValue(value: string) {
  return value ? new Date(value).toISOString() : null;
}

function getIntentChip(intent: AugmisBusinessReplyIntent | null) {
  switch (intent) {
    case "meeting_requested":
    case "proposal_requested":
    case "demo_requested":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "pricing_requested":
    case "needs_more_information":
    case "technical_questions":
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
    case "objection":
    case "procurement_process":
    case "legal_compliance":
      return { bgcolor: "#FFFAEB", color: "#B54708", borderColor: "#FEDF89" };
    case "not_interested":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
    default:
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
  }
}

function getUrgencyChip(urgency: AugmisBusinessReplyUrgency | null) {
  switch (urgency) {
    case "urgent":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
    case "high":
      return { bgcolor: "#FFF7ED", color: "#C2410C", borderColor: "#FDBA74" };
    case "normal":
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
    default:
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
  }
}

function getEngagementChip(engagement: AugmisBusinessReplyEngagementLevel | null) {
  switch (engagement) {
    case "high":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "medium":
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
    case "low":
      return { bgcolor: "#FFFAEB", color: "#B54708", borderColor: "#FEDF89" };
    case "none":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
    default:
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
  }
}

function getStatusChip(status: AugmisBusinessReplyStatus | string | null | undefined) {
  switch (status) {
    case "action_required":
      return { bgcolor: "#FFF7ED", color: "#C2410C", borderColor: "#FDBA74" };
    case "analyzed":
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
    case "responded":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "archived":
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
    default:
      return { bgcolor: "#EEF2FF", color: "#4338CA", borderColor: "#C7D2FE" };
  }
}

function getResponseStatusChip(status: string | null | undefined) {
  switch (status) {
    case "approved":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "rejected":
      return { bgcolor: "#FEF2F2", color: "#B42318", borderColor: "#FECDCA" };
    case "reviewed":
      return { bgcolor: "#EFF8FF", color: "#175CD3", borderColor: "#B2DDFF" };
    case "superseded":
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
    default:
      return { bgcolor: "#EEF2FF", color: "#4338CA", borderColor: "#C7D2FE" };
  }
}

function FieldCard({ label, value }: { label: string; value: string }) {
  return (
    <Paper
      elevation={0}
      sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0", minHeight: 84 }}
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
      <Typography sx={{ mt: 0.75, color: "#0F172A", fontWeight: 600 }}>{value}</Typography>
    </Paper>
  );
}

export default function AugmisBusinessRepliesPage() {
  const searchParams = useSearchParams();
  const { hasPermission } = useAuth();
  const canRead = hasPermission("business_development:read");
  const canCreate = hasPermission("business_development:create");
  const canUpdate = hasPermission("business_development:update");
  const canOutreach = hasPermission("business_development:outreach");

  const leadIdFromQuery = searchParams.get("lead_id") || "";
  const [replies, setReplies] = useState<AugmisBusinessReply[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<AugmisBusinessReplyStatus | "all">("all");
  const [intentFilter, setIntentFilter] = useState<AugmisBusinessReplyIntent | "all">("all");
  const selectedLeadFilter = leadIdFromQuery;
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [summary, setSummary] = useState({
    unreviewed_replies: 0,
    action_required: 0,
    positive_high_engagement: 0,
    objections: 0,
    meetings_or_proposals: 0,
  });
  const [total, setTotal] = useState(0);
  const [toast, setToast] = useState<{ open: boolean; message: string; severity: ToastSeverity }>(
    { open: false, message: "", severity: "success" }
  );

  const [leadOptions, setLeadOptions] = useState<AugmisBusinessLead[]>([]);
  const [contactOptions, setContactOptions] = useState<AugmisBusinessContact[]>([]);
  const [recordOpen, setRecordOpen] = useState(false);
  const [recordSaving, setRecordSaving] = useState(false);
  const [recordError, setRecordError] = useState("");
  const [recordForm, setRecordForm] = useState<RecordReplyForm>({
    ...EMPTY_RECORD_FORM,
    lead_id: leadIdFromQuery,
    received_at: toDatetimeLocalValue(new Date().toISOString()),
  });
  const [recordFieldErrors, setRecordFieldErrors] = useState<Record<string, string>>({});

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailTab, setDetailTab] = useState<DetailTab>("message");
  const [selectedReplyId, setSelectedReplyId] = useState<string | null>(null);
  const [selectedReply, setSelectedReply] = useState<AugmisBusinessReply | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [analyses, setAnalyses] = useState<AugmisBusinessReplyAnalysisSummary[]>([]);
  const [analysis, setAnalysis] = useState<AugmisBusinessReplyAnalysis | null>(null);
  const [responses, setResponses] = useState<AugmisBusinessReplyResponseDraftSummary[]>([]);
  const [responseDraft, setResponseDraft] = useState<AugmisBusinessReplyResponseDraft | null>(null);
  const [strategy, setStrategy] = useState<AugmisBusinessReplyResponseStrategy>("consultative");
  const [responseSubject, setResponseSubject] = useState("");
  const [responseBody, setResponseBody] = useState("");
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [responseBusy, setResponseBusy] = useState(false);
  const [responseSaving, setResponseSaving] = useState(false);
  const [responseStatusBusy, setResponseStatusBusy] = useState(false);

  const [taskDialogOpen, setTaskDialogOpen] = useState(false);
  const [taskSaving, setTaskSaving] = useState(false);
  const [taskForm, setTaskForm] = useState<TaskForm>(EMPTY_TASK_FORM);
  const [taskFieldErrors, setTaskFieldErrors] = useState<Record<string, string>>({});
  const [assignableUsers, setAssignableUsers] = useState<AugmisBusinessAssignableUser[]>([]);
  const [selectedAssignee, setSelectedAssignee] = useState<AugmisBusinessAssignableUser | null>(null);

  function showToast(message: string, severity: ToastSeverity) {
    setToast({ open: true, message, severity });
  }

  async function loadLeads() {
    const result = await listAugmisBusinessLeads({ page: 1, page_size: 100 });
    setLeadOptions(result.data || []);
  }

  async function loadContactsForLead(leadId: string) {
    const lead = leadOptions.find((item) => item.id === leadId);
    if (!lead?.prospect_id) {
      setContactOptions([]);
      return;
    }
    const result = await getAugmisBusinessProspectContacts(lead.prospect_id);
    setContactOptions(result.data || []);
    if (!recordForm.contact_id && lead.primary_contact_id) {
      setRecordForm((current) => ({ ...current, contact_id: lead.primary_contact_id || "" }));
    }
  }

  async function loadReplies() {
    setLoading(true);
    try {
      const result = await listAugmisBusinessReplies({
        page: page + 1,
        page_size: rowsPerPage,
        search: search || undefined,
        status: statusFilter,
        intent: intentFilter,
        lead_id: selectedLeadFilter || undefined,
      });
      setReplies(result.data || []);
      setSummary(result.summary);
      setTotal(result.pagination.total);
    } catch (error) {
      showToast(parseApiValidationError(error, "Unable to load replies.").message, "error");
    } finally {
      setLoading(false);
    }
  }

  async function loadReplyDetail(replyId: string) {
    setDetailLoading(true);
    setDetailError("");
    try {
      const [replyResult, analysesResult, responsesResult] = await Promise.all([
        getAugmisBusinessReply(replyId),
        listAugmisBusinessReplyAnalyses(replyId),
        listAugmisBusinessReplyResponses(replyId),
      ]);
      setSelectedReply(replyResult.data);
      setAnalyses(analysesResult.data || []);
      setResponses(responsesResult.data || []);
      if (analysesResult.data?.length) {
        try {
          const latestAnalysis = await getAugmisBusinessReplyAnalysis(replyId);
          setAnalysis(latestAnalysis.data);
        } catch {
          setAnalysis(null);
        }
      } else {
        setAnalysis(null);
      }
      if (responsesResult.data?.length) {
        const latestResponse = await getAugmisBusinessReplyResponse(responsesResult.data[0].id);
        setResponseDraft(latestResponse.data);
        setResponseSubject(latestResponse.data.subject || "");
        setResponseBody(latestResponse.data.body || "");
        setStrategy(latestResponse.data.structured_content_json.tone);
      } else {
        setResponseDraft(null);
        setResponseSubject("");
        setResponseBody("");
      }
    } catch (error) {
      setDetailError(parseApiValidationError(error, "Unable to load reply detail.").message);
    } finally {
      setDetailLoading(false);
    }
  }

  const triggerLoadReplies = useEffectEvent(() => {
    void loadReplies();
  });

  const triggerLoadContactsForLead = useEffectEvent((leadId: string) => {
    void loadContactsForLead(leadId);
  });

  useEffect(() => {
    if (!canRead) return;
    const handle = window.setTimeout(() => {
      triggerLoadReplies();
    }, 0);
    return () => window.clearTimeout(handle);
  }, [canRead, page, rowsPerPage, search, statusFilter, intentFilter, selectedLeadFilter]);

  useEffect(() => {
    if (!canCreate) return;
    const handle = window.setTimeout(() => {
      void loadLeads().catch(() => undefined);
    }, 0);
    return () => window.clearTimeout(handle);
  }, [canCreate]);

  useEffect(() => {
    if (!recordForm.lead_id) {
      return;
    }
    const handle = window.setTimeout(() => {
      triggerLoadContactsForLead(recordForm.lead_id);
    }, 0);
    return () => window.clearTimeout(handle);
  }, [recordForm.lead_id, leadOptions]);

  const selectedLead = useMemo(
    () => leadOptions.find((lead) => lead.id === recordForm.lead_id) || null,
    [leadOptions, recordForm.lead_id]
  );

  async function openDetail(replyId: string, initialTab: DetailTab = "message") {
    setSelectedReplyId(replyId);
    setDetailTab(initialTab);
    setDetailOpen(true);
    await loadReplyDetail(replyId);
  }

  function resetRecordDialog() {
    setRecordForm({
      ...EMPTY_RECORD_FORM,
      lead_id: selectedLeadFilter || leadIdFromQuery,
      received_at: toDatetimeLocalValue(new Date().toISOString()),
    });
    setRecordFieldErrors({});
    setRecordError("");
  }

  async function handleSaveReply() {
    const errors: Record<string, string> = {};
    if (!recordForm.lead_id) errors.lead_id = "Lead is required.";
    if (!recordForm.raw_message.trim()) errors.raw_message = "Reply message is required.";
    if (!recordForm.received_at) errors.received_at = "Received date and time are required.";
    setRecordFieldErrors(errors);
    if (Object.keys(errors).length) return;

    setRecordSaving(true);
    setRecordError("");
    try {
      const result = await createAugmisBusinessReply({
        lead_id: recordForm.lead_id,
        contact_id: recordForm.contact_id || null,
        channel: recordForm.channel,
        subject: recordForm.subject.trim() || null,
        raw_message: recordForm.raw_message.trim(),
        sender_display: recordForm.sender_display.trim() || null,
        received_at: fromDatetimeLocalValue(recordForm.received_at) || new Date().toISOString(),
        notes: recordForm.notes.trim() || null,
      });
      setRecordOpen(false);
      resetRecordDialog();
      showToast("Reply recorded successfully.", "success");
      await loadReplies();
      await openDetail(result.data.id, "message");
    } catch (error) {
      setRecordError(parseApiValidationError(error, "Unable to record reply.").message);
    } finally {
      setRecordSaving(false);
    }
  }

  async function handleAnalyzeReply() {
    if (!selectedReplyId) return;
    setAnalysisBusy(true);
    setDetailError("");
    try {
      const result = await analyzeAugmisBusinessReply(selectedReplyId);
      setAnalysis(result.data);
      showToast("Reply analyzed successfully.", "success");
      await loadReplyDetail(selectedReplyId);
      await loadReplies();
      setDetailTab("analysis");
    } catch (error) {
      setDetailError(parseApiValidationError(error, "Unable to analyze reply.").message);
    } finally {
      setAnalysisBusy(false);
    }
  }

  async function handleGenerateResponse() {
    if (!selectedReplyId) return;
    setResponseBusy(true);
    setDetailError("");
    try {
      const result = await generateAugmisBusinessReplyResponse(selectedReplyId, {
        strategy,
      });
      setResponseDraft(result.data);
      setResponseSubject(result.data.subject || "");
      setResponseBody(result.data.body || "");
      showToast("Response draft generated successfully.", "success");
      await loadReplyDetail(selectedReplyId);
      setDetailTab("response");
    } catch (error) {
      setDetailError(parseApiValidationError(error, "Unable to generate response draft.").message);
    } finally {
      setResponseBusy(false);
    }
  }

  async function handleSaveResponseDraft() {
    if (!responseDraft) return;
    setResponseSaving(true);
    setDetailError("");
    try {
      const result = await updateAugmisBusinessReplyResponse(responseDraft.id, {
        subject: responseSubject || null,
        body: responseBody,
        structured_content_json: {
          ...responseDraft.structured_content_json,
          subject: responseSubject || null,
          full_message: responseBody,
          response_body: responseBody,
        },
        status: "reviewed",
      });
      setResponseDraft(result.data);
      setResponseSubject(result.data.subject || "");
      setResponseBody(result.data.body || "");
      showToast("Response draft saved.", "success");
      await loadReplyDetail(result.data.reply_id);
    } catch (error) {
      setDetailError(parseApiValidationError(error, "Unable to save response draft.").message);
    } finally {
      setResponseSaving(false);
    }
  }

  async function handleResponseStatus(action: "approve" | "reject") {
    if (!responseDraft) return;
    setResponseStatusBusy(true);
    setDetailError("");
    try {
      const result =
        action === "approve"
          ? await approveAugmisBusinessReplyResponse(responseDraft.id)
          : await rejectAugmisBusinessReplyResponse(responseDraft.id);
      setResponseDraft(result.data);
      showToast(
        action === "approve" ? "Response draft approved." : "Response draft rejected.",
        action === "approve" ? "success" : "warning"
      );
      await loadReplyDetail(result.data.reply_id);
    } catch (error) {
      setDetailError(parseApiValidationError(error, "Unable to update response status.").message);
    } finally {
      setResponseStatusBusy(false);
    }
  }

  async function handleCopyResponse() {
    if (!responseBody.trim()) return;
    await navigator.clipboard.writeText(`${responseSubject ? `${responseSubject}\n\n` : ""}${responseBody}`);
    showToast("Response draft copied to clipboard.", "success");
  }

  async function handleSelectResponseVersion(responseId: string) {
    try {
      const result = await getAugmisBusinessReplyResponse(responseId);
      setResponseDraft(result.data);
      setResponseSubject(result.data.subject || "");
      setResponseBody(result.data.body || "");
      setDetailTab("response");
    } catch (error) {
      setDetailError(parseApiValidationError(error, "Unable to load response version.").message);
    }
  }

  async function handleApplyStageRecommendation() {
    if (!selectedReply?.lead_id || !analysis?.recommended_pipeline_stage) return;
    try {
      await updateAugmisBusinessLeadStage(selectedReply.lead_id, {
        lead_stage: analysis.recommended_pipeline_stage,
      });
      showToast("Lead stage updated from AI recommendation.", "success");
      await loadReplyDetail(selectedReply.id);
    } catch (error) {
      setDetailError(parseApiValidationError(error, "Unable to update lead stage.").message);
    }
  }

  async function handleApplyProbabilityRecommendation() {
    if (!selectedReply?.lead_id || analysis?.analysis_json.recommended_probability == null) return;
    try {
      await updateAugmisBusinessLead(selectedReply.lead_id, {
        probability_pct: analysis.analysis_json.recommended_probability,
      });
      showToast("Lead probability updated from AI recommendation.", "success");
      await loadReplyDetail(selectedReply.id);
    } catch (error) {
      setDetailError(parseApiValidationError(error, "Unable to update lead probability.").message);
    }
  }

  async function openTaskRecommendationDialog() {
    if (!analysis?.analysis_json.recommended_task) return;
    const recommendation = analysis.analysis_json.recommended_task;
    const dueDate = new Date();
    if (recommendation.due_in_days != null) {
      dueDate.setDate(dueDate.getDate() + recommendation.due_in_days);
    }
    setTaskForm({
      title: recommendation.title,
      task_type: recommendation.task_type,
      priority: recommendation.priority,
      description: recommendation.reason,
      due_at: toDatetimeLocalValue(dueDate.toISOString()),
      assigned_user_id: "",
    });
    setTaskFieldErrors({});
    setTaskDialogOpen(true);
    try {
      const users = await listAugmisBusinessAssignableUsers({ limit: 25 });
      setAssignableUsers(users.data || []);
    } catch {
      setAssignableUsers([]);
    }
  }

  async function handleSaveRecommendedTask() {
    if (!selectedReply?.lead_id) return;
    const errors: Record<string, string> = {};
    if (!taskForm.title.trim()) errors.title = "Task title is required.";
    setTaskFieldErrors(errors);
    if (Object.keys(errors).length) return;
    setTaskSaving(true);
    try {
      await createAugmisBusinessTask({
        lead_id: selectedReply.lead_id,
        opportunity_id: selectedReply.opportunity_id,
        prospect_id: selectedReply.prospect_id,
        assigned_user_id: taskForm.assigned_user_id || null,
        title: taskForm.title.trim(),
        description: taskForm.description.trim() || null,
        task_type: taskForm.task_type,
        priority: taskForm.priority,
        due_at: fromDatetimeLocalValue(taskForm.due_at),
        metadata_json: { source_reply_id: selectedReply.id },
      });
      setTaskDialogOpen(false);
      showToast("Recommended task created.", "success");
      await loadReplyDetail(selectedReply.id);
    } catch (error) {
      setDetailError(parseApiValidationError(error, "Unable to create recommended task.").message);
    } finally {
      setTaskSaving(false);
    }
  }

  const replyStatusCards: BusinessStatusCardItem[] = [
    {
      key: "unreviewed",
      title: "Unreviewed Replies",
      value: summary.unreviewed_replies,
      description: "Inbound messages waiting for first review",
      icon: <EmailOutlinedIcon />,
      gradient: "linear-gradient(135deg, #FFFFFF 0%, #EAF2FF 100%)",
      iconTint: "#175CD3",
      iconSurface: "#DBEAFE",
    },
    {
      key: "action-required",
      title: "Action Required",
      value: summary.action_required,
      description: "Replies needing a deliberate operator decision",
      icon: <WarningAmberOutlinedIcon />,
      gradient: "linear-gradient(135deg, #FFFFFF 0%, #FFF2E8 100%)",
      iconTint: "#C2410C",
      iconSurface: "#FED7AA",
    },
    {
      key: "positive-high-engagement",
      title: "Positive / High Engagement",
      value: summary.positive_high_engagement,
      description: "Strong replies with real buying motion",
      icon: <InsightsOutlinedIcon />,
      gradient: "linear-gradient(135deg, #FFFFFF 0%, #E9FAF1 100%)",
      iconTint: "#047857",
      iconSurface: "#BBF7D0",
    },
    {
      key: "objections",
      title: "Objections",
      value: summary.objections,
      description: "Replies that surfaced explicit concerns",
      icon: <LowPriorityOutlinedIcon />,
      gradient: "linear-gradient(135deg, #FFFFFF 0%, #FFF8E1 100%)",
      iconTint: "#B54708",
      iconSurface: "#FDE68A",
    },
    {
      key: "meetings-or-proposals",
      title: "Meetings / Proposals",
      value: summary.meetings_or_proposals,
      description: "Replies indicating serious commercial interest",
      icon: <TimelineOutlinedIcon />,
      gradient: "linear-gradient(135deg, #FFFFFF 0%, #E7FAF7 100%)",
      iconTint: "#0F766E",
      iconSurface: "#99F6E4",
    },
  ];

  return (
    <BusinessPageFrame
      title="Replies Workspace"
      description="Capture inbound prospect replies, analyze intent, draft responses, and apply operator-approved next actions without any automatic sending."
    >
      <Stack spacing={2.5}>
        <BusinessStatusCardStrip items={replyStatusCards} />

        <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #D9E2EC", p: 2 }}>
          <Stack
            direction={{ xs: "column", lg: "row" }}
            spacing={1.5}
            sx={{ alignItems: { lg: "center" }, justifyContent: "space-between" }}
          >
            <Stack direction={{ xs: "column", md: "row" }} spacing={1.25}>
              <TextField
                value={search}
                onChange={(event) => {
                  setPage(0);
                  setSearch(event.target.value);
                }}
                placeholder="Search subject, sender, content, or reply ID"
                size="small"
                sx={{ minWidth: { md: 320 } }}
                slotProps={{
                  input: {
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchRoundedIcon sx={{ color: "#64748B" }} />
                      </InputAdornment>
                    ),
                  },
                }}
              />
              <TextField
                select
                label="Status"
                size="small"
                value={statusFilter}
                onChange={(event) => {
                  setPage(0);
                  setStatusFilter(event.target.value as AugmisBusinessReplyStatus | "all");
                }}
                sx={{ minWidth: 170 }}
              >
                {STATUS_OPTIONS.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label="Intent"
                size="small"
                value={intentFilter}
                onChange={(event) => {
                  setPage(0);
                  setIntentFilter(event.target.value as AugmisBusinessReplyIntent | "all");
                }}
                sx={{ minWidth: 210 }}
              >
                {INTENT_OPTIONS.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            <Stack direction="row" spacing={1}>
              <Button
                variant="outlined"
                startIcon={<RefreshRoundedIcon />}
                onClick={() => void loadReplies()}
                sx={{ borderRadius: "8px", textTransform: "none", fontWeight: 700 }}
              >
                Refresh
              </Button>
              {canCreate ? (
                <Button
                  variant="contained"
                  startIcon={<AddCommentOutlinedIcon />}
                  onClick={() => {
                    resetRecordDialog();
                    setRecordOpen(true);
                  }}
                  sx={{
                    borderRadius: "8px",
                    textTransform: "none",
                    fontWeight: 700,
                    bgcolor: "#175CD3",
                    "&:hover": { bgcolor: "#1249A9" },
                  }}
                >
                  Record Reply
                </Button>
              ) : null}
            </Stack>
          </Stack>
        </Paper>

        <AdminTableCard
          title={
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <EventNoteOutlinedIcon />
              <Typography component="span" sx={{ fontWeight: 700, color: "inherit" }}>
                Inbound Reply Queue
              </Typography>
            </Stack>
          }
          bodySx={{ bgcolor: "#FFFFFF" }}
          paperSx={{ bgcolor: "#FFFFFF" }}
        >
          {loading ? (
            <Stack sx={{ py: 8, alignItems: "center", color: "#475569" }} spacing={1}>
              <CircularProgress size={28} />
              <Typography>Loading replies...</Typography>
            </Stack>
          ) : replies.length ? (
            <>
              <Table size="small" sx={BUSINESS_TABLE_COMPACT_SX}>
                <TableHead>
                  <TableRow>
                    <TableCell>Received</TableCell>
                    <TableCell>Prospect</TableCell>
                    <TableCell>Contact</TableCell>
                    <TableCell>Lead</TableCell>
                    <TableCell>Channel</TableCell>
                    <TableCell>Subject / Preview</TableCell>
                    <TableCell>Intent</TableCell>
                    <TableCell>Engagement</TableCell>
                    <TableCell>Urgency</TableCell>
                    <TableCell>Analysis</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {replies.map((reply) => (
                    <TableRow key={reply.id} hover>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>{formatDateTime(reply.received_at)}</TableCell>
                      <TableCell sx={{ maxWidth: 180 }}>
                        <Box component="span" sx={BUSINESS_TABLE_SINGLE_LINE_TEXT_SX}>
                          {reply.prospect_name || "Not available"}
                        </Box>
                      </TableCell>
                      <TableCell sx={{ maxWidth: 180 }}>
                        <Box component="span" sx={BUSINESS_TABLE_SINGLE_LINE_TEXT_SX}>
                          {reply.contact_name || reply.sender_display || "Not available"}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="text"
                          onClick={() => void openDetail(reply.id)}
                          sx={{ px: 0, textTransform: "none", fontWeight: 700, minWidth: 0, width: "100%", justifyContent: "flex-start" }}
                        >
                          <Box component="span" sx={BUSINESS_TABLE_SINGLE_LINE_TEXT_SX}>
                            {reply.lead_title || reply.lead_id}
                          </Box>
                        </Button>
                      </TableCell>
                      <TableCell>{formatLabel(reply.channel)}</TableCell>
                      <TableCell sx={{ minWidth: 260, maxWidth: 260 }}>
                        <Box component="span" sx={BUSINESS_TABLE_SINGLE_LINE_TEXT_SX}>
                          {reply.subject || reply.raw_message || "No subject"}
                        </Box>
                      </TableCell>
                      <TableCell>
                        {reply.latest_intent ? (
                          <Chip
                            label={formatLabel(reply.latest_intent)}
                            size="small"
                            sx={{ ...getIntentChip(reply.latest_intent), border: "1px solid" }}
                          />
                        ) : (
                          "Not analyzed"
                        )}
                      </TableCell>
                      <TableCell>
                        {reply.latest_engagement_level ? (
                          <Chip
                            label={formatLabel(reply.latest_engagement_level)}
                            size="small"
                            sx={{ ...getEngagementChip(reply.latest_engagement_level), border: "1px solid" }}
                          />
                        ) : (
                          "Not analyzed"
                        )}
                      </TableCell>
                      <TableCell>
                        {reply.latest_urgency ? (
                          <Chip
                            label={formatLabel(reply.latest_urgency)}
                            size="small"
                            sx={{ ...getUrgencyChip(reply.latest_urgency), border: "1px solid" }}
                          />
                        ) : (
                          "Not analyzed"
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={formatLabel(reply.reply_status)}
                          size="small"
                          sx={{ ...getStatusChip(reply.reply_status), border: "1px solid" }}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end", alignItems: "center" }}>
                          <Tooltip title="View Reply">
                            <IconButton size="small" onClick={() => void openDetail(reply.id)} sx={{ border: "1px solid #DBEAFE", bgcolor: "#F8FBFF", borderRadius: "8px" }}>
                              <VisibilityOutlinedIcon sx={{ color: "#175CD3" }} fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          {canOutreach ? (
                            <Tooltip title="Analyze Reply">
                              <IconButton size="small" onClick={() => void openDetail(reply.id, "analysis")} sx={{ border: "1px solid #E9D5FF", bgcolor: "#FAF5FF", borderRadius: "8px" }}>
                                <AutoAwesomeOutlinedIcon sx={{ color: "#7C3AED" }} fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          ) : null}
                          {canOutreach ? (
                            <Tooltip title="Generate Response">
                              <IconButton size="small" onClick={() => void openDetail(reply.id, "response")} sx={{ border: "1px solid #A7F3D0", bgcolor: "#F0FDFA", borderRadius: "8px" }}>
                                <SendOutlinedIcon sx={{ color: "#0F766E" }} fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          ) : null}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <TablePagination
                component="div"
                count={total}
                page={page}
                onPageChange={(_, nextPage) => setPage(nextPage)}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={(event) => {
                  setRowsPerPage(Number(event.target.value));
                  setPage(0);
                }}
                rowsPerPageOptions={[10, 25, 50]}
                sx={ADMIN_TABLE_CARD_PAGINATION_SX}
              />
            </>
          ) : (
            <Stack sx={{ py: 8, px: 3, alignItems: "center", textAlign: "center" }} spacing={1.25}>
              <EmailOutlinedIcon sx={{ color: "#94A3B8", fontSize: 34 }} />
              <Typography sx={{ fontSize: 18, fontWeight: 700, color: "#0F172A" }}>
                No replies recorded yet
              </Typography>
              <Typography sx={{ maxWidth: 560, color: "#64748B" }}>
                Capture inbound email, LinkedIn, meeting-note, or procurement responses here. AI can analyze and draft a response, but the operator remains fully in control.
              </Typography>
            </Stack>
          )}
        </AdminTableCard>
      </Stack>

      <AdminFormDialog
        open={recordOpen}
        title="Record Inbound Reply"
        onClose={() => setRecordOpen(false)}
        maxWidth={760}
        actions={
          <>
            <Button onClick={() => setRecordOpen(false)} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={() => void handleSaveReply()}
              disabled={recordSaving}
              sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "#175CD3" }}
            >
              {recordSaving ? "Saving..." : "Record Reply"}
            </Button>
          </>
        }
      >
        <Stack spacing={2}>
          {recordError ? <Alert severity="error">{recordError}</Alert> : null}
          <AdminFormField label="Lead" helperText={recordFieldErrors.lead_id || "Required"}>
            <Autocomplete
              options={leadOptions}
              value={selectedLead}
              onChange={(_, value) => {
                setRecordForm((current) => ({
                  ...current,
                  lead_id: value?.id || "",
                  contact_id: value?.primary_contact_id || "",
                }));
              }}
              getOptionLabel={(option) => option.title || option.id}
              renderInput={(params) => <TextField {...params} size="small" placeholder="Select lead" />}
              renderOption={(props, option) => {
                const { key, ...optionProps } = props;
                return (
                <Box component="li" key={key} {...optionProps}>
                  <Stack spacing={0.2}>
                    <Typography sx={{ fontWeight: 700 }}>{option.title}</Typography>
                    <Typography sx={{ fontSize: 12, color: "#64748B" }}>
                      {option.prospect?.organization_name || option.prospect_id} • {formatLabel(option.lead_stage)}
                    </Typography>
                  </Stack>
                </Box>
                );
              }}
            />
          </AdminFormField>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <AdminFormTextField
              select
              label="Channel"
              value={recordForm.channel}
              onChange={(event) =>
                setRecordForm((current) => ({
                  ...current,
                  channel: event.target.value as AugmisBusinessReplyChannel,
                }))
              }
              required
            >
              {CHANNEL_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </AdminFormTextField>
            <AdminFormTextField
              label="Received Date / Time"
              type="datetime-local"
              value={recordForm.received_at}
              onChange={(event) =>
                setRecordForm((current) => ({ ...current, received_at: event.target.value }))
              }
              slotProps={{ inputLabel: { shrink: true } }}
              required
              error={Boolean(recordFieldErrors.received_at)}
              helperText={recordFieldErrors.received_at}
            />
          </Stack>
          <AdminFormField label="Contact">
            <Autocomplete
              options={contactOptions}
              value={contactOptions.find((contact) => contact.id === recordForm.contact_id) || null}
              onChange={(_, value) =>
                setRecordForm((current) => ({ ...current, contact_id: value?.id || "" }))
              }
              getOptionLabel={(option) =>
                option.full_name || option.job_title || option.email || option.id
              }
              renderInput={(params) => (
                <TextField {...params} size="small" placeholder="Select stored contact or leave blank" />
              )}
            />
          </AdminFormField>
          <AdminFormTextField
            label="Sender"
            value={recordForm.sender_display}
            onChange={(event) =>
              setRecordForm((current) => ({ ...current, sender_display: event.target.value }))
            }
            placeholder="Optional sender display name"
          />
          <AdminFormTextField
            label="Subject"
            value={recordForm.subject}
            onChange={(event) =>
              setRecordForm((current) => ({ ...current, subject: event.target.value }))
            }
            placeholder="Optional subject line"
          />
          <AdminFormTextField
            label="Reply Message"
            value={recordForm.raw_message}
            onChange={(event) =>
              setRecordForm((current) => ({ ...current, raw_message: event.target.value }))
            }
            multiline
            minRows={8}
            required
            error={Boolean(recordFieldErrors.raw_message)}
            helperText={recordFieldErrors.raw_message}
            placeholder="Paste the inbound reply text exactly as received."
          />
          <AdminFormTextField
            label="Notes"
            value={recordForm.notes}
            onChange={(event) =>
              setRecordForm((current) => ({ ...current, notes: event.target.value }))
            }
            multiline
            minRows={3}
          />
        </Stack>
      </AdminFormDialog>

      <Drawer anchor="right" open={detailOpen} onClose={() => setDetailOpen(false)}>
        <Box sx={{ width: { xs: "100vw", lg: 760 }, height: "100%", display: "flex", flexDirection: "column" }}>
          <Box sx={{ px: 2.25, py: 1.8, borderBottom: "1px solid #E2E8F0", background: "linear-gradient(135deg, #EFF6FF 0%, #E0F2FE 100%)" }}>
            <Stack direction="row" spacing={1.25} sx={{ alignItems: "flex-start", justifyContent: "space-between" }}>
              <Box sx={{ pr: 2 }}>
                <Typography sx={{ fontSize: 20, fontWeight: 800, color: "#0F172A" }}>
                  {selectedReply?.subject || "Inbound Reply Detail"}
                </Typography>
                <Typography sx={{ mt: 0.45, color: "#475569" }}>
                  {selectedReply?.prospect_name || "Unknown prospect"} • {selectedReply?.lead_title || selectedReply?.lead_id || ""}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap", rowGap: 1 }}>
                  {selectedReply?.reply_status ? (
                    <Chip
                      label={formatLabel(selectedReply.reply_status)}
                      size="small"
                      sx={{ ...getStatusChip(selectedReply.reply_status), border: "1px solid" }}
                    />
                  ) : null}
                  {selectedReply?.latest_intent ? (
                    <Chip
                      label={formatLabel(selectedReply.latest_intent)}
                      size="small"
                      sx={{ ...getIntentChip(selectedReply.latest_intent), border: "1px solid" }}
                    />
                  ) : null}
                </Stack>
              </Box>
              <Stack direction="row" spacing={0.75}>
                {canOutreach ? (
                  <Button
                    variant="contained"
                    startIcon={<AutoAwesomeOutlinedIcon />}
                    onClick={() => void handleAnalyzeReply()}
                    disabled={analysisBusy || !selectedReplyId}
                    sx={{ borderRadius: "8px", textTransform: "none", bgcolor: "#7C3AED" }}
                  >
                    {analysis ? "Re-analyze" : "Analyze Reply"}
                  </Button>
                ) : null}
                {canOutreach ? (
                  <Button
                    variant="contained"
                    startIcon={<SendOutlinedIcon />}
                    onClick={() => void handleGenerateResponse()}
                    disabled={responseBusy || !selectedReplyId}
                    sx={{ borderRadius: "8px", textTransform: "none", bgcolor: "#0F766E" }}
                  >
                    {responseDraft ? "Regenerate" : "Generate Response"}
                  </Button>
                ) : null}
              </Stack>
            </Stack>
          </Box>

          <Tabs value={detailTab} onChange={(_, value) => setDetailTab(value)} variant="scrollable">
            <Tab value="message" label="Message" />
            <Tab value="analysis" label="AI Analysis" />
            <Tab value="response" label="Response Draft" />
            <Tab value="context" label="Context" />
            <Tab value="history" label="History" />
          </Tabs>

          <Box sx={{ flex: 1, overflowY: "auto", p: 2.25 }}>
            {detailLoading ? (
              <Stack sx={{ py: 8, alignItems: "center" }} spacing={1}>
                <CircularProgress size={28} />
                <Typography sx={{ color: "#475569" }}>Loading reply detail...</Typography>
              </Stack>
            ) : detailError ? (
              <Alert severity="error">{detailError}</Alert>
            ) : !selectedReply ? (
              <Alert severity="info">Select a reply to begin.</Alert>
            ) : (
              <Stack spacing={2.25}>
                {detailTab === "message" ? (
                  <>
                    <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
                      <FieldCard label="Received" value={formatDateTime(selectedReply.received_at)} />
                      <FieldCard label="Channel" value={formatLabel(selectedReply.channel)} />
                      <FieldCard label="Sender" value={selectedReply.sender_display || "Not available"} />
                    </Stack>
                    <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", p: 2 }}>
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Inbound Reply</Typography>
                      <Typography sx={{ mt: 1.25, color: "#334155", whiteSpace: "pre-wrap", lineHeight: 1.65 }}>
                        {selectedReply.raw_message}
                      </Typography>
                    </Paper>
                    {selectedReply.notes ? (
                      <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", p: 2 }}>
                        <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Operator Notes</Typography>
                        <Typography sx={{ mt: 1, color: "#475569", whiteSpace: "pre-wrap" }}>
                          {selectedReply.notes}
                        </Typography>
                      </Paper>
                    ) : null}
                  </>
                ) : null}

                {detailTab === "analysis" ? (
                  <>
                    {!analysis ? (
                      <Alert severity="info">
                        Run AI analysis to classify intent, urgency, objections, next action, pipeline recommendation, and task guidance.
                      </Alert>
                    ) : (
                      <>
                        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
                          <FieldCard label="Intent" value={formatLabel(analysis.intent)} />
                          <FieldCard label="Sentiment" value={formatLabel(analysis.sentiment)} />
                          <FieldCard label="Engagement" value={formatLabel(analysis.engagement_level)} />
                          <FieldCard label="Urgency" value={formatLabel(analysis.urgency)} />
                        </Stack>
                        <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", p: 2 }}>
                          <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>AI Summary</Typography>
                          <Typography sx={{ mt: 1, color: "#334155" }}>
                            {analysis.analysis_json.summary}
                          </Typography>
                          <Stack spacing={1} sx={{ mt: 1.5 }}>
                            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Questions from Prospect</Typography>
                            {analysis.analysis_json.questions_from_prospect.length ? (
                              analysis.analysis_json.questions_from_prospect.map((question) => (
                                <Typography key={question} sx={{ color: "#475569" }}>
                                  • {question}
                                </Typography>
                              ))
                            ) : (
                              <Typography sx={{ color: "#64748B" }}>No explicit questions extracted.</Typography>
                            )}
                          </Stack>
                          <Stack spacing={1} sx={{ mt: 1.5 }}>
                            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Objections</Typography>
                            {analysis.analysis_json.objections.length ? (
                              analysis.analysis_json.objections.map((objection, index) => (
                                <Paper key={`${objection.category}-${index}`} elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", p: 1.25 }}>
                                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                                    {formatLabel(objection.category)}
                                  </Typography>
                                  <Typography sx={{ mt: 0.5, color: "#475569" }}>{objection.concern}</Typography>
                                  <Typography sx={{ mt: 0.75, fontSize: 12.5, color: "#64748B" }}>
                                    Evidence: {objection.evidence}
                                  </Typography>
                                </Paper>
                              ))
                            ) : (
                              <Typography sx={{ color: "#64748B" }}>No explicit objections detected.</Typography>
                            )}
                          </Stack>
                        </Paper>
                        <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", p: 2 }}>
                          <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Next-Action Recommendation</Typography>
                          <Typography sx={{ mt: 1, color: "#334155" }}>
                            {analysis.analysis_json.recommended_next_action}
                          </Typography>
                          <Stack direction={{ xs: "column", md: "row" }} spacing={1.25} sx={{ mt: 1.5 }}>
                            <FieldCard
                              label="Current Stage"
                              value={formatLabel(selectedReply.lead?.lead_stage || "Not available")}
                            />
                            <FieldCard
                              label="Recommended Stage"
                              value={formatLabel(analysis.analysis_json.recommended_pipeline_stage)}
                            />
                            <FieldCard
                              label="Recommended Probability"
                              value={
                                analysis.analysis_json.recommended_probability == null
                                  ? "Not available"
                                  : `${analysis.analysis_json.recommended_probability}%`
                              }
                            />
                          </Stack>
                          <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ mt: 1.5 }}>
                            {canUpdate && analysis.analysis_json.recommended_pipeline_stage ? (
                              <Button
                                variant="contained"
                                startIcon={<TimelineOutlinedIcon />}
                                onClick={() => void handleApplyStageRecommendation()}
                                sx={{ borderRadius: "8px", textTransform: "none", bgcolor: "#175CD3" }}
                              >
                                Apply Stage Recommendation
                              </Button>
                            ) : null}
                            {canUpdate && analysis.analysis_json.recommended_probability != null ? (
                              <Button
                                variant="outlined"
                                startIcon={<InsightsOutlinedIcon />}
                                onClick={() => void handleApplyProbabilityRecommendation()}
                                sx={{ borderRadius: "8px", textTransform: "none" }}
                              >
                                Update Probability
                              </Button>
                            ) : null}
                            {canCreate && analysis.analysis_json.recommended_task ? (
                              <Button
                                variant="outlined"
                                startIcon={<TaskAltOutlinedIcon />}
                                onClick={() => void openTaskRecommendationDialog()}
                                sx={{ borderRadius: "8px", textTransform: "none" }}
                              >
                                Create Recommended Task
                              </Button>
                            ) : null}
                          </Stack>
                        </Paper>
                      </>
                    )}
                  </>
                ) : null}

                {detailTab === "response" ? (
                  <>
                    <Alert severity="info">AI Generated Draft — Review Before Use</Alert>
                    <Stack direction={{ xs: "column", md: "row" }} spacing={1.25} sx={{ alignItems: { md: "center" } }}>
                      <TextField
                        select
                        label="Response Strategy"
                        size="small"
                        value={strategy}
                        onChange={(event) =>
                          setStrategy(event.target.value as AugmisBusinessReplyResponseStrategy)
                        }
                        sx={{ minWidth: 220 }}
                      >
                        {RESPONSE_STRATEGIES.map((option) => (
                          <MenuItem key={option.value} value={option.value}>
                            {option.label}
                          </MenuItem>
                        ))}
                      </TextField>
                      {canOutreach ? (
                        <Button
                          variant="contained"
                          startIcon={<SendOutlinedIcon />}
                          onClick={() => void handleGenerateResponse()}
                          disabled={responseBusy}
                          sx={{ borderRadius: "8px", textTransform: "none", bgcolor: "#0F766E" }}
                        >
                          {responseDraft ? "Regenerate" : "Generate Response"}
                        </Button>
                      ) : null}
                    </Stack>
                    {responseDraft ? (
                      <>
                        <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", p: 2 }}>
                          <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ justifyContent: "space-between" }}>
                            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                              <Chip
                                label={formatLabel(responseDraft.status)}
                                size="small"
                                sx={{ ...getResponseStatusChip(responseDraft.status), border: "1px solid" }}
                              />
                              <Typography sx={{ fontSize: 12.5, color: "#64748B" }}>
                                Version {responseDraft.generation_version}
                              </Typography>
                            </Stack>
                            <Stack direction="row" spacing={1}>
                              <Button
                                variant="outlined"
                                startIcon={<ContentCopyOutlinedIcon />}
                                onClick={() => void handleCopyResponse()}
                                sx={{ borderRadius: "8px", textTransform: "none" }}
                              >
                                Copy
                              </Button>
                              {canUpdate ? (
                                <Button
                                  variant="contained"
                                  onClick={() => void handleSaveResponseDraft()}
                                  disabled={responseSaving}
                                  sx={{ borderRadius: "8px", textTransform: "none", bgcolor: "#175CD3" }}
                                >
                                  Save Draft
                                </Button>
                              ) : null}
                              {canOutreach ? (
                                <Button
                                  variant="outlined"
                                  onClick={() => void handleResponseStatus("approve")}
                                  disabled={responseStatusBusy}
                                  sx={{ borderRadius: "8px", textTransform: "none" }}
                                >
                                  Approve
                                </Button>
                              ) : null}
                              {canOutreach ? (
                                <Button
                                  variant="outlined"
                                  color="error"
                                  onClick={() => void handleResponseStatus("reject")}
                                  disabled={responseStatusBusy}
                                  sx={{ borderRadius: "8px", textTransform: "none" }}
                                >
                                  Reject
                                </Button>
                              ) : null}
                            </Stack>
                          </Stack>
                          <TextField
                            label="Subject"
                            value={responseSubject}
                            onChange={(event) => setResponseSubject(event.target.value)}
                            fullWidth
                            size="small"
                            sx={{ mt: 1.5 }}
                          />
                          <TextField
                            label="Response Draft"
                            value={responseBody}
                            onChange={(event) => setResponseBody(event.target.value)}
                            fullWidth
                            multiline
                            minRows={10}
                            sx={{ mt: 1.5 }}
                          />
                        </Paper>
                        <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", p: 2 }}>
                          <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Verify Before Sending</Typography>
                          {responseDraft.structured_content_json.facts_requiring_verification.length ? (
                            <Stack spacing={0.65} sx={{ mt: 1 }}>
                              {responseDraft.structured_content_json.facts_requiring_verification.map((fact) => (
                                <Typography key={fact} sx={{ color: "#B54708" }}>
                                  • {fact}
                                </Typography>
                              ))}
                            </Stack>
                          ) : (
                            <Typography sx={{ mt: 1, color: "#64748B" }}>
                              No explicit verification flags were returned.
                            </Typography>
                          )}
                        </Paper>
                      </>
                    ) : (
                      <Alert severity="info">
                        Analyze the reply first where possible, then generate a review-only response draft. No message is sent automatically.
                      </Alert>
                    )}
                  </>
                ) : null}

                {detailTab === "context" ? (
                  <>
                    <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
                      <FieldCard label="Opportunity" value={selectedReply.opportunity?.title || "Not available"} />
                      <FieldCard label="Lead Stage" value={formatLabel(selectedReply.lead?.lead_stage)} />
                      <FieldCard label="Primary Contact" value={selectedReply.contact?.full_name || selectedReply.contact_name || "Not available"} />
                    </Stack>
                    <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", p: 2 }}>
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Stored Context</Typography>
                      <Typography sx={{ mt: 1, color: "#334155" }}>
                        Requirement summary: {selectedReply.opportunity?.requirement_summary || "Not available"}
                      </Typography>
                      <Typography sx={{ mt: 1, color: "#334155" }}>
                        Business problem: {selectedReply.opportunity?.business_problem || "Not available"}
                      </Typography>
                      <Typography sx={{ mt: 1, color: "#334155" }}>
                        Lead notes: {selectedReply.lead?.notes || "Not available"}
                      </Typography>
                      <Typography sx={{ mt: 1, color: "#334155" }}>
                        Prospect industry: {selectedReply.prospect?.industry || "Not available"}
                      </Typography>
                    </Paper>
                    {selectedReply.lead?.id ? (
                      <Button
                        component={Link}
                        href={`/augmis-business/leads?lead_id=${encodeURIComponent(selectedReply.lead.id)}`}
                        variant="outlined"
                        sx={{ alignSelf: "flex-start", borderRadius: "8px", textTransform: "none" }}
                      >
                        Open Lead Workspace
                      </Button>
                    ) : null}
                  </>
                ) : null}

                {detailTab === "history" ? (
                  <Stack spacing={2}>
                    <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", p: 2 }}>
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Analysis Versions</Typography>
                      {analyses.length ? (
                        <Stack spacing={1} sx={{ mt: 1.25 }}>
                          {analyses.map((item) => (
                            <Paper key={item.id} elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", p: 1.25 }}>
                              <Stack direction="row" spacing={1} sx={{ alignItems: "center", justifyContent: "space-between" }}>
                                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                                  Version {item.analysis_version}
                                </Typography>
                                <Chip
                                  label={formatLabel(item.intent)}
                                  size="small"
                                  sx={{ ...getIntentChip(item.intent), border: "1px solid" }}
                                />
                              </Stack>
                              <Typography sx={{ mt: 0.5, color: "#475569" }}>
                                {item.recommended_next_action}
                              </Typography>
                              <Typography sx={{ mt: 0.5, fontSize: 12.5, color: "#64748B" }}>
                                {formatDateTime(item.created_at)}
                              </Typography>
                            </Paper>
                          ))}
                        </Stack>
                      ) : (
                        <Typography sx={{ mt: 1, color: "#64748B" }}>No analysis history yet.</Typography>
                      )}
                    </Paper>
                    <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", p: 2 }}>
                      <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Response Versions</Typography>
                      {responses.length ? (
                        <Stack spacing={1} sx={{ mt: 1.25 }}>
                          {responses.map((item) => (
                            <Paper
                              key={item.id}
                              elevation={0}
                              sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", p: 1.25, cursor: "pointer" }}
                              onClick={() => void handleSelectResponseVersion(item.id)}
                            >
                              <Stack direction="row" spacing={1} sx={{ alignItems: "center", justifyContent: "space-between" }}>
                                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                                  Version {item.generation_version}
                                </Typography>
                                <Chip
                                  label={formatLabel(item.status)}
                                  size="small"
                                  sx={{ ...getResponseStatusChip(item.status), border: "1px solid" }}
                                />
                              </Stack>
                              <Typography sx={{ mt: 0.5, color: "#475569" }}>
                                {item.subject || "No subject"}
                              </Typography>
                              <Typography sx={{ mt: 0.5, fontSize: 12.5, color: "#64748B" }}>
                                {formatDateTime(item.created_at)}
                              </Typography>
                            </Paper>
                          ))}
                        </Stack>
                      ) : (
                        <Typography sx={{ mt: 1, color: "#64748B" }}>No response history yet.</Typography>
                      )}
                    </Paper>
                  </Stack>
                ) : null}
              </Stack>
            )}
          </Box>
        </Box>
      </Drawer>

      <AdminFormDialog
        open={taskDialogOpen}
        title="Create Recommended Task"
        onClose={() => setTaskDialogOpen(false)}
        maxWidth={620}
        actions={
          <>
            <Button onClick={() => setTaskDialogOpen(false)} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={() => void handleSaveRecommendedTask()}
              disabled={taskSaving}
              sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "#175CD3" }}
            >
              {taskSaving ? "Saving..." : "Create Task"}
            </Button>
          </>
        }
      >
        <Stack spacing={2}>
          <AdminFormTextField
            label="Task Title"
            value={taskForm.title}
            onChange={(event) => setTaskForm((current) => ({ ...current, title: event.target.value }))}
            required
            error={Boolean(taskFieldErrors.title)}
            helperText={taskFieldErrors.title}
          />
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <AdminFormTextField
              label="Task Type"
              value={taskForm.task_type}
              onChange={(event) => setTaskForm((current) => ({ ...current, task_type: event.target.value }))}
            />
            <AdminFormTextField
              select
              label="Priority"
              value={taskForm.priority}
              onChange={(event) =>
                setTaskForm((current) => ({
                  ...current,
                  priority: event.target.value as "high" | "medium" | "low",
                }))
              }
            >
              <MenuItem value="high">High</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="low">Low</MenuItem>
            </AdminFormTextField>
          </Stack>
          <AdminFormField label="Assignee">
            <Autocomplete
              options={assignableUsers}
              value={selectedAssignee}
              onChange={(_, value) => {
                setSelectedAssignee(value);
                setTaskForm((current) => ({ ...current, assigned_user_id: value?.user_id || "" }));
              }}
              getOptionLabel={(option) => option.name || option.email || option.user_id}
              renderInput={(params) => (
                <TextField {...params} size="small" placeholder="Select assignee" />
              )}
              renderOption={(props, option) => {
                const { key, ...optionProps } = props;
                return (
                <Box component="li" key={key} {...optionProps}>
                  <Stack spacing={0.15}>
                    <Typography sx={{ fontWeight: 700 }}>{option.name || option.user_id}</Typography>
                    <Typography sx={{ fontSize: 12, color: "#64748B" }}>
                      {option.email} • {option.role}
                    </Typography>
                  </Stack>
                </Box>
                );
              }}
            />
          </AdminFormField>
          <AdminFormTextField
            label="Due At"
            type="datetime-local"
            value={taskForm.due_at}
            onChange={(event) => setTaskForm((current) => ({ ...current, due_at: event.target.value }))}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <AdminFormTextField
            label="Description"
            value={taskForm.description}
            onChange={(event) =>
              setTaskForm((current) => ({ ...current, description: event.target.value }))
            }
            multiline
            minRows={4}
          />
        </Stack>
      </AdminFormDialog>

      <AppNotificationToast
        open={toast.open}
        message={toast.message}
        severity={toast.severity}
        onClose={() => setToast((current) => ({ ...current, open: false }))}
      />
    </BusinessPageFrame>
  );
}
