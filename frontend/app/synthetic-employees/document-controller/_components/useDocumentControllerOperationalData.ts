"use client";

import { useEffect, useState } from "react";

import {
  getArchiveTransfers,
  getDispositionCases,
  getLegalHolds,
  getRecordDeclarations,
} from "@/services/symployeeRecordsService";
import {
  getDocumentControllerApprovals,
  getDocumentControllerCommands,
  getDocumentControllerDocumentDetail,
  getDocumentControllerDocuments,
  getDocumentControllerOverview,
  getDocumentControllerRecommendations,
} from "@/services/symployeeService";
import { getAcknowledgements, getTransmittals } from "@/services/symployeeTransmittalService";
import {
  buildActiveHoldBuckets,
  buildArchiveBuckets,
  buildOpenDispositionBuckets,
  buildRetentionQueue,
  normalize,
} from "../records/_lib/recordsMetrics";

export type OperationalMetricRow = {
  detail?: string;
  href?: string;
  label: string;
  value: number | null;
};

export type OperationalSummaryMetric = {
  label: string;
  value: number;
};

export type OperationalSummaryTile = {
  accentColor: string;
  accentSoft: string;
  items: OperationalMetricRow[];
  key: string;
  note?: string;
  title: string;
};

export type OperationalSection = {
  href: string;
  key: string;
  mode: "live" | "placeholder";
  rows: OperationalMetricRow[];
  summary: OperationalSummaryMetric[];
  title: string;
};

export type DocumentControllerOperationalData = {
  overview: any;
  sections: OperationalSection[];
  summaryTiles: OperationalSummaryTile[];
  topKpis: OperationalMetricRow[];
};

function countRows(items: any[], predicate: (item: any, index: number) => boolean) {
  return items.filter((item, index) => predicate(item, index)).length;
}

function readVitalProfile(item: any) {
  return item?.metadata_json?.vital_profile || {};
}

function summarizeSection(rows: OperationalMetricRow[]): OperationalSummaryMetric[] {
  const scored = rows.filter((row) => typeof row.value === "number").length;
  const nonZero = rows.filter((row) => typeof row.value === "number" && row.value > 0).length;
  const linked = rows.filter((row) => Boolean(row.href)).length;

  return [
    { label: "Items", value: rows.length },
    { label: "Scored", value: scored },
    { label: "Linked", value: linked || nonZero },
  ];
}

const PLACEHOLDER_SECTIONS = [
  {
    key: "handover-closeout",
    title: "Handover and Closeout Status",
    href: "/synthetic-employees/document-controller/handover",
    rows: [
      "Required handover documents",
      "Received",
      "Accepted",
      "Missing",
      "As-built documents pending",
      "Archive transfer pending",
    ],
  },
] as const;

export function useDocumentControllerOperationalData() {
  const [data, setData] = useState<DocumentControllerOperationalData | null>(null);

  useEffect(() => {
    async function load() {
      const [
        overviewResult,
        documentsResult,
        declarationsResult,
        holdsResult,
        dispositionResult,
        archiveResult,
        recommendationsResult,
        approvalsResult,
        commandsResult,
        transmittalsResult,
        acknowledgementsResult,
      ] = await Promise.all([
        getDocumentControllerOverview(),
        getDocumentControllerDocuments(),
        getRecordDeclarations({ limit: 500 }),
        getLegalHolds({ limit: 200 }),
        getDispositionCases({ limit: 200 }),
        getArchiveTransfers({ limit: 200 }),
        getDocumentControllerRecommendations(),
        getDocumentControllerApprovals(),
        getDocumentControllerCommands(),
        getTransmittals({ limit: 200 }),
        getAcknowledgements({ limit: 200 }),
      ]);

      const overview = overviewResult?.data || {};
      const documentItems = documentsResult?.data?.items || [];
      const details = (
        await Promise.all(
          documentItems.map((item: any) =>
            getDocumentControllerDocumentDetail(item.identity_id)
              .then((result) => result?.data || null)
              .catch(() => null)
          )
        )
      ).filter(Boolean);

      const declarations = declarationsResult?.data?.items || [];
      const identities = details.map((item: any) => item.identity).filter(Boolean);
      const holdBuckets = buildActiveHoldBuckets(holdsResult?.data?.items || []);
      const dispositionBuckets = buildOpenDispositionBuckets(dispositionResult?.data?.items || []);
      const archiveBuckets = buildArchiveBuckets(archiveResult?.data?.items || []);
      const retentionQueue = buildRetentionQueue(declarations);
      const latestDeclarationByIdentity = new Map(
        declarations
          .filter((item: any) => item?.identity_id)
          .map((item: any) => [item.identity_id, item])
      );
      const recordsAwaitingDeclaration = identities.filter(
        (item: any) => item?.identity_id && !latestDeclarationByIdentity.has(item.identity_id)
      ).length;
      const recommendations = recommendationsResult?.data?.items || [];
      const approvals = approvalsResult?.data?.items || [];
      const commands = commandsResult?.data?.items || [];
      const transmittals = transmittalsResult?.data?.items || [];
      const acknowledgements = acknowledgementsResult?.data?.items || [];
      const currentVersions = details.map((item: any) => item.current_version).filter(Boolean);
      const documentNumbers = identities
        .map((item: any) => String(item.canonical_document_number || "").trim())
        .filter(Boolean);
      const duplicateDocumentCount = Array.from(
        documentNumbers.reduce((counts, value) => {
          counts.set(value, (counts.get(value) || 0) + 1);
          return counts;
        }, new Map<string, number>()).values()
      )
        .filter((count) => count > 1)
        .reduce((sum, count) => sum + count, 0);

      const topKpis: OperationalMetricRow[] = [
        {
          label: "Records Awaiting Declaration",
          value: recordsAwaitingDeclaration,
          href: "/synthetic-employees/document-controller/registers",
        },
        {
          label: "Active Records",
          value: countRows(declarations, (item) => normalize(item.record_stage) === "ACTIVE"),
          href: "/synthetic-employees/document-controller/records/active-records",
        },
        {
          label: "Inactive Records",
          value: countRows(declarations, (item) => normalize(item.record_stage) === "INACTIVE"),
          href: "/synthetic-employees/document-controller/records/inactive-records",
        },
        {
          label: "Retention Review Due",
          value: retentionQueue.length,
          href: "/synthetic-employees/document-controller/records/retention-review",
        },
        {
          label: "Legal Holds",
          value: holdBuckets.legalIdentitySet.size,
          href: "/synthetic-employees/document-controller/records/legal-holds",
        },
        {
          label: "Other Holds",
          value: holdBuckets.otherIdentitySet.size,
          href: "/synthetic-employees/document-controller/records/legal-holds",
        },
        {
          label: "Vital Records",
          value: countRows(
            declarations,
            (item) => ["VITAL", "VITAL_UNDER_REVIEW"].includes(normalize(item.vital_status))
          ),
          href: "/synthetic-employees/document-controller/records/vital-records",
        },
        {
          label: "Disposition Pending",
          value: dispositionBuckets.identitySet.size,
          href: "/synthetic-employees/document-controller/records/disposition",
        },
        {
          label: "Archive Transfer Pending",
          value: archiveBuckets.pending.length,
          href: "/synthetic-employees/document-controller/records/archive",
        },
      ];

      const sections: OperationalSection[] = [
        (() => {
          const rows: OperationalMetricRow[] = [
            { label: "Registered", value: countRows(identities, (item) => normalize(item.document_lifecycle_stage, item.status) === "REGISTERED") },
            { label: "Under Review", value: countRows(identities, (item) => normalize(item.document_lifecycle_stage, item.status) === "UNDER_REVIEW") },
            { label: "Approved", value: countRows(identities, (item) => normalize(item.document_lifecycle_stage, item.status) === "APPROVED") },
            { label: "Issued", value: countRows(identities, (item) => normalize(item.document_lifecycle_stage, item.status) === "ISSUED") },
            { label: "Active", value: countRows(identities, (item) => normalize(item.document_lifecycle_stage, item.status) === "ACTIVE") },
            { label: "Superseded", value: countRows(identities, (item) => normalize(item.document_lifecycle_stage, item.status) === "SUPERSEDED") },
            { label: "Inactive", value: countRows(identities, (item) => normalize(item.document_lifecycle_stage, item.status) === "INACTIVE") },
            { label: "Archived", value: countRows(identities, (item) => normalize(item.document_lifecycle_stage, item.status) === "ARCHIVED") },
          ];
          return {
          key: "document-lifecycle",
          title: "Document Lifecycle Overview",
          href: "/synthetic-employees/document-controller/documents",
          mode: "live",
            rows,
            summary: summarizeSection(rows),
          };
        })(),
        (() => {
          const rows: OperationalMetricRow[] = [
            {
              label: "Record Candidate",
              value: countRows(declarations, (item) => normalize(item.record_status) === "RECORD_CANDIDATE"),
              href: "/synthetic-employees/document-controller/records",
            },
            {
              label: "Active Records",
              value: countRows(declarations, (item) => normalize(item.record_stage) === "ACTIVE"),
              href: "/synthetic-employees/document-controller/records/active-records",
            },
            {
              label: "Inactive Records",
              value: countRows(declarations, (item) => normalize(item.record_stage) === "INACTIVE"),
              href: "/synthetic-employees/document-controller/records/inactive-records",
            },
            {
              label: "Vital Candidates",
              value: countRows(declarations, (item) => normalize(item.vital_status) === "VITAL_CANDIDATE"),
              href: "/synthetic-employees/document-controller/records/vital-records",
            },
            {
              label: "Vital Under Review",
              value: countRows(declarations, (item) => normalize(item.vital_status) === "VITAL_UNDER_REVIEW"),
              href: "/synthetic-employees/document-controller/records/vital-records",
            },
            {
              label: "Under Legal Hold",
              value: holdBuckets.legalIdentitySet.size,
              href: "/synthetic-employees/document-controller/records/legal-holds",
            },
            {
              label: "Other Holds",
              value: holdBuckets.otherIdentitySet.size,
              href: "/synthetic-employees/document-controller/records/legal-holds",
            },
            {
              label: "Disposition Pending",
              value: dispositionBuckets.identitySet.size,
              href: "/synthetic-employees/document-controller/records/disposition",
            },
            {
              label: "Archived",
              value: countRows(declarations, (item) => normalize(item.record_stage) === "ARCHIVED"),
              href: "/synthetic-employees/document-controller/records/archive",
            },
          ];
          return {
          key: "records-posture",
          title: "Records Management Posture",
          href: "/synthetic-employees/document-controller/records",
          mode: "live",
            rows,
            summary: summarizeSection(rows),
          };
        })(),
        (() => {
          const rows: OperationalMetricRow[] = [
            { label: "Overdue reviews", value: overview.overdue_tasks ?? 0 },
            {
              label: "Missing mandatory metadata",
              value: countRows(
                identities,
                (item) => !item.title || !item.canonical_document_number || !item.originator_code
              ),
            },
            {
              label: "Documents without document numbers",
              value: countRows(identities, (item) => !item.canonical_document_number),
            },
            { label: "Duplicate document numbers", value: duplicateDocumentCount },
            {
              label: "Documents issued with superseded revisions",
              value: countRows(
                identities,
                (item, index) =>
                  normalize(item.document_lifecycle_stage, item.status) === "ISSUED" &&
                  normalize(currentVersions[index]?.revision_status) === "SUPERSEDED"
              ),
            },
            {
              label: "Failed connector actions",
              value: countRows(commands, (item) => normalize(item.status) === "FAILED"),
            },
            {
              label: "Records due for retention review",
              value: countRows(
                declarations,
                (item) =>
                  ["DISPOSITION_PENDING", "PENDING_REVIEW"].includes(
                    normalize(item.retention_status, item.disposition_status)
                  )
              ),
              href: "/synthetic-employees/document-controller/records/retention-review",
            },
            {
              label: "Legal-hold conflicts",
              value: countRows(declarations, (item) => {
                const identityId = item.identity_id;
                return (
                  holdBuckets.legalIdentitySet.has(identityId) &&
                  dispositionBuckets.identitySet.has(identityId)
                );
              }),
              href: "/synthetic-employees/document-controller/records/legal-holds",
            },
            {
              label: "Vital reviews due",
              value: countRows(declarations, (item) => {
                const dueAt = readVitalProfile(item).review_due_at;
                return Boolean(
                  dueAt &&
                    ["VITAL", "VITAL_UNDER_REVIEW"].includes(normalize(item.vital_status)) &&
                    new Date(dueAt).getTime() <= Date.now()
                );
              }),
              href: "/synthetic-employees/document-controller/records/vital-records",
            },
          ];
          return {
          key: "attention-required",
          title: "Attention Required",
          href: "/synthetic-employees/document-controller/inbox?tab=exceptions",
          mode: "live",
            rows,
            summary: summarizeSection(rows),
          };
        })(),
        (() => {
          const rows: OperationalMetricRow[] = [
            {
              label: "Recommendations awaiting review",
              value: countRows(recommendations, (item) => normalize(item.status) === "NEEDS_REVIEW"),
            },
            {
              label: "Reviews in progress",
              value: countRows(identities, (item) =>
                ["AWAITING_REVIEW", "IN_REVIEW"].includes(normalize(item.review_status))
              ),
            },
            {
              label: "Reviews overdue",
              value: overview.overdue_tasks ?? 0,
            },
            {
              label: "Pending action approvals",
              value: countRows(commands, (item) => normalize(item.status) === "PENDING_APPROVAL"),
            },
            {
              label: "Approvals recorded",
              value: approvals.length,
            },
            {
              label: "Approved with comments",
              value: countRows(
                approvals,
                (item) => normalize(item.decision) === "APPROVED" && Boolean(item.comments)
              ),
            },
          ];
          return {
          key: "review-health",
          title: "Review and Approval Health",
          href: "/synthetic-employees/document-controller/inbox?tab=reviews",
          mode: "live",
            rows,
            summary: summarizeSection(rows),
          };
        })(),
        (() => {
          const rows: OperationalMetricRow[] = [
            {
              label: "Outgoing transmittals prepared",
              value: countRows(transmittals, (item) => normalize(item.direction) === "OUTGOING"),
            },
            {
              label: "Pending release",
              value: countRows(transmittals, (item) => normalize(item.transmittal_status) === "DRAFT"),
            },
            {
              label: "Awaiting acknowledgement",
              value: countRows(
                acknowledgements,
                (item) => ["PENDING", "REQUESTED"].includes(normalize(item.status))
              ),
            },
            {
              label: "Response required",
              value: countRows(transmittals, (item) => Boolean(item.response_required)),
            },
            {
              label: "Responses overdue",
              value: countRows(
                acknowledgements,
                (item) => normalize(item.response_status) === "OVERDUE"
              ),
            },
            {
              label: "Incoming transmittals",
              value: countRows(transmittals, (item) => normalize(item.direction) === "INCOMING"),
            },
            {
              label: "Archive transfers open",
              value: archiveBuckets.items.length,
              href: "/synthetic-employees/document-controller/records/archive",
            },
          ];
          return {
          key: "transmittal-control",
          title: "Transmittal Control",
          href: "/synthetic-employees/document-controller/communications",
          mode: "live",
            rows,
            summary: summarizeSection(rows),
          };
        })(),
        (() => {
          const rows: OperationalMetricRow[] = (overview.reviewer_workload || []).length
            ? (overview.reviewer_workload || []).map((row: any) => ({
                label: row.assigned_user_name || row.assigned_user_id || "Unassigned",
                detail: `${row.assigned_role_code || "-"} | warnings ${row.warning_tasks ?? 0} | overdue ${row.overdue_tasks ?? 0}`,
                value: row.pending_tasks ?? 0,
              }))
            : [{ label: "No workload data", value: null }];
          return {
            key: "reviewer-workload",
            title: "Reviewer Workload",
            href: "/synthetic-employees/document-controller/inbox?tab=reviews",
            mode: "live",
            rows,
            summary: summarizeSection(rows),
          };
        })(),
        (() => {
          const rows: OperationalMetricRow[] = [
            ["Missing document numbers", overview.analytics?.compliance?.documents_missing_document_number],
            ["Missing project codes", overview.analytics?.compliance?.documents_missing_project_code],
            ["Missing originators", overview.analytics?.compliance?.documents_missing_originator_code],
            ["No current version", overview.analytics?.compliance?.documents_without_current_version],
            ["Overdue tasks", overview.analytics?.compliance?.overdue_tasks],
            ["Escalated tasks", overview.analytics?.compliance?.escalated_tasks],
          ].map(([label, value]) => ({
            label: String(label),
            value: typeof value === "number" ? value : 0,
          }));
          return {
            key: "compliance-posture",
            title: "Compliance Posture",
            href: "/synthetic-employees/document-controller/inbox?tab=exceptions",
            mode: "live",
            rows,
            summary: summarizeSection(rows),
          };
        })(),
        ...PLACEHOLDER_SECTIONS.map((section) => ({
          key: section.key,
          title: section.title,
          href: section.href,
          mode: "placeholder" as const,
          rows: section.rows.map((label) => ({ label, value: null })),
          summary: summarizeSection(section.rows.map((label) => ({ label, value: null }))),
        })),
      ];

      const summaryTiles: OperationalSummaryTile[] = [
        {
          key: "document-operations",
          title: "Document Operations",
          accentColor: "#16a34a",
          accentSoft: "#f0fdf4",
          note: "Core document throughput",
          items: [
            { label: "Total Documents", value: overview.total_documents ?? 0 },
            { label: "SLA Warnings", value: overview.warning_tasks ?? 0 },
            {
              label: "Attention Required",
              value: overview.analytics?.register?.documents_requiring_attention ?? 0,
            },
          ],
        },
        {
          key: "review-metrics",
          title: "Review Metrics",
          accentColor: "#7c3aed",
          accentSoft: "#f5f3ff",
          note: "Recommendation and review load",
          items: [
            { label: "Pending Recommendations", value: overview.pending_recommendations ?? 0 },
            {
              label: "Avg Open Review Days",
              value: overview.analytics?.review?.average_open_review_age_days ?? 0,
            },
          ],
        },
        {
          key: "command-and-approval",
          title: "Action & Approval",
          accentColor: "#2563eb",
          accentSoft: "#eff6ff",
          note: "Execution and approval status",
          items: [
            {
              label: "Failed Actions",
              value: overview.analytics?.commands?.failed_commands ?? 0,
            },
            { label: "Pending Actions", value: overview.pending_commands ?? 0 },
            { label: "Approved Items", value: overview.approved_items ?? 0 },
          ],
        },
        {
          key: "workflow-risk",
          title: "Workflow Risk",
          accentColor: "#64748b",
          accentSoft: "#f8fafc",
          note: "Open workflow exposure",
          items: [
            { label: "Active Workflows", value: overview.active_workflows ?? 0 },
            { label: "Overdue Tasks", value: overview.overdue_tasks ?? 0 },
            { label: "Escalated Tasks", value: overview.escalated_tasks ?? 0 },
          ],
        },
        {
          key: "records-status",
          title: "Records Status",
          accentColor: "#2563eb",
          accentSoft: "#eff6ff",
          note: "Control center grouped metrics",
          items: topKpis.slice(0, 3),
        },
        {
          key: "retention-and-holds",
          title: "Retention & Holds",
          accentColor: "#7c3aed",
          accentSoft: "#f5f3ff",
          note: "Control center grouped metrics",
          items: topKpis.slice(3, 6),
        },
        {
          key: "vital-and-disposition",
          title: "Vital & Disposition",
          accentColor: "#0f766e",
          accentSoft: "#ecfeff",
          note: "Control center grouped metrics",
          items: topKpis.slice(6, 9),
        },
      ];

      setData({ overview, sections, summaryTiles, topKpis });
    }

    void load();
  }, []);

  return data;
}
