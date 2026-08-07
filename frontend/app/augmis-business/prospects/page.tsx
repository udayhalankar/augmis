"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";

import AddCircleRoundedIcon from "@mui/icons-material/AddCircleRounded";
import ApartmentOutlinedIcon from "@mui/icons-material/ApartmentOutlined";
import BadgeOutlinedIcon from "@mui/icons-material/BadgeOutlined";
import BusinessCenterOutlinedIcon from "@mui/icons-material/BusinessCenterOutlined";
import CloseIcon from "@mui/icons-material/Close";
import DeleteOutline from "@mui/icons-material/DeleteOutlineOutlined";
import EditOutlined from "@mui/icons-material/EditOutlined";
import EmailOutlinedIcon from "@mui/icons-material/EmailOutlined";
import EventNoteOutlinedIcon from "@mui/icons-material/EventNoteOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import LanguageOutlinedIcon from "@mui/icons-material/LanguageOutlined";
import LocationOnOutlinedIcon from "@mui/icons-material/LocationOnOutlined";
import MoreVertRoundedIcon from "@mui/icons-material/MoreVertRounded";
import PersonOutlineOutlinedIcon from "@mui/icons-material/PersonOutlineOutlined";
import PublicOutlinedIcon from "@mui/icons-material/PublicOutlined";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import SourceOutlinedIcon from "@mui/icons-material/SourceOutlined";
import TimelineOutlinedIcon from "@mui/icons-material/TimelineOutlined";
import VisibilityOutlined from "@mui/icons-material/VisibilityOutlined";
import WorkOutlineOutlinedIcon from "@mui/icons-material/WorkOutlineOutlined";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
import { OutletPage } from "@/components/layout/OutletPage";
import { useAuth } from "@/context/AuthContext";
import {
  type AugmisBusinessContact,
  type AugmisBusinessProspect,
  type AugmisBusinessProspectActivity,
  type AugmisBusinessProspectLead,
  type AugmisBusinessProspectOpportunity,
  createAugmisBusinessContact,
  createAugmisBusinessProspect,
  deleteAugmisBusinessContact,
  getAugmisBusinessProspect,
  getAugmisBusinessProspectContacts,
  listAugmisBusinessProspectActivities,
  listAugmisBusinessProspectLeads,
  listAugmisBusinessProspectOpportunities,
  listAugmisBusinessProspects,
  updateAugmisBusinessContact,
  updateAugmisBusinessProspect,
} from "@/services/augmisBusinessService";

type ToastSeverity = "success" | "error" | "info" | "warning";
type ProspectDialogMode = "create" | "edit";
type ContactDialogMode = "create" | "edit";
type DetailTabValue = "overview" | "contacts" | "opportunities" | "leads" | "activity";

type ProspectFormState = {
  organization_name: string;
  organization_domain: string;
  website_url: string;
  country: string;
  region: string;
  city: string;
  industry: string;
  organization_type: string;
  employee_range: string;
  general_email: string;
  general_phone: string;
  prospect_status: string;
  estimated_account_potential_min: string;
  estimated_account_potential_max: string;
  estimated_currency: string;
  notes: string;
};

type ContactFormState = {
  full_name: string;
  email: string;
  phone: string;
  job_title: string;
  department: string;
  buyer_role: string;
  linkedin_url: string;
  company_profile_url: string;
  contact_source: string;
  source_url: string;
  evidence_text: string;
  verification_status: string;
  confidence_score: string;
  contact_status: string;
  is_primary: boolean;
  notes: string;
};

type ProspectRowMeta = {
  contacts: AugmisBusinessContact[];
  opportunities: AugmisBusinessProspectOpportunity[];
  leads: AugmisBusinessProspectLead[];
  activities: AugmisBusinessProspectActivity[];
  error: string | null;
};

const DEFAULT_PROSPECT_FORM: ProspectFormState = {
  organization_name: "",
  organization_domain: "",
  website_url: "",
  country: "",
  region: "",
  city: "",
  industry: "",
  organization_type: "",
  employee_range: "",
  general_email: "",
  general_phone: "",
  prospect_status: "active",
  estimated_account_potential_min: "",
  estimated_account_potential_max: "",
  estimated_currency: "",
  notes: "",
};

const DEFAULT_CONTACT_FORM: ContactFormState = {
  full_name: "",
  email: "",
  phone: "",
  job_title: "",
  department: "",
  buyer_role: "unknown",
  linkedin_url: "",
  company_profile_url: "",
  contact_source: "",
  source_url: "",
  evidence_text: "",
  verification_status: "unverified",
  confidence_score: "",
  contact_status: "active",
  is_primary: false,
  notes: "",
};

const BUYER_ROLE_OPTIONS = [
  "economic_buyer",
  "operational_owner",
  "technical_evaluator",
  "procurement_contact",
  "influencer",
  "general_contact",
  "unknown",
] as const;

const VERIFICATION_STATUS_OPTIONS = [
  "published_by_buyer",
  "official_company_website",
  "public_professional_profile",
  "licensed_enrichment",
  "provider_verified",
  "pattern_inferred",
  "unverified",
  "rejected",
] as const;

function formatDate(value: string | null) {
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

function formatAccountPotential(
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

function getContactDisplayName(contact: AugmisBusinessContact | null) {
  if (!contact) return "Not available";
  return (
    contact.full_name ||
    contact.job_title ||
    contact.email ||
    contact.phone ||
    "Not available"
  );
}

function prospectStatusChipColor(status: string) {
  switch (status) {
    case "active":
      return { bgcolor: "#ECFDF3", color: "#067647", borderColor: "#ABEFC6" };
    case "inactive":
      return { bgcolor: "#FFFAEB", color: "#B54708", borderColor: "#FEDF89" };
    default:
      return { bgcolor: "#F2F4F7", color: "#344054", borderColor: "#D0D5DD" };
  }
}

function verificationChipColor(status: string) {
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

function isOpenOpportunityStatus(status: string) {
  return ["draft", "new", "under_review", "qualified"].includes(status);
}

function isActiveLeadStatus(status: string) {
  return status === "active";
}

function prospectToFormState(prospect: AugmisBusinessProspect): ProspectFormState {
  return {
    organization_name: prospect.organization_name,
    organization_domain: prospect.organization_domain ?? "",
    website_url: prospect.website_url ?? "",
    country: prospect.country ?? "",
    region: prospect.region ?? "",
    city: prospect.city ?? "",
    industry: prospect.industry ?? "",
    organization_type: prospect.organization_type ?? "",
    employee_range: prospect.employee_range ?? "",
    general_email: prospect.general_email ?? "",
    general_phone: prospect.general_phone ?? "",
    prospect_status: prospect.prospect_status,
    estimated_account_potential_min:
      prospect.estimated_account_potential_min == null
        ? ""
        : String(prospect.estimated_account_potential_min),
    estimated_account_potential_max:
      prospect.estimated_account_potential_max == null
        ? ""
        : String(prospect.estimated_account_potential_max),
    estimated_currency: prospect.estimated_currency ?? "",
    notes: prospect.notes ?? "",
  };
}

function prospectFormToPayload(form: ProspectFormState) {
  return {
    organization_name: form.organization_name.trim(),
    organization_domain: normalizeOptionalString(form.organization_domain),
    website_url: normalizeOptionalString(form.website_url),
    country: normalizeOptionalString(form.country),
    region: normalizeOptionalString(form.region),
    city: normalizeOptionalString(form.city),
    industry: normalizeOptionalString(form.industry),
    organization_type: normalizeOptionalString(form.organization_type),
    employee_range: normalizeOptionalString(form.employee_range),
    general_email: normalizeOptionalString(form.general_email),
    general_phone: normalizeOptionalString(form.general_phone),
    prospect_status: form.prospect_status,
    estimated_account_potential_min: normalizeOptionalNumber(
      form.estimated_account_potential_min
    ),
    estimated_account_potential_max: normalizeOptionalNumber(
      form.estimated_account_potential_max
    ),
    estimated_currency: normalizeOptionalString(form.estimated_currency),
    notes: normalizeOptionalString(form.notes),
  };
}

function contactToFormState(contact: AugmisBusinessContact): ContactFormState {
  return {
    full_name: contact.full_name ?? "",
    email: contact.email ?? "",
    phone: contact.phone ?? "",
    job_title: contact.job_title ?? "",
    department: contact.department ?? "",
    buyer_role: contact.buyer_role ?? "unknown",
    linkedin_url: contact.linkedin_url ?? "",
    company_profile_url: contact.company_profile_url ?? "",
    contact_source: contact.contact_source ?? "",
    source_url: contact.source_url ?? "",
    evidence_text: contact.evidence_text ?? "",
    verification_status: contact.verification_status,
    confidence_score:
      contact.confidence_score == null ? "" : String(contact.confidence_score),
    contact_status: contact.contact_status,
    is_primary: contact.is_primary,
    notes: contact.notes ?? "",
  };
}

function contactFormToPayload(form: ContactFormState) {
  return {
    full_name: normalizeOptionalString(form.full_name),
    email: normalizeOptionalString(form.email),
    phone: normalizeOptionalString(form.phone),
    job_title: normalizeOptionalString(form.job_title),
    department: normalizeOptionalString(form.department),
    buyer_role: normalizeOptionalString(form.buyer_role),
    linkedin_url: normalizeOptionalString(form.linkedin_url),
    company_profile_url: normalizeOptionalString(form.company_profile_url),
    contact_source: normalizeOptionalString(form.contact_source),
    source_url: normalizeOptionalString(form.source_url),
    evidence_text: normalizeOptionalString(form.evidence_text),
    verification_status: form.verification_status,
    confidence_score: normalizeOptionalNumber(form.confidence_score),
    contact_status: form.contact_status,
    is_primary: form.is_primary,
    notes: normalizeOptionalString(form.notes),
  };
}

function DetailField({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        borderRadius: "8px",
        border: "1px solid #E2E8F0",
        minHeight: 86,
      }}
    >
      <Stack direction="row" spacing={1.1} sx={{ alignItems: "flex-start" }}>
        <Box sx={{ mt: 0.1, color: "#2563EB" }}>{icon}</Box>
        <Box sx={{ minWidth: 0 }}>
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
          <Typography sx={{ mt: 0.65, color: "#0F172A", wordBreak: "break-word" }}>
            {value}
          </Typography>
        </Box>
      </Stack>
    </Paper>
  );
}

function SectionCard({
  title,
  icon,
  gradient,
  children,
  action,
}: {
  title: string;
  icon: ReactNode;
  gradient: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Paper elevation={0} sx={{ borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
      <Box
        sx={{
          px: 2,
          py: 1.4,
          background: gradient,
          borderBottom: "1px solid #E2E8F0",
        }}
      >
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", justifyContent: "space-between" }}>
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

function ProspectFormFields({
  form,
  onChange,
}: {
  form: ProspectFormState;
  onChange: <K extends keyof ProspectFormState>(field: K, value: ProspectFormState[K]) => void;
}) {
  return (
    <Stack spacing={1.5}>
      <SectionCard
        title="Organization"
        icon={<ApartmentOutlinedIcon fontSize="small" />}
        gradient="linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)"
      >
        <Box sx={{ display: "grid", gap: 1.15, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
          <AdminFormTextField
            label="Organization Name"
            value={form.organization_name}
            onChange={(event) => onChange("organization_name", event.target.value)}
            required
          />
          <AdminFormTextField
            label="Domain"
            value={form.organization_domain}
            onChange={(event) => onChange("organization_domain", event.target.value)}
          />
          <Box sx={{ gridColumn: "1 / -1" }}>
            <AdminFormTextField
              label="Website URL"
              value={form.website_url}
              onChange={(event) => onChange("website_url", event.target.value)}
            />
          </Box>
        </Box>
      </SectionCard>

      <SectionCard
        title="Location"
        icon={<LocationOnOutlinedIcon fontSize="small" />}
        gradient="linear-gradient(90deg, #E0F2FE 0%, #F8FAFC 100%)"
      >
        <Box sx={{ display: "grid", gap: 1.15, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" } }}>
          <AdminFormTextField label="Country" value={form.country} onChange={(event) => onChange("country", event.target.value)} />
          <AdminFormTextField label="Region" value={form.region} onChange={(event) => onChange("region", event.target.value)} />
          <AdminFormTextField label="City" value={form.city} onChange={(event) => onChange("city", event.target.value)} />
        </Box>
      </SectionCard>

      <SectionCard
        title="Business Profile"
        icon={<BusinessCenterOutlinedIcon fontSize="small" />}
        gradient="linear-gradient(90deg, #F0FDFA 0%, #F8FAFC 100%)"
      >
        <Box sx={{ display: "grid", gap: 1.15, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" } }}>
          <AdminFormTextField label="Industry" value={form.industry} onChange={(event) => onChange("industry", event.target.value)} />
          <AdminFormTextField
            label="Organization Type"
            value={form.organization_type}
            onChange={(event) => onChange("organization_type", event.target.value)}
          />
          <AdminFormTextField
            label="Employee Range"
            value={form.employee_range}
            onChange={(event) => onChange("employee_range", event.target.value)}
          />
        </Box>
      </SectionCard>

      <SectionCard
        title="Contact"
        icon={<EmailOutlinedIcon fontSize="small" />}
        gradient="linear-gradient(90deg, #EDE9FE 0%, #F8FAFC 100%)"
      >
        <Box sx={{ display: "grid", gap: 1.15, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
          <AdminFormTextField
            label="General Email"
            value={form.general_email}
            onChange={(event) => onChange("general_email", event.target.value)}
          />
          <AdminFormTextField
            label="General Phone"
            value={form.general_phone}
            onChange={(event) => onChange("general_phone", event.target.value)}
          />
        </Box>
      </SectionCard>

      <SectionCard
        title="Commercial"
        icon={<InsightsOutlinedIcon fontSize="small" />}
        gradient="linear-gradient(90deg, #FDE68A 0%, #F8FAFC 100%)"
      >
        <Box sx={{ display: "grid", gap: 1.15, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
          <AdminFormTextField
            select
            label="Prospect Status"
            value={form.prospect_status}
            onChange={(event) => onChange("prospect_status", event.target.value)}
          >
            <MenuItem value="active">Active</MenuItem>
            <MenuItem value="inactive">Inactive</MenuItem>
            <MenuItem value="archived">Archived</MenuItem>
          </AdminFormTextField>
          <AdminFormTextField
            label="Estimated Currency"
            value={form.estimated_currency}
            onChange={(event) => onChange("estimated_currency", event.target.value)}
          />
          <AdminFormTextField
            label="Estimated Account Potential Minimum"
            type="number"
            value={form.estimated_account_potential_min}
            onChange={(event) => onChange("estimated_account_potential_min", event.target.value)}
          />
          <AdminFormTextField
            label="Estimated Account Potential Maximum"
            type="number"
            value={form.estimated_account_potential_max}
            onChange={(event) => onChange("estimated_account_potential_max", event.target.value)}
          />
        </Box>
      </SectionCard>

      <SectionCard
        title="Notes"
        icon={<EventNoteOutlinedIcon fontSize="small" />}
        gradient="linear-gradient(90deg, #DCFCE7 0%, #F8FAFC 100%)"
      >
        <AdminFormTextField
          label="Notes"
          multiline
          minRows={4}
          value={form.notes}
          onChange={(event) => onChange("notes", event.target.value)}
        />
      </SectionCard>
    </Stack>
  );
}

function ContactFormFields({
  form,
  onChange,
}: {
  form: ContactFormState;
  onChange: <K extends keyof ContactFormState>(field: K, value: ContactFormState[K]) => void;
}) {
  return (
    <Stack spacing={1.5}>
      <SectionCard
        title="Identity"
        icon={<PersonOutlineOutlinedIcon fontSize="small" />}
        gradient="linear-gradient(90deg, #DBEAFE 0%, #F8FAFC 100%)"
      >
        <Box sx={{ display: "grid", gap: 1.15, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
          <AdminFormTextField
            label="Full Name"
            value={form.full_name}
            onChange={(event) => onChange("full_name", event.target.value)}
            helperText="Leave blank for a role-only contact if job title, email, or phone is available."
          />
          <AdminFormTextField
            label="Job Title"
            value={form.job_title}
            onChange={(event) => onChange("job_title", event.target.value)}
          />
          <AdminFormTextField
            label="Department"
            value={form.department}
            onChange={(event) => onChange("department", event.target.value)}
          />
          <AdminFormTextField
            select
            label="Buyer Role"
            value={form.buyer_role}
            onChange={(event) => onChange("buyer_role", event.target.value)}
          >
            {BUYER_ROLE_OPTIONS.map((option) => (
              <MenuItem key={option} value={option}>
                {option.replaceAll("_", " ")}
              </MenuItem>
            ))}
          </AdminFormTextField>
        </Box>
      </SectionCard>

      <SectionCard
        title="Reachability"
        icon={<EmailOutlinedIcon fontSize="small" />}
        gradient="linear-gradient(90deg, #E0F2FE 0%, #F8FAFC 100%)"
      >
        <Box sx={{ display: "grid", gap: 1.15, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
          <AdminFormTextField
            label="Email"
            value={form.email}
            onChange={(event) => onChange("email", event.target.value)}
          />
          <AdminFormTextField
            label="Phone"
            value={form.phone}
            onChange={(event) => onChange("phone", event.target.value)}
          />
          <AdminFormTextField
            label="LinkedIn URL"
            value={form.linkedin_url}
            onChange={(event) => onChange("linkedin_url", event.target.value)}
          />
          <AdminFormTextField
            label="Company Profile URL"
            value={form.company_profile_url}
            onChange={(event) => onChange("company_profile_url", event.target.value)}
          />
        </Box>
      </SectionCard>

      <SectionCard
        title="Source and Verification"
        icon={<SourceOutlinedIcon fontSize="small" />}
        gradient="linear-gradient(90deg, #F0FDFA 0%, #F8FAFC 100%)"
      >
        <Box sx={{ display: "grid", gap: 1.15, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
          <AdminFormTextField
            label="Contact Source"
            value={form.contact_source}
            onChange={(event) => onChange("contact_source", event.target.value)}
          />
          <AdminFormTextField
            label="Source URL"
            value={form.source_url}
            onChange={(event) => onChange("source_url", event.target.value)}
          />
          <AdminFormTextField
            select
            label="Verification Status"
            value={form.verification_status}
            onChange={(event) => onChange("verification_status", event.target.value)}
          >
            {VERIFICATION_STATUS_OPTIONS.map((option) => (
              <MenuItem key={option} value={option}>
                {option.replaceAll("_", " ")}
              </MenuItem>
            ))}
          </AdminFormTextField>
          <AdminFormTextField
            label="Confidence Score"
            type="number"
            value={form.confidence_score}
            onChange={(event) => onChange("confidence_score", event.target.value)}
            helperText="Optional. Must be between 0 and 100."
          />
          <AdminFormTextField
            select
            label="Contact Status"
            value={form.contact_status}
            onChange={(event) => onChange("contact_status", event.target.value)}
          >
            <MenuItem value="active">Active</MenuItem>
            <MenuItem value="inactive">Inactive</MenuItem>
            <MenuItem value="archived">Archived</MenuItem>
          </AdminFormTextField>
          <AdminFormTextField
            select
            label="Primary Contact"
            value={form.is_primary ? "yes" : "no"}
            onChange={(event) => onChange("is_primary", event.target.value === "yes")}
          >
            <MenuItem value="no">No</MenuItem>
            <MenuItem value="yes">Yes</MenuItem>
          </AdminFormTextField>
          <Box sx={{ gridColumn: "1 / -1" }}>
            <AdminFormTextField
              label="Evidence Text"
              multiline
              minRows={3}
              value={form.evidence_text}
              onChange={(event) => onChange("evidence_text", event.target.value)}
            />
          </Box>
        </Box>
      </SectionCard>

      <SectionCard
        title="Notes"
        icon={<EventNoteOutlinedIcon fontSize="small" />}
        gradient="linear-gradient(90deg, #EDE9FE 0%, #F8FAFC 100%)"
      >
        <AdminFormTextField
          label="Notes"
          multiline
          minRows={3}
          value={form.notes}
          onChange={(event) => onChange("notes", event.target.value)}
        />
      </SectionCard>
    </Stack>
  );
}

export default function AugmisBusinessProspectsPage() {
  const { hasPermission } = useAuth();
  const canRead = hasPermission("business_development:read");
  const canCreate = hasPermission("business_development:create");
  const canUpdate = hasPermission("business_development:update");
  const canDelete = hasPermission("business_development:delete");

  const [items, setItems] = useState<AugmisBusinessProspect[]>([]);
  const [rowMeta, setRowMeta] = useState<Record<string, ProspectRowMeta>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [refreshTick, setRefreshTick] = useState(0);

  const [toastOpen, setToastOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastSeverity, setToastSeverity] = useState<ToastSeverity>("success");

  const [menuAnchorEl, setMenuAnchorEl] = useState<HTMLElement | null>(null);
  const [menuProspect, setMenuProspect] = useState<AugmisBusinessProspect | null>(null);

  const [prospectDialogOpen, setProspectDialogOpen] = useState(false);
  const [prospectDialogMode, setProspectDialogMode] = useState<ProspectDialogMode>("create");
  const [prospectDialogSaving, setProspectDialogSaving] = useState(false);
  const [prospectDialogError, setProspectDialogError] = useState("");
  const [prospectForm, setProspectForm] = useState<ProspectFormState>(DEFAULT_PROSPECT_FORM);
  const [editingProspectId, setEditingProspectId] = useState<string | null>(null);
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false);
  const [duplicateMessage, setDuplicateMessage] = useState("");

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailTab, setDetailTab] = useState<DetailTabValue>("overview");
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [selectedProspect, setSelectedProspect] = useState<AugmisBusinessProspect | null>(null);
  const [detailContacts, setDetailContacts] = useState<AugmisBusinessContact[]>([]);
  const [detailOpportunities, setDetailOpportunities] = useState<AugmisBusinessProspectOpportunity[]>([]);
  const [detailLeads, setDetailLeads] = useState<AugmisBusinessProspectLead[]>([]);
  const [detailActivities, setDetailActivities] = useState<AugmisBusinessProspectActivity[]>([]);

  const [contactDialogOpen, setContactDialogOpen] = useState(false);
  const [contactDialogMode, setContactDialogMode] = useState<ContactDialogMode>("create");
  const [contactDialogSaving, setContactDialogSaving] = useState(false);
  const [contactDialogError, setContactDialogError] = useState("");
  const [contactForm, setContactForm] = useState<ContactFormState>(DEFAULT_CONTACT_FORM);
  const [contactDialogProspect, setContactDialogProspect] = useState<AugmisBusinessProspect | null>(null);
  const [editingContactId, setEditingContactId] = useState<string | null>(null);

  const [deleteContactDialogOpen, setDeleteContactDialogOpen] = useState(false);
  const [deleteContactSaving, setDeleteContactSaving] = useState(false);
  const [deleteContactError, setDeleteContactError] = useState("");
  const [deleteContactTarget, setDeleteContactTarget] = useState<AugmisBusinessContact | null>(null);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(0);
    }, 350);

    return () => window.clearTimeout(timeout);
  }, [searchInput]);

  useEffect(() => {
    if (!canRead) return;

    let active = true;

    async function loadProspects() {
      setLoading(true);
      setError("");

      try {
        const result = await listAugmisBusinessProspects({
          page: page + 1,
          page_size: pageSize,
          search: search || undefined,
          status: statusFilter === "all" ? undefined : statusFilter,
        });

        if (!active) return;

        setItems(result.data || []);
        setTotal(result.pagination?.total || 0);

        const metaEntries = await Promise.all(
          (result.data || []).map(async (prospect) => {
            try {
              const [contactsResult, opportunitiesResult, leadsResult, activitiesResult] =
                await Promise.all([
                  getAugmisBusinessProspectContacts(prospect.id),
                  listAugmisBusinessProspectOpportunities(prospect.id),
                  listAugmisBusinessProspectLeads(prospect.id),
                  listAugmisBusinessProspectActivities(prospect.id),
                ]);

              return [
                prospect.id,
                {
                  contacts: contactsResult.data || [],
                  opportunities: opportunitiesResult.data || [],
                  leads: leadsResult.data || [],
                  activities: activitiesResult.data || [],
                  error: null,
                },
              ] as const;
            } catch (metaError) {
              return [
                prospect.id,
                {
                  contacts: [],
                  opportunities: [],
                  leads: [],
                  activities: [],
                  error: getBackendErrorMessage(
                    metaError,
                    "Unable to load related prospect metrics."
                  ),
                },
              ] as const;
            }
          })
        );

        if (!active) return;
        setRowMeta(Object.fromEntries(metaEntries));
      } catch (loadError) {
        if (!active) return;
        setError(getBackendErrorMessage(loadError, "Unable to load prospects."));
        setItems([]);
        setTotal(0);
        setRowMeta({});
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadProspects();

    return () => {
      active = false;
    };
  }, [canRead, page, pageSize, refreshTick, search, statusFilter]);

  const loadedProspectCount = items.length;
  const primaryContactCount = useMemo(
    () =>
      Object.values(rowMeta).filter((meta) => meta.contacts.some((contact) => contact.is_primary))
        .length,
    [rowMeta]
  );

  function showToast(message: string, severity: ToastSeverity) {
    setToastMessage(message);
    setToastSeverity(severity);
    setToastOpen(true);
  }

  function closeActionMenu() {
    setMenuAnchorEl(null);
    setMenuProspect(null);
  }

  function openActionMenu(
    event: React.MouseEvent<HTMLElement>,
    prospect: AugmisBusinessProspect
  ) {
    setMenuAnchorEl(event.currentTarget);
    setMenuProspect(prospect);
  }

  function updateProspectFormField<K extends keyof ProspectFormState>(
    field: K,
    value: ProspectFormState[K]
  ) {
    setProspectForm((current) => ({ ...current, [field]: value }));
  }

  function updateContactFormField<K extends keyof ContactFormState>(
    field: K,
    value: ContactFormState[K]
  ) {
    setContactForm((current) => ({ ...current, [field]: value }));
  }

  function openCreateProspectDialog() {
    setProspectDialogMode("create");
    setEditingProspectId(null);
    setProspectForm(DEFAULT_PROSPECT_FORM);
    setProspectDialogError("");
    setProspectDialogOpen(true);
  }

  function closeProspectDialog() {
    if (prospectDialogSaving) return;
    setProspectDialogOpen(false);
    setProspectDialogError("");
    setDuplicateDialogOpen(false);
  }

  async function openEditProspectDialog(prospect: AugmisBusinessProspect) {
    closeActionMenu();
    setProspectDialogMode("edit");
    setEditingProspectId(prospect.id);
    setProspectForm(prospectToFormState(prospect));
    setProspectDialogError("");
    setProspectDialogOpen(true);
  }

  async function handleSaveProspect() {
    setProspectDialogError("");
    if (!prospectForm.organization_name.trim()) {
      setProspectDialogError("Organization name is required.");
      return;
    }

    setProspectDialogSaving(true);
    try {
      if (prospectDialogMode === "create") {
        const result = await createAugmisBusinessProspect(prospectFormToPayload(prospectForm));
        closeProspectDialog();
        setRefreshTick((value) => value + 1);
        showToast(`Prospect created: ${result.data.organization_name}.`, "success");
      } else if (editingProspectId) {
        const result = await updateAugmisBusinessProspect(
          editingProspectId,
          prospectFormToPayload(prospectForm)
        );
        closeProspectDialog();
        setRefreshTick((value) => value + 1);
        if (selectedProspect?.id === editingProspectId) {
          void openDetailDrawer(result.data.id);
        }
        showToast(`Prospect updated: ${result.data.organization_name}.`, "success");
      }
    } catch (saveError) {
      const message = getBackendErrorMessage(saveError, "Unable to save prospect.");
      setProspectDialogError(message);
      if (message.toLowerCase().includes("matching prospect")) {
        setDuplicateMessage(
          `${message} The current backend does not return the matching prospect record, so review the existing list to inspect the duplicate before retrying.`
        );
        setDuplicateDialogOpen(true);
      }
    } finally {
      setProspectDialogSaving(false);
    }
  }

  async function openDetailDrawer(prospectId: string) {
    setDetailOpen(true);
    setDetailTab("overview");
    setDetailLoading(true);
    setDetailError("");

    try {
      const [prospectResult, contactsResult, opportunitiesResult, leadsResult, activitiesResult] =
        await Promise.all([
          getAugmisBusinessProspect(prospectId),
          getAugmisBusinessProspectContacts(prospectId),
          listAugmisBusinessProspectOpportunities(prospectId),
          listAugmisBusinessProspectLeads(prospectId),
          listAugmisBusinessProspectActivities(prospectId),
        ]);

      setSelectedProspect(prospectResult.data);
      setDetailContacts(contactsResult.data || []);
      setDetailOpportunities(opportunitiesResult.data || []);
      setDetailLeads(leadsResult.data || []);
      setDetailActivities(activitiesResult.data || []);
      setRowMeta((current) => ({
        ...current,
        [prospectId]: {
          contacts: contactsResult.data || [],
          opportunities: opportunitiesResult.data || [],
          leads: leadsResult.data || [],
          activities: activitiesResult.data || [],
          error: null,
        },
      }));
    } catch (drawerError) {
      setDetailError(getBackendErrorMessage(drawerError, "Unable to load prospect details."));
      setSelectedProspect(null);
      setDetailContacts([]);
      setDetailOpportunities([]);
      setDetailLeads([]);
      setDetailActivities([]);
    } finally {
      setDetailLoading(false);
    }
  }

  function closeDetailDrawer() {
    setDetailOpen(false);
  }

  function openCreateContactDialog(prospect: AugmisBusinessProspect) {
    closeActionMenu();
    setContactDialogMode("create");
    setEditingContactId(null);
    setContactDialogProspect(prospect);
    setContactDialogError("");
    setContactForm(DEFAULT_CONTACT_FORM);
    setContactDialogOpen(true);
  }

  function openEditContactDialog(
    prospect: AugmisBusinessProspect,
    contact: AugmisBusinessContact
  ) {
    setContactDialogMode("edit");
    setEditingContactId(contact.id);
    setContactDialogProspect(prospect);
    setContactDialogError("");
    setContactForm(contactToFormState(contact));
    setContactDialogOpen(true);
  }

  function closeContactDialog() {
    if (contactDialogSaving) return;
    setContactDialogOpen(false);
    setContactDialogError("");
  }

  async function refreshDetailIfNeeded(prospectId: string) {
    setRefreshTick((value) => value + 1);
    if (selectedProspect?.id === prospectId) {
      await openDetailDrawer(prospectId);
    }
  }

  async function handleSaveContact() {
    if (!contactDialogProspect) return;

    const hasAnyIdentity =
      Boolean(contactForm.full_name.trim()) ||
      Boolean(contactForm.job_title.trim()) ||
      Boolean(contactForm.email.trim()) ||
      Boolean(contactForm.phone.trim());
    if (!hasAnyIdentity) {
      setContactDialogError(
        "Provide at least one of full name, job title, email, or phone."
      );
      return;
    }

    const confidenceScore = normalizeOptionalNumber(contactForm.confidence_score);
    if (confidenceScore != null && (confidenceScore < 0 || confidenceScore > 100)) {
      setContactDialogError("Confidence score must be between 0 and 100.");
      return;
    }

    setContactDialogSaving(true);
    setContactDialogError("");
    try {
      if (contactDialogMode === "create") {
        const result = await createAugmisBusinessContact(
          contactDialogProspect.id,
          contactFormToPayload(contactForm)
        );
        closeContactDialog();
        await refreshDetailIfNeeded(contactDialogProspect.id);
        showToast(`Contact created: ${getContactDisplayName(result.data)}.`, "success");
      } else if (editingContactId) {
        const result = await updateAugmisBusinessContact(
          editingContactId,
          contactFormToPayload(contactForm)
        );
        closeContactDialog();
        await refreshDetailIfNeeded(contactDialogProspect.id);
        showToast(`Contact updated: ${getContactDisplayName(result.data)}.`, "success");
      }
    } catch (saveError) {
      setContactDialogError(getBackendErrorMessage(saveError, "Unable to save contact."));
    } finally {
      setContactDialogSaving(false);
    }
  }

  function promptDeleteContact(
    prospect: AugmisBusinessProspect,
    contact: AugmisBusinessContact
  ) {
    setContactDialogProspect(prospect);
    setDeleteContactTarget(contact);
    setDeleteContactError("");
    setDeleteContactDialogOpen(true);
  }

  function closeDeleteContactDialog() {
    if (deleteContactSaving) return;
    setDeleteContactDialogOpen(false);
    setDeleteContactError("");
    setDeleteContactTarget(null);
  }

  async function handleDeleteContact() {
    if (!deleteContactTarget || !contactDialogProspect) return;

    setDeleteContactSaving(true);
    setDeleteContactError("");
    try {
      await deleteAugmisBusinessContact(deleteContactTarget.id);
      closeDeleteContactDialog();
      await refreshDetailIfNeeded(contactDialogProspect.id);
      showToast(
        `Contact deleted: ${getContactDisplayName(deleteContactTarget)}.`,
        "success"
      );
    } catch (deleteError) {
      setDeleteContactError(
        getBackendErrorMessage(deleteError, "Unable to delete contact.")
      );
    } finally {
      setDeleteContactSaving(false);
    }
  }

  if (!canRead) {
    return (
      <OutletPage
        title="Prospects"
        description="Prospect management requires business development read access."
      >
        <Alert severity="warning">
          You do not currently have permission to view tenant prospect records.
        </Alert>
      </OutletPage>
    );
  }

  return (
    <>
      <OutletPage
        title="Prospects"
        description="Manage tenant-scoped target organizations, buyer contacts, related opportunities, and live activity history."
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
            <Box
              sx={{
                px: { xs: 2.25, md: 2.5 },
                py: { xs: 2.25, md: 2.4 },
                background:
                  "linear-gradient(135deg, rgba(13,45,78,0.98) 0%, rgba(25,93,161,0.95) 58%, rgba(222,239,255,0.92) 100%)",
                color: "#F8FAFC",
              }}
            >
              <Stack
                direction={{ xs: "column", lg: "row" }}
                spacing={2}
                sx={{ justifyContent: "space-between", alignItems: { lg: "center" } }}
              >
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    Prospect Management
                  </Typography>
                  <Typography sx={{ mt: 0.8, color: "rgba(248,250,252,0.88)", maxWidth: 780 }}>
                    Manual prospect and contact management is now connected to the live
                    AUGMIS Business API. Current backend filtering supports organization search,
                    status, and server-side pagination.
                  </Typography>
                </Box>
                {canCreate ? (
                  <Button
                    variant="contained"
                    startIcon={<AddCircleRoundedIcon />}
                    onClick={openCreateProspectDialog}
                    sx={{
                      textTransform: "none",
                      fontWeight: 700,
                      borderRadius: "8px",
                      bgcolor: "#2563EB",
                      minWidth: 168,
                      "&:hover": { bgcolor: "#1D4ED8" },
                    }}
                  >
                    New Prospect
                  </Button>
                ) : null}
              </Stack>
            </Box>

            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={1.5}
              sx={{ p: 2, borderBottom: "1px solid #E2E8F0", bgcolor: "#F8FAFC" }}
            >
              <Paper
                elevation={0}
                sx={{
                  flex: 1,
                  p: 1.75,
                  borderRadius: "8px",
                  border: "1px solid #E2E8F0",
                }}
              >
                <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: ".05em" }}>
                  Total Prospects
                </Typography>
                <Typography sx={{ mt: 0.6, fontSize: 28, fontWeight: 700, color: "#0F172A" }}>
                  {total}
                </Typography>
              </Paper>
              <Paper
                elevation={0}
                sx={{
                  flex: 1,
                  p: 1.75,
                  borderRadius: "8px",
                  border: "1px solid #E2E8F0",
                }}
              >
                <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: ".05em" }}>
                  Loaded This Page
                </Typography>
                <Typography sx={{ mt: 0.6, fontSize: 28, fontWeight: 700, color: "#0F172A" }}>
                  {loadedProspectCount}
                </Typography>
              </Paper>
              <Paper
                elevation={0}
                sx={{
                  flex: 1,
                  p: 1.75,
                  borderRadius: "8px",
                  border: "1px solid #E2E8F0",
                }}
              >
                <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: ".05em" }}>
                  Primary Contacts Visible
                </Typography>
                <Typography sx={{ mt: 0.6, fontSize: 28, fontWeight: 700, color: "#0F172A" }}>
                  {primaryContactCount}
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
                placeholder="Search organization, domain, or industry"
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
                }}
                fieldSx={{ minWidth: { xs: "100%", md: 180 } }}
              >
                <MenuItem value="all">All statuses</MenuItem>
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="inactive">Inactive</MenuItem>
                <MenuItem value="archived">Archived</MenuItem>
              </AdminFormTextField>
              <Button
                variant="outlined"
                startIcon={<RefreshRoundedIcon />}
                onClick={() => setRefreshTick((value) => value + 1)}
                sx={{
                  textTransform: "none",
                  borderRadius: "8px",
                  alignSelf: { xs: "stretch", md: "flex-end" },
                }}
              >
                Refresh
              </Button>
            </Stack>

            <Box sx={{ px: 2, pb: 1.5 }}>
              <Alert severity="info">
                The current backend list API supports search, status, and pagination. Country,
                region, and industry filters will be added when those server-side filters are
                exposed.
              </Alert>
            </Box>

            {loading ? (
              <Stack sx={{ minHeight: 280, alignItems: "center", justifyContent: "center" }} spacing={1.5}>
                <CircularProgress />
                <Typography sx={{ color: "#475569" }}>Loading prospects...</Typography>
              </Stack>
            ) : error ? (
              <Box sx={{ p: 2 }}>
                <Alert severity="error">{error}</Alert>
              </Box>
            ) : items.length === 0 ? (
              <Box sx={{ p: 2 }}>
                <EmptyPanel
                  title="No prospects found"
                  description="No tenant prospects match the current search and status filter. Create a new prospect or broaden the query."
                />
              </Box>
            ) : (
              <>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Organization</TableCell>
                      <TableCell>Country / Region</TableCell>
                      <TableCell>Industry</TableCell>
                      <TableCell>Domain / Website</TableCell>
                      <TableCell>Primary Buyer / Contact</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Account Potential</TableCell>
                      <TableCell>Open Opportunities</TableCell>
                      <TableCell>Active Leads</TableCell>
                      <TableCell>Last Activity</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {items.map((item) => {
                      const meta = rowMeta[item.id];
                      const primaryContact =
                        meta?.contacts.find((contact) => contact.is_primary) || null;
                      const openOpportunityCount =
                        meta?.opportunities.filter((opportunity) =>
                          isOpenOpportunityStatus(opportunity.opportunity_status)
                        ).length ?? 0;
                      const activeLeadCount =
                        meta?.leads.filter((lead) => isActiveLeadStatus(lead.lead_status)).length ??
                        0;
                      const lastActivity = meta?.activities[0] || null;

                      return (
                        <TableRow key={item.id} hover>
                          <TableCell sx={{ minWidth: 210 }}>
                            <Button
                              onClick={() => void openDetailDrawer(item.id)}
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
                              {item.organization_name}
                            </Button>
                            <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12.5 }}>
                              {item.organization_type || "Not available"}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography sx={{ color: "#0F172A" }}>
                              {item.country || "Not available"}
                            </Typography>
                            <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12.5 }}>
                              {item.region || "Not available"}
                            </Typography>
                          </TableCell>
                          <TableCell>{item.industry || "Not available"}</TableCell>
                          <TableCell sx={{ maxWidth: 220 }}>
                            <Typography sx={{ color: "#0F172A", wordBreak: "break-word" }}>
                              {item.organization_domain || "Not available"}
                            </Typography>
                            <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12.5, wordBreak: "break-word" }}>
                              {item.website_url || "Not available"}
                            </Typography>
                          </TableCell>
                          <TableCell sx={{ maxWidth: 220 }}>
                            <Typography sx={{ color: "#0F172A" }}>
                              {getContactDisplayName(primaryContact)}
                            </Typography>
                            <Typography sx={{ mt: 0.35, color: "#64748B", fontSize: 12.5 }}>
                              {primaryContact?.buyer_role
                                ? primaryContact.buyer_role.replaceAll("_", " ")
                                : "Not available"}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={item.prospect_status.replaceAll("_", " ")}
                              size="small"
                              sx={{
                                textTransform: "capitalize",
                                border: "1px solid",
                                ...prospectStatusChipColor(item.prospect_status),
                              }}
                            />
                          </TableCell>
                          <TableCell>
                            {formatAccountPotential(
                              item.estimated_account_potential_min,
                              item.estimated_account_potential_max,
                              item.estimated_currency
                            )}
                          </TableCell>
                          <TableCell>{openOpportunityCount}</TableCell>
                          <TableCell>{activeLeadCount}</TableCell>
                          <TableCell>{lastActivity ? formatDate(lastActivity.created_at) : "Not available"}</TableCell>
                          <TableCell align="right">
                            <Tooltip title="Actions">
                              <span>
                                <IconButton size="small" onClick={(event) => openActionMenu(event, item)}>
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
      </OutletPage>

      <Menu anchorEl={menuAnchorEl} open={Boolean(menuAnchorEl)} onClose={closeActionMenu}>
        <MenuItem
          onClick={() => {
            if (menuProspect) {
              void openDetailDrawer(menuProspect.id);
            }
            closeActionMenu();
          }}
          disabled={!canRead}
        >
          <VisibilityOutlined fontSize="small" style={{ marginRight: 10 }} />
          View Details
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (menuProspect) {
              void openEditProspectDialog(menuProspect);
            }
          }}
          disabled={!canUpdate}
        >
          <EditOutlined fontSize="small" style={{ marginRight: 10 }} />
          Edit
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (menuProspect) {
              openCreateContactDialog(menuProspect);
            }
          }}
          disabled={!canCreate}
        >
          <AddCircleRoundedIcon fontSize="small" style={{ marginRight: 10, color: "#2563EB" }} />
          Add Contact
        </MenuItem>
      </Menu>

      <AdminFormDialog
        open={prospectDialogOpen}
        onClose={closeProspectDialog}
        title={prospectDialogMode === "create" ? "Create Prospect" : "Edit Prospect"}
        maxWidth={900}
        stackSx={{ maxWidth: 760 }}
        actions={
          <>
            <Button onClick={closeProspectDialog} disabled={prospectDialogSaving} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleSaveProspect}
              disabled={prospectDialogSaving}
              sx={{
                textTransform: "none",
                fontWeight: 700,
                borderRadius: "8px",
                bgcolor: "#2563EB",
                "&:hover": { bgcolor: "#1D4ED8" },
              }}
            >
              {prospectDialogSaving
                ? prospectDialogMode === "create"
                  ? "Creating..."
                  : "Saving..."
                : prospectDialogMode === "create"
                  ? "Create Prospect"
                  : "Save Changes"}
            </Button>
          </>
        }
      >
        {prospectDialogError ? <Alert severity="error">{prospectDialogError}</Alert> : null}
        <ProspectFormFields form={prospectForm} onChange={updateProspectFormField} />
      </AdminFormDialog>

      <AdminFormDialog
        open={contactDialogOpen}
        onClose={closeContactDialog}
        title={
          contactDialogMode === "create"
            ? `Add Contact${contactDialogProspect ? ` - ${contactDialogProspect.organization_name}` : ""}`
            : "Edit Contact"
        }
        maxWidth={900}
        stackSx={{ maxWidth: 760 }}
        actions={
          <>
            <Button onClick={closeContactDialog} disabled={contactDialogSaving} sx={{ textTransform: "none" }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleSaveContact}
              disabled={contactDialogSaving}
              sx={{
                textTransform: "none",
                fontWeight: 700,
                borderRadius: "8px",
                bgcolor: "#2563EB",
                "&:hover": { bgcolor: "#1D4ED8" },
              }}
            >
              {contactDialogSaving
                ? contactDialogMode === "create"
                  ? "Creating..."
                  : "Saving..."
                : contactDialogMode === "create"
                  ? "Create Contact"
                  : "Save Contact"}
            </Button>
          </>
        }
      >
        {contactDialogError ? <Alert severity="error">{contactDialogError}</Alert> : null}
        <ContactFormFields form={contactForm} onChange={updateContactFormField} />
      </AdminFormDialog>

      <Dialog open={duplicateDialogOpen} onClose={() => setDuplicateDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle sx={{ fontWeight: 700 }}>Potential Duplicate Prospect</DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} sx={{ mt: 0.5 }}>
            <Alert severity="warning">{duplicateMessage}</Alert>
            <Typography sx={{ color: "#475569" }}>
              The backend currently returns a duplicate warning but not the existing prospect id or
              display payload, so the duplicate must be reviewed from the live prospect list.
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setDuplicateDialogOpen(false)} sx={{ textTransform: "none" }}>
            Back to Form
          </Button>
          <Button
            variant="contained"
            onClick={() => {
              setDuplicateDialogOpen(false);
              closeProspectDialog();
            }}
            sx={{ textTransform: "none", fontWeight: 700, borderRadius: "8px", bgcolor: "#2563EB" }}
          >
            Review Prospect List
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteContactDialogOpen} onClose={closeDeleteContactDialog} fullWidth maxWidth="sm">
        <DialogTitle sx={{ fontWeight: 700 }}>Delete Contact</DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} sx={{ mt: 0.5 }}>
            {deleteContactError ? <Alert severity="error">{deleteContactError}</Alert> : null}
            <Typography sx={{ color: "#0F172A" }}>
              You are about to permanently delete this contact.
            </Typography>
            <Paper elevation={0} sx={{ p: 2, border: "1px solid #FECACA", borderRadius: "8px", bgcolor: "#FEF2F2" }}>
              <Typography sx={{ fontWeight: 700, color: "#7F1D1D" }}>
                {getContactDisplayName(deleteContactTarget)}
              </Typography>
              <Typography sx={{ mt: 0.4, color: "#991B1B" }}>
                {contactDialogProspect?.organization_name || "Prospect not available"}
              </Typography>
            </Paper>
            <Typography sx={{ color: "#7C2D12" }}>
              This action cannot be undone. If the contact is assigned as a lead primary contact,
              reassign that lead contact first.
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={closeDeleteContactDialog} disabled={deleteContactSaving} sx={{ textTransform: "none" }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDeleteContact}
            disabled={deleteContactSaving}
            sx={{ textTransform: "none", fontWeight: 700, borderRadius: "8px" }}
          >
            {deleteContactSaving ? "Deleting..." : "Delete Contact"}
          </Button>
        </DialogActions>
      </Dialog>

      <Drawer
        anchor="right"
        open={detailOpen}
        onClose={closeDetailDrawer}
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
              background:
                "linear-gradient(135deg, rgba(13,45,78,0.98) 0%, rgba(25,93,161,0.95) 58%, rgba(222,239,255,0.92) 100%)",
              color: "#F8FAFC",
            }}
          >
            <Stack direction="row" spacing={1.5} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  Prospect Details
                </Typography>
                <Typography sx={{ mt: 0.6, color: "rgba(248,250,252,0.88)" }}>
                  Review the full tenant-scoped prospect record, contacts, related opportunities,
                  active leads, and business activity history.
                </Typography>
              </Box>
              <IconButton onClick={closeDetailDrawer} sx={{ color: "#F8FAFC" }}>
                <CloseIcon />
              </IconButton>
            </Stack>
            <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: "wrap" }}>
              <Button
                variant="contained"
                startIcon={<EditOutlined />}
                disabled={!selectedProspect || !canUpdate}
                onClick={() => selectedProspect && void openEditProspectDialog(selectedProspect)}
                sx={{
                  textTransform: "none",
                  borderRadius: "8px",
                  bgcolor: "rgba(255,255,255,0.16)",
                  color: "#FFFFFF",
                  boxShadow: "none",
                }}
              >
                Edit
              </Button>
              <Button
                variant="contained"
                startIcon={<AddCircleRoundedIcon />}
                disabled={!selectedProspect || !canCreate}
                onClick={() => selectedProspect && openCreateContactDialog(selectedProspect)}
                sx={{
                  textTransform: "none",
                  borderRadius: "8px",
                  bgcolor: "rgba(37,99,235,0.78)",
                  color: "#FFFFFF",
                  boxShadow: "none",
                }}
              >
                Add Contact
              </Button>
              <Button
                variant="outlined"
                onClick={closeDetailDrawer}
                sx={{
                  textTransform: "none",
                  borderRadius: "8px",
                  color: "#FFFFFF",
                  borderColor: "rgba(255,255,255,0.4)",
                }}
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
              <Tab value="contacts" label={`Contacts (${detailContacts.length})`} />
              <Tab value="opportunities" label={`Related Opportunities (${detailOpportunities.length})`} />
              <Tab value="leads" label={`Related Leads (${detailLeads.length})`} />
              <Tab value="activity" label={`Activity (${detailActivities.length})`} />
            </Tabs>
          </Box>

          <Box sx={{ p: 2.5, overflowY: "auto", flex: 1 }}>
            {detailLoading ? (
              <Stack sx={{ minHeight: 280, alignItems: "center", justifyContent: "center" }} spacing={1.5}>
                <CircularProgress />
                <Typography sx={{ color: "#475569" }}>Loading prospect details...</Typography>
              </Stack>
            ) : detailError ? (
              <Alert severity="error">{detailError}</Alert>
            ) : selectedProspect ? (
              <>
                {detailTab === "overview" ? (
                  <Stack spacing={2}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2.25,
                        borderRadius: "8px",
                        border: "1px solid #D9E2EC",
                        background:
                          "linear-gradient(180deg, rgba(239,246,255,0.9) 0%, rgba(248,250,252,0.95) 100%)",
                      }}
                    >
                      <Typography variant="h5" sx={{ fontWeight: 700, color: "#0F172A" }}>
                        {selectedProspect.organization_name}
                      </Typography>
                      <Stack direction="row" spacing={1} sx={{ mt: 1.25, flexWrap: "wrap" }}>
                        <Chip
                          label={selectedProspect.prospect_status.replaceAll("_", " ")}
                          size="small"
                          sx={{
                            textTransform: "capitalize",
                            border: "1px solid",
                            ...prospectStatusChipColor(selectedProspect.prospect_status),
                          }}
                        />
                        {detailContacts.some((contact) => contact.is_primary) ? (
                          <Chip
                            label={`Primary: ${getContactDisplayName(
                              detailContacts.find((contact) => contact.is_primary) || null
                            )}`}
                            size="small"
                            sx={{ bgcolor: "#FFFFFF", border: "1px solid #CBD5E1" }}
                          />
                        ) : null}
                      </Stack>
                    </Paper>

                    <Box
                      sx={{
                        display: "grid",
                        gap: 1.5,
                        gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                      }}
                    >
                      <DetailField icon={<LanguageOutlinedIcon fontSize="small" />} label="Domain" value={selectedProspect.organization_domain || "Not available"} />
                      <DetailField icon={<LanguageOutlinedIcon fontSize="small" />} label="Website" value={selectedProspect.website_url || "Not available"} />
                      <DetailField icon={<PublicOutlinedIcon fontSize="small" />} label="Country" value={selectedProspect.country || "Not available"} />
                      <DetailField icon={<LocationOnOutlinedIcon fontSize="small" />} label="Region" value={selectedProspect.region || "Not available"} />
                      <DetailField icon={<LocationOnOutlinedIcon fontSize="small" />} label="City" value={selectedProspect.city || "Not available"} />
                      <DetailField icon={<WorkOutlineOutlinedIcon fontSize="small" />} label="Industry" value={selectedProspect.industry || "Not available"} />
                      <DetailField icon={<ApartmentOutlinedIcon fontSize="small" />} label="Organization Type" value={selectedProspect.organization_type || "Not available"} />
                      <DetailField icon={<BusinessCenterOutlinedIcon fontSize="small" />} label="Employee Range" value={selectedProspect.employee_range || "Not available"} />
                      <DetailField icon={<EmailOutlinedIcon fontSize="small" />} label="General Email" value={selectedProspect.general_email || "Not available"} />
                      <DetailField icon={<BadgeOutlinedIcon fontSize="small" />} label="General Phone" value={selectedProspect.general_phone || "Not available"} />
                      <DetailField
                        icon={<InsightsOutlinedIcon fontSize="small" />}
                        label="Estimated Account Potential"
                        value={formatAccountPotential(
                          selectedProspect.estimated_account_potential_min,
                          selectedProspect.estimated_account_potential_max,
                          selectedProspect.estimated_currency
                        )}
                      />
                      <DetailField icon={<TimelineOutlinedIcon fontSize="small" />} label="Created" value={formatDate(selectedProspect.created_at)} />
                      <DetailField icon={<TimelineOutlinedIcon fontSize="small" />} label="Updated" value={formatDate(selectedProspect.updated_at)} />
                      <DetailField icon={<SourceOutlinedIcon fontSize="small" />} label="Source Opportunity" value={selectedProspect.source_opportunity_id || "Not available"} />
                    </Box>

                    <SectionCard
                      title="Notes"
                      icon={<EventNoteOutlinedIcon fontSize="small" />}
                      gradient="linear-gradient(90deg, #DCFCE7 0%, #F8FAFC 100%)"
                    >
                      <Typography sx={{ color: "#0F172A", whiteSpace: "pre-wrap" }}>
                        {selectedProspect.notes || "Not available"}
                      </Typography>
                    </SectionCard>
                  </Stack>
                ) : null}

                {detailTab === "contacts" ? (
                  <SectionCard
                    title="Contacts"
                    icon={<BadgeOutlinedIcon fontSize="small" />}
                    gradient="linear-gradient(90deg, #EDE9FE 0%, #F8FAFC 100%)"
                    action={
                      canCreate && selectedProspect ? (
                        <Button
                          size="small"
                          variant="contained"
                          startIcon={<AddCircleRoundedIcon />}
                          onClick={() => openCreateContactDialog(selectedProspect)}
                          sx={{
                            textTransform: "none",
                            borderRadius: "8px",
                            bgcolor: "#2563EB",
                            "&:hover": { bgcolor: "#1D4ED8" },
                          }}
                        >
                          Add Contact
                        </Button>
                      ) : null
                    }
                  >
                    {detailContacts.length === 0 ? (
                      <EmptyPanel
                        title="No contacts yet"
                        description="This prospect does not yet have buyer or contact records. Add a named or role-only contact to continue."
                      />
                    ) : (
                      <Stack spacing={1.25}>
                        {detailContacts.map((contact) => (
                          <Paper
                            key={contact.id}
                            elevation={0}
                            sx={{
                              p: 1.5,
                              borderRadius: "8px",
                              border: "1px solid #E2E8F0",
                            }}
                          >
                            <Stack spacing={1.1}>
                              <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                                <Box sx={{ minWidth: 0 }}>
                                  <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                                    {getContactDisplayName(contact)}
                                  </Typography>
                                  <Typography sx={{ mt: 0.35, color: "#475569" }}>
                                    {contact.department || contact.job_title || "Not available"}
                                  </Typography>
                                </Box>
                                <Stack direction="row" spacing={0.75} sx={{ flexWrap: "wrap", justifyContent: "flex-end" }}>
                                  {contact.is_primary ? (
                                    <Chip
                                      size="small"
                                      label="Primary"
                                      sx={{ bgcolor: "#DBEAFE", color: "#1D4ED8", border: "1px solid #93C5FD" }}
                                    />
                                  ) : null}
                                  <Chip
                                    size="small"
                                    label={contact.verification_status.replaceAll("_", " ")}
                                    sx={{
                                      textTransform: "capitalize",
                                      border: "1px solid",
                                      ...verificationChipColor(contact.verification_status),
                                    }}
                                  />
                                </Stack>
                              </Stack>

                              <Box sx={{ display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" } }}>
                                <DetailField icon={<BadgeOutlinedIcon fontSize="small" />} label="Buyer Role" value={contact.buyer_role ? contact.buyer_role.replaceAll("_", " ") : "Not available"} />
                                <DetailField icon={<EmailOutlinedIcon fontSize="small" />} label="Email" value={contact.email || "Not available"} />
                                <DetailField icon={<BadgeOutlinedIcon fontSize="small" />} label="Phone" value={contact.phone || "Not available"} />
                                <DetailField icon={<LanguageOutlinedIcon fontSize="small" />} label="LinkedIn URL" value={contact.linkedin_url || "Not available"} />
                                <DetailField icon={<SourceOutlinedIcon fontSize="small" />} label="Contact Source" value={contact.contact_source || "Not available"} />
                                <DetailField icon={<InsightsOutlinedIcon fontSize="small" />} label="Confidence Score" value={contact.confidence_score == null ? "Not available" : String(contact.confidence_score)} />
                              </Box>

                              <Stack direction="row" spacing={1} sx={{ justifyContent: "flex-end", flexWrap: "wrap" }}>
                                <Button
                                  size="small"
                                  variant="outlined"
                                  startIcon={<EditOutlined />}
                                  disabled={!canUpdate}
                                  onClick={() => openEditContactDialog(selectedProspect, contact)}
                                  sx={{ textTransform: "none", borderRadius: "8px" }}
                                >
                                  Edit
                                </Button>
                                <Button
                                  size="small"
                                  variant="outlined"
                                  color="error"
                                  startIcon={<DeleteOutline />}
                                  disabled={!canDelete}
                                  onClick={() => promptDeleteContact(selectedProspect, contact)}
                                  sx={{ textTransform: "none", borderRadius: "8px" }}
                                >
                                  Delete
                                </Button>
                              </Stack>
                            </Stack>
                          </Paper>
                        ))}
                      </Stack>
                    )}
                  </SectionCard>
                ) : null}

                {detailTab === "opportunities" ? (
                  <SectionCard
                    title="Related Opportunities"
                    icon={<TimelineOutlinedIcon fontSize="small" />}
                    gradient="linear-gradient(90deg, #E0F2FE 0%, #F8FAFC 100%)"
                  >
                    {detailOpportunities.length === 0 ? (
                      <EmptyPanel
                        title="No related opportunities"
                        description="No live opportunity records are currently linked to this prospect."
                      />
                    ) : (
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Title</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Source</TableCell>
                            <TableCell>Closing Date</TableCell>
                            <TableCell>Value</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {detailOpportunities.map((opportunity) => (
                            <TableRow key={opportunity.id}>
                              <TableCell>{opportunity.title}</TableCell>
                              <TableCell>
                                <Chip
                                  size="small"
                                  label={opportunity.opportunity_status.replaceAll("_", " ")}
                                  sx={{
                                    textTransform: "capitalize",
                                    border: "1px solid",
                                    ...prospectStatusChipColor(
                                      opportunity.opportunity_status === "qualified"
                                        ? "active"
                                        : opportunity.opportunity_status === "dismissed" ||
                                            opportunity.opportunity_status === "expired"
                                          ? "archived"
                                          : "inactive"
                                    ),
                                  }}
                                />
                              </TableCell>
                              <TableCell>{opportunity.source_name || opportunity.source_type}</TableCell>
                              <TableCell>{formatDate(opportunity.closing_at)}</TableCell>
                              <TableCell>
                                {formatAccountPotential(
                                  opportunity.estimated_value_min,
                                  opportunity.estimated_value_max,
                                  opportunity.estimated_currency
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    )}
                  </SectionCard>
                ) : null}

                {detailTab === "leads" ? (
                  <SectionCard
                    title="Related Leads"
                    icon={<WorkOutlineOutlinedIcon fontSize="small" />}
                    gradient="linear-gradient(90deg, #DCFCE7 0%, #F8FAFC 100%)"
                  >
                    {detailLeads.length === 0 ? (
                      <EmptyPanel
                        title="No related leads"
                        description="This prospect has not yet been converted into an active lead."
                      />
                    ) : (
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Lead Title</TableCell>
                            <TableCell>Stage</TableCell>
                            <TableCell>Priority</TableCell>
                            <TableCell>Value</TableCell>
                            <TableCell>Probability</TableCell>
                            <TableCell>Due Date</TableCell>
                            <TableCell>Next Action</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {detailLeads.map((lead) => (
                            <TableRow key={lead.id}>
                              <TableCell>{lead.title}</TableCell>
                              <TableCell>{lead.lead_stage.replaceAll("_", " ")}</TableCell>
                              <TableCell>{lead.priority}</TableCell>
                              <TableCell>
                                {lead.estimated_value == null
                                  ? "Not available"
                                  : `${lead.estimated_currency ? `${lead.estimated_currency} ` : ""}${lead.estimated_value.toLocaleString()}`}
                              </TableCell>
                              <TableCell>
                                {lead.probability_pct == null ? "Not available" : `${lead.probability_pct}%`}
                              </TableCell>
                              <TableCell>{formatDate(lead.next_action_due_at)}</TableCell>
                              <TableCell>{lead.next_action || "Not available"}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    )}
                  </SectionCard>
                ) : null}

                {detailTab === "activity" ? (
                  <SectionCard
                    title="Activity History"
                    icon={<EventNoteOutlinedIcon fontSize="small" />}
                    gradient="linear-gradient(90deg, #FDE68A 0%, #F8FAFC 100%)"
                  >
                    {detailActivities.length === 0 ? (
                      <EmptyPanel
                        title="No activity recorded"
                        description="This prospect does not yet have business activities in the current tenant timeline."
                      />
                    ) : (
                      <Stack spacing={1.2}>
                        {detailActivities.map((activity) => (
                          <Paper
                            key={activity.id}
                            elevation={0}
                            sx={{
                              p: 1.5,
                              borderRadius: "8px",
                              border: "1px solid #E2E8F0",
                            }}
                          >
                            <Stack direction="row" spacing={1.2} sx={{ alignItems: "flex-start" }}>
                              <Box sx={{ mt: 0.1, color: "#2563EB" }}>
                                <EventNoteOutlinedIcon fontSize="small" />
                              </Box>
                              <Box sx={{ minWidth: 0 }}>
                                <Typography sx={{ fontWeight: 700, color: "#0F172A" }}>
                                  {activity.activity_summary}
                                </Typography>
                                <Typography sx={{ mt: 0.35, color: "#475569" }}>
                                  {activity.activity_type.replaceAll("_", " ")}
                                </Typography>
                                <Typography sx={{ mt: 0.45, color: "#64748B", fontSize: 12.5 }}>
                                  {activity.performed_by || "System"} • {formatDate(activity.created_at)}
                                </Typography>
                                {activity.activity_details_json.description ? (
                                  <Typography sx={{ mt: 0.8, color: "#334155" }}>
                                    {activity.activity_details_json.description}
                                  </Typography>
                                ) : null}
                              </Box>
                            </Stack>
                          </Paper>
                        ))}
                      </Stack>
                    )}
                  </SectionCard>
                ) : null}
              </>
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
    </>
  );
}
