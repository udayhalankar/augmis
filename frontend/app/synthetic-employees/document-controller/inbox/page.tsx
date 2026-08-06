"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { DocumentControllerMergedInboxWorkspace } from "@/app/synthetic-employees/document-controller/_components/DocumentControllerMergedInboxWorkspace";
import { DocumentControllerDocumentLink } from "@/app/synthetic-employees/document-controller/_components/DocumentControllerDocumentLink";
import { buildDocumentControllerExceptionRegistry } from "@/app/synthetic-employees/document-controller/_components/documentControllerExceptions";
import { AdminTableCard } from "@/components/data-display/AdminTableCard";
import { ADMIN_TABLE_CARD_PAGINATION_SX } from "@/components/data-display/AdminTableCard";
import {
  ADMIN_DATA_TABLE_CELL_CONTENT_SX,
  ADMIN_DATA_TABLE_SX,
} from "@/components/data-display/adminTableStyles";
import {
  ADMIN_TOP_MENU_POST_MENU_CONTENT_SX,
  AdminTopMenu,
} from "@/components/data-display/AdminTopMenu";
import { OutletPage } from "@/components/layout/OutletPage";
import {
  getDocumentControllerApprovals,
  getDocumentControllerCommands,
  getDocumentControllerDocumentDetail,
  getDocumentControllerDocuments,
  getDocumentControllerRecommendations,
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

type InboxItem = {
  identity_id: string;
  title?: string;
  document_type_code?: string | null;
  status?: string | null;
  recommendation_count?: number | null;
  command_count?: number | null;
};

type ApprovalItem = {
  approval_id: string;
  approval_subject_type?: string | null;
  decision?: string | null;
  approver_name?: string | null;
  approver_user_id?: string | null;
  comments?: string | null;
};

type RecommendationItem = {
  recommendation_id: string;
  recommendation_type?: string | null;
  status?: string | null;
  confidence_score?: number | null;
  model_name?: string | null;
};

type ReviewRow = {
  id: string;
  subject: string;
  reviewStatus: string;
  source: string;
  decision: string;
  detail: string;
};

type ExceptionRow = {
  id: string;
  type: string;
  subject: string;
  status: string;
  source: string;
  detail: string;
};

type OverdueTaskRow = {
  id: string;
  subject: string;
  overdueCount: number;
  taskState: string;
  lifecycle: string;
  detail: string;
};

type ActiveView =
  | "inbox"
  | "reviews"
  | "exceptions"
  | "overdue-tasks"
  | "approvals"
  | "commands"
  | "registers"
  | "recommendations";

type GenericColumn<RowType> = {
  key: string;
  label: string;
  render: (row: RowType) => React.ReactNode;
  sortValue?: (row: RowType) => string | number;
  searchableValue?: (row: RowType) => string;
  align?: "left" | "center" | "right";
};

type ViewConfig<RowType> = {
  title: string;
  description: string;
  accentLabel: string;
  pageTitle: string;
  pageDescription: string;
  countLabel: string;
  searchPlaceholder: string;
  defaultSortKey: string;
  columns: GenericColumn<RowType>[];
  rows: RowType[];
};

type WorkQueueMenuItem = {
  key: string;
  label: string;
  href?: string;
};

function normalizeLifecycleStage(item: any) {
  return String(item.document_lifecycle_stage || item.status || "REGISTERED").toUpperCase();
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

function normalizeRecordState(item: any) {
  return String(item.record_status || "NON_RECORD").toUpperCase();
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

export default function DocumentControllerInboxPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<ActiveView>("inbox");
  const [searchValue, setSearchValue] = useState("");
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState("title");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [documents, setDocuments] = useState<InboxItem[]>([]);
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [commands, setCommands] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [registerItems, setRegisterItems] = useState<any[]>([]);
  const [documentDetails, setDocumentDetails] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([
      getDocumentControllerDocuments(),
      getDocumentControllerApprovals(),
      getDocumentControllerCommands(),
      getDocumentControllerRecommendations(),
      getMasterDocumentRegister(),
    ])
      .then(
        ([
          documentsResult,
          approvalsResult,
          commandsResult,
          recommendationsResult,
          registerResult,
        ]) => {
          const documentItems = documentsResult?.data?.items || [];
          setDocuments(documentItems);
          setApprovals(approvalsResult?.data?.items || []);
          setCommands(commandsResult?.data?.items || []);
          setRecommendations(recommendationsResult?.data?.items || []);
          setRegisterItems(registerResult?.data?.items || []);

          void Promise.all(
            documentItems.map((item: InboxItem) =>
              getDocumentControllerDocumentDetail(item.identity_id)
                .then((result) => result?.data || null)
                .catch(() => null)
            )
          ).then((details) => {
            setDocumentDetails(details.filter(Boolean));
          });
        }
      )
      .finally(() => setLoading(false));
  }, []);

  const reviewRows = useMemo<ReviewRow[]>(() => {
    const identities = documentDetails.map((item: any) => item.identity).filter(Boolean);
    const rows: ReviewRow[] = [];

    identities.forEach((item: any) => {
      const reviewStatus = String(item.review_status || "").toUpperCase();
      if (!["AWAITING_REVIEW", "IN_REVIEW", "REVIEW_COMPLETED"].includes(reviewStatus)) {
        return;
      }

      rows.push({
        id: `doc-${item.identity_id}`,
        subject: item.title || item.identity_id,
        reviewStatus: reviewStatus.replaceAll("_", " "),
        source: "Document Review State",
        decision: reviewStatus === "REVIEW_COMPLETED" ? "Completed" : "Pending",
        detail: `Document lifecycle is ${normalizeLifecycleStage(item).replaceAll("_", " ")}.`,
      });
    });

    recommendations
      .filter((item: RecommendationItem) => String(item.status || "").toUpperCase() === "NEEDS_REVIEW")
      .forEach((item: RecommendationItem) => {
        rows.push({
          id: `rec-${item.recommendation_id}`,
          subject: item.recommendation_type || item.recommendation_id,
          reviewStatus: "Awaiting Review",
          source: "AI Recommendation",
          decision: "Pending",
          detail: `Recommendation requires reviewer action${item.model_name ? ` from ${item.model_name}` : ""}.`,
        });
      });

    approvals.forEach((item: ApprovalItem) => {
      rows.push({
        id: `apr-${item.approval_id}`,
        subject: item.approval_subject_type || item.approval_id,
        reviewStatus: "Approval Recorded",
        source: "Approval Audit",
        decision: item.decision || "-",
        detail: item.comments || "Approval decision captured without reviewer comments.",
      });
    });

    return rows;
  }, [approvals, documentDetails, recommendations]);

  const exceptionRows = useMemo<ExceptionRow[]>(() => {
    return buildDocumentControllerExceptionRegistry({
      documentDetails,
      commands,
      recommendations,
    }).rows;
  }, [commands, documentDetails, recommendations]);

  const overdueTaskRows = useMemo<OverdueTaskRow[]>(() => {
    return documentDetails
      .map((detail: any) => {
        const identity = detail.identity;
        if (!identity) return null;
        const overdueCount = Number(identity.overdue_workflow_task_count ?? 0);
        if (overdueCount <= 0) return null;

        const workflowTasks = Array.isArray(detail.workflow_tasks) ? detail.workflow_tasks : [];
        const maxDaysOverdue = workflowTasks.reduce(
          (max: number, task: any) => Math.max(max, Number(task.days_overdue ?? 0)),
          0
        );

        return {
          id: `ovd-${identity.identity_id}`,
          subject: identity.title || identity.identity_id,
          overdueCount,
          taskState: normalizeReviewState(identity).replaceAll("_", " "),
          lifecycle: normalizeLifecycleStage(identity).replaceAll("_", " "),
          detail:
            maxDaysOverdue > 0
              ? `${overdueCount} overdue workflow tasks. Maximum delay: ${maxDaysOverdue} days.`
              : `${overdueCount} overdue workflow tasks require intervention.`,
        };
      })
      .filter(Boolean) as OverdueTaskRow[];
  }, [documentDetails]);

  const viewConfigs = useMemo<Record<ActiveView, ViewConfig<any>>>(() => {
    return {
      inbox: {
        title: "Inbox Documents",
        description:
          "Registered document identities staged for review, recommendation, and action follow-up.",
        accentLabel: "Inbox",
        pageTitle: "Document Controller Inbox",
        pageDescription:
          "Logical documents registered through connector ingestion and staged for Symployee governance.",
        countLabel: "documents available",
        searchPlaceholder: "Search inbox",
        defaultSortKey: "title",
        rows: documents,
        columns: [
          {
            key: "title",
            label: "Title",
            render: (row: InboxItem) => (
              <DocumentControllerDocumentLink
                identityId={row.identity_id}
                label={row.title || row.identity_id}
                sx={ADMIN_DATA_TABLE_CELL_CONTENT_SX}
              />
            ),
            sortValue: (row: InboxItem) => String(row.title || row.identity_id).toLowerCase(),
            searchableValue: (row: InboxItem) =>
              [
                row.title,
                row.identity_id,
                row.document_type_code,
                row.status,
                row.recommendation_count,
                row.command_count,
              ]
                .filter(Boolean)
                .join(" "),
          },
          {
            key: "recommendation_count",
            label: "Recommendations",
            render: (row: InboxItem) => row.recommendation_count ?? 0,
            sortValue: (row: InboxItem) => Number(row.recommendation_count ?? 0),
          },
          {
            key: "command_count",
            label: "Actions",
            render: (row: InboxItem) => row.command_count ?? 0,
            sortValue: (row: InboxItem) => Number(row.command_count ?? 0),
          },
        ],
      },
      reviews: {
        title: "Review Register",
        description:
          "Combined review workspace for document review states, pending recommendations, and approval history.",
        accentLabel: "Reviews",
        pageTitle: "Document Controller Reviews",
        pageDescription:
          "Live review workspace for active document review states, pending recommendations, and approval history.",
        countLabel: "review items",
        searchPlaceholder: "Search reviews",
        defaultSortKey: "subject",
        rows: reviewRows,
        columns: [
          {
            key: "subject",
            label: "Subject",
            render: (row: ReviewRow) => row.subject,
            sortValue: (row: ReviewRow) => row.subject.toLowerCase(),
            searchableValue: (row: ReviewRow) =>
              [row.subject, row.reviewStatus, row.source, row.decision, row.detail].join(" "),
          },
          {
            key: "reviewStatus",
            label: "Review Status",
            render: (row: ReviewRow) => row.reviewStatus,
            sortValue: (row: ReviewRow) => row.reviewStatus.toLowerCase(),
          },
          {
            key: "source",
            label: "Source",
            render: (row: ReviewRow) => row.source,
            sortValue: (row: ReviewRow) => row.source.toLowerCase(),
          },
          {
            key: "decision",
            label: "Decision",
            render: (row: ReviewRow) => row.decision,
            sortValue: (row: ReviewRow) => row.decision.toLowerCase(),
          },
          {
            key: "detail",
            label: "Detail",
            render: (row: ReviewRow) => row.detail,
            sortValue: (row: ReviewRow) => row.detail.toLowerCase(),
          },
        ],
      },
      exceptions: {
        title: "Exception Register",
        description:
          "Operational exception register for document-control breaches, failed automation, and pending interventions.",
        accentLabel: "Exceptions",
        pageTitle: "Document Controller Exceptions",
        pageDescription:
          "Operational exception register for document-control breaches, failed automation, and pending interventions.",
        countLabel: "exceptions available",
        searchPlaceholder: "Search exceptions",
        defaultSortKey: "type",
        rows: exceptionRows,
        columns: [
          {
            key: "type",
            label: "Type",
            render: (row: ExceptionRow) => row.type,
            sortValue: (row: ExceptionRow) => row.type.toLowerCase(),
            searchableValue: (row: ExceptionRow) =>
              [row.type, row.subject, row.status, row.source, row.detail].join(" "),
          },
          {
            key: "subject",
            label: "Subject",
            render: (row: ExceptionRow) => row.subject,
            sortValue: (row: ExceptionRow) => row.subject.toLowerCase(),
          },
          {
            key: "status",
            label: "Status",
            render: (row: ExceptionRow) => row.status,
            sortValue: (row: ExceptionRow) => row.status.toLowerCase(),
          },
          {
            key: "source",
            label: "Source",
            render: (row: ExceptionRow) => row.source,
            sortValue: (row: ExceptionRow) => row.source.toLowerCase(),
          },
          {
            key: "detail",
            label: "Detail",
            render: (row: ExceptionRow) => row.detail,
            sortValue: (row: ExceptionRow) => row.detail.toLowerCase(),
          },
        ],
      },
      "overdue-tasks": {
        title: "Overdue Tasks",
        description:
          "Overdue workflow tasks requiring review intervention and recovery action.",
        accentLabel: "Overdue Tasks",
        pageTitle: "Document Controller Overdue Tasks",
        pageDescription:
          "Overdue review, approval, acknowledgement, and action-task follow-up requiring intervention.",
        countLabel: "overdue tasks",
        searchPlaceholder: "Search overdue tasks",
        defaultSortKey: "subject",
        rows: overdueTaskRows,
        columns: [
          {
            key: "subject",
            label: "Subject",
            render: (row: OverdueTaskRow) => row.subject,
            sortValue: (row: OverdueTaskRow) => row.subject.toLowerCase(),
            searchableValue: (row: OverdueTaskRow) =>
              [row.subject, row.taskState, row.lifecycle, row.detail].join(" "),
          },
          {
            key: "overdueCount",
            label: "Overdue Count",
            render: (row: OverdueTaskRow) => row.overdueCount,
            sortValue: (row: OverdueTaskRow) => row.overdueCount,
          },
          {
            key: "taskState",
            label: "Task State",
            render: (row: OverdueTaskRow) => row.taskState,
            sortValue: (row: OverdueTaskRow) => row.taskState.toLowerCase(),
          },
          {
            key: "lifecycle",
            label: "Lifecycle",
            render: (row: OverdueTaskRow) => row.lifecycle,
            sortValue: (row: OverdueTaskRow) => row.lifecycle.toLowerCase(),
          },
          {
            key: "detail",
            label: "Detail",
            render: (row: OverdueTaskRow) => row.detail,
            sortValue: (row: OverdueTaskRow) => row.detail.toLowerCase(),
          },
        ],
      },
      approvals: {
        title: "Approvals Register",
        description:
          "Audit-facing approval history for recommendation and action decisions.",
        accentLabel: "Approvals",
        pageTitle: "Document Controller Approvals",
        pageDescription:
          "Approval decisions, approvers, and comments associated with document-controller workflows.",
        countLabel: "approvals available",
        searchPlaceholder: "Search approvals",
        defaultSortKey: "approval_subject_type",
        rows: approvals,
        columns: [
          {
            key: "approval_subject_type",
            label: "Subject Type",
            render: (row: ApprovalItem) => row.approval_subject_type || "-",
            sortValue: (row: ApprovalItem) =>
              String(row.approval_subject_type || "").toLowerCase(),
            searchableValue: (row: ApprovalItem) =>
              [
                row.approval_subject_type,
                row.decision,
                row.approver_name || row.approver_user_id,
                row.comments,
              ]
                .filter(Boolean)
                .join(" "),
          },
          {
            key: "decision",
            label: "Decision",
            render: (row: ApprovalItem) => row.decision || "-",
            sortValue: (row: ApprovalItem) => String(row.decision || "").toLowerCase(),
          },
          {
            key: "approver",
            label: "Approver",
            render: (row: ApprovalItem) => row.approver_name || row.approver_user_id || "-",
            sortValue: (row: ApprovalItem) =>
              String(row.approver_name || row.approver_user_id || "").toLowerCase(),
          },
          {
            key: "comments",
            label: "Comments",
            render: (row: ApprovalItem) => row.comments || "-",
            sortValue: (row: ApprovalItem) => String(row.comments || "").toLowerCase(),
          },
        ],
      },
      commands: {
        title: "Actions Register",
        description:
          "Connector action queue covering approval, dispatch, acknowledgement, and rollback states.",
        accentLabel: "Actions",
        pageTitle: "Document Controller Actions",
        pageDescription:
          "Operational action queue for connector writeback, execution, and recovery status.",
        countLabel: "actions available",
        searchPlaceholder: "Search actions",
        defaultSortKey: "document_title",
        rows: commands,
        columns: [
          {
            key: "document_title",
            label: "Document",
            render: (row: any) => row.document_title || row.identity_id || "-",
            sortValue: (row: any) =>
              String(row.document_title || row.identity_id || "").toLowerCase(),
            searchableValue: (row: any) =>
              [
                row.document_title,
                row.identity_id,
                row.command_type,
                row.status,
                row.approval_status,
                row.source_recommendation_type,
                row.source_recommendation_summary,
              ]
                .filter(Boolean)
                .join(" "),
          },
          {
            key: "command_type",
            label: "Action Type",
            render: (row: any) => row.command_type || "-",
            sortValue: (row: any) => String(row.command_type || "").toLowerCase(),
          },
          {
            key: "status",
            label: "Status",
            render: (row: any) => row.status || "-",
            sortValue: (row: any) => String(row.status || "").toLowerCase(),
          },
          {
            key: "approval_status",
            label: "Approval",
            render: (row: any) => row.approval_status || "-",
            sortValue: (row: any) => String(row.approval_status || "").toLowerCase(),
          },
          {
            key: "source_recommendation_type",
            label: "Source",
            render: (row: any) => row.source_recommendation_type || "-",
            sortValue: (row: any) =>
              String(row.source_recommendation_type || "").toLowerCase(),
          },
        ],
      },
      registers: {
        title: "Master Document Register",
        description:
          "Expanded register view for document, review, lifecycle, and record-state visibility.",
        accentLabel: "Registers",
        pageTitle: "Document Controller Registers",
        pageDescription:
          "Master-document-register visibility for lifecycle, review, and records governance fields.",
        countLabel: "register rows",
        searchPlaceholder: "Search registers",
        defaultSortKey: "canonical_document_number",
        rows: registerItems,
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
            sortValue: (row: any) =>
              String(row.canonical_document_number || "").toLowerCase(),
          },
          {
            key: "title",
            label: "Title",
            render: (row: any) => row.title || "-",
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
            key: "document_lifecycle_stage",
            label: "Lifecycle",
            render: (row: any) => normalizeLifecycleStage(row),
            sortValue: (row: any) => normalizeLifecycleStage(row),
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
            render: (row: any) => normalizeRecordState(row),
            sortValue: (row: any) => normalizeRecordState(row),
          },
        ],
      },
      recommendations: {
        title: "Recommendations Queue",
        description:
          "AI and rule-driven recommendations awaiting review, approval, rejection, or follow-up.",
        accentLabel: "Recommendations",
        pageTitle: "Document Controller Recommendations",
        pageDescription:
          "Recommendation queue showing type, status, confidence, and source-model context.",
        countLabel: "recommendations available",
        searchPlaceholder: "Search recommendations",
        defaultSortKey: "recommendation_type",
        rows: recommendations,
        columns: [
          {
            key: "recommendation_type",
            label: "Type",
            render: (row: RecommendationItem) => row.recommendation_type || "-",
            sortValue: (row: RecommendationItem) =>
              String(row.recommendation_type || "").toLowerCase(),
            searchableValue: (row: RecommendationItem) =>
              [
                row.recommendation_type,
                row.status,
                row.confidence_score,
                row.model_name,
              ]
                .filter(Boolean)
                .join(" "),
          },
          {
            key: "status",
            label: "Status",
            render: (row: RecommendationItem) => row.status || "-",
            sortValue: (row: RecommendationItem) => String(row.status || "").toLowerCase(),
          },
          {
            key: "confidence_score",
            label: "Confidence",
            render: (row: RecommendationItem) => row.confidence_score ?? "-",
            sortValue: (row: RecommendationItem) => Number(row.confidence_score ?? 0),
          },
          {
            key: "model_name",
            label: "Model",
            render: (row: RecommendationItem) => row.model_name || "-",
            sortValue: (row: RecommendationItem) => String(row.model_name || "").toLowerCase(),
          },
        ],
      },
    };
  }, [
    approvals,
    commands,
    documents,
    exceptionRows,
    overdueTaskRows,
    recommendations,
    registerItems,
    reviewRows,
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
  const visibleRows = sortedRows.slice(
    safePage * rowsPerPage,
    (safePage + 1) * rowsPerPage
  );

  const menuItems: WorkQueueMenuItem[] = [
    {
      key: "connector-commands",
      label: "Inbox",
      href: "/synthetic-employees/document-controller/inbox",
    },
    { key: "registers", label: "Registers" },
    { key: "recommendations", label: "Recommendations" },
  ] as const;

  useEffect(() => {
    const requestedTab = searchParams.get("tab");
    const internalTab = menuItems.find(
      (item) => !item.href && item.key === requestedTab
    );
    if (internalTab && internalTab.key !== activeView) {
      setActiveView(internalTab.key as ActiveView);
    }
    if (!requestedTab && activeView !== "inbox") {
      setActiveView("inbox");
    }
  }, [activeView, menuItems, searchParams]);

  const selectedMenuValue = useMemo(() => {
    const requestedTab = searchParams.get("tab");
    if (requestedTab) {
      const internalTab = menuItems.find((item) => !item.href && item.key === requestedTab);
      if (internalTab) {
        return internalTab.key;
      }
    }
    const matchedMenu = menuItems.find((item) => item.href && item.href === pathname);
    return matchedMenu?.key || activeView;
  }, [activeView, menuItems, pathname, searchParams]);

  return (
    <OutletPage
      title="Work Queue"
      description="Combined operational workspace for inbox review, approvals, actions, registers, recommendations, exceptions, overdue follow-up, and linked action or completion-status drilldowns."
    >
      {loading ? (
        <CircularProgress />
      ) : (
        <Stack spacing={0}>
          <AdminTopMenu
            menuItems={menuItems.map(({ key, label }) => ({ key, label }))}
            value={selectedMenuValue}
            onChange={(value) => {
              const targetMenu = menuItems.find((item) => item.key === value);
              if (targetMenu?.href) {
                router.push(targetMenu.href);
                return;
              }
              const nextView = value as ActiveView;
              setActiveView(nextView);
              router.push(
                nextView === "inbox"
                  ? "/synthetic-employees/document-controller/inbox"
                  : `/synthetic-employees/document-controller/inbox?tab=${encodeURIComponent(nextView)}`
              );
            }}
            fullBleed
            bleedSx={{ mt: -7 }}
            borderColor="divider"
          />
          <Stack spacing={2} sx={ADMIN_TOP_MENU_POST_MENU_CONTENT_SX}>
            {activeView === "inbox" ? (
              <DocumentControllerMergedInboxWorkspace />
            ) : (
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
                <Table size="small" sx={ADMIN_DATA_TABLE_SX}>
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
                                setSortDirection((current) =>
                                  current === "asc" ? "desc" : "asc"
                                );
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
                                sx={ADMIN_DATA_TABLE_CELL_CONTENT_SX}
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
            )}
          </Stack>
        </Stack>
      )}
    </OutletPage>
  );
}
