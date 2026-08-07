"use client";

import { useEffect, useState } from "react";

import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import CloseIcon from "@mui/icons-material/Close";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import LightbulbOutlinedIcon from "@mui/icons-material/LightbulbOutlined";
import {
  Alert,
  Box,
  Button,
  Chip,
  Drawer,
  IconButton,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { parseApiValidationError } from "@/services/apiErrorParser";
import {
  type AugmisBusinessGenerationTone,
  type AugmisBusinessMiniSolution,
  type AugmisBusinessMiniSolutionSummary,
  approveAugmisBusinessMiniSolution,
  generateAugmisBusinessLeadMiniSolution,
  generateAugmisBusinessOpportunityMiniSolution,
  getAugmisBusinessMiniSolution,
  listAugmisBusinessOpportunityMiniSolutions,
  rejectAugmisBusinessMiniSolution,
  updateAugmisBusinessMiniSolution,
} from "@/services/augmisBusinessService";

type ToastSeverity = "success" | "error" | "info" | "warning";

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
  hasAssessment: boolean;
  onClose: () => void;
  showToast: (message: string, severity: ToastSeverity) => void;
};

export default function MiniSolutionWorkspaceDrawer({
  open,
  opportunityId,
  leadId,
  title,
  hasAssessment,
  onClose,
  showToast,
}: Props) {
  const [tone, setTone] = useState<AugmisBusinessGenerationTone>("consultative");
  const [history, setHistory] = useState<AugmisBusinessMiniSolutionSummary[]>([]);
  const [selectedSolution, setSelectedSolution] = useState<AugmisBusinessMiniSolution | null>(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [approvalBusy, setApprovalBusy] = useState(false);
  const [error, setError] = useState("");
  const [editableTitle, setEditableTitle] = useState("");
  const [executiveSummary, setExecutiveSummary] = useState("");
  const [problemUnderstanding, setProblemUnderstanding] = useState("");
  const [proposedSolution, setProposedSolution] = useState("");
  const [nextStep, setNextStep] = useState("");

  useEffect(() => {
    if (!open) return;
    let active = true;
    async function loadHistory() {
      setHistoryLoading(true);
      setError("");
      try {
        const result = await listAugmisBusinessOpportunityMiniSolutions(opportunityId);
        if (!active) return;
        setHistory(result.data || []);
        const latest = result.data?.[0];
        if (latest) {
          const detail = await getAugmisBusinessMiniSolution(latest.id);
          if (!active) return;
          hydrate(detail.data);
        } else {
          setSelectedSolution(null);
        }
      } catch (loadError) {
        if (!active) return;
        setError(parseApiValidationError(loadError, "Unable to load mini solutions.").message);
      } finally {
        if (active) setHistoryLoading(false);
      }
    }
    void loadHistory();
    return () => {
      active = false;
    };
  }, [open, opportunityId]);

  function hydrate(solution: AugmisBusinessMiniSolution) {
    setSelectedSolution(solution);
    setEditableTitle(solution.title);
    setExecutiveSummary(solution.solution_json.executive_summary);
    setProblemUnderstanding(solution.solution_json.problem_understanding);
    setProposedSolution(solution.solution_json.proposed_solution);
    setNextStep(solution.solution_json.next_step);
  }

  async function handleGenerate() {
    setLoading(true);
    setError("");
    try {
      const result = leadId
        ? await generateAugmisBusinessLeadMiniSolution(leadId, { lead_id: leadId, tone })
        : await generateAugmisBusinessOpportunityMiniSolution(opportunityId, { tone });
      hydrate(result.data);
      const historyResult = await listAugmisBusinessOpportunityMiniSolutions(opportunityId);
      setHistory(historyResult.data || []);
      showToast("Mini solution generated successfully.", "success");
    } catch (generationError) {
      setError(parseApiValidationError(generationError, "Unable to generate mini solution.").message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectVersion(solutionId: string) {
    setHistoryLoading(true);
    setError("");
    try {
      const result = await getAugmisBusinessMiniSolution(solutionId);
      hydrate(result.data);
    } catch (loadError) {
      setError(parseApiValidationError(loadError, "Unable to load mini solution version.").message);
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleSave() {
    if (!selectedSolution) return;
    setSaving(true);
    setError("");
    try {
      const updatedPayload = {
        ...selectedSolution.solution_json,
        title: editableTitle,
        executive_summary: executiveSummary,
        problem_understanding: problemUnderstanding,
        proposed_solution: proposedSolution,
        next_step: nextStep,
      };
      const result = await updateAugmisBusinessMiniSolution(selectedSolution.id, {
        title: editableTitle,
        solution_json: updatedPayload,
        status: "reviewed",
      });
      hydrate(result.data);
      const historyResult = await listAugmisBusinessOpportunityMiniSolutions(opportunityId);
      setHistory(historyResult.data || []);
      showToast("Mini solution saved.", "success");
    } catch (saveError) {
      setError(parseApiValidationError(saveError, "Unable to save mini solution.").message);
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusAction(action: "approve" | "reject") {
    if (!selectedSolution) return;
    setApprovalBusy(true);
    setError("");
    try {
      const result =
        action === "approve"
          ? await approveAugmisBusinessMiniSolution(selectedSolution.id)
          : await rejectAugmisBusinessMiniSolution(selectedSolution.id);
      hydrate(result.data);
      const historyResult = await listAugmisBusinessOpportunityMiniSolutions(opportunityId);
      setHistory(historyResult.data || []);
      showToast(
        action === "approve" ? "Mini solution approved." : "Mini solution rejected.",
        action === "approve" ? "success" : "warning"
      );
    } catch (statusError) {
      setError(parseApiValidationError(statusError, "Unable to update mini solution status.").message);
    } finally {
      setApprovalBusy(false);
    }
  }

  async function handleCopySummary() {
    if (!executiveSummary.trim()) return;
    await navigator.clipboard.writeText(executiveSummary);
    showToast("Mini-solution summary copied to clipboard", "success");
  }

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      slotProps={{ paper: { sx: { width: { xs: "100%", md: 760 }, bgcolor: "#F8FAFC" } } }}
    >
      <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <Box
          sx={{
            px: 2.5,
            py: 2,
            borderBottom: "1px solid #E2E8F0",
            background:
              "linear-gradient(135deg, rgba(13,45,78,0.98) 0%, rgba(25,93,161,0.95) 58%, rgba(222,239,255,0.92) 100%)",
            color: "#F8FAFC",
          }}
        >
          <Stack direction="row" spacing={1.5} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Mini Solution
              </Typography>
              <Typography sx={{ mt: 0.6, color: "rgba(248,250,252,0.88)" }}>
                AI Generated Draft — Review Before Use
              </Typography>
            </Box>
            <IconButton onClick={onClose} sx={{ color: "#F8FAFC" }}>
              <CloseIcon />
            </IconButton>
          </Stack>
          <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: "wrap" }}>
            <Button
              variant="contained"
              startIcon={<AutoAwesomeOutlinedIcon />}
              onClick={handleGenerate}
              disabled={loading}
              sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "rgba(15,118,110,0.9)", color: "#FFFFFF", boxShadow: "none" }}
            >
              {loading ? "Generating..." : selectedSolution ? "Re-generate" : "Generate"}
            </Button>
            <Button
              variant="contained"
              startIcon={<LightbulbOutlinedIcon />}
              onClick={handleSave}
              disabled={!selectedSolution || saving}
              sx={{ textTransform: "none", borderRadius: "8px", bgcolor: "rgba(37,99,235,0.85)", color: "#FFFFFF", boxShadow: "none" }}
            >
              {saving ? "Saving..." : "Save Draft"}
            </Button>
            <Button
              variant="outlined"
              startIcon={<ContentCopyOutlinedIcon />}
              onClick={() => void handleCopySummary()}
              disabled={!selectedSolution}
              sx={{ textTransform: "none", borderRadius: "8px", color: "#FFFFFF", borderColor: "rgba(255,255,255,0.35)" }}
            >
              Copy Summary
            </Button>
            <Button
              variant="outlined"
              onClick={() => void handleStatusAction("approve")}
              disabled={!selectedSolution || approvalBusy}
              sx={{ textTransform: "none", borderRadius: "8px", color: "#FFFFFF", borderColor: "rgba(255,255,255,0.35)" }}
            >
              Approve
            </Button>
            <Button
              variant="outlined"
              onClick={() => void handleStatusAction("reject")}
              disabled={!selectedSolution || approvalBusy}
              sx={{ textTransform: "none", borderRadius: "8px", color: "#FFFFFF", borderColor: "rgba(255,255,255,0.35)" }}
            >
              Reject
            </Button>
          </Stack>
        </Box>

        <Box sx={{ p: 2.5, overflowY: "auto", flex: 1 }}>
          <Stack spacing={2}>
            {!hasAssessment ? (
              <Alert severity="info">Run AI Assessment first for stronger mini-solution grounding.</Alert>
            ) : null}
            {error ? <Alert severity="error">{error}</Alert> : null}

            <Paper elevation={0} sx={{ p: 1.75, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
              <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Target</Typography>
              <Typography sx={{ mt: 0.6, color: "#475569" }}>{title}</Typography>
            </Paper>

            <TextField
              select
              size="small"
              label="Tone"
              value={tone}
              onChange={(event) => setTone(event.target.value as AugmisBusinessGenerationTone)}
            >
              <option value="consultative">Consultative</option>
              <option value="concise">Concise</option>
              <option value="executive">Executive</option>
              <option value="technical">Technical</option>
              <option value="procurement">Procurement</option>
            </TextField>

            {history.length ? (
              <Stack direction="row" spacing={0.75} sx={{ flexWrap: "wrap" }}>
                {history.map((item) => (
                <Chip
                  key={item.id}
                  label={`V${item.generation_version} · ${item.status}`}
                  onClick={() => void handleSelectVersion(item.id)}
                  sx={{
                    border: "1px solid",
                    boxShadow:
                      selectedSolution?.id === item.id ? "inset 0 0 0 1px #2563EB" : "none",
                    ...getStatusChip(item.status),
                  }}
                />
                ))}
              </Stack>
            ) : null}

            {historyLoading ? (
              <Typography sx={{ color: "#475569" }}>Loading mini solution...</Typography>
            ) : selectedSolution ? (
              <Stack spacing={2}>
                <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
                  <Chip
                    label={selectedSolution.status}
                    size="small"
                    sx={{ textTransform: "capitalize", border: "1px solid", ...getStatusChip(selectedSolution.status) }}
                  />
                  <Typography sx={{ color: "#64748B", fontSize: 13 }}>
                    Version {selectedSolution.generation_version} · {selectedSolution.model}
                  </Typography>
                </Stack>

                <TextField label="Title" value={editableTitle} onChange={(event) => setEditableTitle(event.target.value)} fullWidth />
                <TextField label="Executive Summary" value={executiveSummary} onChange={(event) => setExecutiveSummary(event.target.value)} fullWidth multiline minRows={3} />
                <TextField label="Problem Understanding" value={problemUnderstanding} onChange={(event) => setProblemUnderstanding(event.target.value)} fullWidth multiline minRows={3} />
                <TextField label="Proposed Solution" value={proposedSolution} onChange={(event) => setProposedSolution(event.target.value)} fullWidth multiline minRows={4} />
                <TextField label="Next Step" value={nextStep} onChange={(event) => setNextStep(event.target.value)} fullWidth multiline minRows={2} />

                <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
                  <Box sx={{ px: 2, py: 1.35, background: "linear-gradient(90deg, #E0F2FE 0%, #F8FAFC 100%)", borderBottom: "1px solid #E2E8F0" }}>
                    <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Solution Modules</Typography>
                  </Box>
                  <Stack spacing={1.1} sx={{ p: 2 }}>
                    {selectedSolution.solution_json.solution_modules.map((module) => (
                      <Paper key={module.name} elevation={0} sx={{ p: 1.25, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                        <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{module.name}</Typography>
                        <Typography sx={{ mt: 0.5, color: "#475569" }}>{module.purpose}</Typography>
                        <Stack direction="row" spacing={0.75} sx={{ mt: 1, flexWrap: "wrap" }}>
                          {module.key_features.map((item) => (
                            <Chip key={item} label={item} size="small" sx={{ bgcolor: "#F8FAFC", border: "1px solid #CBD5E1" }} />
                          ))}
                        </Stack>
                      </Paper>
                    ))}
                  </Stack>
                </Paper>

                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Suggested Workflow</Typography>
                  <Typography sx={{ mt: 0.8, color: "#475569" }}>
                    {selectedSolution.solution_json.suggested_workflow.join(" → ") || "Not available"}
                  </Typography>
                </Paper>

                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Technology</Typography>
                  <Stack direction="row" spacing={0.75} sx={{ mt: 1, flexWrap: "wrap" }}>
                    {selectedSolution.solution_json.suggested_technology_stack.map((item) => (
                      <Chip key={item} label={item} size="small" sx={{ bgcolor: "#EFF6FF", border: "1px solid #BFDBFE" }} />
                    ))}
                  </Stack>
                </Paper>

                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Relevant Experience</Typography>
                  <Stack spacing={1} sx={{ mt: 1 }}>
                    {selectedSolution.solution_json.experience_references.map((item) => (
                      <Box key={item.experience_item_id}>
                        <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{item.name}</Typography>
                        <Typography sx={{ mt: 0.35, color: "#475569" }}>{item.safe_summary}</Typography>
                      </Box>
                    ))}
                  </Stack>
                </Paper>

                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Risks, Assumptions, and Open Questions</Typography>
                  <Stack spacing={0.7} sx={{ mt: 1 }}>
                    {selectedSolution.solution_json.risks.map((item) => (
                      <Typography key={`risk-${item}`} sx={{ color: "#475569" }}>{`Risk: ${item}`}</Typography>
                    ))}
                    {selectedSolution.solution_json.assumptions.map((item) => (
                      <Typography key={`assumption-${item}`} sx={{ color: "#475569" }}>{`Assumption: ${item}`}</Typography>
                    ))}
                    {selectedSolution.solution_json.open_questions.map((item) => (
                      <Typography key={`question-${item}`} sx={{ color: "#475569" }}>{`Open question: ${item}`}</Typography>
                    ))}
                  </Stack>
                </Paper>

                <Paper elevation={0} sx={{ p: 1.5, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>Discovery Questions</Typography>
                  <Stack spacing={1} sx={{ mt: 1 }}>
                    {selectedSolution.solution_json.discovery_questions.map((item) => (
                      <Paper key={item.question} elevation={0} sx={{ p: 1.2, borderRadius: "8px", border: "1px solid #E2E8F0" }}>
                        <Stack direction="row" spacing={1} sx={{ alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
                          <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{item.question}</Typography>
                          <Chip label={item.priority} size="small" sx={{ textTransform: "capitalize", bgcolor: "#FFFAEB", color: "#B54708" }} />
                        </Stack>
                        <Typography sx={{ mt: 0.45, color: "#475569" }}>{item.category}</Typography>
                        <Typography sx={{ mt: 0.45, color: "#334155" }}>{item.why_it_matters}</Typography>
                      </Paper>
                    ))}
                  </Stack>
                </Paper>
              </Stack>
            ) : (
              <Alert severity="info">Generate a mini solution to begin.</Alert>
            )}
          </Stack>
        </Box>
      </Box>
    </Drawer>
  );
}
