"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert } from "@mui/material";

import {
  CommunicationsColumn,
  CommunicationsWorkspace,
} from "../_components/CommunicationsWorkspace";
import { getTransmittals } from "@/services/symployeeTransmittalService";

function normalize(value?: string | null, fallback = "UNSET") {
  return String(value || fallback).toUpperCase();
}

function toErrorText(error: any) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    "Outgoing transmittal API is not available in the current backend runtime."
  );
}

export default function OutgoingTransmittalsPage() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const columns: CommunicationsColumn<any>[] = [
    {
      key: "transmittal_number",
      label: "Number",
      render: (row) => row.transmittal_number || row.transmittal_id,
      sortValue: (row) => String(row.transmittal_number || row.transmittal_id || "-").toLowerCase(),
      searchableValue: (row) =>
        [
          row.transmittal_number,
          row.transmittal_id,
          row.subject,
          row.transmittal_status,
          row.sender_org,
          row.recipient_org,
          row.purpose_code,
        ]
          .filter(Boolean)
          .join(" "),
    },
    {
      key: "subject",
      label: "Subject",
      render: (row) => row.subject || "-",
      sortValue: (row) => String(row.subject || "-").toLowerCase(),
    },
    {
      key: "transmittal_status",
      label: "Status",
      render: (row) => row.transmittal_status || "-",
      sortValue: (row) => String(row.transmittal_status || "-").toLowerCase(),
    },
    {
      key: "recipient_org",
      label: "Recipient",
      render: (row) => row.recipient_org || "-",
      sortValue: (row) => String(row.recipient_org || "-").toLowerCase(),
    },
    {
      key: "purpose_code",
      label: "Purpose",
      render: (row) => row.purpose_code || "-",
      sortValue: (row) => String(row.purpose_code || "-").toLowerCase(),
    },
    {
      key: "prepared_at",
      label: "Prepared",
      render: (row) => row.prepared_at ? new Date(row.prepared_at).toLocaleString() : "-",
      sortValue: (row) =>
        row.prepared_at ? new Date(row.prepared_at).getTime() : Number.MAX_SAFE_INTEGER,
    },
  ];

  useEffect(() => {
    async function load() {
      try {
        const response = await getTransmittals({ direction: "OUTGOING", limit: 200 });
        setRows(response?.data?.items || []);
        setError(null);
      } catch (loadError: any) {
        setRows([]);
        setError(toErrorText(loadError));
      }
    }

    void load();
  }, []);

  const metrics = useMemo(() => {
    const items = rows || [];
    return [
      { label: "Outgoing Transmittals", value: items.length },
      {
        label: "Draft",
        value: items.filter((item) => normalize(item.transmittal_status) === "DRAFT").length,
      },
      {
        label: "Issued",
        value: items.filter((item) =>
          ["ISSUED", "SENT", "COMPLETED"].includes(normalize(item.transmittal_status))
        ).length,
      },
      {
        label: "Response Required",
        value: items.filter((item) => Boolean(item.response_required)).length,
      },
    ];
  }, [rows]);

  return (
    <CommunicationsWorkspace
      activeMenu="outgoing-transmittals"
      accentLabel="Outgoing"
      cardDescription="Formal issue packages, purpose-of-issue control, and distribution history."
      cardTitle="Outgoing Transmittals"
      columns={columns}
      countLabel={`${rows?.length || 0} outgoing rows`}
      emptyMessage={error ? "Outgoing transmittal data could not be loaded." : "No outgoing transmittals are recorded yet."}
      error={error ? <Alert severity="error">{error}</Alert> : undefined}
      loading={rows === null}
      metrics={metrics}
      pageDescription="Formal issue packages, purpose-of-issue control, and distribution history."
      pageTitle="Transmittals & Communications"
      rows={rows || []}
      searchPlaceholder="Search outgoing transmittals"
    />
  );
}
