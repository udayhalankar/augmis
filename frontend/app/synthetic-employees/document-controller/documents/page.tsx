"use client";

import { useEffect, useMemo, useState } from "react";

import { DocumentControllerDocumentLink } from "@/app/synthetic-employees/document-controller/_components/DocumentControllerDocumentLink";
import { AdminStatusCardStrip } from "@/components/data-display/AdminStatusCardStrip";
import { AdminTableCard } from "@/components/data-display/AdminTableCard";
import { ADMIN_TABLE_CARD_PAGINATION_SX } from "@/components/data-display/AdminTableCard";
import {
  ADMIN_TOP_MENU_POST_MENU_CONTENT_SX,
  AdminTopMenu,
} from "@/components/data-display/AdminTopMenu";
import { OutletPage } from "@/components/layout/OutletPage";
import {
  getDocumentControllerDocumentDetail,
  getDocumentControllerDocuments,
  getMasterDocumentRegister,
} from "@/services/symployeeService";
import {
  Box,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  TextField,
  Typography,
} from "@mui/material";

type ActiveView =
  | "registers"
  | "deliverables"
  | "revision-control"
  | "document-relationships"
  | "lifecycle-history"
  | "dossiers"
  | "as-built-register";

type GenericColumn<RowType> = {
  key: string;
  label: string;
  render: (row: RowType) => React.ReactNode;
  sortValue?: (row: RowType) => string | number;
  searchableValue?: (row: RowType) => string;
  align?: "left" | "center" | "right";
};

type MetricCard = {
  label: string;
  value: number;
};

type ViewConfig<RowType> = {
  title: string;
  description: string;
  accentLabel: string;
  countLabel: string;
  searchPlaceholder: string;
  defaultSortKey: string;
  columns: GenericColumn<RowType>[];
  rows: RowType[];
  metrics: MetricCard[];
};

type RegisterRow = any;

type DeliverableRow = {
  identityId: string;
  documentNumber: string;
  title: string;
  type: string;
  review: string;
  overdue: number;
  lifecycle: string;
};

type RevisionRow = {
  id: string;
  identityId: string;
  title: string;
  version: string;
  revision: string;
  revisionStatus: string;
  issueStatus: string;
  currentRevision: string;
};

type RelationshipRow = {
  identityId: string;
  title: string;
  sourceObjects: number;
  recommendations: number;
  commands: number;
  workflows: number;
  linkedContext: string;
};

type LifecycleRow = {
  identityId: string;
  title: string;
  lifecycle: string;
  review: string;
  record: string;
  retention: string;
  disposition: string;
};

type DossierRow = {
  identityId: string;
  documentNumber: string;
  title: string;
  type: string;
  revision: string;
  lifecycle: string;
  review: string;
  record: string;
};

type AsBuiltRow = {
  identityId: string;
  documentNumber: string;
  title: string;
  type: string;
  revision: string;
  issueStatus: string;
  currentFlag: string;
  lifecycle: string;
};

const TABLE_SX = {
  tableLayout: "fixed",
  "& .MuiTableCell-root": {
    px: 2,
    py: 0.75,
    borderColor: "#D8E1EE",
    verticalAlign: "middle",
  },
  "& .MuiTableHead-root .MuiTableCell-root": {
    py: 0.7,
    fontWeight: 600,
    color: "#243B53",
    whiteSpace: "nowrap",
  },
  "& .MuiTableBody-root .MuiTableRow-root": {
    height: 36,
  },
} as const;

const CELL_CONTENT_SX = {
  display: "block",
  width: "100%",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
  lineHeight: 1.35,
} as const;

function normalizeValue(value?: string | null, fallback = "-") {
  return String(value || fallback);
}

function normalizeStage(value?: string | null, fallback = "REGISTERED") {
  return String(value || fallback).toUpperCase();
}

function normalizeReviewState(item: any) {
  if (item.review_status) {
    return String(item.review_status).toUpperCase();
  }
  if ((item.overdue_workflow_task_count ?? 0) > 0) {
    return "REVIEW_OVERDUE";
  }
  if ((item.pending_recommendation_count ?? 0) > 0 || (item.open_workflow_task_count ?? 0) > 0) {
    return "IN_REVIEW";
  }
  return "REVIEW_COMPLETED";
}

function resolveCellTitle<RowType>(column: GenericColumn<RowType>, row: RowType) {
  if (column.searchableValue) {
    return column.searchableValue(row);
  }
  if (column.sortValue) {
    return String(column.sortValue(row));
  }
  const rendered = column.render(row);
  return typeof rendered === "string" || typeof rendered === "number"
    ? String(rendered)
    : undefined;
}

export default function DocumentControllerDocumentsPage() {
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<ActiveView>("registers");
  const [searchValue, setSearchValue] = useState("");
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState("canonical_document_number");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [registerItems, setRegisterItems] = useState<RegisterRow[]>([]);
  const [documentDetails, setDocumentDetails] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([getDocumentControllerDocuments(), getMasterDocumentRegister()])
      .then(async ([documentsResult, registerResult]) => {
        const documentItems = documentsResult?.data?.items || [];
        setRegisterItems(registerResult?.data?.items || []);

        const details = (
          await Promise.all(
            documentItems.map((item: any) =>
              getDocumentControllerDocumentDetail(item.identity_id)
                .then((result) => result?.data || null)
                .catch(() => null)
            )
          )
        ).filter(Boolean);

        setDocumentDetails(details);
      })
      .finally(() => setLoading(false));
  }, []);

  const deliverableRows = useMemo<DeliverableRow[]>(() => {
    return registerItems.map((item: any) => ({
      identityId: item.identity_id,
      documentNumber: item.canonical_document_number || "-",
      title: item.title || item.identity_id,
      type: item.document_type_code || "-",
      review: normalizeReviewState(item),
      overdue: Number(item.overdue_workflow_task_count ?? 0),
      lifecycle: normalizeStage(item.document_lifecycle_stage, item.status),
    }));
  }, [registerItems]);

  const revisionRows = useMemo<RevisionRow[]>(() => {
    return documentDetails.flatMap((detail: any) => {
      const identity = detail.identity;
      const title = identity?.title || identity?.identity_id || "-";
      return (detail.versions || []).map((version: any) => ({
        id: version.version_id,
        identityId: identity?.identity_id || "-",
        title,
        version: version.version_label || version.version_id,
        revision: version.revision_code || "-",
        revisionStatus: normalizeStage(version.revision_status, "UNSET"),
        issueStatus: normalizeStage(version.issue_status, "UNSET"),
        currentRevision: version.is_current_revision ? "Current" : "Historical",
      }));
    });
  }, [documentDetails]);

  const relationshipRows = useMemo<RelationshipRow[]>(() => {
    return documentDetails.map((detail: any) => {
      const identity = detail.identity;
      const sourceObjects = Number((detail.source_objects || []).length);
      const recommendations = Number((detail.recommendations || []).length);
      const commands = Number((detail.commands || []).length);
      const workflows = Number((detail.workflows || []).length);
      return {
        identityId: identity?.identity_id || "-",
        title: identity?.title || identity?.identity_id || "-",
        sourceObjects,
        recommendations,
        commands,
        workflows,
        linkedContext:
          sourceObjects || recommendations || commands || workflows
            ? "Linked operational context available"
            : "No explicit relationships recorded yet",
      };
    });
  }, [documentDetails]);

  const lifecycleRows = useMemo<LifecycleRow[]>(() => {
    return documentDetails.map((detail: any) => {
      const identity = detail.identity;
      return {
        identityId: identity?.identity_id || "-",
        title: identity?.title || identity?.identity_id || "-",
        lifecycle: normalizeStage(identity?.document_lifecycle_stage, identity?.status),
        review: normalizeStage(identity?.review_status, "UNSET"),
        record: normalizeStage(identity?.record_status, "NON_RECORD"),
        retention: normalizeStage(identity?.retention_status, "UNSET"),
        disposition: normalizeStage(identity?.disposition_status, "UNSET"),
      };
    });
  }, [documentDetails]);

  const dossierRows = useMemo<DossierRow[]>(() => {
    return registerItems.map((item: any) => ({
      identityId: item.identity_id,
      documentNumber: item.canonical_document_number || "-",
      title: item.title || item.identity_id,
      type: item.document_type_code || "-",
      revision: item.current_revision_code || item.current_version_label || "-",
      lifecycle: normalizeStage(item.document_lifecycle_stage, item.status),
      review: normalizeReviewState(item),
      record: normalizeStage(item.record_status, "NON_RECORD"),
    }));
  }, [registerItems]);

  const asBuiltRows = useMemo<AsBuiltRow[]>(() => {
    const detailMap = new Map(
      documentDetails.map((detail: any) => [detail.identity?.identity_id, detail] as const)
    );

    return registerItems.map((item: any) => {
      const detail = detailMap.get(item.identity_id);
      const currentVersion = (detail?.versions || []).find((version: any) => version.is_current_revision);
      return {
        identityId: item.identity_id,
        documentNumber: item.canonical_document_number || "-",
        title: item.title || item.identity_id,
        type: item.document_type_code || "-",
        revision:
          currentVersion?.revision_code ||
          item.current_revision_code ||
          item.current_version_label ||
          "-",
        issueStatus: normalizeStage(currentVersion?.issue_status, "UNSET"),
        currentFlag: currentVersion?.is_current_revision ? "Current" : "Historical",
        lifecycle: normalizeStage(item.document_lifecycle_stage, item.status),
      };
    });
  }, [documentDetails, registerItems]);

  const viewConfigs = useMemo<Record<ActiveView, ViewConfig<any>>>(() => {
    const registerSummary = {
      documents: registerItems.length,
      repositories: new Set(registerItems.map((item: any) => item.repository_name).filter(Boolean)).size,
      metadataGaps: registerItems.filter((item: any) => (item.metadata_missing_fields || []).length > 0).length,
      overdue: registerItems.filter((item: any) => Number(item.overdue_workflow_task_count ?? 0) > 0).length,
    };

    const deliverableSummary = {
      total: deliverableRows.length,
      inReview: deliverableRows.filter((item) => item.review === "IN_REVIEW").length,
      overdue: deliverableRows.filter((item) => item.overdue > 0).length,
      registered: deliverableRows.filter((item) => item.lifecycle === "REGISTERED").length,
    };

    const revisionSummary = {
      total: revisionRows.length,
      current: revisionRows.filter((item) => item.currentRevision === "Current").length,
      superseded: revisionRows.filter((item) => item.revisionStatus === "SUPERSEDED").length,
      issued: revisionRows.filter((item) => item.issueStatus === "ISSUED").length,
    };

    const relationshipSummary = {
      total: relationshipRows.length,
      linked: relationshipRows.filter(
        (item) => item.sourceObjects + item.recommendations + item.commands + item.workflows > 0
      ).length,
      workflowLinked: relationshipRows.filter((item) => item.workflows > 0).length,
      commandLinked: relationshipRows.filter((item) => item.commands > 0).length,
    };

    const lifecycleSummary = {
      total: lifecycleRows.length,
      active: lifecycleRows.filter((item) => item.lifecycle === "ACTIVE").length,
      review: lifecycleRows.filter((item) => item.review === "IN_REVIEW").length,
      records: lifecycleRows.filter((item) => item.record !== "NON_RECORD").length,
    };

    const dossierSummary = {
      total: dossierRows.length,
      active: dossierRows.filter((item) => item.lifecycle === "ACTIVE").length,
      inReview: dossierRows.filter((item) => item.review === "IN_REVIEW").length,
      records: dossierRows.filter((item) => item.record !== "NON_RECORD").length,
    };

    const asBuiltSummary = {
      total: asBuiltRows.length,
      current: asBuiltRows.filter((item) => item.currentFlag === "Current").length,
      issued: asBuiltRows.filter((item) => item.issueStatus === "ISSUED").length,
      active: asBuiltRows.filter((item) => item.lifecycle === "ACTIVE").length,
    };

    return {
      registers: {
        title: "Master Document Register",
        description:
          "Expanded register view for document, review, lifecycle, and records-governance visibility.",
        accentLabel: "Registers",
        countLabel: "register rows",
        searchPlaceholder: "Search registers",
        defaultSortKey: "canonical_document_number",
        rows: registerItems,
        metrics: [
          { label: "Documents", value: registerSummary.documents },
          { label: "Repositories", value: registerSummary.repositories },
          { label: "Metadata Gaps", value: registerSummary.metadataGaps },
          { label: "Overdue", value: registerSummary.overdue },
        ],
        columns: [
          {
            key: "repository_name",
            label: "Repository",
            render: (row: any) => row.repository_name || "-",
            sortValue: (row: any) => String(row.repository_name || "").toLowerCase(),
            searchableValue: (row: any) =>
              [
                row.repository_name,
                row.canonical_document_number,
                row.title,
                row.document_type_code,
                row.project_code,
                row.originator_code,
                row.current_revision_code,
              ]
                .filter(Boolean)
                .join(" "),
          },
          {
            key: "canonical_document_number",
            label: "Document Number",
            render: (row: any) => row.canonical_document_number || "-",
            sortValue: (row: any) => String(row.canonical_document_number || "").toLowerCase(),
          },
          {
            key: "title",
            label: "Title",
            render: (row: any) => (
              <DocumentControllerDocumentLink
                identityId={row.identity_id}
                label={row.title || row.identity_id}
                sx={CELL_CONTENT_SX}
              />
            ),
            sortValue: (row: any) => String(row.title || "").toLowerCase(),
          },
          {
            key: "document_type_code",
            label: "Type",
            render: (row: any) => row.document_type_code || "-",
            sortValue: (row: any) => String(row.document_type_code || "").toLowerCase(),
          },
          {
            key: "current_revision_code",
            label: "Revision",
            render: (row: any) => row.current_revision_code || row.current_version_label || "-",
            sortValue: (row: any) =>
              String(row.current_revision_code || row.current_version_label || "").toLowerCase(),
          },
          {
            key: "review_status",
            label: "Review",
            render: (row: any) => normalizeReviewState(row),
            sortValue: (row: any) => normalizeReviewState(row),
          },
          {
            key: "record_status",
            label: "Record",
            render: (row: any) => normalizeStage(row.record_status, "NON_RECORD"),
            sortValue: (row: any) => normalizeStage(row.record_status, "NON_RECORD"),
          },
        ],
      },
      deliverables: {
        title: "Deliverables Register",
        description:
          "Tracked document deliverables with review readiness, overdue follow-up, and lifecycle visibility.",
        accentLabel: "Deliverables",
        countLabel: "deliverables tracked",
        searchPlaceholder: "Search deliverables",
        defaultSortKey: "documentNumber",
        rows: deliverableRows,
        metrics: [
          { label: "Deliverables", value: deliverableSummary.total },
          { label: "In Review", value: deliverableSummary.inReview },
          { label: "Overdue", value: deliverableSummary.overdue },
          { label: "Registered", value: deliverableSummary.registered },
        ],
        columns: [
          {
            key: "documentNumber",
            label: "Document Number",
            render: (row: DeliverableRow) => row.documentNumber,
            sortValue: (row: DeliverableRow) => row.documentNumber.toLowerCase(),
            searchableValue: (row: DeliverableRow) =>
              [row.documentNumber, row.title, row.type, row.review, row.lifecycle].join(" "),
          },
          {
            key: "title",
            label: "Title",
            render: (row: DeliverableRow) => row.title,
            sortValue: (row: DeliverableRow) => row.title.toLowerCase(),
          },
          {
            key: "type",
            label: "Type",
            render: (row: DeliverableRow) => row.type,
            sortValue: (row: DeliverableRow) => row.type.toLowerCase(),
          },
          {
            key: "review",
            label: "Review State",
            render: (row: DeliverableRow) => row.review,
            sortValue: (row: DeliverableRow) => row.review.toLowerCase(),
          },
          {
            key: "overdue",
            label: "Overdue Tasks",
            render: (row: DeliverableRow) => row.overdue,
            sortValue: (row: DeliverableRow) => row.overdue,
          },
          {
            key: "lifecycle",
            label: "Lifecycle",
            render: (row: DeliverableRow) => row.lifecycle,
            sortValue: (row: DeliverableRow) => row.lifecycle.toLowerCase(),
          },
        ],
      },
      "revision-control": {
        title: "Revision Control",
        description:
          "Revision sequence visibility across current and historical versions, issue states, and supersession control.",
        accentLabel: "Revision Control",
        countLabel: "revision rows",
        searchPlaceholder: "Search revisions",
        defaultSortKey: "title",
        rows: revisionRows,
        metrics: [
          { label: "Versions", value: revisionSummary.total },
          { label: "Current", value: revisionSummary.current },
          { label: "Superseded", value: revisionSummary.superseded },
          { label: "Issued", value: revisionSummary.issued },
        ],
        columns: [
          {
            key: "title",
            label: "Document",
            render: (row: RevisionRow) => row.title,
            sortValue: (row: RevisionRow) => row.title.toLowerCase(),
            searchableValue: (row: RevisionRow) =>
              [
                row.title,
                row.identityId,
                row.version,
                row.revision,
                row.revisionStatus,
                row.issueStatus,
                row.currentRevision,
              ].join(" "),
          },
          {
            key: "version",
            label: "Version",
            render: (row: RevisionRow) => row.version,
            sortValue: (row: RevisionRow) => row.version.toLowerCase(),
          },
          {
            key: "revision",
            label: "Revision",
            render: (row: RevisionRow) => row.revision,
            sortValue: (row: RevisionRow) => row.revision.toLowerCase(),
          },
          {
            key: "revisionStatus",
            label: "Revision State",
            render: (row: RevisionRow) => row.revisionStatus,
            sortValue: (row: RevisionRow) => row.revisionStatus.toLowerCase(),
          },
          {
            key: "issueStatus",
            label: "Issue State",
            render: (row: RevisionRow) => row.issueStatus,
            sortValue: (row: RevisionRow) => row.issueStatus.toLowerCase(),
          },
          {
            key: "currentRevision",
            label: "Current Flag",
            render: (row: RevisionRow) => row.currentRevision,
            sortValue: (row: RevisionRow) => row.currentRevision.toLowerCase(),
          },
        ],
      },
      "document-relationships": {
        title: "Document Relationships",
        description:
          "Operational linkage surface across source objects, workflows, recommendations, and action context.",
        accentLabel: "Relationships",
        countLabel: "documents assessed",
        searchPlaceholder: "Search relationships",
        defaultSortKey: "title",
        rows: relationshipRows,
        metrics: [
          { label: "Documents", value: relationshipSummary.total },
          { label: "Linked Context", value: relationshipSummary.linked },
          { label: "Workflow Linked", value: relationshipSummary.workflowLinked },
          { label: "Action Linked", value: relationshipSummary.commandLinked },
        ],
        columns: [
          {
            key: "title",
            label: "Document",
            render: (row: RelationshipRow) => row.title,
            sortValue: (row: RelationshipRow) => row.title.toLowerCase(),
            searchableValue: (row: RelationshipRow) =>
              [
                row.title,
                row.identityId,
                row.linkedContext,
                row.sourceObjects,
                row.recommendations,
                row.commands,
                row.workflows,
              ].join(" "),
          },
          {
            key: "sourceObjects",
            label: "Source Objects",
            render: (row: RelationshipRow) => row.sourceObjects,
            sortValue: (row: RelationshipRow) => row.sourceObjects,
          },
          {
            key: "recommendations",
            label: "Recommendations",
            render: (row: RelationshipRow) => row.recommendations,
            sortValue: (row: RelationshipRow) => row.recommendations,
          },
          {
            key: "commands",
            label: "Actions",
            render: (row: RelationshipRow) => row.commands,
            sortValue: (row: RelationshipRow) => row.commands,
          },
          {
            key: "workflows",
            label: "Workflows",
            render: (row: RelationshipRow) => row.workflows,
            sortValue: (row: RelationshipRow) => row.workflows,
          },
          {
            key: "linkedContext",
            label: "Context",
            render: (row: RelationshipRow) => row.linkedContext,
            sortValue: (row: RelationshipRow) => row.linkedContext.toLowerCase(),
          },
        ],
      },
      "lifecycle-history": {
        title: "Lifecycle History",
        description:
          "Current lifecycle and governance-state snapshot across registered document identities until deeper event history is expanded.",
        accentLabel: "Lifecycle",
        countLabel: "documents tracked",
        searchPlaceholder: "Search lifecycle",
        defaultSortKey: "title",
        rows: lifecycleRows,
        metrics: [
          { label: "Documents", value: lifecycleSummary.total },
          { label: "Active", value: lifecycleSummary.active },
          { label: "In Review", value: lifecycleSummary.review },
          { label: "Records", value: lifecycleSummary.records },
        ],
        columns: [
          {
            key: "title",
            label: "Document",
            render: (row: LifecycleRow) => row.title,
            sortValue: (row: LifecycleRow) => row.title.toLowerCase(),
            searchableValue: (row: LifecycleRow) =>
              [
                row.title,
                row.identityId,
                row.lifecycle,
                row.review,
                row.record,
                row.retention,
                row.disposition,
              ].join(" "),
          },
          {
            key: "lifecycle",
            label: "Lifecycle",
            render: (row: LifecycleRow) => row.lifecycle,
            sortValue: (row: LifecycleRow) => row.lifecycle.toLowerCase(),
          },
          {
            key: "review",
            label: "Review",
            render: (row: LifecycleRow) => row.review,
            sortValue: (row: LifecycleRow) => row.review.toLowerCase(),
          },
          {
            key: "record",
            label: "Record",
            render: (row: LifecycleRow) => row.record,
            sortValue: (row: LifecycleRow) => row.record.toLowerCase(),
          },
          {
            key: "retention",
            label: "Retention",
            render: (row: LifecycleRow) => row.retention,
            sortValue: (row: LifecycleRow) => row.retention.toLowerCase(),
          },
          {
            key: "disposition",
            label: "Disposition",
            render: (row: LifecycleRow) => row.disposition,
            sortValue: (row: LifecycleRow) => row.disposition.toLowerCase(),
          },
        ],
      },
      dossiers: {
        title: "Handover Dossiers",
        description:
          "Combined dossier workspace for package completeness, document readiness, and final handover visibility.",
        accentLabel: "Dossiers",
        countLabel: "dossiers tracked",
        searchPlaceholder: "Search dossiers",
        defaultSortKey: "documentNumber",
        rows: dossierRows,
        metrics: [
          { label: "Dossiers", value: dossierSummary.total },
          { label: "Active", value: dossierSummary.active },
          { label: "In Review", value: dossierSummary.inReview },
          { label: "Records", value: dossierSummary.records },
        ],
        columns: [
          {
            key: "documentNumber",
            label: "Document Number",
            render: (row: DossierRow) => row.documentNumber,
            sortValue: (row: DossierRow) => row.documentNumber.toLowerCase(),
            searchableValue: (row: DossierRow) =>
              [
                row.documentNumber,
                row.title,
                row.type,
                row.revision,
                row.lifecycle,
                row.review,
                row.record,
              ].join(" "),
          },
          {
            key: "title",
            label: "Title",
            render: (row: DossierRow) => row.title,
            sortValue: (row: DossierRow) => row.title.toLowerCase(),
          },
          {
            key: "type",
            label: "Type",
            render: (row: DossierRow) => row.type,
            sortValue: (row: DossierRow) => row.type.toLowerCase(),
          },
          {
            key: "revision",
            label: "Revision",
            render: (row: DossierRow) => row.revision,
            sortValue: (row: DossierRow) => row.revision.toLowerCase(),
          },
          {
            key: "lifecycle",
            label: "Lifecycle",
            render: (row: DossierRow) => row.lifecycle,
            sortValue: (row: DossierRow) => row.lifecycle.toLowerCase(),
          },
          {
            key: "review",
            label: "Review",
            render: (row: DossierRow) => row.review,
            sortValue: (row: DossierRow) => row.review.toLowerCase(),
          },
          {
            key: "record",
            label: "Record",
            render: (row: DossierRow) => row.record,
            sortValue: (row: DossierRow) => row.record.toLowerCase(),
          },
        ],
      },
      "as-built-register": {
        title: "As-Built Register",
        description:
          "Final revision visibility across current issue state, lifecycle readiness, and as-built register tracking.",
        accentLabel: "As-Built",
        countLabel: "as-built rows",
        searchPlaceholder: "Search as-built register",
        defaultSortKey: "documentNumber",
        rows: asBuiltRows,
        metrics: [
          { label: "As-Built Rows", value: asBuiltSummary.total },
          { label: "Current", value: asBuiltSummary.current },
          { label: "Issued", value: asBuiltSummary.issued },
          { label: "Active", value: asBuiltSummary.active },
        ],
        columns: [
          {
            key: "documentNumber",
            label: "Document Number",
            render: (row: AsBuiltRow) => row.documentNumber,
            sortValue: (row: AsBuiltRow) => row.documentNumber.toLowerCase(),
            searchableValue: (row: AsBuiltRow) =>
              [
                row.documentNumber,
                row.title,
                row.type,
                row.revision,
                row.issueStatus,
                row.currentFlag,
                row.lifecycle,
              ].join(" "),
          },
          {
            key: "title",
            label: "Title",
            render: (row: AsBuiltRow) => row.title,
            sortValue: (row: AsBuiltRow) => row.title.toLowerCase(),
          },
          {
            key: "type",
            label: "Type",
            render: (row: AsBuiltRow) => row.type,
            sortValue: (row: AsBuiltRow) => row.type.toLowerCase(),
          },
          {
            key: "revision",
            label: "Revision",
            render: (row: AsBuiltRow) => row.revision,
            sortValue: (row: AsBuiltRow) => row.revision.toLowerCase(),
          },
          {
            key: "issueStatus",
            label: "Issue State",
            render: (row: AsBuiltRow) => row.issueStatus,
            sortValue: (row: AsBuiltRow) => row.issueStatus.toLowerCase(),
          },
          {
            key: "currentFlag",
            label: "Current Flag",
            render: (row: AsBuiltRow) => row.currentFlag,
            sortValue: (row: AsBuiltRow) => row.currentFlag.toLowerCase(),
          },
          {
            key: "lifecycle",
            label: "Lifecycle",
            render: (row: AsBuiltRow) => row.lifecycle,
            sortValue: (row: AsBuiltRow) => row.lifecycle.toLowerCase(),
          },
        ],
      },
    };
  }, [
    asBuiltRows,
    deliverableRows,
    documentDetails,
    dossierRows,
    lifecycleRows,
    registerItems,
    relationshipRows,
    revisionRows,
  ]);

  const activeConfig = viewConfigs[activeView];

  useEffect(() => {
    setSearchValue("");
    setPage(0);
    setSortDirection("asc");
    setSortKey(viewConfigs[activeView].defaultSortKey);
  }, [activeView, viewConfigs]);

  const filteredRows = useMemo(() => {
    const query = searchValue.trim().toLowerCase();
    if (!query) {
      return activeConfig.rows;
    }

    return activeConfig.rows.filter((row) =>
      activeConfig.columns.some((column) =>
        String(
          column.searchableValue
            ? column.searchableValue(row)
            : column.sortValue
              ? column.sortValue(row)
              : column.render(row)
        )
          .toLowerCase()
          .includes(query)
      )
    );
  }, [activeConfig, searchValue]);

  const sortedRows = useMemo(() => {
    const activeColumn = activeConfig.columns.find((column) => column.key === sortKey);
    if (!activeColumn) {
      return filteredRows;
    }

    const resolveValue =
      activeColumn.sortValue || ((row: any) => String(activeColumn.render(row)).toLowerCase());

    return [...filteredRows].sort((left, right) => {
      const leftValue = resolveValue(left);
      const rightValue = resolveValue(right);
      const normalizedLeft =
        typeof leftValue === "number" ? leftValue : String(leftValue).toLowerCase();
      const normalizedRight =
        typeof rightValue === "number" ? rightValue : String(rightValue).toLowerCase();

      if (normalizedLeft < normalizedRight) {
        return sortDirection === "asc" ? -1 : 1;
      }
      if (normalizedLeft > normalizedRight) {
        return sortDirection === "asc" ? 1 : -1;
      }
      return 0;
    });
  }, [activeConfig.columns, filteredRows, sortDirection, sortKey]);

  const rowsPerPage = 10;
  const maxPage = Math.max(0, Math.ceil(sortedRows.length / rowsPerPage) - 1);
  const safePage = page > maxPage ? maxPage : page;
  const visibleRows = sortedRows.slice(safePage * rowsPerPage, (safePage + 1) * rowsPerPage);

  const menuItems = [
    { key: "registers", label: "Document Registers" },
    { key: "deliverables", label: "Deliverables" },
    { key: "revision-control", label: "Revision Control" },
    { key: "document-relationships", label: "Document Relationships" },
    { key: "lifecycle-history", label: "Lifecycle History" },
    { key: "dossiers", label: "Dossiers" },
    { key: "as-built-register", label: "As-Built Register" },
  ] as const;

  return (
    <OutletPage
      title="Documents"
      description="Combined document workbench for registers, deliverables, revision control, relationships, and lifecycle visibility."
    >
      {loading ? (
        <CircularProgress />
      ) : (
        <Stack spacing={0}>
          <AdminTopMenu
            menuItems={menuItems.map(({ key, label }) => ({ key, label }))}
            value={activeView}
            onChange={(value) => setActiveView(value as ActiveView)}
            fullBleed
            bleedSx={{ mt: -7 }}
            borderColor="divider"
          />

          <Stack spacing={2} sx={ADMIN_TOP_MENU_POST_MENU_CONTENT_SX}>
            <AdminStatusCardStrip
              metrics={activeConfig.metrics.map((metric) => ({
                label: metric.label,
                value: metric.value,
              }))}
            />

            <AdminTableCard
              title={activeConfig.title}
              description={activeConfig.description}
              accentLabel={activeConfig.accentLabel}
              summary={`${filteredRows.length} ${activeConfig.countLabel}`}
              headerActions={
                <TextField
                  size="small"
                  placeholder={activeConfig.searchPlaceholder}
                  value={searchValue}
                  onChange={(event) => {
                    setSearchValue(event.target.value);
                    setPage(0);
                  }}
                  sx={{
                    width: { xs: "100%", sm: 320 },
                    bgcolor: "#FFFFFF",
                    borderRadius: "999px",
                    "& .MuiOutlinedInput-root": {
                      borderRadius: "999px",
                    },
                  }}
                />
              }
              bodySx={{ px: 0, pb: 0 }}
              footerEnd={
                <TablePagination
                  component="div"
                  count={sortedRows.length}
                  page={safePage}
                  onPageChange={(_, nextPage) => setPage(nextPage)}
                  rowsPerPage={rowsPerPage}
                  rowsPerPageOptions={[rowsPerPage]}
                  sx={ADMIN_TABLE_CARD_PAGINATION_SX}
                />
              }
            >
              <Table size="small" sx={TABLE_SX}>
                <TableHead>
                  <TableRow>
                    {activeConfig.columns.map((column) => (
                      <TableCell
                        key={column.key}
                        align={column.align}
                        sortDirection={sortKey === column.key ? sortDirection : false}
                      >
                        <TableSortLabel
                          active={sortKey === column.key}
                          direction={sortKey === column.key ? sortDirection : "asc"}
                          onClick={() => {
                            if (sortKey === column.key) {
                              setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
                            } else {
                              setSortKey(column.key);
                              setSortDirection("asc");
                            }
                            setPage(0);
                          }}
                        >
                          {column.label}
                        </TableSortLabel>
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {visibleRows.length ? (
                    visibleRows.map((row, index) => (
                      <TableRow key={`${activeView}-${safePage}-${index}`} hover>
                        {activeConfig.columns.map((column) => (
                          <TableCell key={column.key} align={column.align}>
                            <Box
                              component="span"
                              sx={CELL_CONTENT_SX}
                              title={resolveCellTitle(column, row)}
                            >
                              {column.render(row)}
                            </Box>
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={activeConfig.columns.length}>
                        No rows match the current search.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </AdminTableCard>
          </Stack>
        </Stack>
      )}
    </OutletPage>
  );
}
