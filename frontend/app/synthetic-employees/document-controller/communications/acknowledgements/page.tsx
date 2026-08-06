"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert } from "@mui/material";

import {
  CommunicationsColumn,
  CommunicationsWorkspace,
} from "../_components/CommunicationsWorkspace";
import { getAcknowledgements } from "@/services/symployeeTransmittalService";

function normalize(value?: string | null, fallback = "UNSET") {
  return String(value || fallback).toUpperCase();
}

function toErrorText(error: any) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    "Acknowledgements API is not available in the current backend runtime."
  );
}

export default function AcknowledgementsPage() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const columns: CommunicationsColumn<any>[] = [
    {
      key: "acknowledgement_id",
      label: "Acknowledgement ID",
      render: (row) => row.acknowledgement_id,
      sortValue: (row) => String(row.acknowledgement_id || "-").toLowerCase(),
      searchableValue: (row) =>
        [
          row.acknowledgement_id,
          row.transmittal_id,
          row.recipient_name,
          row.recipient_ref,
          row.status,
          row.response_status,
          row.comments,
        ]
          .filter(Boolean)
          .join(" "),
    },
    {
      key: "transmittal_id",
      label: "Transmittal",
      render: (row) => row.transmittal_id || "-",
      sortValue: (row) => String(row.transmittal_id || "-").toLowerCase(),
    },
    {
      key: "recipient_name",
      label: "Recipient",
      render: (row) => row.recipient_name || row.recipient_ref || "-",
      sortValue: (row) => String(row.recipient_name || row.recipient_ref || "-").toLowerCase(),
    },
    {
      key: "status",
      label: "Status",
      render: (row) => row.status || "-",
      sortValue: (row) => String(row.status || "-").toLowerCase(),
    },
    {
      key: "response_status",
      label: "Response Status",
      render: (row) => row.response_status || "-",
      sortValue: (row) => String(row.response_status || "-").toLowerCase(),
    },
    {
      key: "due_at",
      label: "Due",
      render: (row) => row.due_at ? new Date(row.due_at).toLocaleString() : "-",
      sortValue: (row) => (row.due_at ? new Date(row.due_at).getTime() : Number.MAX_SAFE_INTEGER),
    },
  ];

  useEffect(() => {
    async function load() {
      try {
        const response = await getAcknowledgements({ limit: 200 });
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
      { label: "Acknowledgements", value: items.length },
      {
        label: "Acknowledged",
        value: items.filter((item) => normalize(item.status) === "ACKNOWLEDGED").length,
      },
      {
        label: "Pending",
        value: items.filter((item) => normalize(item.status) === "PENDING").length,
      },
      {
        label: "Overdue Responses",
        value: items.filter((item) => normalize(item.response_status) === "OVERDUE").length,
      },
    ];
  }, [rows]);

  return (
    <CommunicationsWorkspace
      activeMenu="acknowledgements"
      accentLabel="Acknowledgements"
      cardDescription="Recipient acknowledgement status, pending confirmations, and follow-up evidence for transmittals."
      cardTitle="Acknowledgement Register"
      columns={columns}
      countLabel={`${rows?.length || 0} acknowledgement rows`}
      emptyMessage={error ? "Acknowledgement data could not be loaded." : "No acknowledgements are available yet."}
      error={error ? <Alert severity="error">{error}</Alert> : undefined}
      loading={rows === null}
      metrics={metrics}
      pageDescription="Recipient acknowledgement status, pending confirmations, and follow-up evidence for transmittals."
      pageTitle="Transmittals & Communications"
      rows={rows || []}
      searchPlaceholder="Search acknowledgements"
    />
  );
}
