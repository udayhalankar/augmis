"use client";

import { useEffect, useState } from "react";

import { Alert } from "@mui/material";

import {
  CommunicationsColumn,
  CommunicationsMetricCard,
  CommunicationsWorkspace,
} from "../communications/_components/CommunicationsWorkspace";
import { getTransmittals } from "@/services/symployeeTransmittalService";

function normalize(value?: string | null, fallback = "UNSET") {
  return String(value || fallback).toUpperCase();
}

function countRows(items: any[], predicate: (item: any) => boolean) {
  return items.filter(predicate).length;
}

export default function DocumentControllerTransmittalsPage() {
  const [data, setData] = useState<{
    metrics: CommunicationsMetricCard[];
    items: any[];
  } | null>(null);
  const [error, setError] = useState<string>("");

  const columns: CommunicationsColumn<any>[] = [
    {
      key: "transmittal_number",
      label: "Number",
      render: (row) => row.transmittal_number || row.transmittal_id || "-",
      sortValue: (row) => String(row.transmittal_number || row.transmittal_id || "-").toLowerCase(),
      searchableValue: (row) =>
        [
          row.transmittal_number,
          row.transmittal_id,
          row.direction,
          row.transmittal_status,
          row.purpose_code,
          row.subject,
        ]
          .filter(Boolean)
          .join(" "),
    },
    {
      key: "direction",
      label: "Direction",
      render: (row) => row.direction || "-",
      sortValue: (row) => String(row.direction || "-").toLowerCase(),
    },
    {
      key: "transmittal_status",
      label: "Status",
      render: (row) => row.transmittal_status || "-",
      sortValue: (row) => String(row.transmittal_status || "-").toLowerCase(),
    },
    {
      key: "purpose_code",
      label: "Purpose",
      render: (row) => row.purpose_code || "-",
      sortValue: (row) => String(row.purpose_code || "-").toLowerCase(),
    },
    {
      key: "response_due_at",
      label: "Response Due",
      render: (row) =>
        row.response_due_at ? new Date(row.response_due_at).toLocaleString() : "-",
      sortValue: (row) =>
        row.response_due_at ? new Date(row.response_due_at).getTime() : Number.MAX_SAFE_INTEGER,
    },
  ];

  useEffect(() => {
    getTransmittals({ limit: 100 })
      .then((result) => {
        const items = result?.data?.items || [];
        const metrics: CommunicationsMetricCard[] = [
          { label: "Total Transmittals", value: items.length },
          {
            label: "Incoming",
            value: countRows(items, (item) => normalize(item.direction) === "INCOMING"),
          },
          {
            label: "Outgoing",
            value: countRows(items, (item) => normalize(item.direction) === "OUTGOING"),
          },
          {
            label: "Draft",
            value: countRows(items, (item) => normalize(item.transmittal_status) === "DRAFT"),
          },
          {
            label: "Response Required",
            value: countRows(items, (item) => Boolean(item.response_required)),
          },
          {
            label: "Response Overdue",
            value: countRows(
              items,
              (item) =>
                Boolean(item.response_due_at) &&
                normalize(item.transmittal_status) !== "COMPLETED" &&
                new Date(item.response_due_at).getTime() < Date.now()
            ),
          },
        ];

        setData({ metrics, items });
      })
      .catch((err: any) => {
        const status = err?.response?.status;
        setError(
          status === 404
            ? "Transmittal API is not available yet in the current backend runtime."
            : "Unable to load transmittals right now."
        );
        setData({
          metrics: [
            { label: "Total Transmittals", value: 0 },
            { label: "Incoming", value: 0 },
            { label: "Outgoing", value: 0 },
            { label: "Draft", value: 0 },
            { label: "Response Required", value: 0 },
            { label: "Response Overdue", value: 0 },
          ],
          items: [],
        });
      });
  }, []);

  return (
    <CommunicationsWorkspace
      activeMenu="transmittals"
      accentLabel="Transmittals"
      cardDescription="Formal transmittal register for issue control, response due monitoring, and acknowledgement workflow."
      cardTitle="Transmittals Register"
      columns={columns}
      countLabel={`${data?.items.length || 0} transmittal rows`}
      emptyMessage={error ? "Transmittal data could not be loaded." : "No transmittals recorded yet."}
      error={error ? <Alert severity="warning">{error}</Alert> : undefined}
      loading={!data}
      metrics={data?.metrics || []}
      pageDescription="Formal transmittal register for issue control, response due monitoring, and acknowledgement workflow."
      pageTitle="Transmittals & Communications"
      rows={data?.items || []}
      searchPlaceholder="Search transmittals"
    />
  );
}
