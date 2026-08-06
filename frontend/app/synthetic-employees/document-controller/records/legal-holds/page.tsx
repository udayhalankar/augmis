"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert, MenuItem, Stack, TextField } from "@mui/material";

import { RecordsWorkspace, type RecordsColumn, type RecordsMetricCard } from "../_components/RecordsWorkspace";
import {
  buildActiveHoldBuckets,
  normalize,
} from "../_lib/recordsMetrics";
import { getLegalHolds, getRecordDeclarations } from "@/services/symployeeRecordsService";
import { getRecordVocabulary } from "@/services/symployeeRecordVocabularyService";

type HoldRow = {
  holdId: string;
  identityId: string;
  declarationId: string;
  holdCategory: string;
  holdCode: string;
  holdStatus: string;
  authority: string;
  matterReference: string;
  recordCategory: string;
  placed: string;
  released: string;
};

export default function LegalHoldsPage() {
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [error, setError] = useState<string | null>(null);
  const [holdCategories, setHoldCategories] = useState<string[]>([]);
  const [holdStatuses, setHoldStatuses] = useState<string[]>([]);
  const [allRows, setAllRows] = useState<HoldRow[]>([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [holdsResult, declarationsResult, vocabularyResult] = await Promise.all([
          getLegalHolds({ limit: 500 }),
          getRecordDeclarations({ limit: 500 }),
          getRecordVocabulary(),
        ]);

        const holds = holdsResult?.data?.items || [];
        const declarations = declarationsResult?.data?.items || [];
        const declarationsByIdentity = new Map<string, any>();
        declarations.forEach((item: any) => {
          if (!item?.identity_id || declarationsByIdentity.has(item.identity_id)) return;
          declarationsByIdentity.set(item.identity_id, item);
        });

        setAllRows(
          holds.map((item: any) => {
            const declaration = declarationsByIdentity.get(item.identity_id);
            return {
              holdId: item.legal_hold_id || "-",
              identityId: item.identity_id || "-",
              declarationId: item.record_declaration_id || declaration?.record_declaration_id || "-",
              holdCategory: item.hold_category || "OTHER",
              holdCode: item.hold_code || "-",
              holdStatus: item.hold_status || "-",
              authority: item.authority || "-",
              matterReference: item.matter_reference || "-",
              recordCategory: declaration?.record_category || "-",
              placed: item.placed_at ? new Date(item.placed_at).toLocaleString() : "-",
              released: item.released_at ? new Date(item.released_at).toLocaleString() : "-",
            };
          })
        );
        setHoldCategories(vocabularyResult?.data?.hold_categories || []);
        setHoldStatuses(vocabularyResult?.data?.hold_statuses || []);
      } catch (loadError: any) {
        setError(loadError?.response?.data?.detail || "Hold register could not be loaded.");
        setAllRows([]);
        setHoldCategories(["LEGAL", "VALIDATION", "RECORDS", "OPERATIONAL", "OTHER"]);
        setHoldStatuses(["ACTIVE", "RELEASED"]);
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  const rows = useMemo(
    () =>
      allRows.filter((item) => {
        if (categoryFilter !== "ALL" && normalize(item.holdCategory) !== categoryFilter) return false;
        if (statusFilter !== "ALL" && normalize(item.holdStatus) !== statusFilter) return false;
        return true;
      }),
    [allRows, categoryFilter, statusFilter]
  );

  const metrics = useMemo<RecordsMetricCard[]>(() => {
    const holdBuckets = buildActiveHoldBuckets(
      allRows.map((item) => ({
        identity_id: item.identityId,
        hold_category: item.holdCategory,
        hold_status: item.holdStatus,
      }))
    );
    const releasedHolds = allRows.filter((item) => normalize(item.holdStatus) === "RELEASED");
    return [
      { label: "Total Holds", value: allRows.length },
      { label: "Legal Holds", value: holdBuckets.legal.length },
      { label: "Other Holds", value: holdBuckets.other.length },
      { label: "Released Holds", value: releasedHolds.length },
    ];
  }, [allRows]);

  const columns = useMemo<RecordsColumn<HoldRow>[]>(
    () => [
      {
        key: "identityId",
        label: "Identity",
        render: (row) => row.identityId,
        sortValue: (row) => row.identityId.toLowerCase(),
        searchableValue: (row) =>
          [
            row.holdId,
            row.identityId,
            row.declarationId,
            row.holdCategory,
            row.holdCode,
            row.holdStatus,
            row.authority,
            row.matterReference,
            row.recordCategory,
            row.placed,
            row.released,
          ].join(" "),
      },
      { key: "declarationId", label: "Declaration", render: (row) => row.declarationId, sortValue: (row) => row.declarationId.toLowerCase() },
      { key: "holdCategory", label: "Hold Category", render: (row) => row.holdCategory, sortValue: (row) => row.holdCategory.toLowerCase() },
      { key: "holdCode", label: "Hold Code", render: (row) => row.holdCode, sortValue: (row) => row.holdCode.toLowerCase() },
      { key: "holdStatus", label: "Status", render: (row) => row.holdStatus, sortValue: (row) => row.holdStatus.toLowerCase() },
      { key: "authority", label: "Authority", render: (row) => row.authority, sortValue: (row) => row.authority.toLowerCase() },
      { key: "matterReference", label: "Matter Reference", render: (row) => row.matterReference, sortValue: (row) => row.matterReference.toLowerCase() },
      { key: "recordCategory", label: "Record Category", render: (row) => row.recordCategory, sortValue: (row) => row.recordCategory.toLowerCase() },
      { key: "placed", label: "Placed", render: (row) => row.placed, sortValue: (row) => row.placed.toLowerCase() },
      { key: "released", label: "Released", render: (row) => row.released, sortValue: (row) => row.released.toLowerCase() },
    ],
    []
  );

  return (
    <RecordsWorkspace
      activeMenu="legal-holds"
      pageTitle="Holds"
      pageDescription="Active and released hold records for destruction freeze and release governance."
      cardTitle="Hold Register"
      cardDescription="Hold governance across legal, validation, records, operational, and released hold posture."
      accentLabel="Holds"
      countLabel="hold rows"
      searchPlaceholder="Search holds"
      metrics={metrics}
      rows={rows}
      columns={columns}
      emptyMessage="No holds are recorded yet."
      loading={loading}
      error={error ? <Alert severity="error">{error}</Alert> : undefined}
      bodyTopContent={
        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            select
            label="Hold Category"
            value={categoryFilter}
            onChange={(event) => setCategoryFilter(event.target.value)}
            fullWidth
            sx={{ maxWidth: 260 }}
          >
            {["ALL", ...holdCategories].map((value) => (
              <MenuItem key={value} value={value}>
                {value}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Hold Status"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            fullWidth
            sx={{ maxWidth: 220 }}
          >
            {["ALL", ...holdStatuses].map((value) => (
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
