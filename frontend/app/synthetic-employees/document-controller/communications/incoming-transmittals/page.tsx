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
    "Incoming transmittal API is not available in the current backend runtime."
  );
}

export default function IncomingTransmittalsPage() {
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
      key: "sender_org",
      label: "Sender",
      render: (row) => row.sender_org || "-",
      sortValue: (row) => String(row.sender_org || "-").toLowerCase(),
    },
    {
      key: "recipient_org",
      label: "Recipient",
      render: (row) => row.recipient_org || "-",
      sortValue: (row) => String(row.recipient_org || "-").toLowerCase(),
    },
    {
      key: "response_due_at",
      label: "Response Due",
      render: (row) => row.response_due_at ? new Date(row.response_due_at).toLocaleString() : "-",
      sortValue: (row) =>
        row.response_due_at ? new Date(row.response_due_at).getTime() : Number.MAX_SAFE_INTEGER,
    },
  ];

  useEffect(() => {
    async function load() {
      try {
        const response = await getTransmittals({ direction: "INCOMING", limit: 200 });
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
      { label: "Incoming Transmittals", value: items.length },
      {
        label: "Response Required",
        value: items.filter((item) => Boolean(item.response_required)).length,
      },
      {
        label: "Response Overdue",
        value: items.filter((item) => normalize(item.transmittal_status) === "RESPONSE_OVERDUE")
          .length,
      },
      {
        label: "Acknowledged",
        value: items.filter((item) => normalize(item.transmittal_status) === "ACKNOWLEDGED").length,
      },
    ];
  }, [rows]);

  return (
    <CommunicationsWorkspace
      activeMenu="incoming-transmittals"
      accentLabel="Incoming"
      cardDescription="Incoming transmittal register for receipt logging, due monitoring, and acknowledgement tracking."
      cardTitle="Incoming Transmittals"
      columns={columns}
      countLabel={`${rows?.length || 0} incoming rows`}
      emptyMessage={error ? "Incoming transmittal data could not be loaded." : "No incoming transmittals are recorded yet."}
      error={error ? <Alert severity="error">{error}</Alert> : undefined}
      loading={rows === null}
      metrics={metrics}
      pageDescription="Incoming transmittal register for receipt logging, due monitoring, and acknowledgement tracking."
      pageTitle="Transmittals & Communications"
      rows={rows || []}
      searchPlaceholder="Search incoming transmittals"
    />
  );
}
