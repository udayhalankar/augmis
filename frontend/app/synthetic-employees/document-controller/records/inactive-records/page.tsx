"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert } from "@mui/material";

import { RecordsWorkspace, type RecordsColumn, type RecordsMetricCard } from "../_components/RecordsWorkspace";
import {
  buildActiveHoldBuckets,
  buildOpenDispositionBuckets,
  normalize,
} from "../_lib/recordsMetrics";
import {
  getDispositionCases,
  getLegalHolds,
  getRecordDeclarations,
} from "@/services/symployeeRecordsService";

type InactiveRow = {
  declarationId: string;
  identityId: string;
  category: string;
  stage: string;
  recordStatus: string;
  inactiveFrom: string;
  inactiveReason: string;
  legalHold: string;
  otherHold: string;
  dispositionOpen: string;
  owner: string;
};

export default function InactiveRecordsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<InactiveRow[]>([]);
  const [metrics, setMetrics] = useState<RecordsMetricCard[]>([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [declarationsResult, holdsResult, dispositionResult] = await Promise.all([
          getRecordDeclarations({ limit: 500, record_stage: "INACTIVE" }),
          getLegalHolds({ limit: 500 }),
          getDispositionCases({ limit: 500 }),
        ]);

        const declarations = declarationsResult?.data?.items || [];
        const holdBuckets = buildActiveHoldBuckets(holdsResult?.data?.items || []);
        const dispositionBuckets = buildOpenDispositionBuckets(dispositionResult?.data?.items || []);

        const mappedRows = declarations.map((item: any) => ({
          declarationId: item.record_declaration_id || "-",
          identityId: item.identity_id || "-",
          category: item.record_category || "-",
          stage: item.record_stage || "-",
          recordStatus: item.record_status || "-",
          inactiveFrom: item.inactive_from ? new Date(item.inactive_from).toLocaleString() : "-",
          inactiveReason: item.inactive_reason_code || "-",
          legalHold: holdBuckets.legalIdentitySet.has(item.identity_id) ? "Yes" : "No",
          otherHold: holdBuckets.otherIdentitySet.has(item.identity_id) ? "Yes" : "No",
          dispositionOpen: dispositionBuckets.identitySet.has(item.identity_id) ? "Yes" : "No",
          owner: item.owner_user_id || "-",
        }));

        setRows(mappedRows);
        setMetrics([
          { label: "Inactive Records", value: mappedRows.length },
          { label: "Archived", value: mappedRows.filter((item: InactiveRow) => normalize(item.recordStatus) === "ARCHIVED").length },
          { label: "Disposition Pending", value: mappedRows.filter((item: InactiveRow) => item.dispositionOpen === "Yes").length },
          { label: "Legal Holds", value: mappedRows.filter((item: InactiveRow) => item.legalHold === "Yes").length },
          { label: "Other Holds", value: mappedRows.filter((item: InactiveRow) => item.otherHold === "Yes").length },
        ]);
      } catch (loadError: any) {
        setError(loadError?.response?.data?.detail || "Inactive records could not be loaded.");
        setRows([]);
        setMetrics([]);
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  const columns = useMemo<RecordsColumn<InactiveRow>[]>(
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
            row.stage,
            row.recordStatus,
            row.inactiveFrom,
            row.inactiveReason,
            row.legalHold,
            row.otherHold,
            row.dispositionOpen,
            row.owner,
          ].join(" "),
      },
      { key: "category", label: "Category", render: (row) => row.category, sortValue: (row) => row.category.toLowerCase() },
      { key: "stage", label: "Stage", render: (row) => row.stage, sortValue: (row) => row.stage.toLowerCase() },
      { key: "recordStatus", label: "Record Status", render: (row) => row.recordStatus, sortValue: (row) => row.recordStatus.toLowerCase() },
      { key: "inactiveFrom", label: "Inactive From", render: (row) => row.inactiveFrom, sortValue: (row) => row.inactiveFrom.toLowerCase() },
      { key: "inactiveReason", label: "Inactive Reason", render: (row) => row.inactiveReason, sortValue: (row) => row.inactiveReason.toLowerCase() },
      { key: "legalHold", label: "Legal Hold", render: (row) => row.legalHold, sortValue: (row) => row.legalHold.toLowerCase() },
      { key: "otherHold", label: "Other Hold", render: (row) => row.otherHold, sortValue: (row) => row.otherHold.toLowerCase() },
      { key: "dispositionOpen", label: "Disposition Open", render: (row) => row.dispositionOpen, sortValue: (row) => row.dispositionOpen.toLowerCase() },
      { key: "owner", label: "Owner", render: (row) => row.owner, sortValue: (row) => row.owner.toLowerCase() },
    ],
    []
  );

  return (
    <RecordsWorkspace
      activeMenu="inactive-records"
      pageTitle="Inactive Records"
      pageDescription="Inactive and retained records still under governance, hold, or disposition control."
      cardTitle="Inactive Record Register"
      cardDescription="Inactive record posture across archival state, holds, and open disposition activity."
      accentLabel="Inactive Records"
      countLabel="inactive records"
      searchPlaceholder="Search inactive records"
      metrics={metrics}
      rows={rows}
      columns={columns}
      emptyMessage="No inactive records are available yet."
      loading={loading}
      error={error ? <Alert severity="error">{error}</Alert> : undefined}
    />
  );
}
