"use client";

import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import { DocumentLifecycleBadge } from "@/app/synthetic-employees/document-controller/_components/DocumentLifecycleBadge";
import {
  ADMIN_DATA_TABLE_CELL_CONTENT_SX,
  ADMIN_DATA_TABLE_SX,
} from "@/components/data-display/adminTableStyles";

type SimpleSx = Record<string, any>;

type DocumentControllerDocumentDetailContentProps = {
  detail: any;
  message?: string | null;
  isPending?: boolean;
  mode?: "page" | "modal";
  onDraftManualAction?: () => void;
  onOpenCurrentDocument: () => void;
  onOpenVersionDocument: (versionId?: string | null) => void;
};

const SURFACE_CARD_SX = {
  borderRadius: 5,
  borderColor: "#D8E1EE",
  boxShadow: "0 18px 42px rgba(15, 23, 42, 0.08)",
  overflow: "hidden",
} as const;

const CONTEXT_PANEL_SX = {
  borderRadius: 4,
  px: 2.5,
  py: 2.2,
  color: "#E5EEF8",
  background: "linear-gradient(145deg, #274674 0%, #1D355D 100%)",
  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.08)",
} as const;

const SUMMARY_CARD_BASE_SX = {
  borderRadius: 3.5,
  p: 2,
  minHeight: 132,
  border: "1px solid",
  boxShadow: "0 12px 28px rgba(15, 23, 42, 0.05)",
} as const;

const SECTION_HEADER_SX = {
  px: 2.5,
  py: 1.5,
  borderBottom: "1px solid #D8E1EE",
  background:
    "linear-gradient(180deg, rgba(247,250,252,0.92) 0%, rgba(241,245,249,0.92) 100%)",
} as const;

const SECTION_BODY_SX = {
  px: 0,
  py: 0,
  backgroundColor: "#FFFFFF",
} as const;

const VALUE_TEXT_SX = {
  ...ADMIN_DATA_TABLE_CELL_CONTENT_SX,
  whiteSpace: "normal",
  overflow: "visible",
  textOverflow: "unset",
  color: "#102A43",
} as const;

function renderStatusChip(value?: string | null) {
  const normalized = String(value || "").toUpperCase();
  const color =
    normalized === "APPROVED" || normalized === "ACKNOWLEDGED" || normalized === "COMPLETED"
      ? "success"
      : normalized === "REJECTED" ||
          normalized === "FAILED" ||
          normalized === "OVERDUE" ||
          normalized === "ESCALATED"
        ? "error"
        : normalized === "PENDING_APPROVAL" || normalized === "WARNING"
          ? "warning"
          : normalized === "DISPATCHED" ||
              normalized === "ACTIVE" ||
              normalized === "IN_PROGRESS"
            ? "info"
            : "default";

  return (
    <Chip
      size="small"
      label={(normalized || "-").replaceAll("_", " ")}
      color={color as any}
      variant="outlined"
      sx={{
        height: 24,
        borderRadius: 999,
        fontSize: 10.5,
        fontWeight: 700,
        letterSpacing: 0.12,
        backgroundColor: "#FFFFFF",
      }}
    />
  );
}

function formatDisplayValue(value?: string | null, fallback = "-") {
  const normalized = String(value || fallback);
  return normalized
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function DetailMetricCard({
  label,
  primary,
  secondary,
  toneSx,
}: {
  label: string;
  primary: React.ReactNode;
  secondary?: React.ReactNode;
  toneSx: SimpleSx;
}) {
  return (
    <Paper variant="outlined" sx={{ ...SUMMARY_CARD_BASE_SX, ...toneSx }}>
      <Stack spacing={1.2} sx={{ height: "100%" }}>
        <Typography
          sx={{
            fontSize: 10.5,
            fontWeight: 800,
            letterSpacing: 1.1,
            textTransform: "uppercase",
            color: "inherit",
            opacity: 0.74,
          }}
        >
          {label}
        </Typography>
        <Box sx={{ flex: 1, display: "flex", alignItems: "center" }}>{primary}</Box>
        {secondary ? (
          <Typography sx={{ fontSize: 12, lineHeight: 1.45, color: "inherit", opacity: 0.82 }}>
            {secondary}
          </Typography>
        ) : null}
      </Stack>
    </Paper>
  );
}

function DetailSection({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <Paper variant="outlined" sx={SURFACE_CARD_SX}>
      <Stack sx={SECTION_HEADER_SX}>
        <Typography sx={{ fontSize: 16, fontWeight: 800, color: "#102A43" }}>{title}</Typography>
        <Typography sx={{ fontSize: 12, color: "#627D98" }}>{description}</Typography>
      </Stack>
      <Box sx={SECTION_BODY_SX}>{children}</Box>
    </Paper>
  );
}

export function DocumentControllerDocumentDetailContent({
  detail,
  message,
  isPending = false,
  mode = "page",
  onDraftManualAction,
  onOpenCurrentDocument,
  onOpenVersionDocument,
}: DocumentControllerDocumentDetailContentProps) {
  const identity = detail?.identity || {};
  const versions = detail?.versions || [];
  const sourceObjects = detail?.source_objects || [];
  const recommendations = detail?.recommendations || [];
  const workflows = detail?.workflows || [];
  const commands = detail?.commands || [];

  return (
    <Stack spacing={2.25}>
      {message ? <Alert severity="success">{message}</Alert> : null}

      <Paper
        variant="outlined"
        sx={{
          ...SURFACE_CARD_SX,
          borderRadius: mode === "modal" ? 4.5 : SURFACE_CARD_SX.borderRadius,
        }}
      >
        <Stack spacing={2.25} sx={{ p: { xs: 2.25, md: 2.75 } }}>
          <Stack
            direction={{ xs: "column", lg: "row" }}
            spacing={2}
            sx={{
              justifyContent: "space-between",
              alignItems: { xs: "flex-start", lg: "flex-start" },
            }}
          >
            <Stack spacing={1.1} sx={{ minWidth: 0, flex: 1 }}>
              <Typography
                sx={{
                  fontSize: { xs: 24, md: 31 },
                  lineHeight: 1.14,
                  fontWeight: 800,
                  color: "#102A43",
                  letterSpacing: "-0.02em",
                }}
              >
                {identity.title || identity.identity_id}
              </Typography>
              <Typography sx={{ fontSize: 13, color: "#627D98", lineHeight: 1.6 }}>
                Identity: {identity.identity_id || "-"} | Repository: {identity.repository_id || "-"}{" "}
                | Status: {formatDisplayValue(identity.status)}
              </Typography>
            </Stack>

            <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ width: { xs: "100%", lg: "auto" } }}>
              <Button
                size="small"
                variant="outlined"
                disabled={!detail?.actual_document_available}
                onClick={onOpenCurrentDocument}
                sx={{ borderRadius: 999, px: 2.1, fontWeight: 700 }}
              >
                Open Actual Document
              </Button>
              {onDraftManualAction ? (
                <Button
                  size="small"
                  variant="contained"
                  disabled={isPending}
                  onClick={onDraftManualAction}
                  sx={{
                    borderRadius: 999,
                    px: 2.1,
                    fontWeight: 700,
                    boxShadow: "0 10px 24px rgba(37, 99, 235, 0.28)",
                  }}
                >
                  Draft Manual Action
                </Button>
              ) : null}
            </Stack>
          </Stack>

          <Paper variant="outlined" sx={CONTEXT_PANEL_SX}>
            <Stack spacing={1.1}>
              <Typography
                sx={{
                  fontSize: 11,
                  fontWeight: 800,
                  letterSpacing: 1.2,
                  textTransform: "uppercase",
                  color: "rgba(229,238,248,0.72)",
                }}
              >
                Document Context
              </Typography>
              <Typography
                sx={{
                  fontSize: 17,
                  fontWeight: 700,
                  lineHeight: 1.6,
                  color: "#FFFFFF",
                  fontFamily: "Consolas, 'Courier New', monospace",
                }}
              >
                {identity.canonical_document_number || "No document number"} ·{" "}
                {formatDisplayValue(identity.document_type_code, "Pending Type")} · Revision{" "}
                {identity.current_version_label || identity.current_revision_code || "-"}
              </Typography>
              <Typography sx={{ fontSize: 12, lineHeight: 1.75, color: "rgba(229,238,248,0.78)" }}>
                Project: {identity.project_code || "-"} | Originator: {identity.originator_code || "-"} |
                Current Version Id: {identity.current_version_id || "-"}
              </Typography>
            </Stack>
          </Paper>

          <Grid container spacing={1.5}>
            <Grid size={{ xs: 12, md: 4 }}>
              <DetailMetricCard
                label="Lifecycle"
                toneSx={{
                  background: "linear-gradient(180deg, #F4F8FF 0%, #EEF4FF 100%)",
                  borderColor: "#C7D7FE",
                  color: "#1D4ED8",
                }}
                primary={
                  <Stack direction="row" spacing={0.8} useFlexGap sx={{ flexWrap: "wrap" }}>
                    <DocumentLifecycleBadge stage={identity.document_lifecycle_stage} />
                    {renderStatusChip(identity.review_status)}
                    {renderStatusChip(identity.issue_status)}
                  </Stack>
                }
                secondary={`Lifecycle stage ${formatDisplayValue(identity.document_lifecycle_stage, "Registered")}.`}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <DetailMetricCard
                label="Records"
                toneSx={{
                  background: "linear-gradient(180deg, #F4FFF8 0%, #EDFDF4 100%)",
                  borderColor: "#B6F0C8",
                  color: "#15803D",
                }}
                primary={
                  <Stack direction="row" spacing={0.8} useFlexGap sx={{ flexWrap: "wrap" }}>
                    {renderStatusChip(identity.record_status)}
                    {renderStatusChip(identity.retention_status)}
                    {renderStatusChip(identity.disposition_status)}
                  </Stack>
                }
                secondary={`Records status ${formatDisplayValue(identity.record_status, "Non Record")}.`}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <DetailMetricCard
                label="Security"
                toneSx={{
                  background: "linear-gradient(180deg, #FFF9F1 0%, #FFF4E4 100%)",
                  borderColor: "#F7D39A",
                  color: "#B45309",
                }}
                primary={<Stack direction="row">{renderStatusChip(identity.security_status)}</Stack>}
                secondary={`${sourceObjects.length} source objects · ${commands.length} linked actions.`}
              />
            </Grid>
          </Grid>
        </Stack>
      </Paper>

      <DetailSection
        title="Versions"
        description="Revision sequence, current issue state, and direct file access across document versions."
      >
        <Box sx={{ overflowX: "auto" }}>
          <Table size="small" sx={ADMIN_DATA_TABLE_SX}>
            <TableHead>
              <TableRow>
                <TableCell>Version</TableCell>
                <TableCell>File</TableCell>
                <TableCell>Revision</TableCell>
                <TableCell>Revision State</TableCell>
                <TableCell>Issue State</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Document</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {versions.length ? (
                versions.map((item: any) => (
                  <TableRow key={item.version_id} hover>
                    <TableCell>{item.version_label || item.version_id}</TableCell>
                    <TableCell>
                      <Box component="span" sx={VALUE_TEXT_SX}>
                        {item.file_name || "-"}
                      </Box>
                    </TableCell>
                    <TableCell>{item.revision_code || "-"}</TableCell>
                    <TableCell>
                      <Stack
                        direction="row"
                        spacing={0.8}
                        useFlexGap
                        sx={{ alignItems: "center", flexWrap: "wrap" }}
                      >
                        {renderStatusChip(item.revision_status)}
                        {item.is_current_revision ? (
                          <Chip
                            size="small"
                            label="CURRENT"
                            sx={{
                              height: 22,
                              borderRadius: 999,
                              fontSize: 10.5,
                              fontWeight: 800,
                              color: "#15803D",
                              backgroundColor: "#EAFBF0",
                            }}
                          />
                        ) : null}
                      </Stack>
                    </TableCell>
                    <TableCell>{renderStatusChip(item.issue_status)}</TableCell>
                    <TableCell>{renderStatusChip(item.status)}</TableCell>
                    <TableCell>
                      <Button size="small" sx={{ borderRadius: 999 }} onClick={() => onOpenVersionDocument(item.version_id)}>
                        Open File
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={7}>No versions recorded yet.</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Box>
      </DetailSection>

      <DetailSection
        title="Source Objects"
        description="Connector source traces linked to this logical document identity."
      >
        <Box sx={{ overflowX: "auto" }}>
          <Table size="small" sx={ADMIN_DATA_TABLE_SX}>
            <TableHead>
              <TableRow>
                <TableCell>Source Type</TableCell>
                <TableCell>Path</TableCell>
                <TableCell>External Id</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sourceObjects.length ? (
                sourceObjects.map((item: any) => (
                  <TableRow key={item.source_object_id} hover>
                    <TableCell>{item.source_system_type || "-"}</TableCell>
                    <TableCell>
                      <Box component="span" sx={VALUE_TEXT_SX}>
                        {item.source_path || "-"}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Box component="span" sx={VALUE_TEXT_SX}>
                        {item.external_object_id || "-"}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={3}>No source objects linked yet.</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Box>
      </DetailSection>

      <DetailSection
        title="Recommendations"
        description="Recommendation lineage, confidence, and lifecycle targeting for this document."
      >
        <Box sx={{ overflowX: "auto" }}>
          <Table size="small" sx={ADMIN_DATA_TABLE_SX}>
            <TableHead>
              <TableRow>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Confidence</TableCell>
                <TableCell>Lifecycle</TableCell>
                <TableCell>Recommendation Id</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {recommendations.length ? (
                recommendations.map((item: any) => (
                  <TableRow key={item.recommendation_id} hover>
                    <TableCell>{formatDisplayValue(item.recommendation_type)}</TableCell>
                    <TableCell>{renderStatusChip(item.status)}</TableCell>
                    <TableCell>{item.confidence_score ?? "-"}</TableCell>
                    <TableCell>
                      <Stack spacing={0.45}>
                        {renderStatusChip(item.lifecycle_action_type)}
                        <Typography sx={{ fontSize: 11.5, lineHeight: 1.45, color: "#627D98" }}>
                          {formatDisplayValue(item.lifecycle_state_dimension)} /{" "}
                          {formatDisplayValue(item.lifecycle_target_state)}
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell>{item.recommendation_id}</TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={5}>No recommendations recorded yet.</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Box>
      </DetailSection>

      <DetailSection
        title="Workflow"
        description="Workflow instances, task routing, SLA posture, and recent event context."
      >
        <Stack spacing={1.5} sx={{ p: 2 }}>
          {workflows.length ? (
            workflows.map((workflow: any) => (
              <Paper
                key={workflow.workflow_instance_id}
                variant="outlined"
                sx={{ borderRadius: 3.25, borderColor: "#D8E1EE", overflow: "hidden" }}
              >
                <Stack spacing={1.2} sx={{ p: 2 }}>
                  <Stack
                    direction="row"
                    spacing={1}
                    useFlexGap
                    sx={{ alignItems: "center", flexWrap: "wrap" }}
                  >
                    <Typography sx={{ fontSize: 15, fontWeight: 800, color: "#102A43" }}>
                      {workflow.workflow_code}
                    </Typography>
                    {renderStatusChip(workflow.workflow_status)}
                    {renderStatusChip(workflow.routing_status)}
                    {workflow.current_step_code ? (
                      <Typography sx={{ fontSize: 11.5, color: "#627D98" }}>
                        Current step: {workflow.current_step_code}
                      </Typography>
                    ) : null}
                  </Stack>
                  <Typography sx={{ fontSize: 11.5, color: "#627D98" }}>
                    Lifecycle target: {formatDisplayValue(workflow.lifecycle_state_dimension)} /{" "}
                    {formatDisplayValue(workflow.lifecycle_target_state)}
                  </Typography>
                </Stack>
                <Box sx={{ overflowX: "auto" }}>
                  <Table size="small" sx={ADMIN_DATA_TABLE_SX}>
                    <TableHead>
                      <TableRow>
                        <TableCell>Step</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Assigned Role</TableCell>
                        <TableCell>SLA</TableCell>
                        <TableCell>Outcome</TableCell>
                        <TableCell>Recommendation</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {(workflow.tasks || []).length ? (
                        workflow.tasks.map((task: any) => (
                          <TableRow key={task.workflow_task_id} hover>
                            <TableCell>{task.task_name || "-"}</TableCell>
                            <TableCell>{renderStatusChip(task.status)}</TableCell>
                            <TableCell>
                              <Stack spacing={0.35}>
                                <Typography sx={{ fontSize: 12.5, color: "#102A43" }}>
                                  {task.assigned_role_code || "-"}
                                </Typography>
                                <Typography sx={{ fontSize: 11.5, color: "#627D98" }}>
                                  {task.assigned_user_name || task.assigned_user_id || "Unassigned"}
                                </Typography>
                              </Stack>
                            </TableCell>
                            <TableCell>
                              <Stack spacing={0.3}>
                                {renderStatusChip(task.sla_status)}
                                <Typography sx={{ fontSize: 11.5, color: "#627D98" }}>
                                  Due: {task.due_at ? new Date(task.due_at).toLocaleString() : "-"}
                                </Typography>
                                <Typography sx={{ fontSize: 11.5, color: "#627D98" }}>
                                  Days overdue: {task.days_overdue ?? 0}
                                </Typography>
                              </Stack>
                            </TableCell>
                            <TableCell>
                              <Stack spacing={0.3}>
                                {renderStatusChip(task.outcome_code)}
                                <Typography sx={{ fontSize: 11.5, color: "#627D98" }}>
                                  Response: {task.response_code || "-"}
                                </Typography>
                              </Stack>
                            </TableCell>
                            <TableCell>{task.task_payload?.recommendation_type || "-"}</TableCell>
                          </TableRow>
                        ))
                      ) : (
                        <TableRow>
                          <TableCell colSpan={6}>No workflow tasks recorded yet.</TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </Box>
              </Paper>
            ))
          ) : (
            <Typography sx={{ fontSize: 12.5, color: "#627D98" }}>
              No workflow instances created yet.
            </Typography>
          )}
        </Stack>
      </DetailSection>

      <DetailSection
        title="Actions"
        description="Linked connector actions, approval posture, and source-recommendation context."
      >
        <Box sx={{ overflowX: "auto" }}>
          <Table size="small" sx={ADMIN_DATA_TABLE_SX}>
            <TableHead>
              <TableRow>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Approval</TableCell>
                <TableCell>Source Recommendation</TableCell>
                <TableCell>Lifecycle Event</TableCell>
                <TableCell>Approval History</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {commands.length ? (
                commands.map((item: any) => (
                  <TableRow key={item.command_id} hover>
                    <TableCell>{formatDisplayValue(item.command_type)}</TableCell>
                    <TableCell>{renderStatusChip(item.status)}</TableCell>
                    <TableCell>{renderStatusChip(item.approval_status)}</TableCell>
                    <TableCell>
                      <Stack spacing={0.4}>
                        <Typography sx={{ fontSize: 12.5, color: "#102A43" }}>
                          {formatDisplayValue(item.source_recommendation_type, "Manual")}
                        </Typography>
                        <Typography sx={{ fontSize: 11.5, lineHeight: 1.45, color: "#627D98" }}>
                          {item.source_recommendation_summary ||
                            item.source_recommendation_id ||
                            "No recommendation source"}
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Typography sx={{ fontSize: 11.5, color: "#627D98" }}>
                        {item.lifecycle_event_id || "-"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Stack spacing={0.4}>
                        {item.approval_history?.length ? (
                          item.approval_history.map((history: any) => (
                            <Typography
                              key={history.approval_id}
                              sx={{ fontSize: 11.5, lineHeight: 1.45, color: "#627D98" }}
                            >
                              {history.decision} by {history.approver_name || history.approver_user_id}
                              {history.comments ? `: ${history.comments}` : ""}
                            </Typography>
                          ))
                        ) : (
                          <Typography sx={{ fontSize: 11.5, color: "#627D98" }}>
                            No decisions yet
                          </Typography>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6}>No linked actions recorded yet.</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Box>
      </DetailSection>

      {mode === "page" ? <Divider /> : null}
    </Stack>
  );
}
