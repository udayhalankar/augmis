"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert } from "@mui/material";

import { RecordsWorkspace, type RecordsColumn, type RecordsMetricCard } from "../_components/RecordsWorkspace";
import { getDispositionCases, getRecordDeclarations } from "@/services/symployeeRecordsService";
import { buildOpenDispositionBuckets, normalize } from "../_lib/recordsMetrics";

function readApprovals(item: any) {
  return item?.metadata_json?.approvals || {};
}

type DispositionRow = {
  caseId: string;
  identityId: string;
  declarationId: string;
  dispositionType: string;
  caseStatus: string;
  approvalSummary: string;
  recordCategory: string;
  eligibilityDate: string;
  requestedAt: string;
  requestedBy: string;
};

export default function DispositionPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<DispositionRow[]>([]);
  const [metrics, setMetrics] = useState<RecordsMetricCard[]>([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [casesResult, declarationsResult] = await Promise.all([
          getDispositionCases({ limit: 500 }),
          getRecordDeclarations({ limit: 500 }),
        ]);

        const cases = buildOpenDispositionBuckets(casesResult?.data?.items || []).active;
        const declarations = declarationsResult?.data?.items || [];
        const declarationsById = new Map<string, any>();
        declarations.forEach((item: any) => {
          if (!item?.record_declaration_id || declarationsById.has(item.record_declaration_id)) return;
          declarationsById.set(item.record_declaration_id, item);
        });

        const mappedRows = cases.map((item: any) => {
          const declaration = declarationsById.get(item.record_declaration_id);
          return {
            caseId: item.disposition_case_id || "-",
            identityId: item.identity_id || declaration?.identity_id || "-",
            declarationId: item.record_declaration_id || "-",
            dispositionType: item.disposition_type || "-",
            caseStatus: item.case_status || "-",
            approvalSummary: Object.keys(readApprovals(item)).join(", ") || "-",
            eligibilityDate: item.eligibility_date
              ? new Date(item.eligibility_date).toLocaleDateString()
              : "-",
            requestedAt: item.requested_at ? new Date(item.requested_at).toLocaleString() : "-",
            requestedBy: item.requested_by || "-",
            recordCategory: declaration?.record_category || "-",
          };
        });

        setRows(mappedRows);
        setMetrics([
          { label: "Disposition Queue", value: mappedRows.length },
          {
            label: "Pending Review",
            value: mappedRows.filter((item) => normalize(item.caseStatus) === "PENDING_REVIEW").length,
          },
          {
            label: "Pending Approvals",
            value: mappedRows.filter((item) => normalize(item.caseStatus) === "PENDING_APPROVALS").length,
          },
          {
            label: "With Eligibility Date",
            value: mappedRows.filter((item) => item.eligibilityDate !== "-").length,
          },
        ]);
      } catch (loadError: any) {
        setError(loadError?.response?.data?.detail || "Disposition cases could not be loaded.");
        setRows([]);
        setMetrics([]);
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  const columns = useMemo<RecordsColumn<DispositionRow>[]>(
    () => [
      {
        key: "identityId",
        label: "Identity",
        render: (row) => row.identityId,
        sortValue: (row) => row.identityId.toLowerCase(),
        searchableValue: (row) =>
          [
            row.caseId,
            row.identityId,
            row.declarationId,
            row.dispositionType,
            row.caseStatus,
            row.approvalSummary,
            row.recordCategory,
            row.eligibilityDate,
            row.requestedAt,
            row.requestedBy,
          ].join(" "),
      },
      { key: "declarationId", label: "Declaration", render: (row) => row.declarationId, sortValue: (row) => row.declarationId.toLowerCase() },
      { key: "dispositionType", label: "Disposition Type", render: (row) => row.dispositionType, sortValue: (row) => row.dispositionType.toLowerCase() },
      { key: "caseStatus", label: "Status", render: (row) => row.caseStatus, sortValue: (row) => row.caseStatus.toLowerCase() },
      { key: "approvalSummary", label: "Approvals", render: (row) => row.approvalSummary, sortValue: (row) => row.approvalSummary.toLowerCase() },
      { key: "recordCategory", label: "Record Category", render: (row) => row.recordCategory, sortValue: (row) => row.recordCategory.toLowerCase() },
      { key: "eligibilityDate", label: "Eligibility Date", render: (row) => row.eligibilityDate, sortValue: (row) => row.eligibilityDate.toLowerCase() },
      { key: "requestedAt", label: "Requested", render: (row) => row.requestedAt, sortValue: (row) => row.requestedAt.toLowerCase() },
      { key: "requestedBy", label: "Requested By", render: (row) => row.requestedBy, sortValue: (row) => row.requestedBy.toLowerCase() },
    ],
    []
  );

  return (
    <RecordsWorkspace
      activeMenu="disposition"
      pageTitle="Disposition"
      pageDescription="Disposition cases for review, approval, and controlled destruction or transfer execution."
      cardTitle="Disposition Register"
      cardDescription="Disposition queue visibility across case state, approvals, eligibility, and execution routing."
      accentLabel="Disposition"
      countLabel="disposition cases"
      searchPlaceholder="Search disposition cases"
      metrics={metrics}
      rows={rows}
      columns={columns}
      emptyMessage="No disposition cases are recorded yet."
      loading={loading}
      error={error ? <Alert severity="error">{error}</Alert> : undefined}
    />
  );
}
