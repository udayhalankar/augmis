"use client";

import { useEffect, useMemo, useState, useTransition } from "react";

import { Alert, Button, MenuItem, Stack, TextField } from "@mui/material";

import { RecordsWorkspace, type RecordsColumn, type RecordsMetricCard } from "../_components/RecordsWorkspace";
import { getRecordDeclarations, updateRecordVitalStatus } from "@/services/symployeeRecordsService";

const VITAL_STATES = ["ALL", "NON_VITAL", "VITAL_CANDIDATE", "VITAL_UNDER_REVIEW", "VITAL"] as const;

function normalize(value?: string | null, fallback = "UNSET") {
  return String(value || fallback).toUpperCase();
}

function readVitalProfile(item: any) {
  return item?.metadata_json?.vital_profile || {};
}

type VitalRow = {
  declarationId: string;
  identityId: string;
  category: string;
  vitalStatus: string;
  policy: string;
  reviewDue: string;
  recovery: string;
  protection: string;
  actions: any;
};

export default function VitalRecordsPage() {
  const [loading, setLoading] = useState(true);
  const [isPending, startTransition] = useTransition();
  const [items, setItems] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await getRecordDeclarations({ limit: 500 });
      setItems(response?.data?.items || []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Vital records could not be loaded.");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const vitalStatus = normalize(item.vital_status, "NON_VITAL");
      if (statusFilter !== "ALL" && vitalStatus !== statusFilter) return false;
      return true;
    });
  }, [items, statusFilter]);

  const metrics = useMemo<RecordsMetricCard[]>(
    () => [
      {
        label: "Vital Records",
        value: filteredItems.filter((item) =>
          ["VITAL", "VITAL_UNDER_REVIEW"].includes(normalize(item.vital_status))
        ).length,
      },
      {
        label: "Vital Candidates",
        value: filteredItems.filter((item) => normalize(item.vital_status) === "VITAL_CANDIDATE").length,
      },
      {
        label: "Under Review",
        value: filteredItems.filter((item) => normalize(item.vital_status) === "VITAL_UNDER_REVIEW").length,
      },
      {
        label: "Non-Vital",
        value: filteredItems.filter((item) => normalize(item.vital_status) === "NON_VITAL").length,
      },
    ],
    [filteredItems]
  );

  function applyVitalStatus(
    identityId: string,
    vitalStatus: "NON_VITAL" | "VITAL_CANDIDATE" | "VITAL_UNDER_REVIEW" | "VITAL"
  ) {
    setMessage(null);
    setError(null);
    startTransition(async () => {
      try {
        await updateRecordVitalStatus({
          identity_id: identityId,
          vital_status: vitalStatus,
          reason: "Manual vital records update from vital register",
        });
        setMessage(`Updated ${identityId} to ${vitalStatus}.`);
        await load();
      } catch (err: any) {
        setError(err?.response?.data?.detail || "Vital status update failed.");
      }
    });
  }

  const rows = useMemo<VitalRow[]>(
    () =>
      filteredItems.map((item) => {
        const profile = readVitalProfile(item);
        return {
          declarationId: item.record_declaration_id || "-",
          identityId: item.identity_id || "-",
          category: item.record_category || "-",
          vitalStatus: item.vital_status || "NON_VITAL",
          policy: profile.policy_code || "-",
          reviewDue: profile.review_due_at
            ? new Date(profile.review_due_at).toLocaleDateString()
            : "-",
          recovery:
            profile.recovery_metadata?.strategy ||
            profile.recovery_metadata?.recovery_objective_hours ||
            "-",
          protection:
            profile.protection_metadata?.level ||
            profile.protection_metadata?.backup_required ||
            "-",
          actions: (
            <Stack direction="row" spacing={1} sx={{ justifyContent: "flex-end" }}>
              <Button
                size="small"
                variant="outlined"
                disabled={isPending}
                onClick={() => applyVitalStatus(item.identity_id, "VITAL_CANDIDATE")}
              >
                Candidate
              </Button>
              <Button
                size="small"
                variant="outlined"
                disabled={isPending}
                onClick={() => applyVitalStatus(item.identity_id, "VITAL_UNDER_REVIEW")}
              >
                Review
              </Button>
              <Button
                size="small"
                variant="outlined"
                disabled={isPending}
                onClick={() => applyVitalStatus(item.identity_id, "VITAL")}
              >
                Vital
              </Button>
            </Stack>
          ),
        };
      }),
    [filteredItems, isPending]
  );

  const columns = useMemo<RecordsColumn<VitalRow>[]>(
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
            row.vitalStatus,
            row.policy,
            row.reviewDue,
            row.recovery,
            row.protection,
          ].join(" "),
      },
      { key: "category", label: "Category", render: (row) => row.category, sortValue: (row) => row.category.toLowerCase() },
      { key: "vitalStatus", label: "Vital Status", render: (row) => row.vitalStatus, sortValue: (row) => row.vitalStatus.toLowerCase() },
      { key: "policy", label: "Policy", render: (row) => row.policy, sortValue: (row) => row.policy.toLowerCase() },
      { key: "reviewDue", label: "Review Due", render: (row) => row.reviewDue, sortValue: (row) => row.reviewDue.toLowerCase() },
      { key: "recovery", label: "Recovery", render: (row) => row.recovery, sortValue: (row) => row.recovery.toLowerCase() },
      { key: "protection", label: "Protection", render: (row) => row.protection, sortValue: (row) => row.protection.toLowerCase() },
      {
        key: "actions",
        label: "Actions",
        render: (row) => row.actions,
        align: "right",
        disableTruncate: true,
      },
    ],
    []
  );

  return (
    <RecordsWorkspace
      activeMenu="vital-records"
      pageTitle="Vital Records"
      pageDescription="Explicit vital-record classification, review cadence, and recovery/protection posture."
      cardTitle="Vital Records Register"
      cardDescription="Vital-state classification workspace with policy, review cadence, recovery, and protection visibility."
      accentLabel="Vital Records"
      countLabel="vital rows"
      searchPlaceholder="Search vital records"
      metrics={metrics}
      rows={rows}
      columns={columns}
      emptyMessage="No vital record rows match the current filters."
      loading={loading}
      error={
        <Stack spacing={1.5}>
          {message ? <Alert severity="success">{message}</Alert> : null}
          {error ? <Alert severity="error">{error}</Alert> : null}
        </Stack>
      }
      bodyTopContent={
        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            select
            label="Vital Status"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            fullWidth
            sx={{ maxWidth: 260 }}
          >
            {VITAL_STATES.map((value) => (
              <MenuItem key={value} value={value}>
                {value}
              </MenuItem>
            ))}
          </TextField>
        </Stack>
      }
    />
  );
}
