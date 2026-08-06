"use client";

import { useEffect, useMemo, useState, useTransition } from "react";

import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  MenuItem,
  Paper,
  Snackbar,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import {
  ADMIN_FORM_LABEL_SX,
  ADMIN_FORM_TEXTFIELD_SX,
  ADMIN_FORM_MULTILINE_TEXTFIELD_SX,
  AdminFormDialog,
  AdminFormField,
  AdminFormTextField,
} from "@/components/forms/AdminFormDialog";
import { OutletPage } from "@/components/layout/OutletPage";
import { getRepositories } from "@/services/repositoryService";
import {
  createDocumentControllerRecordsConfigurationRow,
  deleteDocumentControllerRecordsConfigurationRow,
  getDocumentControllerRecordsConfiguration,
  updateDocumentControllerRecordsConfigurationRow,
} from "@/services/symployeeRecordConfigurationService";
import {
  bootstrapDocumentControllerPolicies,
  createDocumentControllerPolicy,
  getDocumentControllerPolicies,
  updateDocumentControllerPolicy,
} from "@/services/symployeeService";

type PolicyDomain = "classification" | "metadata_schema" | "reviewer_assignment" | "sla_rules";
type ConfigurationArea = "document_control" | "records_management" | "transmittals";
type RecordConfigurationDomain =
  | "record-categories"
  | "declaration-rules"
  | "lifecycle-rules"
  | "retention-schedules"
  | "vital-policies"
  | "hold-policies"
  | "disposition-policies"
  | "archive-policies"
  | "assignment-rules";

type PolicyVersion = {
  policy_id: string;
  policy_code: string;
  policy_domain: PolicyDomain;
  name: string;
  version_no: number;
  status: string;
  is_default: boolean;
  scope_type?: string;
  scope_ref?: string | null;
  config: Record<string, any>;
};

type ConfigurationField =
  | { label: string; type: "text" | "select"; value: string; options?: string[] }
  | { label: string; type: "toggle"; value: boolean }
  | { label: string; type: "json"; value: string };

type RecordsFormFieldType = "text" | "textarea" | "select" | "toggle" | "number" | "json";

type RecordsFormFieldDefinition = {
  key: string;
  label: string;
  type: RecordsFormFieldType;
  helperText?: string;
  options?: string[];
  required?: boolean;
  nullable?: boolean;
  minRows?: number;
  jsonFallback?: any;
};

type ConfigurationSection = {
  key: string;
  domain: RecordConfigurationDomain;
  title: string;
  description: string;
  scopeRows: Array<{ setting: string; value: string; note?: string }>;
  matrixRows: Array<{ setting: string; value: string; note?: string }>;
  createTemplate: Record<string, any>;
  fields: ConfigurationField[];
};

type RecordsConfigurationRow = Record<string, any>;
type RecordsFormValue = string | boolean;

const RECORDS_FORM_FIELD_DEFAULTS: Record<string, any> = {
  status: "DRAFT",
  version_no: 1,
  is_current_version: true,
  rule_priority: 100,
  config_payload_json: {},
};

type SortableTableColumn<RowType> = {
  key: string;
  label: string;
  align?: "left" | "right" | "center";
  sortable?: boolean;
  sortValue?: (row: RowType) => string | number;
  render: (row: RowType) => React.ReactNode;
};

type PolicyForm = {
  policy_code: string;
  name: string;
  status: string;
  scope_type: string;
  scope_ref: string;
  is_default: boolean;
  document_types: string;
  required_outputs: string;
  auto_confidence: string;
  manual_confidence: string;
  hard_fail_confidence: string;
  required_fields: string;
  optional_fields: string;
  field_rules_json: string;
  default_role: string;
  default_strategy: string;
  classification_role: string;
  classification_strategy: string;
  metadata_role: string;
  metadata_strategy: string;
  routing_rules_json: string;
  default_target_hours: string;
  default_warning_hours: string;
  default_escalate_hours: string;
  classification_target_hours: string;
  classification_warning_hours: string;
  classification_escalate_hours: string;
  metadata_target_hours: string;
  metadata_warning_hours: string;
  metadata_escalate_hours: string;
  advanced_json: string;
};

const DOMAIN_LABELS: Record<PolicyDomain, string> = {
  classification: "Classification",
  metadata_schema: "Metadata",
  reviewer_assignment: "Reviewer Matrix",
  sla_rules: "SLA Rules",
};

const DOMAIN_CODES: Record<PolicyDomain, string> = {
  classification: "default_document_classification",
  metadata_schema: "default_document_metadata_schema",
  reviewer_assignment: "default_document_reviewer_assignment",
  sla_rules: "default_document_sla_rules",
};

const CONFIG_WORKBENCH_HEADER = "linear-gradient(90deg, #214C9D 0%, #2F69D9 100%)";
const CONFIG_FORM_MULTILINE_LABEL_SX = {
  ...ADMIN_FORM_LABEL_SX,
  mb: 0.5,
} as const;

const RECORDS_SELECT_OPTIONS = {
  status: ["DRAFT", "ACTIVE", "INACTIVE", "RETIRED"],
  security_classification_default: ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"],
  declaration_mode: ["CANDIDATE_FIRST", "DIRECT_DECLARE"],
  lifecycle_clock_basis: ["DECLARATION_DATE", "WORKFLOW_COMPLETE_DATE", "LAST_ACTIVITY_DATE"],
  retention_period_unit: ["DAYS", "MONTHS", "YEARS"],
  review_offset_unit: ["", "DAYS", "MONTHS", "YEARS"],
  classification_mode: ["RULE_DRIVEN", "MANUAL_APPROVAL", "MIXED"],
  hold_category: ["LEGAL", "VALIDATION", "RECORDS", "OPERATIONAL", "OTHER"],
  default_expiry_mode: ["MANUAL_RELEASE", "DATE_DRIVEN", "EVENT_DRIVEN"],
  allowed_outcome: ["ARCHIVE", "DESTROY", "REVIEW_EXTEND", "MIXED"],
  assignment_context: [
    "DECLARATION",
    "VITAL_REVIEW",
    "HOLD_PLACEMENT",
    "RETENTION_REVIEW",
    "DISPOSITION_APPROVAL",
    "DISPOSITION_EXECUTION",
    "ARCHIVE_TRANSFER",
  ],
  active_start_event: ["DECLARED_RECORD", "APPROVED", "ISSUED", "REGISTERED"],
  inactive_eligibility_event: [
    "LAST_ACTIVITY_ELAPSED",
    "WORKFLOW_COMPLETE",
    "SUPERSEDED",
    "MANUAL_REEVALUATION",
  ],
  retention_start_event: ["DECLARED_RECORD", "DECLARED_INACTIVE", "WORKFLOW_COMPLETE", "ISSUED"],
  candidate_trigger_event: [
    "INGESTION",
    "DOCUMENT_REGISTRATION",
    "METADATA_UPDATE",
    "WORKFLOW_COMPLETE",
    "MANUAL_REEVALUATION",
  ],
  declaration_trigger_event: [
    "MANUAL_REEVALUATION",
    "MANUAL_APPROVAL",
    "WORKFLOW_COMPLETE",
    "INGESTION",
  ],
} as const;

function splitLines(value: string) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseJson(value: string, fallback: any) {
  try {
    return JSON.parse(value || "");
  } catch {
    return fallback;
  }
}

function toRecordsJsonText(value: any, fallback: any = {}) {
  if (value === null || value === undefined || value === "") {
    return JSON.stringify(fallback, null, 2);
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function formatRecordsFormValue(
  value: any,
  field: RecordsFormFieldDefinition
): RecordsFormValue {
  if (field.type === "toggle") {
    return Boolean(value);
  }
  if (field.type === "json") {
    return toRecordsJsonText(value, field.jsonFallback ?? {});
  }
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function parseRecordsFormValue(
  value: RecordsFormValue,
  field: RecordsFormFieldDefinition
) {
  if (field.type === "toggle") {
    return Boolean(value);
  }
  if (field.type === "number") {
    const numericText = String(value).trim();
    return numericText === "" ? null : Number(numericText);
  }
  if (field.type === "json") {
    return parseJson(String(value || ""), field.jsonFallback ?? {});
  }
  const text = String(value ?? "").trim();
  if (text === "" && field.nullable) {
    return null;
  }
  return text;
}

function formatConfigurationErrorDetail(detail: any, fallback: string) {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item === "object") {
          const loc = Array.isArray(item.loc) ? item.loc.join(" > ") : "";
          const msg = typeof item.msg === "string" ? item.msg : JSON.stringify(item);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(item);
      })
      .join(" | ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return fallback;
}

function buildRecordsFormPayload(
  fields: RecordsFormFieldDefinition[],
  values: Record<string, RecordsFormValue>
) {
  return fields.reduce<Record<string, any>>((acc, field) => {
    const parsed = parseRecordsFormValue(values[field.key], field);

    if (parsed === "") {
      return acc;
    }

    if (parsed === null && !field.nullable) {
      return acc;
    }

    acc[field.key] = parsed;
    return acc;
  }, {});
}

function listText(items: any) {
  return Array.isArray(items) ? items.join("\n") : "";
}

function makeBlankForm(domain: PolicyDomain): PolicyForm {
  const name = `Default Document ${DOMAIN_LABELS[domain]}`;
  return {
    policy_code: DOMAIN_CODES[domain],
    name,
    status: "ACTIVE",
    scope_type: "tenant",
    scope_ref: "",
    is_default: true,
    document_types: "drawing\ncalculation\nprocedure\nspecification\ncontract\nletter\ninvoice",
    required_outputs: "document_type_code\ntitle\ndiscipline_code\nproject_code\noriginator_code\nconfidence_score",
    auto_confidence: "0.85",
    manual_confidence: "0.6",
    hard_fail_confidence: "0.6",
    required_fields: "document_number\ndocument_type_code\ndiscipline_code\nproject_code\noriginator_code\nrevision_code\ndocument_status\ndocument_date",
    optional_fields: "vendor_code\npackage\nwork_breakdown_structure\npriority\nconfidentiality",
    field_rules_json: JSON.stringify(
      {
        document_number: { type: "text", required: true },
        revision_code: { type: "text", required: true },
        document_date: { type: "date", required: false },
      },
      null,
      2
    ),
    default_role: "tenant_admin",
    default_strategy: "least_loaded_in_role",
    classification_role: "tenant_admin",
    classification_strategy: "least_loaded_in_role",
    metadata_role: "tenant_admin",
    metadata_strategy: "least_loaded_in_role",
    routing_rules_json: "[]",
    default_target_hours: "48",
    default_warning_hours: "12",
    default_escalate_hours: "24",
    classification_target_hours: "24",
    classification_warning_hours: "6",
    classification_escalate_hours: "12",
    metadata_target_hours: "48",
    metadata_warning_hours: "12",
    metadata_escalate_hours: "24",
    advanced_json: "",
  };
}

function formFromPolicy(domain: PolicyDomain, policy: PolicyVersion): PolicyForm {
  const form = makeBlankForm(domain);
  const config = policy.config || {};
  form.policy_code = policy.policy_code;
  form.name = policy.name;
  form.status = policy.status || "ACTIVE";
  form.scope_type = policy.scope_type || "tenant";
  form.scope_ref = policy.scope_ref || "";
  form.is_default = Boolean(policy.is_default);
  form.advanced_json = JSON.stringify(config, null, 2);

  if (domain === "classification") {
    form.document_types = listText(config.document_types);
    form.required_outputs = listText(config.required_outputs);
    form.auto_confidence = String(config.confidence_thresholds?.auto_recommend_min_confidence ?? "0.85");
    form.manual_confidence = String(config.confidence_thresholds?.manual_review_min_confidence ?? "0.6");
    form.hard_fail_confidence = String(config.confidence_thresholds?.hard_fail_below_confidence ?? "0.6");
  }
  if (domain === "metadata_schema") {
    form.required_fields = listText(config.required_fields);
    form.optional_fields = listText(config.optional_fields);
    form.field_rules_json = JSON.stringify(config.field_rules || {}, null, 2);
  }
  if (domain === "reviewer_assignment") {
    form.default_role = config.default_assignment?.role_code || "tenant_admin";
    form.default_strategy = config.default_assignment?.strategy || "least_loaded_in_role";
    form.classification_role = config.task_assignments?.classification_review?.role_code || "tenant_admin";
    form.classification_strategy =
      config.task_assignments?.classification_review?.strategy || "least_loaded_in_role";
    form.metadata_role = config.task_assignments?.metadata_review?.role_code || "tenant_admin";
    form.metadata_strategy = config.task_assignments?.metadata_review?.strategy || "least_loaded_in_role";
    form.routing_rules_json = JSON.stringify(config.routing_rules || [], null, 2);
  }
  if (domain === "sla_rules") {
    form.default_target_hours = String(config.default_rule?.target_hours ?? "48");
    form.default_warning_hours = String(config.default_rule?.warning_before_hours ?? "12");
    form.default_escalate_hours = String(config.default_rule?.escalate_after_hours ?? "24");
    form.classification_target_hours = String(config.task_rules?.classification_review?.target_hours ?? "24");
    form.classification_warning_hours = String(config.task_rules?.classification_review?.warning_before_hours ?? "6");
    form.classification_escalate_hours = String(config.task_rules?.classification_review?.escalate_after_hours ?? "12");
    form.metadata_target_hours = String(config.task_rules?.metadata_review?.target_hours ?? "48");
    form.metadata_warning_hours = String(config.task_rules?.metadata_review?.warning_before_hours ?? "12");
    form.metadata_escalate_hours = String(config.task_rules?.metadata_review?.escalate_after_hours ?? "24");
  }

  return form;
}

function buildConfig(domain: PolicyDomain, form: PolicyForm) {
  const advanced = parseJson(form.advanced_json, null);
  if (advanced && Object.keys(advanced).length > 0) {
    return advanced;
  }
  if (domain === "classification") {
    return {
      document_types: splitLines(form.document_types),
      required_outputs: splitLines(form.required_outputs),
      confidence_thresholds: {
        auto_recommend_min_confidence: Number(form.auto_confidence || 0),
        manual_review_min_confidence: Number(form.manual_confidence || 0),
        hard_fail_below_confidence: Number(form.hard_fail_confidence || 0),
      },
    };
  }
  if (domain === "metadata_schema") {
    return {
      required_fields: splitLines(form.required_fields),
      optional_fields: splitLines(form.optional_fields),
      field_rules: parseJson(form.field_rules_json, {}),
    };
  }
  if (domain === "reviewer_assignment") {
    return {
      default_assignment: {
        role_code: form.default_role,
        strategy: form.default_strategy,
      },
      task_assignments: {
        classification_review: {
          role_code: form.classification_role,
          strategy: form.classification_strategy,
        },
        metadata_review: {
          role_code: form.metadata_role,
          strategy: form.metadata_strategy,
        },
      },
      routing_rules: parseJson(form.routing_rules_json, []),
    };
  }
  return {
    default_rule: {
      target_hours: Number(form.default_target_hours || 0),
      warning_before_hours: Number(form.default_warning_hours || 0),
      escalate_after_hours: Number(form.default_escalate_hours || 0),
    },
    task_rules: {
      classification_review: {
        target_hours: Number(form.classification_target_hours || 0),
        warning_before_hours: Number(form.classification_warning_hours || 0),
        escalate_after_hours: Number(form.classification_escalate_hours || 0),
      },
      metadata_review: {
        target_hours: Number(form.metadata_target_hours || 0),
        warning_before_hours: Number(form.metadata_warning_hours || 0),
        escalate_after_hours: Number(form.metadata_escalate_hours || 0),
      },
    },
  };
}

function scopeLabel(policy: PolicyVersion) {
  const type = policy.scope_type || "tenant";
  if (type === "tenant") return "Tenant default";
  return `${type.replace("_", " ")}: ${policy.scope_ref || "-"}`;
}

function readMatchValue(match: Record<string, any>, key: string) {
  if (match?.[key]) return match[key];
  const allRules = Array.isArray(match?.all) ? match.all : [];
  const anyRules = Array.isArray(match?.any) ? match.any : [];
  const direct = [...allRules, ...anyRules].find((rule) => rule?.[key]);
  return direct?.[key] || "";
}

function renderWorkbenchCard({
  title,
  subtitle,
  tabs,
  body,
  accentLabel,
  paperSx,
  bodySx,
}: {
  title: string;
  subtitle?: string;
  tabs?: React.ReactNode;
  body: React.ReactNode;
  accentLabel?: string;
  paperSx?: Record<string, any>;
  bodySx?: Record<string, any>;
}) {
  return (
    <Paper
      variant="outlined"
      sx={{
        borderRadius: 2.5,
        overflow: "hidden",
        borderColor: "#D8E3F4",
        boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
        ...paperSx,
      }}
    >
      <Box
        sx={{
          px: 2.25,
          py: 1.5,
          color: "#FFFFFF",
          background: CONFIG_WORKBENCH_HEADER,
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={1}
          sx={{ justifyContent: "space-between", alignItems: { xs: "flex-start", md: "center" } }}
        >
          <Box>
            <Typography variant="h6" fontWeight={800} sx={{ color: "inherit" }}>
              {title}
            </Typography>
            {subtitle ? (
              <Typography
                variant="body2"
                sx={{ color: "rgba(255,255,255,0.82)", mt: 0.35 }}
              >
                {subtitle}
              </Typography>
            ) : null}
          </Box>
          {accentLabel ? (
            <Chip
              label={accentLabel}
              size="small"
              sx={{
                bgcolor: "rgba(255,255,255,0.16)",
                color: "#FFFFFF",
                border: "1px solid rgba(255,255,255,0.22)",
                "& .MuiChip-label": {
                  fontWeight: 700,
                },
              }}
            />
          ) : null}
        </Stack>
      </Box>

      {tabs ? (
        <Box
          sx={{
            px: 2,
            borderBottom: "1px solid #D8E3F4",
            bgcolor: "#FFFFFF",
            "& .MuiTabs-root": {
              minHeight: 46,
            },
            "& .MuiTab-root": {
              minHeight: 46,
              textTransform: "none",
              fontWeight: 700,
              fontSize: 13.5,
              color: "#5A6B85",
              alignItems: "center",
            },
            "& .Mui-selected": {
              color: "#214C9D !important",
            },
            "& .MuiTabs-indicator": {
              height: 3,
              borderRadius: 999,
              bgcolor: "#2F69D9",
            },
          }}
        >
          {tabs}
        </Box>
      ) : null}

      <Box sx={{ p: 2.25, bgcolor: "#F6FAFF", ...bodySx }}>{body}</Box>
    </Paper>
  );
}

function renderConfigurationMatrix(
  title: string,
  description: string,
  rows: Array<{ setting: string; value: string; note?: string }>,
  options?: {
    flattenCard?: boolean;
    flattenTable?: boolean;
    hideHeader?: boolean;
    cardRadius?: string | number;
    tableRadius?: string | number;
  }
) {
  const content = (
    <Stack spacing={2}>
        {!options?.hideHeader ? (
          <>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <Typography variant="h6" fontWeight={800}>
                {title}
              </Typography>
              <Chip label="Configured Surface" size="small" color="success" variant="outlined" />
            </Stack>
            <Typography color="text.secondary">{description}</Typography>
          </>
        ) : null}
        <SortablePagedTable
          rows={rows}
          flatten={options?.flattenTable}
          paperRadius={options?.tableRadius}
          rowKey={(row) => `${title}-${row.setting}`}
          columns={[
            {
              key: "setting",
              label: "Setting",
              sortable: true,
              sortValue: (row) => row.setting,
              render: (row) => <Typography fontWeight={700}>{row.setting}</Typography>,
            },
            {
              key: "value",
              label: "Current Value",
              sortable: true,
              sortValue: (row) => row.value,
              render: (row) => row.value,
            },
            {
              key: "note",
              label: "Notes",
              sortable: true,
              sortValue: (row) => row.note || "",
              render: (row) => (
                <Typography variant="body2" color="text.secondary">
                  {row.note || "-"}
                </Typography>
              ),
            },
          ]} 
        />
      </Stack>
  );

  if (options?.flattenCard) {
    return content;
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: options?.cardRadius ?? 2 }}>
      {content}
    </Paper>
  );
}

function SortablePagedTable<RowType>({
  columns,
  emptyMessage = "No rows available.",
  flatten = false,
  paperRadius = 0,
  rowKey,
  rows,
}: {
  columns: SortableTableColumn<RowType>[];
  emptyMessage?: React.ReactNode;
  flatten?: boolean;
  paperRadius?: string | number;
  rowKey: (row: RowType, index: number) => string;
  rows: RowType[];
}) {
  const initialSortKey = columns.find((column) => column.sortable)?.key || columns[0]?.key || "row";
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState(initialSortKey);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  const sortedRows = useMemo(() => {
    const activeColumn = columns.find((column) => column.key === sortKey);
    if (!activeColumn?.sortable) {
      return rows;
    }
    const resolveValue = activeColumn.sortValue || ((row: RowType) => String(activeColumn.render(row)));
    return [...rows].sort((left, right) => {
      const leftValue = resolveValue(left);
      const rightValue = resolveValue(right);
      const normalizedLeft = typeof leftValue === "number" ? leftValue : String(leftValue).toLowerCase();
      const normalizedRight = typeof rightValue === "number" ? rightValue : String(rightValue).toLowerCase();
      if (normalizedLeft < normalizedRight) {
        return sortDirection === "asc" ? -1 : 1;
      }
      if (normalizedLeft > normalizedRight) {
        return sortDirection === "asc" ? 1 : -1;
      }
      return 0;
    });
  }, [columns, rows, sortDirection, sortKey]);

  const pagedRows = useMemo(() => {
    const start = page * 5;
    return sortedRows.slice(start, start + 5);
  }, [page, sortedRows]);

  useEffect(() => {
    const maxPage = Math.max(0, Math.ceil(rows.length / 5) - 1);
    if (page > maxPage) {
      setPage(maxPage);
    }
  }, [page, rows.length]);

  const handleSort = (columnKey: string) => {
    if (sortKey === columnKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(columnKey);
      setSortDirection("asc");
    }
    setPage(0);
  };

  const tableContent = (
    <>
      <Table size="small">
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableCell key={column.key} align={column.align}>
                {column.sortable ? (
                  <TableSortLabel
                    active={sortKey === column.key}
                    direction={sortKey === column.key ? sortDirection : "asc"}
                    onClick={() => handleSort(column.key)}
                  >
                    {column.label}
                  </TableSortLabel>
                ) : (
                  column.label
                )}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {pagedRows.length ? (
            pagedRows.map((row, index) => (
              <TableRow key={rowKey(row, index)} hover>
                {columns.map((column) => (
                  <TableCell key={column.key} align={column.align}>
                    {column.render(row)}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length}>{emptyMessage}</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <TablePagination
        component="div"
        count={rows.length}
        page={page}
        onPageChange={(_, nextPage) => setPage(nextPage)}
        rowsPerPage={5}
        rowsPerPageOptions={[5]}
      />
    </>
  );

  if (flatten) {
    return tableContent;
  }

  return (
    <Paper
      variant="outlined"
      sx={{
        overflow: "hidden",
        borderRadius: paperRadius,
        "&.MuiPaper-rounded": {
          borderRadius:
            typeof paperRadius === "number" ? `${paperRadius}px !important` : `${paperRadius} !important`,
        },
      }}
    >
      {tableContent}
    </Paper>
  );
}

function renderConfigurationField(field: ConfigurationField) {
  if (field.type === "toggle") {
    return (
      <TextField key={field.label} label={field.label} value={field.value ? "Enabled" : "Disabled"} disabled fullWidth />
    );
  }

  if (field.type === "select") {
    return (
      <TextField key={field.label} select label={field.label} value={field.value} disabled fullWidth>
        {(field.options || []).map((option) => (
          <MenuItem key={`${field.label}-${option}`} value={option}>
            {option}
          </MenuItem>
        ))}
      </TextField>
    );
  }

  return (
    <TextField
      key={field.label}
      label={field.label}
      value={field.value}
      disabled
      fullWidth
      multiline={field.type === "json"}
      minRows={field.type === "json" ? 4 : undefined}
    />
  );
}

function buildRecordsSectionFields(
  section: ConfigurationSection,
  options: {
    repositories: Array<{ value: string; label: string }>;
    businessAreas: string[];
    recordCategoryCodes: string[];
    retentionScheduleCodes: string[];
    vitalPolicyCodes: string[];
    holdPolicyCodes: string[];
    dispositionPolicyCodes: string[];
    archivePolicyCodes: string[];
  }
): RecordsFormFieldDefinition[] {
  const commonFields: RecordsFormFieldDefinition[] = [
    {
      key: "repository_id",
      label: "Repository",
      type: "select",
      options: ["", ...options.repositories.map((item) => item.value)],
      helperText: "Optional narrower scope. Leave blank for tenant-level default.",
      nullable: true,
    },
    {
      key: "business_area",
      label: "Business Area",
      type: "select",
      options: ["", ...options.businessAreas],
      helperText: "Optional business-area override scope.",
      nullable: true,
    },
    {
      key: "document_type",
      label: "Document Type",
      type: "text",
      helperText: "Optional document-type scope key used by backend precedence.",
      nullable: true,
    },
    {
      key: "project_code",
      label: "Project Code",
      type: "text",
      helperText: "Optional project-level scope for tighter records-governance routing.",
      nullable: true,
    },
  ];

  const governanceFields: RecordsFormFieldDefinition[] = [
    {
      key: "status",
      label: "Status",
      type: "select",
      options: [...RECORDS_SELECT_OPTIONS.status],
      required: true,
    },
    {
      key: "effective_from",
      label: "Effective From",
      type: "text",
      helperText: "ISO datetime from which this configuration version becomes active.",
      nullable: true,
    },
    {
      key: "effective_to",
      label: "Effective To",
      type: "text",
      helperText: "Optional end date for this version.",
      nullable: true,
    },
    {
      key: "version_no",
      label: "Version No",
      type: "number",
      helperText: "Configuration version number.",
      required: true,
    },
    {
      key: "is_current_version",
      label: "Is Current Version",
      type: "toggle",
      helperText: "Marks the currently effective version in the same scope.",
    },
    {
      key: "rule_priority",
      label: "Rule Priority",
      type: "number",
      helperText: "Lower numbers can be used for tighter precedence.",
      required: true,
    },
    {
      key: "config_payload_json",
      label: "Config Payload",
      type: "json",
      minRows: 4,
      helperText: "Reserved extension payload for controlled future enrichment.",
      jsonFallback: {},
    },
  ];

  switch (section.domain) {
    case "record-categories":
      return [
        ...commonFields,
        { key: "category_code", label: "Category Code", type: "text", required: true },
        { key: "category_name", label: "Category Name", type: "text", required: true },
        {
          key: "category_description",
          label: "Category Description",
          type: "textarea",
          minRows: 3,
          nullable: true,
        },
        {
          key: "parent_category_code",
          label: "Parent Category Code",
          type: "select",
          options: ["", ...options.recordCategoryCodes],
          helperText: "Optional parent category to support taxonomy hierarchy.",
          nullable: true,
        },
        {
          key: "security_classification_default",
          label: "Security Classification Default",
          type: "select",
          options: ["", ...RECORDS_SELECT_OPTIONS.security_classification_default],
          nullable: true,
        },
        {
          key: "retention_schedule_code_default",
          label: "Retention Schedule Default",
          type: "select",
          options: ["", ...options.retentionScheduleCodes],
          helperText: "Default retention schedule attached when records use this category.",
          nullable: true,
        },
        {
          key: "vital_policy_code_default",
          label: "Vital Policy Default",
          type: "select",
          options: ["", ...options.vitalPolicyCodes],
          nullable: true,
        },
        {
          key: "hold_policy_code_default",
          label: "Hold Policy Default",
          type: "select",
          options: ["", ...options.holdPolicyCodes],
          nullable: true,
        },
        {
          key: "disposition_policy_code_default",
          label: "Disposition Policy Default",
          type: "select",
          options: ["", ...options.dispositionPolicyCodes],
          nullable: true,
        },
        {
          key: "archive_policy_code_default",
          label: "Archive Policy Default",
          type: "select",
          options: ["", ...options.archivePolicyCodes],
          nullable: true,
        },
        ...governanceFields,
      ];
    case "declaration-rules":
      return [
        ...commonFields,
        { key: "rule_code", label: "Rule Code", type: "text", required: true },
        { key: "rule_name", label: "Rule Name", type: "text", required: true },
        {
          key: "rule_description",
          label: "Rule Description",
          type: "textarea",
          minRows: 3,
          nullable: true,
        },
        {
          key: "record_category_code",
          label: "Record Category Code",
          type: "select",
          options: ["", ...options.recordCategoryCodes],
          helperText: "Links declaration to the target record category.",
          nullable: true,
        },
        {
          key: "declaration_mode",
          label: "Declaration Mode",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.declaration_mode],
          required: true,
        },
        {
          key: "approval_required",
          label: "Approval Required",
          type: "toggle",
        },
        {
          key: "approval_role_code",
          label: "Approval Role Code",
          type: "text",
          helperText: "Optional performer/approver role when approval is required.",
          nullable: true,
        },
        {
          key: "candidate_trigger_event",
          label: "Candidate Trigger Event",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.candidate_trigger_event],
          required: true,
        },
        {
          key: "declaration_trigger_event",
          label: "Declaration Trigger Event",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.declaration_trigger_event],
          required: true,
        },
        {
          key: "metadata_requirements_json",
          label: "Metadata Requirements",
          type: "json",
          minRows: 4,
          helperText: "Structured metadata checks that must pass before declaration.",
          jsonFallback: {},
        },
        {
          key: "matching_criteria_json",
          label: "Matching Criteria",
          type: "json",
          minRows: 4,
          helperText: "Structured backend matching criteria for candidate selection.",
          jsonFallback: {},
        },
        ...governanceFields,
      ];
    case "lifecycle-rules":
      return [
        ...commonFields,
        { key: "rule_code", label: "Rule Code", type: "text", required: true },
        { key: "rule_name", label: "Rule Name", type: "text", required: true },
        {
          key: "rule_description",
          label: "Rule Description",
          type: "textarea",
          minRows: 3,
          nullable: true,
        },
        {
          key: "record_category_code",
          label: "Record Category Code",
          type: "select",
          options: ["", ...options.recordCategoryCodes],
          helperText: "Optional category-specific lifecycle override.",
          nullable: true,
        },
        {
          key: "active_start_event",
          label: "Active Start Event",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.active_start_event],
          required: true,
        },
        {
          key: "inactive_eligibility_event",
          label: "Inactive Eligibility Event",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.inactive_eligibility_event],
          required: true,
        },
        {
          key: "inactive_after_days",
          label: "Inactive After Days",
          type: "number",
          helperText: "Elapsed inactivity threshold in days.",
          nullable: true,
        },
        {
          key: "inactive_override_required",
          label: "Inactive Override Required",
          type: "toggle",
        },
        {
          key: "reopen_to_active_allowed",
          label: "Reopen To Active Allowed",
          type: "toggle",
        },
        {
          key: "reopen_trigger_events_json",
          label: "Reopen Trigger Events",
          type: "json",
          minRows: 4,
          helperText: "Structured list of lifecycle events allowed to reopen the record.",
          jsonFallback: [],
        },
        {
          key: "lifecycle_clock_basis",
          label: "Lifecycle Clock Basis",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.lifecycle_clock_basis],
          required: true,
        },
        ...governanceFields,
      ];
    case "retention-schedules":
      return [
        ...commonFields,
        { key: "schedule_code", label: "Schedule Code", type: "text", required: true },
        { key: "schedule_name", label: "Schedule Name", type: "text", required: true },
        {
          key: "schedule_description",
          label: "Schedule Description",
          type: "textarea",
          minRows: 3,
          nullable: true,
        },
        {
          key: "record_category_code",
          label: "Record Category Code",
          type: "select",
          options: ["", ...options.recordCategoryCodes],
          nullable: true,
        },
        {
          key: "retention_start_event",
          label: "Retention Start Event",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.retention_start_event],
          required: true,
        },
        {
          key: "retention_period_value",
          label: "Retention Period Value",
          type: "number",
          required: true,
        },
        {
          key: "retention_period_unit",
          label: "Retention Period Unit",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.retention_period_unit],
          required: true,
        },
        {
          key: "review_required",
          label: "Review Required",
          type: "toggle",
        },
        {
          key: "review_offset_value",
          label: "Review Offset Value",
          type: "number",
          nullable: true,
        },
        {
          key: "review_offset_unit",
          label: "Review Offset Unit",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.review_offset_unit],
          nullable: true,
        },
        {
          key: "suspend_on_hold",
          label: "Suspend On Hold",
          type: "toggle",
        },
        {
          key: "final_disposition_policy_code",
          label: "Final Disposition Policy Code",
          type: "select",
          options: ["", ...options.dispositionPolicyCodes],
          helperText: "Cross-links retention to the disposition policy used at completion.",
          nullable: true,
        },
        ...governanceFields,
      ];
    case "vital-policies":
      return [
        ...commonFields,
        { key: "policy_code", label: "Policy Code", type: "text", required: true },
        { key: "policy_name", label: "Policy Name", type: "text", required: true },
        {
          key: "policy_description",
          label: "Policy Description",
          type: "textarea",
          minRows: 3,
          nullable: true,
        },
        {
          key: "record_category_code",
          label: "Record Category Code",
          type: "select",
          options: ["", ...options.recordCategoryCodes],
          nullable: true,
        },
        {
          key: "classification_mode",
          label: "Classification Mode",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.classification_mode],
          required: true,
        },
        {
          key: "default_vital_flag",
          label: "Default Vital Flag",
          type: "toggle",
        },
        {
          key: "review_required",
          label: "Review Required",
          type: "toggle",
        },
        {
          key: "review_role_code",
          label: "Review Role Code",
          type: "text",
          nullable: true,
        },
        {
          key: "review_interval_days",
          label: "Review Interval Days",
          type: "number",
          nullable: true,
        },
        {
          key: "criteria_json",
          label: "Criteria",
          type: "json",
          minRows: 4,
          helperText: "Structured vitality classification criteria used by backend evaluation.",
          jsonFallback: {},
        },
        ...governanceFields,
      ];
    case "hold-policies":
      return [
        { key: "policy_code", label: "Policy Code", type: "text", required: true },
        { key: "policy_name", label: "Policy Name", type: "text", required: true },
        {
          key: "policy_description",
          label: "Policy Description",
          type: "textarea",
          minRows: 3,
          nullable: true,
        },
        {
          key: "hold_category",
          label: "Hold Category",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.hold_category],
          required: true,
        },
        {
          key: "placement_role_code",
          label: "Placement Role Code",
          type: "text",
          required: true,
        },
        {
          key: "release_role_code",
          label: "Release Role Code",
          type: "text",
          required: true,
        },
        {
          key: "matter_reference_required",
          label: "Matter Reference Required",
          type: "toggle",
        },
        {
          key: "reason_required",
          label: "Reason Required",
          type: "toggle",
        },
        {
          key: "blocks_disposition",
          label: "Blocks Disposition",
          type: "toggle",
        },
        {
          key: "blocks_archive_transfer",
          label: "Blocks Archive Transfer",
          type: "toggle",
        },
        {
          key: "default_expiry_mode",
          label: "Default Expiry Mode",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.default_expiry_mode],
          required: true,
        },
        {
          key: "criteria_json",
          label: "Criteria",
          type: "json",
          minRows: 4,
          helperText: "Structured hold placement/release criteria used by backend services.",
          jsonFallback: {},
        },
        {
          key: "config_payload_json",
          label: "Config Payload",
          type: "json",
          minRows: 4,
          helperText: "Reserved extension payload for controlled future enrichment.",
          jsonFallback: {},
        },
        {
          key: "status",
          label: "Status",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.status],
          required: true,
        },
        {
          key: "rule_priority",
          label: "Rule Priority",
          type: "number",
          required: true,
        },
      ];
    case "disposition-policies":
      return [
        ...commonFields,
        { key: "policy_code", label: "Policy Code", type: "text", required: true },
        { key: "policy_name", label: "Policy Name", type: "text", required: true },
        {
          key: "policy_description",
          label: "Policy Description",
          type: "textarea",
          minRows: 3,
          nullable: true,
        },
        {
          key: "record_category_code",
          label: "Record Category Code",
          type: "select",
          options: ["", ...options.recordCategoryCodes],
          nullable: true,
        },
        {
          key: "allowed_outcome",
          label: "Allowed Outcome",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.allowed_outcome],
          required: true,
        },
        { key: "approval_required", label: "Approval Required", type: "toggle" },
        { key: "records_approval_required", label: "Records Approval Required", type: "toggle" },
        { key: "legal_approval_required", label: "Legal Approval Required", type: "toggle" },
        {
          key: "business_owner_approval_required",
          label: "Business Owner Approval Required",
          type: "toggle",
        },
        {
          key: "evidence_requirements_json",
          label: "Evidence Requirements",
          type: "json",
          minRows: 4,
          helperText: "Structured evidence rules required before execution.",
          jsonFallback: {},
        },
        { key: "blocked_by_active_hold", label: "Blocked By Active Hold", type: "toggle" },
        {
          key: "disposition_execution_role_code",
          label: "Disposition Execution Role Code",
          type: "text",
          required: true,
        },
        ...governanceFields,
      ];
    case "archive-policies":
      return [
        ...commonFields,
        { key: "policy_code", label: "Policy Code", type: "text", required: true },
        { key: "policy_name", label: "Policy Name", type: "text", required: true },
        {
          key: "policy_description",
          label: "Policy Description",
          type: "textarea",
          minRows: 3,
          nullable: true,
        },
        {
          key: "record_category_code",
          label: "Record Category Code",
          type: "select",
          options: ["", ...options.recordCategoryCodes],
          nullable: true,
        },
        { key: "transfer_required", label: "Transfer Required", type: "toggle" },
        { key: "destination_code", label: "Destination Code", type: "text", required: true },
        { key: "package_format_code", label: "Package Format Code", type: "text", required: true },
        { key: "checksum_required", label: "Checksum Required", type: "toggle" },
        { key: "metadata_profile_code", label: "Metadata Profile Code", type: "text", required: true },
        {
          key: "preservation_review_interval_days",
          label: "Preservation Review Interval Days",
          type: "number",
          nullable: true,
        },
        {
          key: "receipt_confirmation_required",
          label: "Receipt Confirmation Required",
          type: "toggle",
        },
        {
          key: "criteria_json",
          label: "Criteria",
          type: "json",
          minRows: 4,
          helperText: "Structured archive packaging and destination rules.",
          jsonFallback: {},
        },
        ...governanceFields,
      ];
    case "assignment-rules":
      return [
        ...commonFields,
        { key: "rule_code", label: "Rule Code", type: "text", required: true },
        { key: "rule_name", label: "Rule Name", type: "text", required: true },
        {
          key: "rule_description",
          label: "Rule Description",
          type: "textarea",
          minRows: 3,
          nullable: true,
        },
        {
          key: "record_category_code",
          label: "Record Category Code",
          type: "select",
          options: ["", ...options.recordCategoryCodes],
          nullable: true,
        },
        {
          key: "assignment_context",
          label: "Assignment Context",
          type: "select",
          options: [...RECORDS_SELECT_OPTIONS.assignment_context],
          required: true,
        },
        { key: "owner_role_code", label: "Owner Role Code", type: "text", required: true },
        { key: "performer_role_code", label: "Performer Role Code", type: "text", required: true },
        { key: "approver_role_code", label: "Approver Role Code", type: "text", nullable: true },
        { key: "escalation_role_code", label: "Escalation Role Code", type: "text", nullable: true },
        { key: "fallback_role_code", label: "Fallback Role Code", type: "text", nullable: true },
        {
          key: "assignment_logic_json",
          label: "Assignment Logic",
          type: "json",
          minRows: 5,
          helperText: "Structured routing and performer resolution logic.",
          jsonFallback: {},
        },
        ...governanceFields,
      ];
    default:
      return governanceFields;
  }
}

function renderRecordsConfigurationSection(section: ConfigurationSection) {
  return (
    <Accordion key={section.key} defaultExpanded disableGutters sx={{ borderRadius: 2, overflow: "hidden" }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={1}
          sx={{
            width: "100%",
            justifyContent: "space-between",
            alignItems: { xs: "flex-start", md: "center" },
          }}
        >
          <Box>
            <Typography variant="h6" fontWeight={800}>
              {section.title}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {section.description}
            </Typography>
          </Box>
          <Chip label="UI Shell" size="small" color="primary" variant="outlined" />
        </Stack>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={2}>
          {renderConfigurationMatrix(
            "Scope And Ownership",
            "Resolved through configuration precedence and backend rule evaluation.",
            section.scopeRows
          )}
          {renderConfigurationMatrix(
            "Rule Surface",
            "Baseline rule matrix for this domain. Save and load will be wired in later backend phases.",
            section.matrixRows
          )}
          <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
            <Stack spacing={2}>
              <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                <Typography variant="h6" fontWeight={800}>
                  Draft Editor
                </Typography>
                <Chip label="Placeholder" size="small" variant="outlined" />
              </Stack>
              <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
                {section.fields.map((field) => renderConfigurationField(field))}
              </Box>
              <Stack direction="row" spacing={1} sx={{ justifyContent: "flex-end" }}>
                <Button variant="outlined" disabled>
                  Add Row
                </Button>
                <Button variant="contained" disabled>
                  Save
                </Button>
              </Stack>
            </Stack>
          </Paper>
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

function buildRecordsConfigurationSections(
  repositoryCount: number,
  businessAreas: string[]
): ConfigurationSection[] {
  const scopeValue = `${repositoryCount} repositories / ${businessAreas.length || 0} business areas`;

  return [
    {
      key: "record_categories",
      domain: "record-categories",
      title: "Record Categories",
      description: "Define the records taxonomy and default policy attachments without mixing in lifecycle timing.",
      createTemplate: {
        category_code: "PROJECT_RECORD",
        category_name: "Project Record",
        category_description: "",
        status: "DRAFT",
        security_classification_default: "INTERNAL",
        rule_priority: 100,
        config_payload_json: {},
      },
      scopeRows: [
        { setting: "Scope Support", value: scopeValue, note: "Narrower scopes override broader defaults." },
        { setting: "Category Ownership", value: "Taxonomy only", note: "Retention, hold, and archive behavior remain in their own domains." },
      ],
      matrixRows: [
        { setting: "Category Defaults", value: "Retention, vital, hold, disposition, archive policy codes", note: "Defaults only, not transactional state." },
        { setting: "Hierarchy", value: "Parent-child category support", note: "Use for top-level records class and sub-class drilldown." },
      ],
      fields: [
        { label: "Category Code", type: "text", value: "PROJECT_RECORD" },
        { label: "Category Name", type: "text", value: "Project Record" },
        { label: "Status", type: "select", value: "ACTIVE", options: ["DRAFT", "ACTIVE", "INACTIVE", "RETIRED"] },
        { label: "Security Classification Default", type: "select", value: "INTERNAL", options: ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"] },
        { label: "Retention Schedule Default", type: "text", value: "PROJECT_RETENTION_07Y" },
        { label: "Policy Linkage JSON", type: "json", value: '{\n  "vital_policy_code_default": "PROJECT_VITAL_DEFAULT",\n  "hold_policy_code_default": "PROJECT_HOLD_STANDARD"\n}' },
      ],
    },
    {
      key: "declaration_rules",
      domain: "declaration-rules",
      title: "Declaration Rules",
      description: "Control candidate-first versus direct declaration and metadata readiness rules.",
      createTemplate: {
        rule_code: "PROJECT_CLOSEOUT_DECLARATION",
        rule_name: "Project Closeout Declaration",
        rule_description: "",
        record_category_code: "PROJECT_RECORD",
        declaration_mode: "CANDIDATE_FIRST",
        approval_required: true,
        approval_role_code: "records_officer",
        candidate_trigger_event: "WORKFLOW_COMPLETE",
        declaration_trigger_event: "MANUAL_APPROVAL",
        matching_criteria_json: {},
        metadata_requirements_json: {},
        status: "DRAFT",
        rule_priority: 100,
        config_payload_json: {},
      },
      scopeRows: [
        { setting: "Primary Mode", value: "Candidate-first by default", note: "Direct declaration is allowed only through explicit configuration." },
        { setting: "Scope Match Inputs", value: "Repository, business area, document type", note: "Rule matching is backend-driven and precedence-aware." },
      ],
      matrixRows: [
        { setting: "Declaration Modes", value: "CANDIDATE_FIRST, DIRECT_DECLARE", note: "Chosen per rule, not per page." },
        { setting: "Approval Routing", value: "Optional role-based approval", note: "Approval role comes from assignment rules and configuration." },
      ],
      fields: [
        { label: "Rule Code", type: "text", value: "PROJECT_CLOSEOUT_DECLARATION" },
        { label: "Declaration Mode", type: "select", value: "CANDIDATE_FIRST", options: ["CANDIDATE_FIRST", "DIRECT_DECLARE"] },
        { label: "Approval Required", type: "toggle", value: true },
        { label: "Approval Role", type: "text", value: "records_officer" },
        { label: "Candidate Trigger Event", type: "text", value: "WORKFLOW_COMPLETE" },
        { label: "Matching Criteria JSON", type: "json", value: '{\n  "document_type": "handover_package",\n  "business_area": "project_delivery"\n}' },
      ],
    },
    {
      key: "lifecycle_rules",
      domain: "lifecycle-rules",
      title: "Lifecycle Rules",
      description: "Define active and inactive transitions without redefining retention or declaration semantics.",
      createTemplate: {
        rule_code: "STANDARD_ACTIVE_INACTIVE",
        rule_name: "Standard Active Inactive",
        rule_description: "",
        active_start_event: "DECLARED_RECORD",
        inactive_eligibility_event: "LAST_ACTIVITY_ELAPSED",
        inactive_after_days: 180,
        inactive_override_required: false,
        reopen_to_active_allowed: true,
        reopen_trigger_events_json: [],
        lifecycle_clock_basis: "LAST_ACTIVITY_DATE",
        status: "DRAFT",
        rule_priority: 100,
        config_payload_json: {},
      },
      scopeRows: [
        { setting: "State Ownership", value: "Active / inactive activity state only", note: "Separate from declaration, hold, and retention states." },
        { setting: "Clock Basis", value: "Declaration / workflow completion / last activity", note: "Resolved in backend precedence order." },
      ],
      matrixRows: [
        { setting: "Inactive Triggers", value: "Event-driven or elapsed inactivity", note: "Supports business-area overrides later." },
        { setting: "Reopen Control", value: "Optional return to active", note: "Reopen remains explicit and auditable." },
      ],
      fields: [
        { label: "Rule Code", type: "text", value: "STANDARD_ACTIVE_INACTIVE" },
        { label: "Lifecycle Clock Basis", type: "select", value: "LAST_ACTIVITY_DATE", options: ["DECLARATION_DATE", "WORKFLOW_COMPLETE_DATE", "LAST_ACTIVITY_DATE"] },
        { label: "Inactive After Days", type: "text", value: "180" },
        { label: "Reopen To Active Allowed", type: "toggle", value: true },
        { label: "Reopen Trigger Events JSON", type: "json", value: '[\n  "REACTIVATED_FOR_AUDIT",\n  "BUSINESS_REOPEN_REQUEST"\n]' },
      ],
    },
    {
      key: "retention_schedules",
      domain: "retention-schedules",
      title: "Retention Schedules",
      description: "Define retention duration, review offsets, and hold suspension behavior.",
      createTemplate: {
        schedule_code: "PROJECT_RETENTION_07Y",
        schedule_name: "Project Retention 7 Years",
        schedule_description: "",
        retention_start_event: "DECLARED_INACTIVE",
        retention_period_value: 7,
        retention_period_unit: "YEARS",
        review_required: true,
        review_offset_value: 90,
        review_offset_unit: "DAYS",
        suspend_on_hold: true,
        final_disposition_policy_code: "PROJECT_DISPOSITION_STANDARD",
        status: "DRAFT",
        rule_priority: 100,
        config_payload_json: {},
      },
      scopeRows: [
        { setting: "Timing Ownership", value: "Retention only", note: "Disposition outcome remains in disposition policy." },
        { setting: "Hold Interaction", value: "Supports suspension on hold", note: "Hold category and hold status remain separate dimensions." },
      ],
      matrixRows: [
        { setting: "Retention Units", value: "Days / months / years", note: "Period value and unit are both configuration-driven." },
        { setting: "Review Control", value: "Optional review before disposition", note: "Review due offset remains independent from archive transfer." },
      ],
      fields: [
        { label: "Schedule Code", type: "text", value: "PROJECT_RETENTION_07Y" },
        { label: "Retention Start Event", type: "text", value: "DECLARED_INACTIVE" },
        { label: "Retention Period", type: "text", value: "7" },
        { label: "Retention Unit", type: "select", value: "YEARS", options: ["DAYS", "MONTHS", "YEARS"] },
        { label: "Suspend On Hold", type: "toggle", value: true },
        { label: "Review Rules JSON", type: "json", value: '{\n  "review_required": true,\n  "review_offset_value": 90,\n  "review_offset_unit": "DAYS"\n}' },
      ],
    },
    {
      key: "vital_policies",
      domain: "vital-policies",
      title: "Vital Records",
      description: "Capture policy-driven vital classification and review requirements without turning vital into a lifecycle stage.",
      createTemplate: {
        policy_code: "PROJECT_VITAL_DEFAULT",
        policy_name: "Project Vital Default",
        policy_description: "",
        classification_mode: "MIXED",
        default_vital_flag: false,
        review_required: true,
        review_role_code: "records_officer",
        review_interval_days: 365,
        criteria_json: {},
        status: "DRAFT",
        rule_priority: 100,
        config_payload_json: {},
      },
      scopeRows: [
        { setting: "Classification Model", value: "Policy-driven", note: "Vital meaning comes from configuration, not page logic." },
        { setting: "Override Handling", value: "Manual or mixed review", note: "Override rules remain auditable and approval-driven." },
      ],
      matrixRows: [
        { setting: "Classification Modes", value: "RULE_DRIVEN, MANUAL_APPROVAL, MIXED", note: "Use per category or per document type scope." },
        { setting: "Review Frequency", value: "Configurable interval", note: "Vital review cadence is independent from retention review cadence." },
      ],
      fields: [
        { label: "Policy Code", type: "text", value: "PROJECT_VITAL_DEFAULT" },
        { label: "Classification Mode", type: "select", value: "MIXED", options: ["RULE_DRIVEN", "MANUAL_APPROVAL", "MIXED"] },
        { label: "Default Vital Flag", type: "toggle", value: false },
        { label: "Review Role", type: "text", value: "records_officer" },
        { label: "Criteria JSON", type: "json", value: '{\n  "contains": ["contract_award", "statutory_approval"],\n  "loss_impact": "high"\n}' },
      ],
    },
    {
      key: "holds",
      domain: "hold-policies",
      title: "Holds",
      description: "Define allowed hold categories, authorities, and blocking behavior without inferring legal meaning in the frontend.",
      createTemplate: {
        policy_code: "PROJECT_HOLD_STANDARD",
        policy_name: "Project Hold Standard",
        policy_description: "",
        hold_category: "LEGAL",
        placement_role_code: "legal_counsel",
        release_role_code: "legal_counsel",
        matter_reference_required: true,
        reason_required: true,
        blocks_disposition: true,
        blocks_archive_transfer: true,
        default_expiry_mode: "MANUAL_RELEASE",
        criteria_json: {},
        status: "DRAFT",
        rule_priority: 100,
        config_payload_json: {},
      },
      scopeRows: [
        { setting: "Classification Source", value: "hold_category from backend policy", note: "Legal and other hold meaning must remain DB-backed." },
        { setting: "Blocking Behaviour", value: "Disposition and archive can be blocked separately", note: "Policy controls the effect of each hold category." },
      ],
        matrixRows: [
          { setting: "Hold Categories", value: "LEGAL, VALIDATION, RECORDS, OPERATIONAL, OTHER", note: "Matches the canonical state vocabulary." },
          { setting: "Validation Hold Governance", value: "Managed under records governance for now", note: "Treat validation holds as non-legal holds until a separate quality-governance module owns them." },
          { setting: "Authority Model", value: "Placement and release role per policy", note: "Release approval remains separate from hold status." },
        ],
      fields: [
        { label: "Policy Code", type: "text", value: "PROJECT_HOLD_STANDARD" },
        { label: "Hold Category", type: "select", value: "LEGAL", options: ["LEGAL", "VALIDATION", "RECORDS", "OPERATIONAL", "OTHER"] },
        { label: "Matter Reference Required", type: "toggle", value: true },
        { label: "Blocks Disposition", type: "toggle", value: true },
        { label: "Blocks Archive Transfer", type: "toggle", value: true },
        { label: "Criteria JSON", type: "json", value: '{\n  "placement_role_code": "legal_counsel",\n  "release_role_code": "legal_counsel"\n}' },
      ],
    },
    {
      key: "disposition",
      domain: "disposition-policies",
      title: "Disposition",
      description: "Define eligible outcomes, approval checkpoints, and execution ownership for disposition actions.",
      createTemplate: {
        policy_code: "PROJECT_DISPOSITION_STANDARD",
        policy_name: "Project Disposition Standard",
        policy_description: "",
        allowed_outcome: "MIXED",
        approval_required: true,
        records_approval_required: true,
        legal_approval_required: true,
        business_owner_approval_required: false,
        evidence_requirements_json: {},
        blocked_by_active_hold: true,
        disposition_execution_role_code: "records_officer",
        status: "DRAFT",
        rule_priority: 100,
        config_payload_json: {},
      },
      scopeRows: [
        { setting: "Outcome Ownership", value: "Disposition only", note: "Archive packaging is configured separately in archive policy." },
        { setting: "Hold Dependency", value: "Blocked by active hold where configured", note: "Hold state is checked at runtime by backend services." },
      ],
      matrixRows: [
        { setting: "Allowed Outcomes", value: "ARCHIVE, DESTROY, REVIEW_EXTEND, MIXED", note: "Configured per record category or scope." },
        { setting: "Approvals", value: "Records, legal, business owner", note: "Each can be required independently." },
      ],
      fields: [
        { label: "Policy Code", type: "text", value: "PROJECT_DISPOSITION_STANDARD" },
        { label: "Allowed Outcome", type: "select", value: "MIXED", options: ["ARCHIVE", "DESTROY", "REVIEW_EXTEND", "MIXED"] },
        { label: "Records Approval Required", type: "toggle", value: true },
        { label: "Legal Approval Required", type: "toggle", value: true },
        { label: "Business Owner Approval Required", type: "toggle", value: false },
        { label: "Evidence Requirements JSON", type: "json", value: '{\n  "certificate_required": true,\n  "supporting_note_required": true\n}' },
      ],
    },
    {
      key: "archive",
      domain: "archive-policies",
      title: "Archive",
      description: "Define archive-transfer packaging, preservation metadata, and destination controls.",
      createTemplate: {
        policy_code: "PROJECT_ARCHIVE_STANDARD",
        policy_name: "Project Archive Standard",
        policy_description: "",
        transfer_required: true,
        destination_code: "CORP_ARCHIVE",
        package_format_code: "AIP_STANDARD_V1",
        checksum_required: true,
        metadata_profile_code: "ARCHIVE_CORE",
        preservation_review_interval_days: 365,
        receipt_confirmation_required: true,
        criteria_json: {},
        status: "DRAFT",
        rule_priority: 100,
        config_payload_json: {},
      },
      scopeRows: [
        { setting: "Transfer Ownership", value: "Archive transfer and preservation only", note: "Does not replace disposition approval logic." },
        { setting: "Destination Model", value: "Destination code and metadata profile", note: "Preservation context remains configuration-driven." },
      ],
      matrixRows: [
        { setting: "Package Controls", value: "Format, checksum, metadata profile", note: "Use for archive transfer completeness." },
        { setting: "Confirmation Rules", value: "Receipt and preservation review", note: "Archive completion is tracked separately from transfer initiation." },
      ],
      fields: [
        { label: "Policy Code", type: "text", value: "PROJECT_ARCHIVE_STANDARD" },
        { label: "Destination Code", type: "text", value: "CORP_ARCHIVE" },
        { label: "Package Format Code", type: "text", value: "AIP_STANDARD_V1" },
        { label: "Checksum Required", type: "toggle", value: true },
        { label: "Receipt Confirmation Required", type: "toggle", value: true },
        { label: "Archive Rules JSON", type: "json", value: '{\n  "metadata_profile_code": "ARCHIVE_CORE",\n  "preservation_review_interval_days": 365\n}' },
      ],
    },
    {
      key: "owners_performers",
      domain: "assignment-rules",
      title: "Owners And Performers",
      description: "Define performer, approver, escalation, and fallback routing for records-governance actions.",
      createTemplate: {
        rule_code: "RECORD_DECLARATION_ASSIGNMENT",
        rule_name: "Record Declaration Assignment",
        rule_description: "",
        assignment_context: "DECLARATION",
        project_code: null,
        owner_role_code: "records_officer",
        performer_role_code: "document_controller",
        approver_role_code: "records_manager",
        escalation_role_code: "compliance_lead",
        fallback_role_code: "tenant_admin",
        assignment_logic_json: {
          declaration_owner_role_code: "records_officer",
          records_officer_role_code: "records_officer",
          legal_approver_role_code: "legal_counsel",
          business_approver_role_code: "business_owner",
          archive_approver_role_code: "archive_manager",
          disposition_executor_role_code: "records_executor",
        },
        status: "DRAFT",
        rule_priority: 100,
        config_payload_json: {},
      },
      scopeRows: [
        { setting: "Routing Ownership", value: "Assignment logic only", note: "Business meaning remains in the other policy tables." },
        { setting: "Resolution Model", value: "Role-based with fallback", note: "Resolved after repository, business area, project, document type, and category selection." },
      ],
      matrixRows: [
        { setting: "Assignment Contexts", value: "Declaration, vital review, hold placement, retention review, disposition approval, disposition execution, archive transfer", note: "Each context may have its own routing rule." },
        { setting: "Escalation Paths", value: "Approver, performer, fallback, escalation", note: "Supports controlled ownership handoff later." },
      ],
      fields: [
        { label: "Assignment Context", type: "select", value: "DECLARATION", options: ["DECLARATION", "VITAL_REVIEW", "HOLD_PLACEMENT", "RETENTION_REVIEW", "DISPOSITION_APPROVAL", "DISPOSITION_EXECUTION", "ARCHIVE_TRANSFER"] },
        { label: "Project Code", type: "text", value: "AKML" },
        { label: "Owner Role", type: "text", value: "records_officer" },
        { label: "Performer Role", type: "text", value: "document_controller" },
        { label: "Approver Role", type: "text", value: "records_manager" },
        { label: "Escalation Role", type: "text", value: "compliance_lead" },
        { label: "Assignment Logic JSON", type: "json", value: '{\n  "strategy": "business_area_then_repository",\n  "declaration_owner_role_code": "records_officer",\n  "records_officer_role_code": "records_officer",\n  "legal_approver_role_code": "legal_counsel",\n  "business_approver_role_code": "business_owner",\n  "archive_approver_role_code": "archive_manager",\n  "disposition_executor_role_code": "records_executor",\n  "fallback_role_code": "tenant_admin"\n}' },
      ],
    },
  ];
}

function getRecordsConfigurationRowId(row: RecordsConfigurationRow) {
  const idKey = Object.keys(row).find(
    (key) => key.endsWith("_id") && key !== "tenant_id" && key !== "repository_id"
  );
  return idKey ? row[idKey] : null;
}

function getRecordsConfigurationRowCode(row: RecordsConfigurationRow) {
  return row.category_code || row.rule_code || row.schedule_code || row.policy_code || "-";
}

function getRecordsConfigurationRowName(row: RecordsConfigurationRow) {
  return row.category_name || row.rule_name || row.schedule_name || row.policy_name || "-";
}

function getRecordsConfigurationRowScope(row: RecordsConfigurationRow) {
  const parts = [row.repository_id, row.business_area, row.project_code, row.document_type].filter(Boolean);
  return parts.length ? parts.join(" / ") : "Tenant";
}

function toRecordsConfigurationEditablePayload(row: RecordsConfigurationRow) {
  const payload = { ...row };
  delete payload.created_by;
  delete payload.created_at;
  delete payload.modified_by;
  delete payload.modified_at;
  delete payload.tenant_id;
  Object.keys(payload)
    .filter((key) => key.endsWith("_id") && key !== "repository_id")
    .forEach((key) => {
      delete payload[key];
    });
  return payload;
}

export default function DocumentControllerConfigurationPage() {
  const [activeArea, setActiveArea] = useState<ConfigurationArea>("document_control");
  const [activeDomain, setActiveDomain] = useState<PolicyDomain>("classification");
  const [policies, setPolicies] = useState<Record<string, PolicyVersion[]>>({});
  const [repositories, setRepositories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [editingPolicy, setEditingPolicy] = useState<PolicyVersion | null>(null);
  const [form, setForm] = useState<PolicyForm>(makeBlankForm("classification"));
  const [showForm, setShowForm] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [recordsConfiguration, setRecordsConfiguration] = useState<
    Record<string, RecordsConfigurationRow[]>
  >({});
  const [recordsConfigurationError, setRecordsConfigurationError] = useState("");
  const [recordsConfigurationSavingDomain, setRecordsConfigurationSavingDomain] = useState("");
  const [recordsConfigurationEditors, setRecordsConfigurationEditors] = useState<
    Record<string, { rowId: string | null; value: string }>
  >({});
  const [expandedRecordsSectionKey, setExpandedRecordsSectionKey] = useState<string | false>(false);
  const [recordsFormSectionKey, setRecordsFormSectionKey] = useState<string | null>(null);
  const [recordsFormRowId, setRecordsFormRowId] = useState<string | null>(null);
  const [recordsFormValues, setRecordsFormValues] = useState<Record<string, RecordsFormValue>>({});
  const [showRecordsForm, setShowRecordsForm] = useState(false);
  const notificationMessage = recordsConfigurationError || error || message;
  const notificationSeverity = (recordsConfigurationError || error ? "error" : "success") as
    | "error"
    | "success";

  const activePolicies = useMemo(
    () => (policies[activeDomain] || []).filter((item) => item.policy_domain === activeDomain || true),
    [policies, activeDomain]
  );
  const businessAreas = useMemo(
    () => Array.from(new Set(repositories.map((repo) => repo.business_area).filter(Boolean))).sort(),
    [repositories]
  );
  const scopeOptions = useMemo(() => {
    if (form.scope_type === "repository") {
      return repositories.map((repo) => ({
        value: repo.repository_id,
        label: repo.repository_name || repo.repository_id,
      }));
    }
    if (form.scope_type === "business_area") {
      return businessAreas.map((area) => ({ value: area, label: area }));
    }
    return [];
  }, [repositories, businessAreas, form.scope_type]);
  const recordsConfigurationSections = useMemo(
    () => buildRecordsConfigurationSections(repositories.length, businessAreas),
    [repositories.length, businessAreas]
  );
  const repositoryScopeOptions = useMemo(
    () =>
      repositories.map((repo) => ({
        value: repo.repository_id,
        label: repo.repository_name || repo.repository_id,
      })),
    [repositories]
  );
  const recordCategoryCodes = useMemo(
    () =>
      ((recordsConfiguration["record-categories"] || []) as RecordsConfigurationRow[])
        .map((row) => row.category_code)
        .filter(Boolean),
    [recordsConfiguration]
  );
  const retentionScheduleCodes = useMemo(
    () =>
      ((recordsConfiguration["retention-schedules"] || []) as RecordsConfigurationRow[])
        .map((row) => row.schedule_code)
        .filter(Boolean),
    [recordsConfiguration]
  );
  const vitalPolicyCodes = useMemo(
    () =>
      ((recordsConfiguration["vital-policies"] || []) as RecordsConfigurationRow[])
        .map((row) => row.policy_code)
        .filter(Boolean),
    [recordsConfiguration]
  );
  const holdPolicyCodes = useMemo(
    () =>
      ((recordsConfiguration["hold-policies"] || []) as RecordsConfigurationRow[])
        .map((row) => row.policy_code)
        .filter(Boolean),
    [recordsConfiguration]
  );
  const dispositionPolicyCodes = useMemo(
    () =>
      ((recordsConfiguration["disposition-policies"] || []) as RecordsConfigurationRow[])
        .map((row) => row.policy_code)
        .filter(Boolean),
    [recordsConfiguration]
  );
  const archivePolicyCodes = useMemo(
    () =>
      ((recordsConfiguration["archive-policies"] || []) as RecordsConfigurationRow[])
        .map((row) => row.policy_code)
        .filter(Boolean),
    [recordsConfiguration]
  );
  const recordsFormSectionsByKey = useMemo(
    () =>
      Object.fromEntries(
        recordsConfigurationSections.map((section) => [section.key, section] as const)
      ),
    [recordsConfigurationSections]
  );
  const activeRecordsFormSection = useMemo(
    () => (recordsFormSectionKey ? recordsFormSectionsByKey[recordsFormSectionKey] || null : null),
    [recordsFormSectionKey, recordsFormSectionsByKey]
  );
  const activeRecordsFormFields = useMemo(
    () =>
      activeRecordsFormSection
        ? buildRecordsSectionFields(activeRecordsFormSection, {
            repositories: repositoryScopeOptions,
            businessAreas,
            recordCategoryCodes,
            retentionScheduleCodes,
            vitalPolicyCodes,
            holdPolicyCodes,
            dispositionPolicyCodes,
            archivePolicyCodes,
          })
        : [],
    [
      activeRecordsFormSection,
      archivePolicyCodes,
      businessAreas,
      dispositionPolicyCodes,
      holdPolicyCodes,
      recordCategoryCodes,
      repositoryScopeOptions,
      retentionScheduleCodes,
      vitalPolicyCodes,
    ]
  );

  function updateRecordsConfigurationEditor(
    domain: string,
    updater: { rowId: string | null; value: string }
  ) {
    setRecordsConfigurationEditors((current) => ({
      ...current,
      [domain]: updater,
    }));
  }

  function makeRecordsFormValues(
    section: ConfigurationSection,
    source: RecordsConfigurationRow
  ): Record<string, RecordsFormValue> {
    const fieldDefinitions = buildRecordsSectionFields(section, {
      repositories: repositoryScopeOptions,
      businessAreas,
      recordCategoryCodes,
      retentionScheduleCodes,
      vitalPolicyCodes,
      holdPolicyCodes,
      dispositionPolicyCodes,
      archivePolicyCodes,
    });
    return fieldDefinitions.reduce<Record<string, RecordsFormValue>>((acc, field) => {
      const sourceValue =
        source[field.key] !== undefined
          ? source[field.key]
          : RECORDS_FORM_FIELD_DEFAULTS[field.key];
      acc[field.key] = formatRecordsFormValue(sourceValue, field);
      return acc;
    }, {});
  }

  async function loadData() {
    setLoading(true);
    setError("");
    setRecordsConfigurationError("");
    try {
      const [policyResult, repositoryResult, recordsConfigurationResult] = await Promise.all([
        getDocumentControllerPolicies(),
        getRepositories(),
        getDocumentControllerRecordsConfiguration(),
      ]);
      setPolicies(policyResult?.data?.domains || {});
      setRepositories(repositoryResult?.data || []);
      setRecordsConfiguration(recordsConfigurationResult?.data || {});
    } catch (err: any) {
      const detail = formatConfigurationErrorDetail(
        err?.response?.data?.detail || err?.message,
        "Unable to load configuration"
      );
      setError(detail);
      setRecordsConfigurationError(detail);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function updateForm(key: keyof PolicyForm, value: string | boolean) {
    setForm((current) => ({
      ...current,
      [key]: value,
      ...(key !== "advanced_json" ? { advanced_json: "" } : {}),
      ...(key === "scope_type" && value === "tenant" ? { scope_ref: "" } : {}),
    }));
  }

  function updateFieldRule(fieldName: string, key: string, value: string | boolean) {
    const rules = parseJson(form.field_rules_json, {});
    const nextRules = {
      ...rules,
      [fieldName]: {
        ...(rules[fieldName] || {}),
        [key]: value,
      },
    };
    updateForm("field_rules_json", JSON.stringify(nextRules, null, 2));
  }

  function updateRoutingRule(index: number, key: string, value: string) {
    const rules = parseJson(form.routing_rules_json, []);
    const nextRules = Array.isArray(rules) ? [...rules] : [];
    const current = nextRules[index] || {
      task_code: "classification_review",
      match: {},
      assignee: { role_code: "tenant_admin", strategy: "least_loaded_in_role" },
    };
    if (key === "task_code") {
      nextRules[index] = { ...current, task_code: value };
    } else if (key === "role_code" || key === "strategy") {
      nextRules[index] = {
        ...current,
        assignee: {
          ...(current.assignee || {}),
          [key]: value,
        },
      };
    } else {
      nextRules[index] = {
        ...current,
        match: {
          ...(current.match || {}),
          [key]: value,
        },
      };
    }
    updateForm("routing_rules_json", JSON.stringify(nextRules, null, 2));
  }

  function addRoutingRule() {
    const rules = parseJson(form.routing_rules_json, []);
    const nextRules = Array.isArray(rules) ? [...rules] : [];
    nextRules.push({
      task_code: "classification_review",
      match: { document_type_code: "" },
      assignee: { role_code: "tenant_admin", strategy: "least_loaded_in_role" },
    });
    updateForm("routing_rules_json", JSON.stringify(nextRules, null, 2));
  }

  function removeRoutingRule(index: number) {
    const rules = parseJson(form.routing_rules_json, []);
    const nextRules = Array.isArray(rules) ? rules.filter((_, itemIndex) => itemIndex !== index) : [];
    updateForm("routing_rules_json", JSON.stringify(nextRules, null, 2));
  }

  function startCreate(domain: PolicyDomain) {
    setEditingPolicy(null);
    setForm(makeBlankForm(domain));
    setShowForm(true);
  }

  function startEdit(policy: PolicyVersion) {
    setEditingPolicy(policy);
    setForm(formFromPolicy(activeDomain, policy));
    setShowForm(true);
  }

  async function handleBootstrap() {
    setError("");
    setMessage("");
    startTransition(async () => {
      try {
        await bootstrapDocumentControllerPolicies();
        setMessage("Default tenant policies are ready.");
        await loadData();
      } catch (err: any) {
        setError(err?.response?.data?.detail || err?.message || "Unable to create default policies");
      }
    });
  }

  async function handleSave() {
    setError("");
    setMessage("");
    startTransition(async () => {
      try {
        const payload = {
          policy_domain: activeDomain,
          policy_code: form.policy_code,
          name: form.name,
          scope_type: form.scope_type,
          scope_ref: form.scope_type === "tenant" ? null : form.scope_ref,
          config_json: buildConfig(activeDomain, form),
          is_default: form.is_default,
          status: form.status,
        };
        if (editingPolicy) {
          await updateDocumentControllerPolicy(activeDomain, editingPolicy.policy_code, payload);
        } else {
          await createDocumentControllerPolicy(payload);
        }
        setMessage(`${DOMAIN_LABELS[activeDomain]} policy saved.`);
        setShowForm(false);
        setEditingPolicy(null);
        await loadData();
      } catch (err: any) {
        setError(err?.response?.data?.detail || err?.message || "Policy save failed");
      }
    });
  }

  function startNewRecordsConfigurationRow(section: ConfigurationSection) {
    setRecordsFormSectionKey(section.key);
    setRecordsFormRowId(null);
    setRecordsFormValues(makeRecordsFormValues(section, section.createTemplate));
    setShowRecordsForm(true);
    updateRecordsConfigurationEditor(section.domain, {
      rowId: null,
      value: JSON.stringify(section.createTemplate, null, 2),
    });
    setRecordsConfigurationError("");
  }

  function startEditRecordsConfigurationRow(
    section: ConfigurationSection,
    row: RecordsConfigurationRow
  ) {
    const editablePayload = toRecordsConfigurationEditablePayload(row);
    setRecordsFormSectionKey(section.key);
    setRecordsFormRowId(String(getRecordsConfigurationRowId(row) || ""));
    setRecordsFormValues(makeRecordsFormValues(section, editablePayload));
    setShowRecordsForm(true);
    updateRecordsConfigurationEditor(section.domain, {
      rowId: String(getRecordsConfigurationRowId(row) || ""),
      value: JSON.stringify(editablePayload, null, 2),
    });
    setRecordsConfigurationError("");
  }

  function updateRecordsFormValue(key: string, value: RecordsFormValue) {
    setRecordsFormValues((current) => ({
      ...current,
      [key]: value,
    }));
  }

  function closeRecordsForm() {
    setShowRecordsForm(false);
    setRecordsFormSectionKey(null);
    setRecordsFormRowId(null);
    setRecordsFormValues({});
  }

  async function handleSaveRecordsConfigurationForm() {
    if (!activeRecordsFormSection) return;
    setRecordsConfigurationError("");
    setMessage("");
    setRecordsConfigurationSavingDomain(activeRecordsFormSection.domain);
    try {
      const missingRequiredField = activeRecordsFormFields.find((field) => {
        if (!field.required) {
          return false;
        }
        const parsedValue = parseRecordsFormValue(recordsFormValues[field.key], field);
        if (field.type === "toggle") {
          return false;
        }
        if (field.type === "number") {
          return parsedValue === null || Number.isNaN(parsedValue);
        }
        if (field.type === "json") {
          return parsedValue === null || parsedValue === undefined || parsedValue === "";
        }
        if (typeof parsedValue === "string") {
          return parsedValue.trim() === "";
        }
        return parsedValue === null || parsedValue === undefined;
      });

      if (missingRequiredField) {
        setRecordsConfigurationError(`${missingRequiredField.label} is required.`);
        return;
      }

      const payload = buildRecordsFormPayload(activeRecordsFormFields, recordsFormValues);
      if (recordsFormRowId) {
        await updateDocumentControllerRecordsConfigurationRow(
          activeRecordsFormSection.domain,
          recordsFormRowId,
          payload
        );
      } else {
        await createDocumentControllerRecordsConfigurationRow(
          activeRecordsFormSection.domain,
          payload
        );
      }
      const recordsConfigurationResult = await getDocumentControllerRecordsConfiguration();
      setRecordsConfiguration(recordsConfigurationResult?.data || {});
      updateRecordsConfigurationEditor(activeRecordsFormSection.domain, {
        rowId: recordsFormRowId,
        value: JSON.stringify(payload, null, 2),
      });
      setMessage(`${activeRecordsFormSection.title} saved.`);
      closeRecordsForm();
    } catch (err: any) {
      setRecordsConfigurationError(
        formatConfigurationErrorDetail(
          err?.response?.data?.detail || err?.message,
          `${activeRecordsFormSection.title} save failed`
        )
      );
    } finally {
      setRecordsConfigurationSavingDomain("");
    }
  }

  async function handleSaveRecordsConfiguration(section: ConfigurationSection) {
    const editor = recordsConfigurationEditors[section.domain];
    if (!editor) return;
    setRecordsConfigurationError("");
    setMessage("");
    setRecordsConfigurationSavingDomain(section.domain);
    try {
      const payload = JSON.parse(editor.value || "{}");
      if (editor.rowId) {
        await updateDocumentControllerRecordsConfigurationRow(section.domain, editor.rowId, payload);
      } else {
        await createDocumentControllerRecordsConfigurationRow(section.domain, payload);
      }
      const recordsConfigurationResult = await getDocumentControllerRecordsConfiguration();
      setRecordsConfiguration(recordsConfigurationResult?.data || {});
      setMessage(`${section.title} saved.`);
    } catch (err: any) {
      setRecordsConfigurationError(
        formatConfigurationErrorDetail(
          err?.response?.data?.detail || err?.message,
          `${section.title} save failed`
        )
      );
    } finally {
      setRecordsConfigurationSavingDomain("");
    }
  }

  async function handleDeleteRecordsConfiguration(section: ConfigurationSection) {
    const editor = recordsConfigurationEditors[section.domain];
    if (!editor?.rowId) return;
    setRecordsConfigurationError("");
    setMessage("");
    setRecordsConfigurationSavingDomain(section.domain);
    try {
      await deleteDocumentControllerRecordsConfigurationRow(section.domain, editor.rowId);
      const recordsConfigurationResult = await getDocumentControllerRecordsConfiguration();
      setRecordsConfiguration(recordsConfigurationResult?.data || {});
      updateRecordsConfigurationEditor(section.domain, {
        rowId: null,
        value: JSON.stringify(section.createTemplate, null, 2),
      });
      setMessage(`${section.title} row deleted.`);
    } catch (err: any) {
      setRecordsConfigurationError(
        formatConfigurationErrorDetail(
          err?.response?.data?.detail || err?.message,
          `${section.title} delete failed`
        )
      );
    } finally {
      setRecordsConfigurationSavingDomain("");
    }
  }

  function renderAreaMenuStrip(
    items: Array<{ key: string; label: string }>,
    value: string,
    onChange: (value: string) => void,
    options?: {
      actions?: React.ReactNode;
      fullBleed?: boolean;
      bleedSx?: Record<string, any>;
      borderColor?: string;
    }
  ) {
    const borderColor = options?.borderColor || "#21344D";
    return (
      <Paper
        variant="outlined"
        sx={{
          mt: 0,
          ml: 0,
          mr: 0,
          width: "100%",
          borderRadius: 0,
          overflow: "hidden",
          borderColor,
          ...(options?.fullBleed
            ? {
                ml: -4,
                mr: -5,
                width: "calc(100% + 80px)",
                borderLeft: 0,
                borderRight: 0,
                ...options?.bleedSx,
              }
            : {}),
          "&.MuiPaper-rounded": {
            borderRadius: "0 !important",
          },
        }}
      >
        <Box sx={{ px: 2, py: 0, bgcolor: "#FFFFFF" }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={2}
            sx={{
              justifyContent: "space-between",
              alignItems: { xs: "stretch", md: "center" },
              minHeight: 44,
            }}
          >
            <Tabs
              value={value}
              onChange={(_, nextValue) => onChange(nextValue)}
              variant="scrollable"
              sx={{
                minHeight: 44,
                "& .MuiTab-root": {
                  minHeight: 44,
                  textTransform: "none",
                  fontWeight: 700,
                  fontSize: 13.5,
                  px: 2,
                },
                "& .MuiTabs-indicator": {
                  height: 3,
                  borderRadius: 0,
                },
              }}
            >
              {items.map((item) => (
                <Tab key={item.key} value={item.key} label={item.label} />
              ))}
            </Tabs>
            {options?.actions ? (
              <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                {options.actions}
              </Stack>
            ) : null}
          </Stack>
        </Box>
      </Paper>
    );
  }

  function renderLiveRecordsConfigurationSection(section: ConfigurationSection) {
    const rows = recordsConfiguration[section.domain] || [];
    const editor = recordsConfigurationEditors[section.domain];
    return (
      <Accordion
        key={section.key}
        expanded={expandedRecordsSectionKey === section.key}
        onChange={(_, isExpanded) =>
          setExpandedRecordsSectionKey(isExpanded ? section.key : false)
        }
        disableGutters
        sx={{
          borderRadius: "5px",
          overflow: "hidden",
          "&.MuiPaper-root": {
            borderRadius: "5px !important",
          },
        }}
      >
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={1}
            sx={{
              width: "100%",
              justifyContent: "space-between",
              alignItems: { xs: "flex-start", md: "center" },
            }}
          >
            <Box>
              <Typography variant="h6" fontWeight={800}>
                {section.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {section.description}
              </Typography>
            </Box>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <Chip label={`${rows.length} rows`} size="small" color="success" variant="outlined" />
              <Chip label="Live API" size="small" color="primary" variant="outlined" />
            </Stack>
          </Stack>
        </AccordionSummary>
        <AccordionDetails>
          <Stack spacing={2}>
            <Box sx={{ "& .MuiPaper-root": { borderRadius: "5px !important" } }}>
              {renderConfigurationMatrix(
                "Scope And Ownership",
                "Resolved through configuration precedence and backend rule evaluation.",
                section.scopeRows,
                { cardRadius: "5px", tableRadius: "5px" }
              )}
            </Box>
            <Box sx={{ "& .MuiPaper-root": { borderRadius: "5px !important" } }}>
              {renderConfigurationMatrix(
                "Rule Surface",
                "Backend-backed domain registry. Rows below are loaded from the consolidated records configuration API.",
                section.matrixRows,
                { cardRadius: "5px", tableRadius: "5px" }
              )}
            </Box>
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                overflow: "hidden",
                borderRadius: "5px",
                "&.MuiPaper-rounded": {
                  borderRadius: "5px !important",
                },
              }}
            >
              <Stack spacing={2}>
                <Stack
                  direction="row"
                  spacing={1}
                  sx={{ justifyContent: "space-between", alignItems: "center" }}
                >
                  <Typography variant="h6" fontWeight={800}>
                    Current Rows
                  </Typography>
                  <Button variant="outlined" onClick={() => startNewRecordsConfigurationRow(section)}>
                    New Row
                  </Button>
                </Stack>
                <SortablePagedTable
                  rows={rows}
                  paperRadius="5px"
                  rowKey={(row) =>
                    `${section.domain}-${getRecordsConfigurationRowId(row) || getRecordsConfigurationRowCode(row)}`
                  }
                  emptyMessage="No configuration rows found for this domain."
                  columns={[
                    {
                      key: "code",
                      label: "Code",
                      sortable: true,
                      sortValue: (row) => getRecordsConfigurationRowCode(row),
                      render: (row) => getRecordsConfigurationRowCode(row),
                    },
                    {
                      key: "name",
                      label: "Name",
                      sortable: true,
                      sortValue: (row) => getRecordsConfigurationRowName(row),
                      render: (row) => getRecordsConfigurationRowName(row),
                    },
                    {
                      key: "status",
                      label: "Status",
                      sortable: true,
                      sortValue: (row) => row.status || "",
                      render: (row) => row.status || "-",
                    },
                    {
                      key: "scope",
                      label: "Scope",
                      sortable: true,
                      sortValue: (row) => getRecordsConfigurationRowScope(row),
                      render: (row) => getRecordsConfigurationRowScope(row),
                    },
                    {
                      key: "action",
                      label: "Action",
                      align: "right",
                      render: (row) => (
                        <Button size="small" onClick={() => startEditRecordsConfigurationRow(section, row)}>
                          Edit
                        </Button>
                      ),
                    },
                  ]}
                />
              </Stack>
            </Paper>
          </Stack>
        </AccordionDetails>
      </Accordion>
    );
  }

  function renderDomainFields() {
    if (activeDomain === "classification") {
      return (
        <Stack spacing={2}>
          <AdminFormTextField
            label="DOCUMENT TYPES"
            value={form.document_types}
            onChange={(event) => updateForm("document_types", event.target.value)}
            multiline
            minRows={5}
            maxRows={5}
            placeholder={"drawing\ncalculation\nprocedure"}
            labelSx={CONFIG_FORM_MULTILINE_LABEL_SX}
            fieldSx={{
              ...ADMIN_FORM_MULTILINE_TEXTFIELD_SX,
              "& textarea": {
                overflowY: "auto",
              },
            }}
          />
          <AdminFormTextField
            label="REQUIRED OUTPUTS"
            value={form.required_outputs}
            onChange={(event) => updateForm("required_outputs", event.target.value)}
            multiline
            minRows={5}
            maxRows={5}
            placeholder={"document_type_code\ntitle\ndiscipline_code"}
            labelSx={CONFIG_FORM_MULTILINE_LABEL_SX}
            fieldSx={{
              ...ADMIN_FORM_MULTILINE_TEXTFIELD_SX,
              "& textarea": {
                overflowY: "auto",
              },
            }}
          />
          <Box>
            <Typography
              variant="caption"
              sx={{ display: "block", mb: 0.75, fontWeight: 700, color: "#5A6B85" }}
            >
              AUTO RECOMMEND MIN CONFIDENCE
            </Typography>
            <TextField
              value={form.auto_confidence}
              onChange={(event) => updateForm("auto_confidence", event.target.value)}
              fullWidth
            />
          </Box>
          <Box>
            <Typography
              variant="caption"
              sx={{ display: "block", mb: 0.75, fontWeight: 700, color: "#5A6B85" }}
            >
              MANUAL REVIEW MIN CONFIDENCE
            </Typography>
            <TextField
              value={form.manual_confidence}
              onChange={(event) => updateForm("manual_confidence", event.target.value)}
              fullWidth
            />
          </Box>
          <Box>
            <Typography
              variant="caption"
              sx={{ display: "block", mb: 0.75, fontWeight: 700, color: "#5A6B85" }}
            >
              HARD FAIL BELOW CONFIDENCE
            </Typography>
            <TextField
              value={form.hard_fail_confidence}
              onChange={(event) => updateForm("hard_fail_confidence", event.target.value)}
              fullWidth
            />
          </Box>
        </Stack>
      );
    }
    if (activeDomain === "metadata_schema") {
      const fieldRules = parseJson(form.field_rules_json, {});
      const fields = Array.from(new Set([...splitLines(form.required_fields), ...splitLines(form.optional_fields)]));
      return (
        <Stack spacing={2}>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
          <TextField label="Required Fields" value={form.required_fields} onChange={(event) => updateForm("required_fields", event.target.value)} multiline minRows={8} />
          <TextField label="Optional Fields" value={form.optional_fields} onChange={(event) => updateForm("optional_fields", event.target.value)} multiline minRows={8} />
          </Box>
          <Paper variant="outlined" sx={{ overflow: "hidden" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Field</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Required</TableCell>
                  <TableCell>Default Value</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {fields.map((fieldName) => {
                  const rule = fieldRules[fieldName] || {};
                  return (
                    <TableRow key={fieldName}>
                      <TableCell>
                        <Typography fontWeight={700}>{fieldName}</Typography>
                      </TableCell>
                      <TableCell>
                        <TextField
                          select
                          size="small"
                          value={rule.type || "text"}
                          onChange={(event) => updateFieldRule(fieldName, "type", event.target.value)}
                          fullWidth
                        >
                          <MenuItem value="text">Text</MenuItem>
                          <MenuItem value="date">Date</MenuItem>
                          <MenuItem value="number">Number</MenuItem>
                          <MenuItem value="boolean">Boolean</MenuItem>
                        </TextField>
                      </TableCell>
                      <TableCell>
                        <TextField
                          select
                          size="small"
                          value={rule.required === false ? "no" : "yes"}
                          onChange={(event) => updateFieldRule(fieldName, "required", event.target.value === "yes")}
                          fullWidth
                        >
                          <MenuItem value="yes">Yes</MenuItem>
                          <MenuItem value="no">No</MenuItem>
                        </TextField>
                      </TableCell>
                      <TableCell>
                        <TextField
                          size="small"
                          value={rule.default || ""}
                          onChange={(event) => updateFieldRule(fieldName, "default", event.target.value)}
                          fullWidth
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Paper>
        </Stack>
      );
    }
    if (activeDomain === "reviewer_assignment") {
      const routingRules = parseJson(form.routing_rules_json, []);
      const routingRows = Array.isArray(routingRules) ? routingRules : [];
      return (
        <Stack spacing={2}>
          {[
            ["Default", "default_role", "default_strategy"],
            ["Classification Review", "classification_role", "classification_strategy"],
            ["Metadata Review", "metadata_role", "metadata_strategy"],
          ].map(([label, roleKey, strategyKey]) => (
            <Box key={label} sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" }, alignItems: "center" }}>
              <Typography fontWeight={700}>{label}</Typography>
              <TextField label="Reviewer Role" value={form[roleKey as keyof PolicyForm]} onChange={(event) => updateForm(roleKey as keyof PolicyForm, event.target.value)} />
              <TextField select label="Assignment Strategy" value={form[strategyKey as keyof PolicyForm]} onChange={(event) => updateForm(strategyKey as keyof PolicyForm, event.target.value)}>
                <MenuItem value="least_loaded_in_role">Least loaded in role</MenuItem>
                <MenuItem value="first_active_in_role">First active in role</MenuItem>
              </TextField>
            </Box>
          ))}
          <Paper variant="outlined" sx={{ overflow: "hidden" }}>
            <Box sx={{ p: 1.5, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <Typography fontWeight={800}>Routing Rules</Typography>
              <Button size="small" variant="outlined" onClick={addRoutingRule}>Add Rule</Button>
            </Box>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Task</TableCell>
                  <TableCell>Document Type</TableCell>
                  <TableCell>Business Area</TableCell>
                  <TableCell>Priority</TableCell>
                  <TableCell>Reviewer Role</TableCell>
                  <TableCell>Strategy</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {routingRows.map((rule, index) => (
                  <TableRow key={`${rule.task_code || "rule"}-${index}`}>
                    <TableCell>
                      <TextField
                        select
                        size="small"
                        value={rule.task_code || "classification_review"}
                        onChange={(event) => updateRoutingRule(index, "task_code", event.target.value)}
                        fullWidth
                      >
                        <MenuItem value="classification_review">Classification</MenuItem>
                        <MenuItem value="metadata_review">Metadata</MenuItem>
                      </TextField>
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={readMatchValue(rule.match || {}, "document_type_code")}
                        onChange={(event) => updateRoutingRule(index, "document_type_code", event.target.value)}
                        fullWidth
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={readMatchValue(rule.match || {}, "business_area")}
                        onChange={(event) => updateRoutingRule(index, "business_area", event.target.value)}
                        fullWidth
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={readMatchValue(rule.match || {}, "priority")}
                        onChange={(event) => updateRoutingRule(index, "priority", event.target.value)}
                        fullWidth
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={rule.assignee?.role_code || "tenant_admin"}
                        onChange={(event) => updateRoutingRule(index, "role_code", event.target.value)}
                        fullWidth
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        select
                        size="small"
                        value={rule.assignee?.strategy || "least_loaded_in_role"}
                        onChange={(event) => updateRoutingRule(index, "strategy", event.target.value)}
                        fullWidth
                      >
                        <MenuItem value="least_loaded_in_role">Least loaded</MenuItem>
                        <MenuItem value="first_active_in_role">First active</MenuItem>
                      </TextField>
                    </TableCell>
                    <TableCell align="right">
                      <Button size="small" color="warning" onClick={() => removeRoutingRule(index)}>Remove</Button>
                    </TableCell>
                  </TableRow>
                ))}
                {!routingRows.length ? (
                  <TableRow>
                    <TableCell colSpan={7}>
                      <Typography color="text.secondary">No routing rules. Default reviewer assignments will be used.</Typography>
                    </TableCell>
                  </TableRow>
                ) : null}
              </TableBody>
            </Table>
          </Paper>
        </Stack>
      );
    }
    return (
      <Stack spacing={2}>
        {[
          ["Default", "default_target_hours", "default_warning_hours", "default_escalate_hours"],
          ["Classification Review", "classification_target_hours", "classification_warning_hours", "classification_escalate_hours"],
          ["Metadata Review", "metadata_target_hours", "metadata_warning_hours", "metadata_escalate_hours"],
        ].map(([label, targetKey, warningKey, escalateKey]) => (
          <Box key={label} sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr 1fr" }, alignItems: "center" }}>
            <Typography fontWeight={700}>{label}</Typography>
            <TextField label="Target Hours" value={form[targetKey as keyof PolicyForm]} onChange={(event) => updateForm(targetKey as keyof PolicyForm, event.target.value)} />
            <TextField label="Warning Before Hours" value={form[warningKey as keyof PolicyForm]} onChange={(event) => updateForm(warningKey as keyof PolicyForm, event.target.value)} />
            <TextField label="Escalate After Hours" value={form[escalateKey as keyof PolicyForm]} onChange={(event) => updateForm(escalateKey as keyof PolicyForm, event.target.value)} />
          </Box>
        ))}
      </Stack>
    );
  }

  function renderPolicyModal() {
    return (
      <AdminFormDialog
        open={showForm}
        onClose={() => setShowForm(false)}
        maxWidth={570}
        title={`${editingPolicy ? "Edit Policy" : "Create Policy"} - ${DOMAIN_LABELS[activeDomain]}`}
        titleSx={{ fontSize: "1.1rem", fontWeight: 700 }}
        contentSx={{
          "&.MuiDialogContent-root": {
            paddingTop: "20px !important",
          },
        }}
        stackSx={{ maxWidth: 570 }}
        actions={
          <>
            <Button onClick={() => setShowForm(false)}>Cancel</Button>
            <Button variant="contained" onClick={handleSave} disabled={isPending}>
              Save Policy
            </Button>
          </>
        }
      >
        <AdminFormTextField
          label="POLICY NAME"
          value={form.name}
          onChange={(event) => updateForm("name", event.target.value)}
          placeholder="Policy name"
          helperText="Visible policy label shown to administrators."
        />
        <AdminFormTextField
          label="POLICY CODE"
          value={form.policy_code}
          onChange={(event) => updateForm("policy_code", event.target.value)}
          disabled={Boolean(editingPolicy)}
          placeholder="policy_code"
          helperText="Stable system identifier used for configuration versioning."
        />
        <AdminFormTextField
          label="STATUS"
          select
          value={form.status}
          onChange={(event) => updateForm("status", event.target.value)}
        >
          <MenuItem value="ACTIVE">Active</MenuItem>
          <MenuItem value="DRAFT">Draft</MenuItem>
          <MenuItem value="RETIRED">Retired</MenuItem>
        </AdminFormTextField>
        <AdminFormTextField
          label="SCOPE TYPE"
          select
          value={form.scope_type}
          onChange={(event) => updateForm("scope_type", event.target.value)}
        >
          <MenuItem value="tenant">Tenant default</MenuItem>
          <MenuItem value="business_area">Business area</MenuItem>
          <MenuItem value="repository">Repository</MenuItem>
          <MenuItem value="project">Project</MenuItem>
        </AdminFormTextField>
        <AdminFormField label="SCOPE REFERENCE">
          {form.scope_type === "project" ? (
            <TextField
              value={form.scope_ref}
              onChange={(event) => updateForm("scope_ref", event.target.value)}
              placeholder="Project identifier"
              fullWidth
              sx={ADMIN_FORM_TEXTFIELD_SX}
            />
          ) : form.scope_type === "tenant" ? (
            <TextField value="Tenant default" disabled fullWidth sx={ADMIN_FORM_TEXTFIELD_SX} />
          ) : (
            <TextField
              select
              value={form.scope_ref}
              onChange={(event) => updateForm("scope_ref", event.target.value)}
              fullWidth
              sx={ADMIN_FORM_TEXTFIELD_SX}
            >
              {scopeOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
          )}
        </AdminFormField>
        <AdminFormTextField
          label="DEFAULT FOR SCOPE"
          select
          value={form.is_default ? "yes" : "no"}
          onChange={(event) => updateForm("is_default", event.target.value === "yes")}
          helperText="Marks the active default policy when multiple versions exist in the same scope."
        >
          <MenuItem value="yes">Yes</MenuItem>
          <MenuItem value="no">No</MenuItem>
        </AdminFormTextField>
        {renderDomainFields()}
      </AdminFormDialog>
    );
  }

  function renderRecordsConfigurationForm() {
    if (!activeRecordsFormSection) return null;

    return (
      <AdminFormDialog
        open={showRecordsForm}
        onClose={closeRecordsForm}
        maxWidth={570}
        title={`${recordsFormRowId ? "Edit" : "Create"} - ${activeRecordsFormSection.title}`}
        titleSx={{ fontSize: "1.1rem", fontWeight: 700 }}
        contentSx={{
          "&.MuiDialogContent-root": {
            paddingTop: "20px !important",
          },
        }}
        stackSx={{ maxWidth: 570 }}
        actions={
          <>
            <Button onClick={closeRecordsForm}>Cancel</Button>
            <Button
              variant="contained"
              onClick={handleSaveRecordsConfigurationForm}
              disabled={recordsConfigurationSavingDomain === activeRecordsFormSection.domain}
            >
              {recordsConfigurationSavingDomain === activeRecordsFormSection.domain
                ? "Saving..."
                : "Save"}
            </Button>
          </>
        }
      >
        {activeRecordsFormFields.map((field) => {
          const value = recordsFormValues[field.key];

          if (field.type === "toggle") {
            return (
              <AdminFormTextField
                key={field.key}
                label={field.label}
                select
                value={value ? "yes" : "no"}
                onChange={(event) => updateRecordsFormValue(field.key, event.target.value === "yes")}
                helperText={field.helperText}
              >
                <MenuItem value="yes">Yes</MenuItem>
                <MenuItem value="no">No</MenuItem>
              </AdminFormTextField>
            );
          }

          if (field.type === "select") {
            return (
              <AdminFormTextField
                key={field.key}
                label={field.label}
                select
                value={String(value ?? "")}
                onChange={(event) => updateRecordsFormValue(field.key, event.target.value)}
                helperText={field.helperText}
              >
                {(field.options || []).map((option) => (
                  <MenuItem key={`${field.key}-${option || "blank"}`} value={option}>
                    {option === "" ? "Not set" : option}
                  </MenuItem>
                ))}
              </AdminFormTextField>
            );
          }

          if (field.type === "textarea" || field.type === "json") {
            return (
              <AdminFormTextField
                key={field.key}
                label={field.label}
                value={String(value ?? "")}
                onChange={(event) => updateRecordsFormValue(field.key, event.target.value)}
                multiline
                minRows={field.minRows || (field.type === "json" ? 4 : 3)}
                maxRows={field.minRows || (field.type === "json" ? 4 : 3)}
                helperText={field.helperText}
                fieldSx={{
                  ...ADMIN_FORM_MULTILINE_TEXTFIELD_SX,
                  "& textarea": {
                    overflowY: "auto",
                  },
                }}
              />
            );
          }

          return (
            <AdminFormTextField
              key={field.key}
              label={field.label}
              type={field.type === "number" ? "number" : "text"}
              value={String(value ?? "")}
              onChange={(event) => updateRecordsFormValue(field.key, event.target.value)}
              helperText={field.helperText}
            />
          );
        })}
      </AdminFormDialog>
    );
  }

  return (
    <OutletPage
      title="Configuration"
      description="Manage document control, records management, and transmittals configuration for the Symployee Document Controller."
    >
      {loading ? (
        <CircularProgress />
      ) : (
        <Stack spacing={0}>
          {renderAreaMenuStrip(
            [
              { key: "document_control", label: "Document Control" },
              { key: "records_management", label: "Records Management" },
              { key: "transmittals", label: "Transmittals & Communications" },
            ],
            activeArea,
            (value) => setActiveArea(value as ConfigurationArea),
            {
              fullBleed: true,
              bleedSx: { mt: -7 },
              borderColor: "divider",
            }
          )}

          <Box sx={{ mt: 0 }}>
            {renderWorkbenchCard({
              title:
                activeArea === "document_control"
                  ? "Document Controller Configuration"
                  : activeArea === "records_management"
                    ? "Records Management Configuration"
                    : "Transmittals & Communications Configuration",
              subtitle:
                activeArea === "document_control"
                  ? "Common configuration shell for document control, records management, and transmittals, with section menus placed beneath a centralized title bar."
                  : activeArea === "records_management"
                    ? "Manage records categories, declaration rules, lifecycle controls, retention schedules, vital policies, hold policies, disposition policies, archive policies, and assignment rules."
                    : "Manage transmittal numbering, communication categories, acknowledgements, response handling, distribution rules, and operational workflow controls.",
              accentLabel:
                activeArea === "document_control"
                  ? "Document Control"
                  : activeArea === "records_management"
                  ? "Records Management"
                    : "Transmittals",
              tabs: null,
              paperSx: {
                mt: 2,
                width: "100%",
                borderRadius: 2.25,
                borderColor: "#21344D",
                borderWidth: "1.5px",
                boxShadow: "0 10px 24px rgba(15, 23, 42, 0.06)",
              },
              bodySx: {
                p: 0,
                bgcolor: "#F6FAFF",
              },
              body: (
                <Stack spacing={0}>
                  {activeArea === "document_control" ? (
                    <>
                      {renderAreaMenuStrip(
                        (Object.keys(DOMAIN_LABELS) as PolicyDomain[]).map((domain) => ({
                          key: domain,
                          label: DOMAIN_LABELS[domain],
                        })),
                        activeDomain,
                        (value) => {
                          setActiveDomain(value as PolicyDomain);
                          setShowForm(false);
                        },
                        {
                          actions: (
                            <>
                              <Button
                                variant="outlined"
                                onClick={handleBootstrap}
                                disabled={isPending}
                                sx={{ minHeight: 36 }}
                              >
                                Create Defaults
                              </Button>
                              <Button
                                variant="contained"
                                onClick={() => startCreate(activeDomain)}
                                disabled={isPending}
                                sx={{ minHeight: 36 }}
                              >
                                Create New
                              </Button>
                            </>
                          ),
                        }
                      )}

                      <Box sx={{ px: 0, py: 0, bgcolor: "#F6FAFF" }}>
                        <SortablePagedTable
                          rows={activePolicies}
                          flatten
                          rowKey={(policy) => policy.policy_id}
                          emptyMessage={
                            <Typography color="text.secondary">
                              No policies configured for this domain.
                            </Typography>
                          }
                          columns={[
                            {
                              key: "policy",
                              label: "Policy",
                              sortable: true,
                              sortValue: (policy) => policy.name,
                              render: (policy) => (
                                <>
                                  <Typography fontWeight={700}>{policy.name}</Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    {policy.policy_code}
                                  </Typography>
                                </>
                              ),
                            },
                            {
                              key: "scope",
                              label: "Scope",
                              sortable: true,
                              sortValue: (policy) => scopeLabel(policy),
                              render: (policy) => scopeLabel(policy),
                            },
                            {
                              key: "version",
                              label: "Version",
                              sortable: true,
                              sortValue: (policy) => policy.version_no,
                              render: (policy) => `v${policy.version_no}`,
                            },
                            {
                              key: "status",
                              label: "Status",
                              sortable: true,
                              sortValue: (policy) => policy.status,
                              render: (policy) => (
                                <Chip
                                  size="small"
                                  label={policy.status}
                                  color={policy.status === "ACTIVE" ? "success" : "default"}
                                  variant="outlined"
                                />
                              ),
                            },
                            {
                              key: "default",
                              label: "Default",
                              sortable: true,
                              sortValue: (policy) => (policy.is_default ? 1 : 0),
                              render: (policy) => (policy.is_default ? "Yes" : "No"),
                            },
                            {
                              key: "actions",
                              label: "Actions",
                              align: "right",
                              render: (policy) => (
                                <>
                                  <Button size="small" onClick={() => startEdit(policy)}>
                                    Edit
                                  </Button>
                                  <Button
                                    size="small"
                                    color="warning"
                                    onClick={() => startEdit({ ...policy, status: "RETIRED" })}
                                  >
                                    Retire
                                  </Button>
                                </>
                              ),
                            },
                          ]}
                        />

                    </Box>
                  </>
                ) : null}

                {activeArea === "records_management" ? (
                  <Stack spacing={0}>
                    {renderAreaMenuStrip(
                      recordsConfigurationSections.map((section) => ({
                        key: section.key,
                        label: section.title,
                      })),
                      expandedRecordsSectionKey || recordsConfigurationSections[0]?.key || "",
                      (value) => setExpandedRecordsSectionKey(value)
                    )}
                    {recordsConfigurationSections
                      .filter(
                        (section) =>
                          section.key ===
                          (expandedRecordsSectionKey || recordsConfigurationSections[0]?.key)
                      )
                      .map((section) => renderLiveRecordsConfigurationSection(section))}
                  </Stack>
                ) : null}

                  {activeArea === "transmittals"
                    ? (
                        <Stack spacing={2}>
                          {renderAreaMenuStrip(
                            [{ key: "transmittals", label: "Transmittals" }],
                            "transmittals",
                            () => {}
                          )}
                          {renderConfigurationMatrix(
                            "Transmittals & Communications Configuration",
                            "Operational controls for numbering, purpose codes, response handling, acknowledgements, correspondence categories, and workflow performers.",
                            [
                              {
                                setting: "Numbering Scope",
                                value: "Tenant / business area / repository",
                                note: "Use scope-aware numbering for incoming and outgoing transmittal sequences.",
                              },
                              {
                                setting: "Direction Modes",
                                value: "INCOMING, OUTGOING",
                                note: "Matches the dedicated transmittals route and service already created.",
                              },
                              {
                                setting: "Purpose-of-Issue Codes",
                                value: "Configurable by module policy",
                                note: "Examples include review, approval, information, issue for construction, or as-built handover.",
                              },
                              {
                                setting: "Response Codes",
                                value: "Recipient response workflow",
                                note: "Define expected response and acknowledgement codes per issue type.",
                              },
                              {
                                setting: "Acknowledgement Control",
                                value: "Pending, sent, due, overdue, acknowledged",
                                note: "Overdue acknowledgement handling is already supported in backend transmittal logic.",
                              },
                              {
                                setting: "Distribution Rules",
                                value: "Role, user, recipient organization",
                                note: "Use distribution defaults to prebuild recipient lists for formal issue packages.",
                              },
                              {
                                setting: "Workflow Performers",
                                value: "Reviewer matrix / tenant roles",
                                note: "Workflow performer assignment should align with the reviewer-assignment policy tab.",
                              },
                              {
                                setting: "Correspondence Governance",
                                value: "Category and control taxonomy",
                                note: "Supports separation between formal transmittals and general correspondence streams.",
                              },
                              {
                                setting: "Template / Package Controls",
                                value: "Frozen issue packages and cover sheets",
                                note: "Use for official issue bundles, transmittal templates, and sealed handover packages.",
                              },
                            ],
                            { flattenCard: true, flattenTable: true, hideHeader: true }
                          )}
                        </Stack>
                      )
                    : null}
                </Stack>
              ),
            })}
          </Box>
        </Stack>
      )}
      {activeArea === "document_control" ? renderPolicyModal() : null}
      {showRecordsForm ? renderRecordsConfigurationForm() : null}
      <Snackbar
        open={Boolean(notificationMessage)}
        autoHideDuration={3500}
        onClose={() => {
          setMessage("");
          setError("");
          setRecordsConfigurationError("");
        }}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          onClose={() => {
            setMessage("");
            setError("");
            setRecordsConfigurationError("");
          }}
          severity={notificationSeverity}
          variant="filled"
          sx={{ width: "100%" }}
        >
          {notificationMessage}
        </Alert>
      </Snackbar>
    </OutletPage>
  );
}
