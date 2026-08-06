"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert } from "@mui/material";

import { RecordsWorkspace, type RecordsColumn, type RecordsMetricCard } from "../records/_components/RecordsWorkspace";
import { getArchiveTransfers } from "@/services/symployeeRecordsService";
import { buildArchiveBuckets } from "../records/_lib/recordsMetrics";

function readCompletion(item: any) {
  return item?.metadata_json?.completion || {};
}

function toErrorText(error: any) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    "Archive transfer API is not available in the current backend runtime."
  );
}

type ArchiveTransferRow = {
  transferId: string;
  identityId: string;
  declarationId: string;
  dispositionCaseId: string;
  transferStatus: string;
  destination: string;
  preservationFormat: string;
  checksum: string;
  integrityVerified: string;
  requestedAt: string;
  requestedBy: string;
};

export default function DocumentControllerArchiveTransfersPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<ArchiveTransferRow[]>([]);
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
              integrityVerified:
                completion.integrity_verified === true
                  ? "Verified"
                  : completion.integrity_verified === false
                    ? "Pending"
                    : "-",
              requestedAt: item.requested_at ? new Date(item.requested_at).toLocaleString() : "-",
              requestedBy: item.requested_by || "-",
            };
          })
        );
        setMetrics([
          { label: "Transfer Queue", value: archiveBuckets.items.length },
          { label: "Pending", value: archiveBuckets.pending.length },
          { label: "Completed", value: archiveBuckets.completed.length },
          {
            label: "With Integrity Check",
            value: items.filter((item: any) => item?.metadata_json?.completion?.integrity_verified === true)
              .length,
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

  const columns = useMemo<RecordsColumn<ArchiveTransferRow>[]>(
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
            row.integrityVerified,
            row.requestedAt,
            row.requestedBy,
          ].join(" "),
      },
      { key: "declarationId", label: "Declaration", render: (row) => row.declarationId, sortValue: (row) => row.declarationId.toLowerCase() },
      { key: "dispositionCaseId", label: "Disposition Case", render: (row) => row.dispositionCaseId, sortValue: (row) => row.dispositionCaseId.toLowerCase() },
      { key: "transferStatus", label: "Status", render: (row) => row.transferStatus, sortValue: (row) => row.transferStatus.toLowerCase() },
      { key: "destination", label: "Destination", render: (row) => row.destination, sortValue: (row) => row.destination.toLowerCase() },
      { key: "preservationFormat", label: "Format", render: (row) => row.preservationFormat, sortValue: (row) => row.preservationFormat.toLowerCase() },
      { key: "checksum", label: "Checksum", render: (row) => row.checksum, sortValue: (row) => row.checksum.toLowerCase() },
      { key: "integrityVerified", label: "Integrity", render: (row) => row.integrityVerified, sortValue: (row) => row.integrityVerified.toLowerCase() },
      { key: "requestedAt", label: "Requested", render: (row) => row.requestedAt, sortValue: (row) => row.requestedAt.toLowerCase() },
      { key: "requestedBy", label: "Requested By", render: (row) => row.requestedBy, sortValue: (row) => row.requestedBy.toLowerCase() },
    ],
    []
  );

  return (
    <RecordsWorkspace
      activeMenu="archive-transfers"
      pageTitle="Archive Transfers"
      pageDescription="Operational transfer queue for archive packaging, receipt confirmation, and preservation evidence."
      cardTitle="Archive Transfers Register"
      cardDescription="Archive-transfer execution workspace across destination, format, checksum, integrity verification, and receipt tracking."
      accentLabel="Archive Transfers"
      countLabel="transfer rows"
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
