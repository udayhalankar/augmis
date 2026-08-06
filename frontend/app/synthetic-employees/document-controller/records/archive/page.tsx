"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert } from "@mui/material";

import { RecordsWorkspace, type RecordsColumn, type RecordsMetricCard } from "../_components/RecordsWorkspace";
import { getArchiveTransfers } from "@/services/symployeeRecordsService";
import { buildArchiveBuckets } from "../_lib/recordsMetrics";

function readCompletion(item: any) {
  return item?.metadata_json?.completion || {};
}

function toErrorText(error: any) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    "Archive transfer data could not be loaded."
  );
}

type ArchiveRow = {
  transferId: string;
  identityId: string;
  declarationId: string;
  dispositionCaseId: string;
  transferStatus: string;
  destination: string;
  preservationFormat: string;
  checksum: string;
  receiptReference: string;
  requestedAt: string;
  requestedBy: string;
};

export default function ArchivePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<ArchiveRow[]>([]);
  const [metrics, setMetrics] = useState<RecordsMetricCard[]>([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const response = await getArchiveTransfers({ limit: 500 });
        const items = response?.data?.items || [];
        const archiveBuckets = buildArchiveBuckets(items);

        setRows(
          items.map((item: any) => {
            const completion = readCompletion(item);
            return {
              transferId: item.archive_transfer_id || "-",
              identityId: item.identity_id || "-",
              declarationId: item.record_declaration_id || "-",
              dispositionCaseId: item.disposition_case_id || "-",
              transferStatus: item.transfer_status || "-",
              destination: item.archive_destination || "-",
              preservationFormat: item.preservation_format || "-",
              checksum: item.checksum_value || "-",
              receiptReference: completion.receipt_reference || "-",
              requestedAt: item.requested_at ? new Date(item.requested_at).toLocaleString() : "-",
              requestedBy: item.requested_by || "-",
            };
          })
        );
        setMetrics([
          { label: "Archive Transfers", value: archiveBuckets.items.length },
          { label: "Pending Transfers", value: archiveBuckets.pending.length },
          { label: "Completed Transfers", value: archiveBuckets.completed.length },
          {
            label: "With Checksum",
            value: archiveBuckets.items.filter((item: any) => Boolean(item.checksum_value)).length,
          },
        ]);
        setError(null);
      } catch (loadError: any) {
        setRows([]);
        setMetrics([]);
        setError(toErrorText(loadError));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  const columns = useMemo<RecordsColumn<ArchiveRow>[]>(
    () => [
      {
        key: "identityId",
        label: "Identity",
        render: (row) => row.identityId,
        sortValue: (row) => row.identityId.toLowerCase(),
        searchableValue: (row) =>
          [
            row.transferId,
            row.identityId,
            row.declarationId,
            row.dispositionCaseId,
            row.transferStatus,
            row.destination,
            row.preservationFormat,
            row.checksum,
            row.receiptReference,
            row.requestedAt,
            row.requestedBy,
          ].join(" "),
      },
      { key: "declarationId", label: "Declaration", render: (row) => row.declarationId, sortValue: (row) => row.declarationId.toLowerCase() },
      { key: "dispositionCaseId", label: "Disposition Case", render: (row) => row.dispositionCaseId, sortValue: (row) => row.dispositionCaseId.toLowerCase() },
      { key: "transferStatus", label: "Status", render: (row) => row.transferStatus, sortValue: (row) => row.transferStatus.toLowerCase() },
      { key: "destination", label: "Destination", render: (row) => row.destination, sortValue: (row) => row.destination.toLowerCase() },
      { key: "preservationFormat", label: "Preservation Format", render: (row) => row.preservationFormat, sortValue: (row) => row.preservationFormat.toLowerCase() },
      { key: "checksum", label: "Checksum", render: (row) => row.checksum, sortValue: (row) => row.checksum.toLowerCase() },
      { key: "receiptReference", label: "Receipt Ref", render: (row) => row.receiptReference, sortValue: (row) => row.receiptReference.toLowerCase() },
      { key: "requestedAt", label: "Requested", render: (row) => row.requestedAt, sortValue: (row) => row.requestedAt.toLowerCase() },
      { key: "requestedBy", label: "Requested By", render: (row) => row.requestedBy, sortValue: (row) => row.requestedBy.toLowerCase() },
    ],
    []
  );

  return (
    <RecordsWorkspace
      activeMenu="archive"
      pageTitle="Archive"
      pageDescription="Archive transfer register, preservation package details, and long-term integrity evidence."
      cardTitle="Archive Transfer Register"
      cardDescription="Archive transfer posture across destination, package format, checksum, receipt, and execution state."
      accentLabel="Archive"
      countLabel="archive rows"
      searchPlaceholder="Search archive transfers"
      metrics={metrics}
      rows={rows}
      columns={columns}
      emptyMessage={error ? "Archive transfer data could not be loaded." : "No archive transfers are recorded yet."}
      loading={loading}
      error={error ? <Alert severity="error">{error}</Alert> : undefined}
    />
  );
}
