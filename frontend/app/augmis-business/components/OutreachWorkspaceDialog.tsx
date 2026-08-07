"use client";

import { useEffect, useMemo, useState } from "react";

import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import MarkEmailReadOutlinedIcon from "@mui/icons-material/MarkEmailReadOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { parseApiValidationError } from "@/services/apiErrorParser";
import {
  type AugmisBusinessGenerationTone,
  type AugmisBusinessOutreachDraft,
  type AugmisBusinessOutreachDraftSummary,
  type AugmisBusinessOutreachType,
  approveAugmisBusinessOutreach,
  generateAugmisBusinessLeadOutreach,
  generateAugmisBusinessOpportunityOutreach,
  getAugmisBusinessOutreach,
  listAugmisBusinessOpportunityOutreach,
  rejectAugmisBusinessOutreach,
  updateAugmisBusinessOutreach,
} from "@/services/augmisBusinessService";

type ToastSeverity = "success" | "error" | "info" | "warning";

const OUTREACH_TYPE_OPTIONS: Array<{ value: AugmisBusinessOutreachType; label: string }> = [
  { value: "initial_email", label: "Initial Email" },
  { value: "linkedin_message", label: "LinkedIn Message" },
  { value: "executive_intro", label: "Executive Introduction" },
  { value: "follow_up_email", label: "Follow-up Email" },
  { value: "procurement_clarification", label: "Procurement Clarification" },
];

const TONE_OPTIONS: Array<{ value: AugmisBusinessGenerationTone; label: string }> = [
  { value: "consultative", label: "Consultative" },
  { value: "concise", label: "Concise" },
  { value: "executive", label: "Executive" },
  { value: "technical", label: "Technical" },
  { value: "procurement", label: "Procurement" },
];

function getStatusChip(status: string) {
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

type Props = {
  open: boolean;
  opportunityId: string;
  leadId?: string | null;
  title: string;
  organizationName?: string | null;
  hasAssessment: boolean;
  onClose: () => void;
  showToast: (message: string, severity: ToastSeverity) => void;
};

export default function OutreachWorkspaceDialog({
  open,
  opportunityId,
  leadId,
  title,
  organizationName,
  hasAssessment,
  onClose,
  showToast,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [approvalBusy, setApprovalBusy] = useState(false);
  const [outreachType, setOutreachType] =
    useState<AugmisBusinessOutreachType>("initial_email");
  const [tone, setTone] = useState<AugmisBusinessGenerationTone>("consultative");
  const [history, setHistory] = useState<AugmisBusinessOutreachDraftSummary[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<AugmisBusinessOutreachDraft | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  useEffect(() => {
    if (!open) return;
    let active = true;
    async function loadHistory() {
      setHistoryLoading(true);
      setError("");
      try {
        const result = await listAugmisBusinessOpportunityOutreach(opportunityId);
        if (!active) return;
        setHistory(result.data || []);
        const latest = result.data?.[0];
        if (latest) {
          const detail = await getAugmisBusinessOutreach(latest.id);
          if (!active) return;
          setSelectedDraft(detail.data);
          setSubject(detail.data.subject || "");
          setBody(detail.data.body || "");
          setOutreachType(detail.data.outreach_type);
          setTone(detail.data.tone);
        } else {
          setSelectedDraft(null);
          setSubject("");
          setBody("");
        }
      } catch (loadError) {
        if (!active) return;
        setError(parseApiValidationError(loadError, "Unable to load outreach drafts.").message);
      } finally {
        if (active) setHistoryLoading(false);
      }
    }
    void loadHistory();
    return () => {
      active = false;
    };
  }, [open, opportunityId]);

  const verificationItems = useMemo(
    () => selectedDraft?.structured_content_json.content.facts_requiring_verification || [],
    [selectedDraft]
  );

  async function handleGenerate() {
    setLoading(true);
    setError("");
    try {
      const result = leadId
        ? await generateAugmisBusinessLeadOutreach(leadId, {
            outreach_type: outreachType,
            tone,
            lead_id: leadId,
          })
        : await generateAugmisBusinessOpportunityOutreach(opportunityId, {
            outreach_type: outreachType,
            tone,
          });
      const draft = result.data;
      setSelectedDraft(draft);
      setSubject(draft.subject || "");
      setBody(draft.body || "");
      const historyResult = await listAugmisBusinessOpportunityOutreach(opportunityId);
      setHistory(historyResult.data || []);
      showToast("Outreach draft generated successfully.", "success");
    } catch (generationError) {
      setError(
        parseApiValidationError(generationError, "Unable to generate outreach draft.").message
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectDraft(draftId: string) {
    setHistoryLoading(true);
    setError("");
    try {
      const result = await getAugmisBusinessOutreach(draftId);
      setSelectedDraft(result.data);
      setSubject(result.data.subject || "");
      setBody(result.data.body || "");
    } catch (loadError) {
      setError(parseApiValidationError(loadError, "Unable to load outreach draft.").message);
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleSave() {
    if (!selectedDraft) return;
    setSaving(true);
    setError("");
    try {
      const updatedStructured = {
        ...selectedDraft.structured_content_json,
        content: {
          ...selectedDraft.structured_content_json.content,
          recommended_subject: subject || null,
          body,
          full_message: body,
        },
      };
      const result = await updateAugmisBusinessOutreach(selectedDraft.id, {
        subject,
        body,
        structured_content_json: updatedStructured,
        status: "reviewed",
      });
      setSelectedDraft(result.data);
      setSubject(result.data.subject || "");
      setBody(result.data.body || "");
      const historyResult = await listAugmisBusinessOpportunityOutreach(opportunityId);
      setHistory(historyResult.data || []);
      showToast("Outreach draft saved.", "success");
    } catch (saveError) {
      setError(parseApiValidationError(saveError, "Unable to save outreach draft.").message);
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusAction(action: "approve" | "reject") {
    if (!selectedDraft) return;
    setApprovalBusy(true);
    setError("");
    try {
      const result =
        action === "approve"
          ? await approveAugmisBusinessOutreach(selectedDraft.id)
          : await rejectAugmisBusinessOutreach(selectedDraft.id);
      setSelectedDraft(result.data);
      const historyResult = await listAugmisBusinessOpportunityOutreach(opportunityId);
      setHistory(historyResult.data || []);
      showToast(
        action === "approve" ? "Outreach draft approved." : "Outreach draft rejected.",
        action === "approve" ? "success" : "warning"
      );
    } catch (statusError) {
      setError(parseApiValidationError(statusError, "Unable to update outreach status.").message);
    } finally {
      setApprovalBusy(false);
    }
  }

  async function handleCopy() {
    const copyText = `${subject ? `${subject}\n\n` : ""}${body}`;
    if (!copyText.trim()) return;
    await navigator.clipboard.writeText(copyText);
    showToast("Outreach copied to clipboard", "success");
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle sx={{ fontWeight: 700 }}>
        Personalized Outreach
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 0.75 }}>
          <Paper
            elevation={0}
            sx={{
              p: 1.75,
              borderRadius: "8px",
              border: "1px solid #BFDBFE",
              bgcolor: "#EFF6FF",
            }}
          >
            <Stack direction="row" spacing={1} sx={{ alignItems: "flex-start" }}>
              <WarningAmberOutlinedIcon sx={{ color: "#2563EB", mt: 0.1 }} />
              <Box>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                  AI Generated Draft — Review Before Use
                </Typography>
                <Typography sx={{ mt: 0.45, color: "#475569" }}>
                  This phase stores drafts only. Nothing is sent externally.
                </Typography>
              </Box>
            </Stack>
          </Paper>

          {!hasAssessment ? (
            <Alert severity="info">Run AI Assessment first for stronger outreach grounding.</Alert>
          ) : null}
          {error ? <Alert severity="error">{error}</Alert> : null}

          <Paper elevation={0} sx={{ p: 1.75, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Target</Typography>
            <Typography sx={{ mt: 0.6, color: "#475569" }}>{title}</Typography>
            <Typography sx={{ mt: 0.35, color: "#64748B" }}>
              {organizationName || "Organization not available"}
            </Typography>
          </Paper>

          <Box sx={{ display: "grid", gap: 1.15, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
            <TextField
              select
              size="small"
              label="Outreach Type"
              value={outreachType}
              onChange={(event) => setOutreachType(event.target.value as AugmisBusinessOutreachType)}
            >
              {OUTREACH_TYPE_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              size="small"
              label="Tone"
              value={tone}
              onChange={(event) => setTone(event.target.value as AugmisBusinessGenerationTone)}
            >
              {TONE_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
          </Box>

          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
            <Button
              variant="contained"
              startIcon={<AutoAwesomeOutlinedIcon />}
              onClick={handleGenerate}
              disabled={loading}
              sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "#0F766E", "&:hover": { bgcolor: "#115E59" } }}
            >
              {loading ? "Generating..." : selectedDraft ? "Regenerate" : "Generate"}
            </Button>
            <Button
              variant="contained"
              startIcon={<MarkEmailReadOutlinedIcon />}
              onClick={handleSave}
              disabled={!selectedDraft || saving}
              sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "#2563EB", "&:hover": { bgcolor: "#1D4ED8" } }}
            >
              {saving ? "Saving..." : "Save Draft"}
            </Button>
            <Button
              variant="outlined"
              startIcon={<ContentCopyOutlinedIcon />}
              onClick={() => void handleCopy()}
              disabled={!selectedDraft}
              sx={{ textTransform: "none", borderRadius: "8px" }}
            >
              Copy
            </Button>
            <Button
              variant="outlined"
              onClick={() => void handleStatusAction("approve")}
              disabled={!selectedDraft || approvalBusy}
              sx={{ textTransform: "none", borderRadius: "8px", color: "#067647", borderColor: "#ABEFC6" }}
            >
              Approve
            </Button>
            <Button
              variant="outlined"
              onClick={() => void handleStatusAction("reject")}
              disabled={!selectedDraft || approvalBusy}
              sx={{ textTransform: "none", borderRadius: "8px", color: "#B42318", borderColor: "#FECDCA" }}
            >
              Reject
            </Button>
          </Stack>

          {history.length ? (
            <Stack direction="row" spacing={0.75} sx={{ flexWrap: "wrap" }}>
              {history.map((item) => (
                <Chip
                  key={item.id}
                  label={`V${item.generation_version} · ${item.status}`}
                  onClick={() => void handleSelectDraft(item.id)}
                  sx={{
                    border: "1px solid",
                    boxShadow:
                      selectedDraft?.id === item.id ? "inset 0 0 0 1px #2563EB" : "none",
                    ...getStatusChip(item.status),
                  }}
                />
              ))}
            </Stack>
          ) : null}

          {historyLoading ? (
            <Typography sx={{ color: "#475569" }}>Loading outreach draft...</Typography>
          ) : selectedDraft ? (
            <Stack spacing={1.5}>
              <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
                <Chip
                  label={selectedDraft.status}
                  size="small"
                  sx={{ textTransform: "capitalize", border: "1px solid", ...getStatusChip(selectedDraft.status) }}
                />
                <Typography sx={{ color: "#64748B", fontSize: 13 }}>
                  Version {selectedDraft.generation_version} · {selectedDraft.model}
                </Typography>
              </Stack>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Context</Typography>
                <Typography sx={{ mt: 0.6, color: "#475569" }}>
                  Buyer role: {selectedDraft.structured_content_json.target_summary.buyer_role?.replaceAll("_", " ") || "Not available"}
                </Typography>
                <Typography sx={{ mt: 0.35, color: "#475569" }}>
                  Contact: {selectedDraft.structured_content_json.target_summary.contact_name || selectedDraft.structured_content_json.target_summary.contact_job_title || "Role-oriented only"}
                </Typography>
                <Typography sx={{ mt: 0.35, color: "#475569" }}>
                  Verification: {selectedDraft.structured_content_json.target_summary.verification_status || "Not available"}
                </Typography>
                {selectedDraft.structured_content_json.target_summary.contact_verification_notice ? (
                  <Alert severity="warning" sx={{ mt: 1.1 }}>
                    {selectedDraft.structured_content_json.target_summary.contact_verification_notice}
                  </Alert>
                ) : null}
              </Paper>

              <TextField
                label="Subject"
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
                fullWidth
                size="small"
              />
              <TextField
                label="Message"
                value={body}
                onChange={(event) => setBody(event.target.value)}
                fullWidth
                multiline
                minRows={8}
              />

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Personalization Points</Typography>
                <Stack direction="row" spacing={0.75} sx={{ mt: 1, flexWrap: "wrap" }}>
                  {selectedDraft.structured_content_json.content.personalization_points.map((item) => (
                    <Chip key={item} label={item} size="small" sx={{ bgcolor: "#F8FAFC", border: "1px solid #CBD5E1" }} />
                  ))}
                </Stack>
              </Paper>

              <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Claims Used</Typography>
                <Stack direction="row" spacing={0.75} sx={{ mt: 1, flexWrap: "wrap" }}>
                  {selectedDraft.structured_content_json.content.claims_used.map((item) => (
                    <Chip key={item} label={item} size="small" sx={{ bgcolor: "#F0FDF4", border: "1px solid #BBF7D0" }} />
                  ))}
                </Stack>
              </Paper>

              {verificationItems.length ? (
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #FDE68A", bgcolor: "#FFFBEB" }}>
                  <Typography sx={{ fontWeight: 700, color: "#92400E" }}>Verify Before Sending</Typography>
                  <Stack spacing={0.7} sx={{ mt: 1 }}>
                    {verificationItems.map((item) => (
                      <Typography key={item} sx={{ color: "#B45309" }}>
                        {item}
                      </Typography>
                    ))}
                  </Stack>
                </Paper>
              ) : null}
            </Stack>
          ) : (
            <Alert severity="info">Generate an outreach draft to begin.</Alert>
          )}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={onClose} sx={{ textTransform: "none" }}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}
