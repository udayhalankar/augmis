"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import DatasetOutlinedIcon from "@mui/icons-material/DatasetOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import SyncAltOutlinedIcon from "@mui/icons-material/SyncAltOutlined";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import {
  WorkAreaChartCard,
  WorkAreaChartType,
  WorkAreaChartTypeSelector,
  WorkAreaFlexibleSeries,
  WorkAreaInsightsCard,
  WorkAreaMetricStrip,
  WorkAreaRegisterCard,
} from "@/components/work-area/WorkAreaIntelligence";
import { getBusinessAreaDetail } from "@/services/businessAreaService";

type BusinessAreaDetailPayload = {
  display_name: string;
  description: string;
  status_label: string;
  status_tone: "success" | "warning" | "error" | "info" | "default";
  metrics: {
    repository_count: number;
    tracked_files: number;
    documents_indexed: number;
    chunks_indexed: number;
    needs_attention_count: number;
    active_sources: number;
  };
  charts: {
    sync_status_distribution: Array<Record<string, any>>;
    source_distribution: Array<Record<string, any>>;
    repository_chunk_distribution: Array<Record<string, any>>;
  };
  insights: string[];
  enabled_checks?: string[];
  required_specifics?: string[];
  rule_finding_count?: number;
  rule_summary?: Record<string, number>;
  rule_findings?: Array<{
    label?: string;
    severity?: string;
    field?: string;
    operator?: string;
    expected?: string | number | string[];
    actual?: string | number;
    record_id?: string;
  }>;
  repositories: Array<{
    repository_id: string;
    repository_name: string;
    source_type: string;
    sync_status: string;
    tracked_files: number;
    documents_indexed: number;
    chunks_indexed: number;
    last_sync_at: string | null;
    last_sync_error: string | null;
  }>;
};

function statusAccent(tone: BusinessAreaDetailPayload["status_tone"]) {
  if (tone === "success") return "#14b8a6";
  if (tone === "warning") return "#f59e0b";
  if (tone === "error") return "#ef4444";
  if (tone === "info") return "#2563eb";
  return "#64748b";
}

function formatRuleValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  return value === undefined || value === null || value === "" ? "-" : String(value);
}

export default function BusinessAreaDetailPage() {
  const params = useParams<{ area: string }>();
  const area = String(params?.area || "");
  const [data, setData] = useState<BusinessAreaDetailPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [registerPage, setRegisterPage] = useState(0);
  const [ruleFindingsPage, setRuleFindingsPage] = useState(0);
  const [ruleFindingsRowsPerPage, setRuleFindingsRowsPerPage] = useState(5);
  const [ruleFindingsSearch, setRuleFindingsSearch] = useState("");
  const [syncChartType, setSyncChartType] = useState<WorkAreaChartType>("bar");
  const [sourceChartType, setSourceChartType] = useState<WorkAreaChartType>("donut");
  const [chunkChartType, setChunkChartType] = useState<WorkAreaChartType>("horizontalBar");

  useEffect(() => {
    let active = true;

    async function loadAreaDetail() {
      setLoading(true);
      setError("");
      try {
        const response = await getBusinessAreaDetail(area);
        if (!active) return;
        setData(response?.data || null);
      } catch (err: any) {
        if (!active) return;
        setError(err?.response?.data?.detail || "Unable to load business area details.");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    if (area) {
      void loadAreaDetail();
    }

    return () => {
      active = false;
    };
  }, [area]);

  const rowsPerPage = 10;
  const registerRows = data?.repositories || [];
  const pagedRows = useMemo(
    () =>
      registerRows.slice(
        registerPage * rowsPerPage,
        registerPage * rowsPerPage + rowsPerPage
      ),
    [registerPage, registerRows]
  );

  useEffect(() => {
    const maxPage = Math.max(0, Math.ceil(registerRows.length / rowsPerPage) - 1);
    if (registerPage > maxPage) {
      setRegisterPage(maxPage);
    }
  }, [registerPage, registerRows.length]);

  const ruleFindings = data?.rule_findings || [];
  const normalizedRuleFindingsSearch = ruleFindingsSearch.trim().toLowerCase();
  const filteredRuleFindings = useMemo(
    () =>
      ruleFindings.filter((finding) => {
        if (!normalizedRuleFindingsSearch) {
          return true;
        }

        const searchableValues = [
          finding.label,
          finding.severity,
          finding.field,
          finding.operator,
          finding.record_id,
          formatRuleValue(finding.expected),
          formatRuleValue(finding.actual),
        ]
          .map((value) => String(value || "").toLowerCase())
          .join(" ");

        return searchableValues.includes(normalizedRuleFindingsSearch);
      }),
    [normalizedRuleFindingsSearch, ruleFindings]
  );
  const pagedRuleFindings = useMemo(
    () =>
      filteredRuleFindings.slice(
        ruleFindingsPage * ruleFindingsRowsPerPage,
        ruleFindingsPage * ruleFindingsRowsPerPage + ruleFindingsRowsPerPage
      ),
    [filteredRuleFindings, ruleFindingsPage, ruleFindingsRowsPerPage]
  );

  useEffect(() => {
    setRuleFindingsPage(0);
  }, [area, normalizedRuleFindingsSearch, ruleFindingsRowsPerPage]);

  useEffect(() => {
    const maxPage = Math.max(0, Math.ceil(filteredRuleFindings.length / ruleFindingsRowsPerPage) - 1);
    if (ruleFindingsPage > maxPage) {
      setRuleFindingsPage(maxPage);
    }
  }, [filteredRuleFindings.length, ruleFindingsPage, ruleFindingsRowsPerPage]);

  if (loading) {
    return (
      <ModuleGuard moduleName="documents" permission="documents:read">
        <OutletPage title="Business Area Intelligence">
          <Box sx={{ p: 4, display: "flex", alignItems: "center", gap: 2 }}>
            <CircularProgress size={24} />
            <Typography>Loading business area intelligence...</Typography>
          </Box>
        </OutletPage>
      </ModuleGuard>
    );
  }

  if (error || !data) {
    return (
      <ModuleGuard moduleName="documents" permission="documents:read">
        <OutletPage title="Business Area Intelligence">
          <Alert severity="error">{error || "Business area not found."}</Alert>
        </OutletPage>
      </ModuleGuard>
    );
  }

  const accent = statusAccent(data.status_tone);
  const metrics = [
    {
      title: "Repositories",
      value: data.metrics.repository_count,
      subtitle: "Active mapped repositories",
      icon: <FolderOpenOutlinedIcon />,
      accent: "#2563eb",
    },
    {
      title: "Files Tracked",
      value: data.metrics.tracked_files,
      subtitle: "Connector-tracked source files",
      icon: <DescriptionOutlinedIcon />,
      accent: "#14b8a6",
    },
    {
      title: "Documents Indexed",
      value: data.metrics.documents_indexed,
      subtitle: "Current indexed documents",
      icon: <DatasetOutlinedIcon />,
      accent: "#8b5cf6",
    },
    {
      title: "Knowledge Chunks",
      value: data.metrics.chunks_indexed,
      subtitle: "Searchable indexed chunks",
      icon: <HubOutlinedIcon />,
      accent: "#0f766e",
    },
    {
      title: "Needs Attention",
      value: data.metrics.needs_attention_count,
      subtitle: data.status_label,
      icon: <WarningAmberOutlinedIcon />,
      accent: accent,
    },
    {
      title: "Active Sources",
      value: data.metrics.active_sources,
      subtitle: "Distinct connected source types",
      icon: <SyncAltOutlinedIcon />,
      accent: "#f59e0b",
    },
  ];

  return (
    <ModuleGuard moduleName="documents" permission="documents:read">
      <OutletPage title={`${data.display_name} Intelligence`}>
        <WorkAreaMetricStrip metrics={metrics} />

        <Box
          sx={{
            mt: 2,
            display: "grid",
            gridTemplateColumns: { xs: "1fr", xl: "repeat(3, minmax(0, 1fr))" },
            gap: "var(--outlet-grid-gap)",
          }}
        >
          <WorkAreaChartCard
            title="Repository Sync Status"
            subtitle="Operational view of repository readiness for this business area."
            actions={<WorkAreaChartTypeSelector value={syncChartType} onChange={setSyncChartType} />}
          >
            <WorkAreaFlexibleSeries
              data={data.charts.sync_status_distribution || []}
              type={syncChartType}
              color="#2563eb"
            />
          </WorkAreaChartCard>

          <WorkAreaChartCard
            title="Source Composition"
            subtitle="Connected source types contributing content to this business area."
            actions={<WorkAreaChartTypeSelector value={sourceChartType} onChange={setSourceChartType} />}
          >
            <WorkAreaFlexibleSeries
              data={data.charts.source_distribution || []}
              type={sourceChartType}
              color="#14b8a6"
            />
          </WorkAreaChartCard>

          <WorkAreaChartCard
            title="Chunks By Repository"
            subtitle="Knowledge depth by repository within this business area."
            actions={<WorkAreaChartTypeSelector value={chunkChartType} onChange={setChunkChartType} />}
          >
            <WorkAreaFlexibleSeries
              data={data.charts.repository_chunk_distribution || []}
              type={chunkChartType}
              color="#f59e0b"
            />
          </WorkAreaChartCard>
        </Box>

        <WorkAreaInsightsCard
          title="Executive Notes"
          subtitle="A fast operational readout of the current repository and indexing posture."
          insights={data.insights || []}
        />

        <Box
          sx={{
            mt: 3,
            display: "flex",
            flexDirection: "column",
            gap: "var(--outlet-grid-gap)",
          }}
        >
          <WorkAreaRegisterCard
            title="Configured Intelligence Checks"
            footerNote="These checks come from the selected intelligence pattern and work-area definition."
          >
            <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }}>
              {(data.enabled_checks || []).length ? (
                (data.enabled_checks || []).map((check) => (
                  <Chip key={check} size="small" label={check} color="info" variant="outlined" />
                ))
              ) : (
                <Typography color="text.secondary">
                  No explicit checks are configured for this work area yet.
                </Typography>
              )}
            </Stack>

            <Typography variant="body2" color="text.secondary">
              Required specifics: {(data.required_specifics || []).length
                ? data.required_specifics?.join(", ")
                : "None defined yet."}
            </Typography>
          </WorkAreaRegisterCard>

          <WorkAreaRegisterCard
            title="Structured Rule Findings"
            footerNote="Only concrete rule matches are shown here. AI summaries should build on these findings instead of inventing unsupported risks."
          >
            <Stack spacing={2} sx={{ mb: 2 }}>
              <TextField
                size="small"
                label="Search findings"
                value={ruleFindingsSearch}
                onChange={(event) => setRuleFindingsSearch(event.target.value)}
                fullWidth
              />

              <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                <Chip
                  size="small"
                  label={`${filteredRuleFindings.length} findings`}
                  color={filteredRuleFindings.length ? "warning" : "default"}
                />
                {Object.entries(data.rule_summary || {}).map(([severity, count]) => (
                  <Chip key={severity} size="small" label={`${severity}: ${count}`} variant="outlined" />
                ))}
              </Stack>
            </Stack>

            {filteredRuleFindings.length ? (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Finding</TableCell>
                    <TableCell>Severity</TableCell>
                    <TableCell>Record</TableCell>
                    <TableCell>Condition</TableCell>
                    <TableCell>Actual</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pagedRuleFindings.map((finding, index) => (
                    <TableRow key={`${finding.record_id || "record"}-${finding.label || "rule"}-${index}`} hover>
                      <TableCell>
                        <Typography sx={{ fontWeight: 500 }}>{finding.label || "Rule match"}</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip size="small" label={finding.severity || "Medium"} />
                      </TableCell>
                      <TableCell>{finding.record_id || "-"}</TableCell>
                      <TableCell>
                        {finding.field || "-"} {finding.operator || "-"} {formatRuleValue(finding.expected)}
                      </TableCell>
                      <TableCell>{formatRuleValue(finding.actual)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <Alert severity="info">
                {normalizedRuleFindingsSearch
                  ? "No concrete rule matches were found for the current search."
                  : "No concrete rule matches were found for this business area."}
              </Alert>
            )}

            {filteredRuleFindings.length ? (
              <TablePagination
                component="div"
                count={filteredRuleFindings.length}
                page={ruleFindingsPage}
                onPageChange={(_, nextPage) => setRuleFindingsPage(nextPage)}
                rowsPerPage={ruleFindingsRowsPerPage}
                onRowsPerPageChange={(event) => {
                  setRuleFindingsRowsPerPage(parseInt(event.target.value, 10));
                  setRuleFindingsPage(0);
                }}
                rowsPerPageOptions={[5, 10, 25]}
              />
            ) : null}
          </WorkAreaRegisterCard>
        </Box>

        <WorkAreaRegisterCard
          title="Repository Register"
          footerNote="This workspace appears immediately after repository creation. Indexed file, document, and chunk metrics deepen automatically after sync or reindex."
        >
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Repository</TableCell>
                <TableCell>Source</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Files</TableCell>
                <TableCell align="right">Docs</TableCell>
                <TableCell align="right">Chunks</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {pagedRows.map((row) => (
                <TableRow key={row.repository_id} hover>
                  <TableCell>
                    <Typography sx={{ fontWeight: 700 }}>{row.repository_name}</Typography>
                    {row.last_sync_error ? (
                      <Typography variant="caption" color="error.main">
                        {row.last_sync_error}
                      </Typography>
                    ) : null}
                  </TableCell>
                  <TableCell>{row.source_type}</TableCell>
                  <TableCell>
                    <Chip size="small" label={row.sync_status} />
                  </TableCell>
                  <TableCell align="right">{row.tracked_files}</TableCell>
                  <TableCell align="right">{row.documents_indexed}</TableCell>
                  <TableCell align="right">{row.chunks_indexed}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <TablePagination
            component="div"
            count={registerRows.length}
            page={registerPage}
            onPageChange={(_, nextPage) => setRegisterPage(nextPage)}
            rowsPerPage={rowsPerPage}
            rowsPerPageOptions={[10]}
          />
        </WorkAreaRegisterCard>
      </OutletPage>
    </ModuleGuard>
  );
}

