"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";

import ApartmentOutlinedIcon from "@mui/icons-material/ApartmentOutlined";
import BadgeOutlinedIcon from "@mui/icons-material/BadgeOutlined";
import BusinessCenterOutlinedIcon from "@mui/icons-material/BusinessCenterOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import PersonSearchOutlinedIcon from "@mui/icons-material/PersonSearchOutlined";
import PlaylistAddCheckCircleOutlinedIcon from "@mui/icons-material/PlaylistAddCheckCircleOutlined";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  FormControlLabel,
  MenuItem,
  Paper,
  Radio,
  RadioGroup,
  Stack,
  Typography,
} from "@mui/material";

import {
  AdminFormDialog,
  AdminFormTextField,
} from "@/components/forms/AdminFormDialog";
import {
  type AugmisBusinessContact,
  type AugmisBusinessExperienceItem,
  type AugmisBusinessLead,
  type AugmisBusinessOpportunity,
  type AugmisBusinessProspect,
  type AugmisBusinessTask,
  buildAugmisBusinessLead,
  getAugmisBusinessProspectContacts,
  listAugmisBusinessExperienceItems,
  listAugmisBusinessProspects,
} from "@/services/augmisBusinessService";

type ToastSeverity = "success" | "error" | "info" | "warning";

type BuildLeadDialogProps = {
  open: boolean;
  opportunity: AugmisBusinessOpportunity | null;
  onClose: () => void;
  onSuccess: (result: {
    lead: AugmisBusinessLead;
    first_task: AugmisBusinessTask;
    opportunity: AugmisBusinessOpportunity;
  }) => void;
  showToast: (message: string, severity: ToastSeverity) => void;
};

type ProspectResolutionMode = "use_matching" | "create_from_opportunity";
type ContactMode = "existing" | "new" | "role_only";

type BuildLeadFormState = {
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  contact_job_title: string;
  lead_title: string;
  lead_summary: string;
  identified_problem: string;
  proposed_solution: string;
  probability_pct: string;
  lead_priority: "high" | "medium" | "low";
  first_task_title: string;
  first_task_description: string;
  first_task_priority: "high" | "medium" | "low";
  first_task_due_at: string;
};

type MatchDraft = {
  selected: boolean;
  relevance_score: string;
  match_notes: string;
};

const DEFAULT_FORM: BuildLeadFormState = {
  contact_name: "",
  contact_email: "",
  contact_phone: "",
  contact_job_title: "",
  lead_title: "",
  lead_summary: "",
  identified_problem: "",
  proposed_solution: "",
  probability_pct: "",
  lead_priority: "medium",
  first_task_title: "",
  first_task_description: "",
  first_task_priority: "medium",
  first_task_due_at: "",
};

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

function getBackendErrorMessage(error: unknown, fallback: string) {
  if (typeof error !== "object" || error === null) {
    return fallback;
  }

  const response = "response" in error ? (error as { response?: unknown }).response : undefined;
  if (typeof response !== "object" || response === null) {
    return fallback;
  }

  const data = "data" in response ? (response as { data?: unknown }).data : undefined;
  if (typeof data !== "object" || data === null) {
    return fallback;
  }

  const detail = "detail" in data ? (data as { detail?: unknown }).detail : undefined;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  const message = "message" in data ? (data as { message?: unknown }).message : undefined;
  if (typeof message === "string" && message.trim()) {
    return message;
  }

  return fallback;
}

function formatDate(value: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatMoney(
  minValue: number | null,
  maxValue: number | null,
  currency: string | null
) {
  const prefix = currency ? `${currency} ` : "";
  if (minValue != null && maxValue != null) {
    return `${prefix}${minValue.toLocaleString()} - ${prefix}${maxValue.toLocaleString()}`;
  }
  if (maxValue != null) {
    return `${prefix}${maxValue.toLocaleString()}`;
  }
  if (minValue != null) {
    return `${prefix}${minValue.toLocaleString()}`;
  }
  return "Not available";
}

function buildInitialForm(opportunity: AugmisBusinessOpportunity): BuildLeadFormState {
  return {
    ...DEFAULT_FORM,
    lead_title: opportunity.title,
    lead_summary: opportunity.requirement_summary,
    identified_problem: opportunity.business_problem ?? "",
    proposed_solution: opportunity.ai_recommendation ?? "",
    first_task_title: `Initial follow-up for ${opportunity.organization_name}`,
    first_task_description:
      "Review the converted opportunity, confirm qualification details, and prepare the first outreach step.",
  };
}

function SectionCard({
  icon,
  title,
  subtitle,
  children,
  gradient,
}: {
  icon: ReactNode;
  title: string;
  subtitle?: string;
  children: ReactNode;
  gradient: string;
}) {
  return (
    <Paper
      elevation={0}
      sx={{ borderRadius: "8px", border: "1px solid #D7E1EA", overflow: "hidden" }}
    >
      <Box
        sx={{
          px: 2,
          py: 1.35,
          background: gradient,
          borderBottom: "1px solid #D7E1EA",
        }}
      >
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <Box sx={{ color: "#1D4ED8", display: "flex", alignItems: "center" }}>{icon}</Box>
          <Box>
            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>{title}</Typography>
            {subtitle ? (
              <Typography sx={{ fontSize: 12, color: "#475569" }}>{subtitle}</Typography>
            ) : null}
          </Box>
        </Stack>
      </Box>
      <Box sx={{ p: 2 }}>{children}</Box>
    </Paper>
  );
}

function SummaryField({ label, value }: { label: string; value: string }) {
  return (
    <Box>
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
      <Typography sx={{ mt: 0.45, color: "#0F172A", fontSize: 13.5 }}>{value}</Typography>
    </Box>
  );
}

export default function BuildLeadDialog({
  open,
  opportunity,
  onClose,
  onSuccess,
  showToast,
}: BuildLeadDialogProps) {
  const [form, setForm] = useState<BuildLeadFormState>(() =>
    opportunity ? buildInitialForm(opportunity) : DEFAULT_FORM
  );
  const [submitError, setSubmitError] = useState("");
  const [saving, setSaving] = useState(false);
  const [bootstrapLoading, setBootstrapLoading] = useState(true);
  const [contactsLoading, setContactsLoading] = useState(false);
  const [bootstrapError, setBootstrapError] = useState("");
  const [prospectMode, setProspectMode] = useState<ProspectResolutionMode>("create_from_opportunity");
  const [contactMode, setContactMode] = useState<ContactMode>("new");
  const [matchedProspects, setMatchedProspects] = useState<AugmisBusinessProspect[]>([]);
  const [selectedProspectId, setSelectedProspectId] = useState("");
  const [prospectContacts, setProspectContacts] = useState<AugmisBusinessContact[]>([]);
  const [selectedContactId, setSelectedContactId] = useState("");
  const [experienceItems, setExperienceItems] = useState<AugmisBusinessExperienceItem[]>([]);
  const [experienceDrafts, setExperienceDrafts] = useState<Record<string, MatchDraft>>({});

  const selectedProspect = useMemo(
    () => matchedProspects.find((prospect) => prospect.id === selectedProspectId) || null,
    [matchedProspects, selectedProspectId]
  );

  useEffect(() => {
    if (!open || !opportunity) {
      return;
    }

    let active = true;
    void (async () => {
      try {
        const [experienceResult, prospectResult] = await Promise.all([
          listAugmisBusinessExperienceItems({ status: "active" }),
          listAugmisBusinessProspects({
            page: 1,
            page_size: 25,
            search: opportunity.organization_name,
            status: "active",
          }),
        ]);

        if (!active) return;

        const likelyMatches = (prospectResult.data || []).filter((prospect) => {
          const domainMatch =
            opportunity.organization_domain &&
            prospect.organization_domain &&
            prospect.organization_domain.toLowerCase() ===
              opportunity.organization_domain.toLowerCase();
          const nameMatch =
            prospect.organization_name.trim().toLowerCase() ===
            opportunity.organization_name.trim().toLowerCase();
          return Boolean(domainMatch || nameMatch);
        });

        setExperienceItems(experienceResult.data || []);
        setMatchedProspects(likelyMatches);
        if (likelyMatches.length === 1) {
          setProspectMode("use_matching");
          setSelectedProspectId(likelyMatches[0].id);
          setContactMode("existing");
        }
      } catch (error) {
        if (!active) return;
        setBootstrapError(
          getBackendErrorMessage(error, "Unable to load prospect and experience data.")
        );
      } finally {
        if (active) {
          setBootstrapLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [open, opportunity]);

  useEffect(() => {
    if (!open || !selectedProspectId || prospectMode !== "use_matching") return;

    let active = true;

    getAugmisBusinessProspectContacts(selectedProspectId)
      .then((result) => {
        if (!active) return;
        setProspectContacts(result.data || []);
      })
      .catch((error) => {
        if (!active) return;
        setSubmitError(getBackendErrorMessage(error, "Unable to load contacts for this prospect."));
      })
      .finally(() => {
        if (active) {
          setContactsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [open, prospectMode, selectedProspectId]);

  function closeDialog() {
    if (saving) return;
    onClose();
  }

  function updateFormField<K extends keyof BuildLeadFormState>(
    field: K,
    value: BuildLeadFormState[K]
  ) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateExperienceDraft(
    experienceItemId: string,
    updater: (current: MatchDraft) => MatchDraft
  ) {
    setExperienceDrafts((current) => {
      const next = updater(
        current[experienceItemId] || {
          selected: false,
          relevance_score: "",
          match_notes: "",
        }
      );
      return { ...current, [experienceItemId]: next };
    });
  }

  async function handleSubmit() {
    if (!opportunity) return;
    setSubmitError("");

    if (!form.lead_title.trim()) {
      setSubmitError("Lead title is required.");
      return;
    }

    const probability = normalizeOptionalNumber(form.probability_pct);
    if (probability != null && (probability < 0 || probability > 100)) {
      setSubmitError("Probability must be between 0 and 100.");
      return;
    }

    if (prospectMode === "use_matching" && matchedProspects.length > 0 && !selectedProspectId) {
      setSubmitError("Select the matching prospect to continue.");
      return;
    }

    if (contactMode === "existing") {
      if (!selectedContactId) {
        setSubmitError("Select an existing contact to continue.");
        return;
      }
    } else if (!form.contact_name.trim()) {
      setSubmitError("Enter a contact name or role label for the new buyer/contact.");
      return;
    }

    const leadNotesParts = [
      form.lead_summary.trim() ? `Lead summary:\n${form.lead_summary.trim()}` : "",
      form.identified_problem.trim()
        ? `Identified problem:\n${form.identified_problem.trim()}`
        : "",
      form.proposed_solution.trim()
        ? `Proposed solution:\n${form.proposed_solution.trim()}`
        : "",
    ].filter(Boolean);

    const selected_experience_matches = Object.entries(experienceDrafts)
      .filter(([, draft]) => draft.selected)
      .map(([experience_item_id, draft]) => ({
        experience_item_id,
        relevance_score: normalizeOptionalNumber(draft.relevance_score),
        match_notes: normalizeOptionalString(draft.match_notes),
      }));

    setSaving(true);
    try {
      const result = await buildAugmisBusinessLead(opportunity.id, {
        contact_id: contactMode === "existing" ? selectedContactId : null,
        contact_name:
          contactMode === "existing" ? null : normalizeOptionalString(form.contact_name),
        contact_email:
          contactMode === "existing" ? null : normalizeOptionalString(form.contact_email),
        contact_phone:
          contactMode === "existing" ? null : normalizeOptionalString(form.contact_phone),
        contact_job_title:
          contactMode === "existing" ? null : normalizeOptionalString(form.contact_job_title),
        lead_title: form.lead_title.trim(),
        lead_priority: form.lead_priority,
        lead_stage: "new",
        lead_notes: leadNotesParts.length ? leadNotesParts.join("\n\n") : null,
        probability_pct: probability,
        selected_experience_matches,
        first_task_title: normalizeOptionalString(form.first_task_title),
        first_task_description: normalizeOptionalString(form.first_task_description),
        first_task_priority: form.first_task_priority,
        first_task_due_at: normalizeOptionalString(form.first_task_due_at),
        assigned_user_id: null,
      });

      const { lead, first_task, opportunity: updatedOpportunity } = result.data;
      onSuccess({ lead, first_task, opportunity: updatedOpportunity });
      onClose();
      showToast(
        `Lead created: ${lead.title}. Prospect: ${
          lead.prospect?.organization_name || updatedOpportunity.organization_name
        }. First task due: ${formatDate(first_task.due_at)}.`,
        "success"
      );
    } catch (error) {
      setSubmitError(getBackendErrorMessage(error, "Unable to build lead from this opportunity."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AdminFormDialog
      open={open}
      onClose={closeDialog}
      title="Build Lead"
      maxWidth={980}
      stackSx={{ maxWidth: 860 }}
      actions={
        <>
          <Button onClick={closeDialog} disabled={saving} sx={{ textTransform: "none" }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={saving || bootstrapLoading || !opportunity}
            sx={{
              textTransform: "none",
              fontWeight: 700,
              borderRadius: "8px",
              bgcolor: "#2563EB",
              "&:hover": { bgcolor: "#1D4ED8" },
            }}
          >
            {saving ? "Building lead..." : "Build Lead"}
          </Button>
        </>
      }
    >
      {bootstrapLoading ? (
        <Stack sx={{ minHeight: 260, alignItems: "center", justifyContent: "center" }} spacing={1.5}>
          <CircularProgress />
          <Typography sx={{ color: "#475569" }}>Loading opportunity conversion data...</Typography>
        </Stack>
      ) : opportunity ? (
        <>
          {bootstrapError ? <Alert severity="error">{bootstrapError}</Alert> : null}
          {submitError ? <Alert severity="error">{submitError}</Alert> : null}

          <SectionCard
            icon={<BusinessCenterOutlinedIcon fontSize="small" />}
            title="Opportunity Summary"
            subtitle="Read-only source values for this conversion"
            gradient="linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)"
          >
            <Box
              sx={{
                display: "grid",
                gap: 1.5,
                gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
              }}
            >
              <SummaryField label="Title" value={opportunity.title} />
              <SummaryField label="Organization" value={opportunity.organization_name} />
              <SummaryField label="Country" value={opportunity.country || "Not available"} />
              <SummaryField label="Industry" value={opportunity.industry || "Not available"} />
              <SummaryField
                label="Estimated Value"
                value={formatMoney(
                  opportunity.estimated_value_min,
                  opportunity.estimated_value_max,
                  opportunity.estimated_currency
                )}
              />
              <SummaryField
                label="Opportunity Status"
                value={opportunity.opportunity_status.replaceAll("_", " ")}
              />
              <SummaryField
                label="Fit Score"
                value={opportunity.fit_score == null ? "Not available" : String(opportunity.fit_score)}
              />
              <SummaryField
                label="Requirement Summary"
                value={opportunity.requirement_summary || "Not available"}
              />
            </Box>
          </SectionCard>

          <SectionCard
            icon={<ApartmentOutlinedIcon fontSize="small" />}
            title="Prospect"
            subtitle="Current backend derives prospect creation or reuse from the opportunity organization/domain"
            gradient="linear-gradient(90deg, #E0F2FE 0%, #F8FAFC 100%)"
          >
            <Stack spacing={1.5}>
              <Alert severity="info" icon={<InfoOutlinedIcon fontSize="inherit" />}>
                Prospect fields are not independently writable in the current Phase 3A API. This
                dialog shows likely matches and the prospect preview the backend will use from the
                opportunity record.
              </Alert>

              {matchedProspects.length ? (
                <Alert severity={matchedProspects.length > 1 ? "warning" : "success"}>
                  Potential existing prospect found
                  {matchedProspects.length > 1
                    ? `: ${matchedProspects.length} matching tenant prospects were detected.`
                    : `: ${matchedProspects[0].organization_name}.`}
                </Alert>
              ) : null}

              <RadioGroup
                value={prospectMode}
                onChange={(event) => {
                  const nextMode = event.target.value as ProspectResolutionMode;
                  setProspectMode(nextMode);
                  setSelectedContactId("");
                  setProspectContacts([]);
                  if (nextMode !== "use_matching") {
                    setContactsLoading(false);
                  } else if (selectedProspectId) {
                    setContactsLoading(true);
                  }
                }}
              >
                <FormControlLabel
                  value="create_from_opportunity"
                  control={<Radio />}
                  label="Create from current opportunity organization details"
                />
                <FormControlLabel
                  value="use_matching"
                  control={<Radio />}
                  label="Use detected matching prospect"
                  disabled={!matchedProspects.length}
                />
              </RadioGroup>

              {prospectMode === "use_matching" && matchedProspects.length ? (
                <AdminFormTextField
                  select
                  label="Matching Prospect"
                  value={selectedProspectId}
                  onChange={(event) => {
                    setSelectedProspectId(event.target.value);
                    setSelectedContactId("");
                    setProspectContacts([]);
                    setContactsLoading(true);
                  }}
                  helperText="Required when using an existing prospect for contact selection."
                >
                  {matchedProspects.map((prospect) => (
                    <MenuItem key={prospect.id} value={prospect.id}>
                      {prospect.organization_name}
                      {prospect.organization_domain ? ` (${prospect.organization_domain})` : ""}
                    </MenuItem>
                  ))}
                </AdminFormTextField>
              ) : null}

              <Box
                sx={{
                  display: "grid",
                  gap: 1.15,
                  gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                }}
              >
                <AdminFormTextField
                  label="Organization Name"
                  value={opportunity.organization_name}
                  disabled
                />
                <AdminFormTextField
                  label="Domain"
                  value={opportunity.organization_domain || ""}
                  disabled
                />
                <AdminFormTextField
                  label="Website"
                  value={opportunity.source_url || ""}
                  disabled
                />
                <AdminFormTextField
                  label="Country"
                  value={opportunity.country || ""}
                  disabled
                />
                <AdminFormTextField label="Region" value={opportunity.region || ""} disabled />
                <AdminFormTextField label="Industry" value={opportunity.industry || ""} disabled />
              </Box>
            </Stack>
          </SectionCard>

          <SectionCard
            icon={<BadgeOutlinedIcon fontSize="small" />}
            title="Buyer / Contact"
            subtitle="Select an existing contact or create a new manual buyer/contact"
            gradient="linear-gradient(90deg, #EDE9FE 0%, #F8FAFC 100%)"
          >
            <Stack spacing={1.5}>
              <RadioGroup
                value={contactMode}
                onChange={(event) => {
                  setContactMode(event.target.value as ContactMode);
                  setSelectedContactId("");
                  if (event.target.value !== "existing") {
                    setContactsLoading(false);
                  } else if (selectedProspectId) {
                    setContactsLoading(true);
                  }
                }}
              >
                <FormControlLabel
                  value="existing"
                  control={<Radio />}
                  label="Select an existing contact"
                  disabled={prospectMode !== "use_matching" || !selectedProspectId}
                />
                <FormControlLabel value="new" control={<Radio />} label="Create a new contact" />
                <FormControlLabel
                  value="role_only"
                  control={<Radio />}
                  label="Create a role-only contact"
                />
              </RadioGroup>

              {contactMode === "existing" ? (
                contactsLoading ? (
                  <Stack direction="row" spacing={1.2} sx={{ alignItems: "center" }}>
                    <CircularProgress size={18} />
                    <Typography sx={{ color: "#475569", fontSize: 13 }}>
                      Loading contacts for the selected prospect...
                    </Typography>
                  </Stack>
                ) : (
                  <AdminFormTextField
                    select
                    label="Existing Contact"
                    value={selectedContactId}
                    onChange={(event) => setSelectedContactId(event.target.value)}
                    helperText={
                      selectedProspect
                        ? `Loaded for ${selectedProspect.organization_name}.`
                        : "Select a matching prospect first."
                    }
                  >
                    {prospectContacts.map((contact) => (
                      <MenuItem key={contact.id} value={contact.id}>
                        {contact.full_name}
                        {contact.job_title ? ` - ${contact.job_title}` : ""}
                        {contact.email ? ` (${contact.email})` : ""}
                      </MenuItem>
                    ))}
                  </AdminFormTextField>
                )
              ) : (
                <Box
                  sx={{
                    display: "grid",
                    gap: 1.15,
                    gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                  }}
                >
                  <AdminFormTextField
                    label={contactMode === "role_only" ? "Contact Name / Role" : "Full Name"}
                    value={form.contact_name}
                    onChange={(event) => updateFormField("contact_name", event.target.value)}
                    helperText={
                      contactMode === "role_only"
                        ? "Use a role label such as Procurement Contact if no named buyer is available."
                        : undefined
                    }
                    required
                  />
                  <AdminFormTextField
                    label="Job Title"
                    value={form.contact_job_title}
                    onChange={(event) => updateFormField("contact_job_title", event.target.value)}
                  />
                  <AdminFormTextField
                    label="Email"
                    value={form.contact_email}
                    onChange={(event) => updateFormField("contact_email", event.target.value)}
                  />
                  <AdminFormTextField
                    label="Phone"
                    value={form.contact_phone}
                    onChange={(event) => updateFormField("contact_phone", event.target.value)}
                  />
                </Box>
              )}

              <Alert severity="info" icon={<InfoOutlinedIcon fontSize="inherit" />}>
                Buyer role, verification status, department, and contact-source metadata are not
                currently accepted by the Phase 3A backend and are therefore not submitted here.
              </Alert>
            </Stack>
          </SectionCard>

          <SectionCard
            icon={<PersonSearchOutlinedIcon fontSize="small" />}
            title="Experience Match"
            subtitle="Select the most relevant existing experience items manually"
            gradient="linear-gradient(90deg, #DCFCE7 0%, #F8FAFC 100%)"
          >
            <Stack spacing={1.25}>
              {experienceItems.length === 0 ? (
                <Typography sx={{ color: "#475569", fontSize: 13 }}>
                  No active experience items are available for this tenant.
                </Typography>
              ) : (
                experienceItems.map((item) => {
                  const draft = experienceDrafts[item.id] || {
                    selected: false,
                    relevance_score: "",
                    match_notes: "",
                  };
                  return (
                    <Paper
                      key={item.id}
                      elevation={0}
                      sx={{
                        p: 1.5,
                        borderRadius: "8px",
                        border: draft.selected ? "1px solid #60A5FA" : "1px solid #D9E2EC",
                        bgcolor: draft.selected ? "#EFF6FF" : "#FFFFFF",
                      }}
                    >
                      <Stack spacing={1.2}>
                        <Stack
                          direction={{ xs: "column", md: "row" }}
                          spacing={1}
                          sx={{ justifyContent: "space-between", alignItems: { md: "center" } }}
                        >
                          <Box>
                            <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                              {item.name}
                            </Typography>
                            <Stack direction="row" spacing={0.8} sx={{ mt: 0.55, flexWrap: "wrap" }}>
                              <Chip
                                size="small"
                                label={item.category}
                                sx={{
                                  bgcolor: "#F8FAFC",
                                  border: "1px solid #CBD5E1",
                                  color: "#334155",
                                }}
                              />
                              {item.technologies_json.slice(0, 2).map((technology) => (
                                <Chip
                                  key={`${item.id}-${technology}`}
                                  size="small"
                                  label={technology}
                                  sx={{
                                    bgcolor: "#F0FDF4",
                                    border: "1px solid #BBF7D0",
                                    color: "#166534",
                                  }}
                                />
                              ))}
                            </Stack>
                          </Box>
                          <FormControlLabel
                            control={
                              <Checkbox
                                checked={draft.selected}
                                onChange={(event) =>
                                  updateExperienceDraft(item.id, (current) => ({
                                    ...current,
                                    selected: event.target.checked,
                                  }))
                                }
                              />
                            }
                            label="Select"
                          />
                        </Stack>
                        <Typography sx={{ color: "#475569", fontSize: 13 }}>
                          {item.confidentiality_safe_summary || "No summary available."}
                        </Typography>
                        <Typography sx={{ color: "#64748B", fontSize: 12.5 }}>
                          Reusable capabilities:{" "}
                          {item.reusable_capabilities_json.length
                            ? item.reusable_capabilities_json.join(", ")
                            : "Not available"}
                        </Typography>
                        {draft.selected ? (
                          <Box
                            sx={{
                              display: "grid",
                              gap: 1.15,
                              gridTemplateColumns: { xs: "1fr", md: "160px 1fr" },
                            }}
                          >
                            <AdminFormTextField
                              label="Relevance Score"
                              type="number"
                              value={draft.relevance_score}
                              onChange={(event) =>
                                updateExperienceDraft(item.id, (current) => ({
                                  ...current,
                                  relevance_score: event.target.value,
                                }))
                              }
                            />
                            <AdminFormTextField
                              label="Match Notes"
                              value={draft.match_notes}
                              onChange={(event) =>
                                updateExperienceDraft(item.id, (current) => ({
                                  ...current,
                                  match_notes: event.target.value,
                                }))
                              }
                            />
                          </Box>
                        ) : null}
                      </Stack>
                    </Paper>
                  );
                })
              )}
            </Stack>
          </SectionCard>

          <SectionCard
            icon={<PlaylistAddCheckCircleOutlinedIcon fontSize="small" />}
            title="Lead Details"
            subtitle="Only fields supported by the current backend are submitted"
            gradient="linear-gradient(90deg, #FDE68A 0%, #F8FAFC 100%)"
          >
            <Stack spacing={1.5}>
              <Box
                sx={{
                  display: "grid",
                  gap: 1.15,
                  gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                }}
              >
                <AdminFormTextField
                  label="Lead Title"
                  value={form.lead_title}
                  onChange={(event) => updateFormField("lead_title", event.target.value)}
                  required
                />
                <AdminFormTextField
                  select
                  label="Priority"
                  value={form.lead_priority}
                  onChange={(event) =>
                    updateFormField(
                      "lead_priority",
                      event.target.value as BuildLeadFormState["lead_priority"]
                    )
                  }
                >
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="low">Low</MenuItem>
                </AdminFormTextField>
                <AdminFormTextField
                  label="Probability Percent"
                  type="number"
                  value={form.probability_pct}
                  onChange={(event) => updateFormField("probability_pct", event.target.value)}
                  helperText="Optional. Must be between 0 and 100."
                />
                <AdminFormTextField
                  label="Initial Task Due Date"
                  type="datetime-local"
                  value={form.first_task_due_at}
                  onChange={(event) => updateFormField("first_task_due_at", event.target.value)}
                  helperText="Leave blank to use the backend working-day default."
                  slotProps={{ inputLabel: { shrink: true } }}
                />
              </Box>

              <AdminFormTextField
                label="Lead Summary"
                multiline
                minRows={3}
                value={form.lead_summary}
                onChange={(event) => updateFormField("lead_summary", event.target.value)}
              />
              <AdminFormTextField
                label="Identified Problem"
                multiline
                minRows={3}
                value={form.identified_problem}
                onChange={(event) => updateFormField("identified_problem", event.target.value)}
              />
              <AdminFormTextField
                label="Proposed Solution"
                multiline
                minRows={3}
                value={form.proposed_solution}
                onChange={(event) => updateFormField("proposed_solution", event.target.value)}
              />

              <Box
                sx={{
                  display: "grid",
                  gap: 1.15,
                  gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                }}
              >
                <AdminFormTextField
                  label="Next Action / Initial Task"
                  value={form.first_task_title}
                  onChange={(event) => updateFormField("first_task_title", event.target.value)}
                />
                <AdminFormTextField
                  select
                  label="Initial Task Priority"
                  value={form.first_task_priority}
                  onChange={(event) =>
                    updateFormField(
                      "first_task_priority",
                      event.target.value as BuildLeadFormState["first_task_priority"]
                    )
                  }
                >
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="low">Low</MenuItem>
                </AdminFormTextField>
              </Box>
              <AdminFormTextField
                label="Initial Task Notes"
                multiline
                minRows={3}
                value={form.first_task_description}
                onChange={(event) =>
                  updateFormField("first_task_description", event.target.value)
                }
              />
              <Alert severity="info" icon={<InsightsOutlinedIcon fontSize="inherit" />}>
                Lead estimated values and currency are currently derived from the opportunity by the
                backend transaction. They are not separately writable through this Phase 3A API.
              </Alert>
            </Stack>
          </SectionCard>
        </>
      ) : null}
    </AdminFormDialog>
  );
}
