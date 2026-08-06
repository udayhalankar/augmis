"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert } from "@mui/material";

import { RecordsWorkspace, type RecordsColumn, type RecordsMetricCard } from "../_components/RecordsWorkspace";
import {
  buildOpenDispositionBuckets,
  buildRetentionQueue,
  normalize,
} from "../_lib/recordsMetrics";
import {
  getDispositionCases,
  getLegalHolds,
  getRecordDeclarations,
} from "@/services/symployeeRecordsService";

function readRetentionAutomation(item: any) {
  return item?.metadata_json?.retention_automation || {};
}

type RetentionRow = {
  declarationId: string;
  identityId: string;
  category: string;
  reviewState: string;
  retentionStatus: string;
  reviewDue: string;
  eligibility: string;
  schedule: string;
  owner: string;
  declaredAt: string;
};

export default function RetentionReviewPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<RetentionRow[]>([]);
  const [metrics, setMetrics] = useState<RecordsMetricCard[]>([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [declarationsResult, holdsResult, dispositionResult] = await Promise.all([
          getRecordDeclarations({ limit: 500 }),
          getLegalHolds({ limit: 500 }),
          getDispositionCases({ limit: 500 }),
        ]);

        const declarations = buildRetentionQueue(declarationsResult?.data?.items || []);
        const activeHolds = new Set<string>(
          (holdsResult?.data?.items || [])
            .filter((item: any) => normalize(item.hold_status) === "ACTIVE")
            .map((item: any) => item.identity_id)
            .filter((value: any): value is string => Boolean(value))
        );
        const openDispositions = buildOpenDispositionBuckets(
          dispositionResult?.data?.items || []
        ).identitySet;

        const mappedRows = declarations.map((item: any) => {
          const hasHold = activeHolds.has(item.identity_id);
          const hasDisposition = openDispositions.has(item.identity_id);
          const retentionStatus = normalize(item.retention_status);
          const automation = readRetentionAutomation(item);

          let reviewState = "Pending Review";
          if (hasHold) reviewState = "Blocked by Legal Hold";
          else if (hasDisposition) reviewState = "Disposition In Progress";
          else if (retentionStatus === "ARCHIVED") reviewState = "Transferred to Archive";
          else if (retentionStatus === "DISPOSITION_PENDING") reviewState = "Ready for Disposition";

          return {
            declarationId: item.record_declaration_id || "-",
            identityId: item.identity_id || "-",
            category: item.record_category || "-",
            reviewState,
            retentionStatus: item.retention_status || "-",
            reviewDue: automation.review_due_at
              ? new Date(automation.review_due_at).toLocaleDateString()
              : "-",
            eligibility: automation.eligibility_at
              ? new Date(automation.eligibility_at).toLocaleDateString()
              : "-",
            schedule: automation.retention_schedule_code || "-",
            owner: item.owner_user_id || "-",
            declaredAt: item.declared_at ? new Date(item.declared_at).toLocaleString() : "-",
          };
        });

        setRows(mappedRows);
        setMetrics([
          { label: "Retention Queue", value: mappedRows.length },
          { label: "Ready for Review", value: mappedRows.filter((item) => item.reviewState === "Pending Review").length },
          { label: "Blocked by Hold", value: mappedRows.filter((item) => item.reviewState === "Blocked by Legal Hold").length },
          {
            label: "Ready for Disposition",
            value: mappedRows.filter((item) => normalize(item.retentionStatus) === "ELIGIBLE_FOR_DISPOSITION").length,
          },
        ]);
      } catch (loadError: any) {
        setError(loadError?.response?.data?.detail || "Retention review could not be loaded.");
        setRows([]);
        setMetrics([]);
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  const columns = useMemo<RecordsColumn<RetentionRow>[]>(
    () => [
      {
        key: "identityId",
        label: "Identity",
        render: (row) => row.identityId,
        sortValue: (row) => row.identityId.toLowerCase(),
        searchableValue: (row) =>
          [
            row.declarationId,
            row.identityId,
            row.category,
            row.reviewState,
            row.retentionStatus,
            row.reviewDue,
            row.eligibility,
            row.schedule,
            row.owner,
            row.declaredAt,
          ].join(" "),
      },
      { key: "category", label: "Category", render: (row) => row.category, sortValue: (row) => row.category.toLowerCase() },
      { key: "reviewState", label: "Review State", render: (row) => row.reviewState, sortValue: (row) => row.reviewState.toLowerCase() },
      { key: "retentionStatus", label: "Retention Status", render: (row) => row.retentionStatus, sortValue: (row) => row.retentionStatus.toLowerCase() },
      { key: "reviewDue", label: "Review Due", render: (row) => row.reviewDue, sortValue: (row) => row.reviewDue.toLowerCase() },
      { key: "eligibility", label: "Eligibility", render: (row) => row.eligibility, sortValue: (row) => row.eligibility.toLowerCase() },
      { key: "schedule", label: "Schedule", render: (row) => row.schedule, sortValue: (row) => row.schedule.toLowerCase() },
      { key: "owner", label: "Owner", render: (row) => row.owner, sortValue: (row) => row.owner.toLowerCase() },
      { key: "declaredAt", label: "Declared", render: (row) => row.declaredAt, sortValue: (row) => row.declaredAt.toLowerCase() },
    ],
    []
  );

  return (
    <RecordsWorkspace
      activeMenu="retention-review"
      pageTitle="Retention Review"
      pageDescription="Retention posture for declared records, including legal-hold impact and disposition readiness."
      cardTitle="Retention Review Queue"
      cardDescription="Retention-driven review posture across review due dates, eligibility timing, and hold or disposition blockers."
      accentLabel="Retention Review"
      countLabel="retention items"
      searchPlaceholder="Search retention queue"
      metrics={metrics}
      rows={rows}
      columns={columns}
      emptyMessage="No declared records are available for review."
      loading={loading}
      error={error ? <Alert severity="error">{error}</Alert> : undefined}
    />
  );
}
