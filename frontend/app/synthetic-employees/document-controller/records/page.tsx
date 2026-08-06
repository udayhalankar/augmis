"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert } from "@mui/material";

import { RecordsWorkspace, type RecordsColumn, type RecordsMetricCard } from "./_components/RecordsWorkspace";
import {
  buildActiveHoldBuckets,
  buildArchiveBuckets,
  buildOpenDispositionBuckets,
  buildRetentionQueue,
  normalize,
} from "./_lib/recordsMetrics";
import {
  getArchiveTransfers,
  getDispositionCases,
  getLegalHolds,
  getRecordDeclarations,
} from "@/services/symployeeRecordsService";
import { getDocumentControllerDocuments } from "@/services/symployeeService";

type RecordsOverviewRow = {
  declarationId: string;
  identityId: string;
  recordCategory: string;
  recordStage: string;
  recordStatus: string;
  vitalStatus: string;
  retentionStatus: string;
  dispositionStatus: string;
  owner: string;
};

export default function DocumentControllerRecordsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<RecordsOverviewRow[]>([]);
  const [metrics, setMetrics] = useState<RecordsMetricCard[]>([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [documentsResult, declarationsResult, holdsResult, dispositionResult, archiveResult] =
          await Promise.all([
            getDocumentControllerDocuments(),
            getRecordDeclarations({ limit: 500 }),
            getLegalHolds({ limit: 500 }),
            getDispositionCases({ limit: 500 }),
            getArchiveTransfers({ limit: 500 }),
          ]);

        const documentItems = documentsResult?.data?.items || [];
        const declarations = declarationsResult?.data?.items || [];
        const holdBuckets = buildActiveHoldBuckets(holdsResult?.data?.items || []);
        const dispositionBuckets = buildOpenDispositionBuckets(dispositionResult?.data?.items || []);
        const archiveBuckets = buildArchiveBuckets(archiveResult?.data?.items || []);
        const retentionQueue = buildRetentionQueue(declarations);

        setRows(
          declarations.map((item: any) => ({
            declarationId: item.record_declaration_id || "-",
            identityId: item.identity_id || "-",
            recordCategory: item.record_category || "-",
            recordStage: item.record_stage || "-",
            recordStatus: item.record_status || "-",
            vitalStatus: item.vital_status || "NON_VITAL",
            retentionStatus: item.retention_status || "-",
            dispositionStatus: item.disposition_status || "-",
            owner: item.owner_user_id || "-",
          }))
        );
        setMetrics([
          { label: "Controlled Documents", value: documentItems.length },
          {
            label: "Active Records",
            value: declarations.filter((item: any) => normalize(item.record_stage) === "ACTIVE").length,
          },
          {
            label: "Inactive Records",
            value: declarations.filter((item: any) => normalize(item.record_stage) === "INACTIVE").length,
          },
          { label: "Retention Review Due", value: retentionQueue.length },
          { label: "Legal Holds", value: holdBuckets.legal.length },
          { label: "Other Holds", value: holdBuckets.other.length },
          {
            label: "Vital Records",
            value: declarations.filter((item: any) =>
              ["VITAL", "VITAL_UNDER_REVIEW"].includes(normalize(item.vital_status))
            ).length,
          },
          { label: "Disposition Pending", value: dispositionBuckets.active.length },
          { label: "Archive Transfer Pending", value: archiveBuckets.pending.length },
        ]);
      } catch (loadError: any) {
        setError(loadError?.response?.data?.detail || "Records overview could not be loaded.");
        setRows([]);
        setMetrics([]);
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  const columns = useMemo<RecordsColumn<RecordsOverviewRow>[]>(
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
            row.recordCategory,
            row.recordStage,
            row.recordStatus,
            row.vitalStatus,
            row.retentionStatus,
            row.dispositionStatus,
            row.owner,
          ].join(" "),
      },
      {
        key: "recordCategory",
        label: "Category",
        render: (row) => row.recordCategory,
        sortValue: (row) => row.recordCategory.toLowerCase(),
      },
      {
        key: "recordStage",
        label: "Stage",
        render: (row) => row.recordStage,
        sortValue: (row) => row.recordStage.toLowerCase(),
      },
      {
        key: "recordStatus",
        label: "Record Status",
        render: (row) => row.recordStatus,
        sortValue: (row) => row.recordStatus.toLowerCase(),
      },
      {
        key: "vitalStatus",
        label: "Vital",
        render: (row) => row.vitalStatus,
        sortValue: (row) => row.vitalStatus.toLowerCase(),
      },
      {
        key: "retentionStatus",
        label: "Retention",
        render: (row) => row.retentionStatus,
        sortValue: (row) => row.retentionStatus.toLowerCase(),
      },
      {
        key: "dispositionStatus",
        label: "Disposition",
        render: (row) => row.dispositionStatus,
        sortValue: (row) => row.dispositionStatus.toLowerCase(),
      },
      {
        key: "owner",
        label: "Owner",
        render: (row) => row.owner,
        sortValue: (row) => row.owner.toLowerCase(),
      },
    ],
    []
  );

  return (
    <RecordsWorkspace
      activeMenu="overview"
      pageTitle="Records"
      pageDescription="Dedicated module area for record declaration, retention governance, legal holds, and archival workflow."
      cardTitle="Records Overview"
      cardDescription="Combined record-governance snapshot for declaration, lifecycle, hold, retention, disposition, and archive posture."
      accentLabel="Records"
      countLabel="declared records"
      searchPlaceholder="Search records"
      metrics={metrics}
      rows={rows}
      columns={columns}
      emptyMessage="No declared records are available yet."
      loading={loading}
      error={error ? <Alert severity="error">{error}</Alert> : undefined}
    />
  );
}
