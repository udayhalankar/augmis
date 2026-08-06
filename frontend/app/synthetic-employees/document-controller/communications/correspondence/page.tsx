"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert } from "@mui/material";

import {
  CommunicationsColumn,
  CommunicationsWorkspace,
} from "../_components/CommunicationsWorkspace";
import { getCorrespondence } from "@/services/symployeeTransmittalService";

function normalize(value?: string | null, fallback = "UNSET") {
  return String(value || fallback).toUpperCase();
}

function toErrorText(error: any) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    "Correspondence API is not available in the current backend runtime."
  );
}

export default function CorrespondencePage() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const columns: CommunicationsColumn<any>[] = [
    {
      key: "reference_number",
      label: "Reference",
      render: (row) => row.reference_number || row.correspondence_id || "-",
      sortValue: (row) => String(row.reference_number || row.correspondence_id || "-").toLowerCase(),
      searchableValue: (row) =>
        [
          row.reference_number,
          row.subject,
          row.direction,
          row.correspondence_type,
          row.document_lifecycle_stage,
          row.review_status,
          row.repository_name,
          row.current_file_name,
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
      key: "direction",
      label: "Direction",
      render: (row) => row.direction || "-",
      sortValue: (row) => String(row.direction || "-").toLowerCase(),
    },
    {
      key: "correspondence_type",
      label: "Type",
      render: (row) => row.correspondence_type || "-",
      sortValue: (row) => String(row.correspondence_type || "-").toLowerCase(),
    },
    {
      key: "document_lifecycle_stage",
      label: "Lifecycle",
      render: (row) => row.document_lifecycle_stage || "-",
      sortValue: (row) => String(row.document_lifecycle_stage || "-").toLowerCase(),
    },
    {
      key: "review_status",
      label: "Review",
      render: (row) => row.review_status || "-",
      sortValue: (row) => String(row.review_status || "-").toLowerCase(),
    },
  ];

  useEffect(() => {
    async function load() {
      try {
        const response = await getCorrespondence({ limit: 200 });
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
      { label: "Correspondence Items", value: items.length },
      {
        label: "Incoming",
        value: items.filter((item) => normalize(item.direction) === "INCOMING").length,
      },
      {
        label: "Outgoing",
        value: items.filter((item) => normalize(item.direction) === "OUTGOING").length,
      },
      {
        label: "In Review",
        value: items.filter((item) => normalize(item.review_status) === "IN_REVIEW").length,
      },
    ];
  }, [rows]);

  return (
    <CommunicationsWorkspace
      activeMenu="correspondence"
      accentLabel="Correspondence"
      cardDescription="Controlled correspondence linked to document identities, review state, and portfolio context."
      cardTitle="Correspondence Register"
      columns={columns}
      countLabel={`${rows?.length || 0} correspondence rows`}
      emptyMessage={error ? "Correspondence data could not be loaded." : "No correspondence items are available yet."}
      error={error ? <Alert severity="error">{error}</Alert> : undefined}
      loading={rows === null}
      metrics={metrics}
      pageDescription="Controlled correspondence linked to document identities, review state, and portfolio context."
      pageTitle="Transmittals & Communications"
      rows={rows || []}
      searchPlaceholder="Search correspondence"
    />
  );
}
