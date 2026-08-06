"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert, Stack } from "@mui/material";

import {
  CommunicationsColumn,
  CommunicationsMetricCard,
  CommunicationsWorkspace,
} from "./_components/CommunicationsWorkspace";
import {
  getAcknowledgements,
  getCorrespondence,
  getTransmittals,
} from "@/services/symployeeTransmittalService";

type CommunicationRow = {
  id: string;
  channel: string;
  reference: string;
  status: string;
  directionOrRecipient: string;
};

function normalize(value?: string | null, fallback = "UNSET") {
  return String(value || fallback).toUpperCase();
}

function countRows(items: any[], predicate: (item: any) => boolean) {
  return items.filter(predicate).length;
}

export default function DocumentControllerCommunicationsPage() {
  const [loading, setLoading] = useState(true);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [metrics, setMetrics] = useState<CommunicationsMetricCard[]>([]);
  const [rows, setRows] = useState<CommunicationRow[]>([]);

  useEffect(() => {
    async function load() {
      const [transmittalsResult, correspondenceResult, acknowledgementsResult] =
        await Promise.allSettled([
          getTransmittals({ limit: 100 }),
          getCorrespondence({ limit: 100 }),
          getAcknowledgements({ limit: 100 }),
        ]);

      const nextWarnings: string[] = [];

      const transmittals =
        transmittalsResult.status === "fulfilled"
          ? transmittalsResult.value?.data?.items || []
          : (nextWarnings.push("Transmittals API is not available in the current backend runtime."), []);

      const correspondence =
        correspondenceResult.status === "fulfilled"
          ? correspondenceResult.value?.data?.items || []
          : (nextWarnings.push("Correspondence API is not available in the current backend runtime."), []);

      const acknowledgements =
        acknowledgementsResult.status === "fulfilled"
          ? acknowledgementsResult.value?.data?.items || []
          : (nextWarnings.push("Acknowledgements API is not available in the current backend runtime."), []);

      setMetrics([
        {
          label: "Incoming Transmittals",
          value: countRows(transmittals, (item) => normalize(item.direction) === "INCOMING"),
        },
        {
          label: "Outgoing Transmittals",
          value: countRows(transmittals, (item) => normalize(item.direction) === "OUTGOING"),
        },
        { label: "Correspondence Records", value: correspondence.length },
        {
          label: "Pending Acknowledgements",
          value: countRows(
            acknowledgements,
            (item) => ["PENDING", "SENT", "DUE"].includes(normalize(item.acknowledgement_status))
          ),
        },
        {
          label: "Overdue Acknowledgements",
          value: countRows(
            acknowledgements,
            (item) => normalize(item.acknowledgement_status) === "OVERDUE"
          ),
        },
        {
          label: "Acknowledged",
          value: countRows(
            acknowledgements,
            (item) =>
              ["ACKNOWLEDGED", "RECEIVED", "RESPONDED"].includes(
                normalize(item.acknowledgement_status)
              )
          ),
        },
      ]);

      setRows([
        ...transmittals.map((item: any) => ({
          id: `transmittal-${item.transmittal_id}`,
          channel: "Transmittal",
          reference: item.transmittal_number || item.transmittal_id || "-",
          status: item.transmittal_status || "-",
          directionOrRecipient: item.direction || "-",
        })),
        ...correspondence.map((item: any) => ({
          id: `correspondence-${item.correspondence_id}`,
          channel: "Correspondence",
          reference:
            item.correspondence_number || item.subject || item.correspondence_id || "-",
          status: item.status || "-",
          directionOrRecipient: item.direction || item.recipient_ref || "-",
        })),
        ...acknowledgements.map((item: any) => ({
          id: `acknowledgement-${item.acknowledgement_id}`,
          channel: "Acknowledgement",
          reference: item.acknowledgement_id || item.transmittal_id || "-",
          status: item.acknowledgement_status || "-",
          directionOrRecipient: item.recipient_ref || item.recipient_name || "-",
        })),
      ]);

      setWarnings(nextWarnings);
      setLoading(false);
    }

    void load();
  }, []);

  const columns = useMemo<CommunicationsColumn<CommunicationRow>[]>(
    () => [
      {
        key: "channel",
        label: "Channel",
        render: (row: CommunicationRow) => row.channel,
        sortValue: (row: CommunicationRow) => row.channel.toLowerCase(),
        searchableValue: (row: CommunicationRow) =>
          [row.channel, row.reference, row.status, row.directionOrRecipient].join(" "),
      },
      {
        key: "reference",
        label: "Reference",
        render: (row: CommunicationRow) => row.reference,
        sortValue: (row: CommunicationRow) => row.reference.toLowerCase(),
      },
      {
        key: "status",
        label: "Status",
        render: (row: CommunicationRow) => row.status,
        sortValue: (row: CommunicationRow) => row.status.toLowerCase(),
      },
      {
        key: "directionOrRecipient",
        label: "Direction / Recipient",
        render: (row: CommunicationRow) => row.directionOrRecipient,
        sortValue: (row: CommunicationRow) => row.directionOrRecipient.toLowerCase(),
      },
    ],
    []
  );

  return (
    <CommunicationsWorkspace
      activeMenu="overview"
      accentLabel="Overview"
      cardDescription="Combined operational snapshot for formal transmittals, correspondence tracking & acknowledgement follow-up."
      cardTitle="Communications Overview"
      columns={columns}
      countLabel={`${rows.length} communication rows`}
      emptyMessage="No communications recorded yet."
      error={
        warnings.length ? (
          <Stack spacing={1}>
            {warnings.map((warning) => (
              <Alert key={warning} severity="warning">
                {warning}
              </Alert>
            ))}
          </Stack>
        ) : undefined
      }
      loading={loading}
      metrics={metrics}
      pageDescription="Dedicated module area for formal transmittals, correspondence, and acknowledgement tracking."
      pageTitle="Transmittals & Communications"
      rows={rows}
      searchPlaceholder="Search communications"
    />
  );
}
