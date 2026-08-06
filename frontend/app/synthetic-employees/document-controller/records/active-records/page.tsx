"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert } from "@mui/material";

import { RecordsWorkspace, type RecordsColumn, type RecordsMetricCard } from "../_components/RecordsWorkspace";
import { buildActiveHoldBuckets } from "../_lib/recordsMetrics";
import { getLegalHolds, getRecordDeclarations } from "@/services/symployeeRecordsService";

type ActiveRecordRow = {
  declarationId: string;
  identityId: string;
  category: string;
  stage: string;
  status: string;
  activeFrom: string;
  owner: string;
  legalHold: string;
  otherHold: string;
};

export default function ActiveRecordsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<ActiveRecordRow[]>([]);
  const [metrics, setMetrics] = useState<RecordsMetricCard[]>([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [declarationsResult, holdsResult] = await Promise.all([
          getRecordDeclarations({ limit: 500, record_stage: "ACTIVE" }),
          getLegalHolds({ limit: 500 }),
        ]);

        const declarations = declarationsResult?.data?.items || [];
        const activeRecordIdentities = new Set(
          declarations.map((item: any) => item.identity_id).filter(Boolean)
        );
        const holdBuckets = buildActiveHoldBuckets(
          (holdsResult?.data?.items || []).filter((item: any) =>
            activeRecordIdentities.has(item.identity_id)
          )
        );

        setRows(
          declarations.map((item: any) => ({
            declarationId: item.record_declaration_id || "-",
            identityId: item.identity_id || "-",
            category: item.record_category || "-",
            stage: item.record_stage || "-",
            status: item.record_status || "-",
            activeFrom: item.active_from ? new Date(item.active_from).toLocaleString() : "-",
            owner: item.owner_user_id || "-",
            legalHold: holdBuckets.legalIdentitySet.has(item.identity_id) ? "Yes" : "No",
            otherHold: holdBuckets.otherIdentitySet.has(item.identity_id) ? "Yes" : "No",
          }))
        );
        setMetrics([
          { label: "Active Records", value: declarations.length },
          { label: "Legal Holds", value: holdBuckets.legal.length },
          { label: "Other Holds", value: holdBuckets.other.length },
          {
            label: "With Owner",
            value: declarations.filter((item: any) => Boolean(item.owner_user_id)).length,
          },
        ]);
      } catch (loadError: any) {
        setError(loadError?.response?.data?.detail || "Active records could not be loaded.");
        setRows([]);
        setMetrics([]);
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  const columns = useMemo<RecordsColumn<ActiveRecordRow>[]>(
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
            row.status,
            row.activeFrom,
            row.owner,
            row.legalHold,
            row.otherHold,
          ].join(" "),
      },
      { key: "category", label: "Category", render: (row) => row.category, sortValue: (row) => row.category.toLowerCase() },
      { key: "stage", label: "Stage", render: (row) => row.stage, sortValue: (row) => row.stage.toLowerCase() },
      { key: "status", label: "Status", render: (row) => row.status, sortValue: (row) => row.status.toLowerCase() },
      { key: "activeFrom", label: "Active From", render: (row) => row.activeFrom, sortValue: (row) => row.activeFrom.toLowerCase() },
      { key: "owner", label: "Owner", render: (row) => row.owner, sortValue: (row) => row.owner.toLowerCase() },
      { key: "legalHold", label: "Legal Hold", render: (row) => row.legalHold, sortValue: (row) => row.legalHold.toLowerCase() },
      { key: "otherHold", label: "Other Hold", render: (row) => row.otherHold, sortValue: (row) => row.otherHold.toLowerCase() },
    ],
    []
  );

  return (
    <RecordsWorkspace
      activeMenu="active-records"
      pageTitle="Active Records"
      pageDescription="Declared records that remain in active business use and are still governed operationally."
      cardTitle="Active Record Register"
      cardDescription="Operationally active records with ownership and active hold visibility."
      accentLabel="Active Records"
      countLabel="active records"
      searchPlaceholder="Search active records"
      metrics={metrics}
      rows={rows}
      columns={columns}
      emptyMessage="No active records are declared yet."
      loading={loading}
      error={error ? <Alert severity="error">{error}</Alert> : undefined}
    />
  );
}
