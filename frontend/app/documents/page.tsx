"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Stack,
  Chip,
  Divider,
  Paper,
  CircularProgress,
  IconButton,
  MenuItem,
} from "@mui/material";

import SearchIcon from "@mui/icons-material/Search";
import DescriptionIcon from "@mui/icons-material/Description";
import SourceIcon from "@mui/icons-material/Source";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import apiClient from "@/services/apiClient";
import { getBusinessAreaCatalog } from "@/services/businessAreaService";

type SearchResult = {
  source?: string;
  file_name?: string;
  document?: string;
  business_area?: string;
  risk_level?: string;
  score?: number;
  text?: string;
  chunk?: string;
  chunk_text?: string;
  page?: number;
  metadata?: Record<string, any>;
};

type SearchStatus = {
  query?: string;
  search_mode?: string;
  browse_mode?: boolean;
  result_count?: number;
  allowed_repository_count?: number | null;
  allowed_business_areas?: string[];
  intelligence_pattern?: string | null;
  rule_finding_count?: number;
  message?: string | null;
};

export default function DocumentIntelligencePage() {
  const searchParams = useSearchParams();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [status, setStatus] = useState<SearchStatus | null>(null);
  const [businessArea, setBusinessArea] = useState("All");
  const [businessAreas, setBusinessAreas] = useState<Array<{ label: string; value: string }>>([
    { label: "All", value: "All" },
  ]);

  const groupedResults = useMemo(() => {
    const groups = new Map<
      string,
      { item: SearchResult; count: number }
    >();

    for (const item of results) {
      const key = `${getSourceName(item)}::${item.business_area || ""}`;
      const existing = groups.get(key);

      if (existing) {
        existing.count += 1;
      } else {
        groups.set(key, { item, count: 1 });
      }
    }

    return Array.from(groups.values());
  }, [results]);

  function getErrorMessage(error: any) {
    const detail = error?.response?.data?.detail;
    const topLevel = error?.response?.data?.message;

    if (typeof detail === "string" && detail.trim()) return detail;
    if (detail?.message) return detail.message;
    if (typeof topLevel === "string" && topLevel.trim()) return topLevel;
    return "Document search is unavailable right now. Please try again.";
  }

  async function searchDocuments() {
    if (!query.trim()) return;

    setLoading(true);
    setHasSearched(true);
    setMessage("");
    setStatus(null);

    try {
      const res = await apiClient.get("/api/search", {
        params: {
          q: query,
          top_k: 10,
          business_area: businessArea,
        },
      });

      const data =
        res.data.results ||
        res.data.data ||
        res.data.matches ||
        res.data.sources ||
        res.data ||
        [];

      setResults(Array.isArray(data) ? data : []);
      setSelected(Array.isArray(data) && data.length > 0 ? data[0] : null);
      setMessage(res.data.message || "");
      setStatus(res.data.status || null);
    } catch (err) {
      console.error("Document search failed:", err);
      setResults([]);
      setSelected(null);
      const fallbackMessage = getErrorMessage(err);
      setMessage(fallbackMessage);
      setStatus({
        query: query.trim(),
        search_mode: "request_failed",
        result_count: 0,
        allowed_repository_count: null,
        allowed_business_areas: [],
        message: fallbackMessage,
      });
    } finally {
      setLoading(false);
    }
  }

  async function browseIndexedDocuments() {
    await browseIndexedDocumentsWithFilters();
  }

  async function browseIndexedDocumentsWithFilters(filters?: {
    repositoryId?: string;
    fileName?: string;
  }) {
    setLoading(true);
    setHasSearched(true);
    setMessage("");
    setStatus(null);

    try {
      const res = await apiClient.get("/api/search/browse", {
        params: {
          limit: filters?.fileName ? 200 : 50,
          repository_id: filters?.repositoryId,
          file_name: filters?.fileName,
          business_area: businessArea !== "All" ? businessArea : undefined,
        },
      });

      const data =
        res.data.results ||
        res.data.data ||
        [];

      setResults(Array.isArray(data) ? data : []);
      setSelected(Array.isArray(data) && data.length > 0 ? data[0] : null);
      setMessage(res.data.message || "");
      setStatus(res.data.status || null);
    } catch (err) {
      console.error("Browse indexed documents failed:", err);
      setResults([]);
      setSelected(null);
      const fallbackMessage = getErrorMessage(err);
      setMessage(fallbackMessage);
      setStatus({
        query: "",
        search_mode: "browse_failed",
        result_count: 0,
        allowed_repository_count: null,
        allowed_business_areas: [],
        message: fallbackMessage,
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    async function loadBusinessAreas() {
      try {
        const response = await getBusinessAreaCatalog();
        if (!active) return;
        const options = (response?.data || []).map((item: any) => ({
          label: String(item.display_name || item.name || item.slug || ""),
          value: String(item.slug || item.name || ""),
        }));
        setBusinessAreas([{ label: "All", value: "All" }, ...options.filter((item: any) => item.label && item.value)]);
      } catch (error) {
        console.error("Failed to load business areas for document intelligence", error);
      }
    }
    void loadBusinessAreas();

    const browse = searchParams.get("browse");
    const repositoryId = searchParams.get("repository_id") || "";
    const fileName = searchParams.get("file_name") || "";

    if (browse !== "1") return;

    void browseIndexedDocumentsWithFilters({
      repositoryId: repositoryId || undefined,
      fileName: fileName || undefined,
    });
    return () => {
      active = false;
    };
  }, [searchParams, businessArea]);

  function getSourceName(item: SearchResult) {
    return (
      item.file_name ||
      item.source ||
      item.document ||
      item.metadata?.source ||
      "Unknown Document"
    );
  }

  function getPreviewText(item: SearchResult) {
    return (
      item.text ||
      item.chunk_text ||
      item.chunk ||
      item.metadata?.text ||
      "No preview available."
    );
  }

  function askCopilotAboutThis() {
    const text = selected ? getPreviewText(selected) : "";
    const source = selected ? getSourceName(selected) : "";

    const prompt = `Analyze this document source: ${source}\n\n${text}`;

    window.location.href = `/copilot?prompt=${encodeURIComponent(prompt)}`;
  }

  return (
    <ModuleGuard moduleName="documents" permission="documents:read">
      <OutletPage
        title="Document Intelligence"
      >

      <Card sx={{ border: "1px solid", borderColor: "divider", mb: 2.5 }}>
        <CardContent>
          <Stack spacing={1.5}>
            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={1.5}
              sx={{ justifyContent: "flex-end", alignItems: { xs: "stretch", md: "center" } }}
            >
              <TextField
                select
                size="small"
                label="Business Area"
                value={businessArea}
                onChange={(event) => setBusinessArea(event.target.value)}
                sx={{ minWidth: 220, flexShrink: 0 }}
              >
                {businessAreas.map((area) => (
                  <MenuItem key={area.value} value={area.value}>
                    {area.label}
                  </MenuItem>
                ))}
              </TextField>
              <Button component={Link} href="/documents/upload" variant="outlined">
                Upload Document
              </Button>
              <Button variant="outlined" onClick={browseIndexedDocuments}>
                Browse Indexed
              </Button>
              {selected ? (
                <Button
                  variant="contained"
                  startIcon={<SmartToyIcon />}
                  onClick={askCopilotAboutThis}
                >
                  Ask Copilot About This
                </Button>
              ) : null}
            </Stack>

            <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
              <TextField
                fullWidth
                placeholder="Search documents, contracts, invoices, risks, and exceptions..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") searchDocuments();
                }}
              />

              <Button
                variant="contained"
                startIcon={
                  loading ? <CircularProgress size={18} color="inherit" /> : <SearchIcon />
                }
                onClick={searchDocuments}
                disabled={loading || !query.trim()}
                sx={{ minWidth: 150 }}
              >
                Search
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, lg: 4 }}>
          <Card
            sx={{
              border: "1px solid",
              borderColor: "divider",
              height: "calc((100vh - 270px) * 0.90)",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <CardContent>
              <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                <DescriptionIcon color="primary" />
                <Typography variant="h6">Matched Sources</Typography>
              </Stack>

              <Typography variant="body2" color="text.secondary">
                {groupedResults.length} matched files
                {results.length !== groupedResults.length
                  ? ` across ${results.length} matching chunks`
                  : ""}
              </Typography>
            </CardContent>

            <Divider />

            <Box sx={{ p: 2, overflowY: "auto", flex: 1 }}>
              {message && (
                <Typography color="text.secondary" sx={{ mb: 2 }}>
                  {message}
                </Typography>
              )}
              {status && (
                <>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Status: mode `{status.search_mode || (status.browse_mode ? "browse" : "unknown")}`, results {status.result_count ?? 0},
                    accessible repositories {status.allowed_repository_count ?? "unknown"}.
                  </Typography>
                  {(status.intelligence_pattern || typeof status.rule_finding_count === "number") && (
                    <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }}>
                      {status.intelligence_pattern ? (
                        <Chip size="small" label={`Pattern: ${status.intelligence_pattern}`} variant="outlined" />
                      ) : null}
                      {typeof status.rule_finding_count === "number" ? (
                        <Chip size="small" label={`Rule findings: ${status.rule_finding_count}`} color="warning" variant="outlined" />
                      ) : null}
                    </Stack>
                  )}
                </>
              )}
              {groupedResults.length === 0 ? (
                <Stack spacing={1}>
                  <Typography color="text.secondary">
                    {hasSearched ? "No matching document chunks were found." : "Search results will appear here."}
                  </Typography>
                  {hasSearched && (
                    <Typography variant="body2" color="text.secondary">
                      Tip: this screen searches indexed text chunks, not repository file counts. Natural questions like
                      "how many documents are in the repository" work better in Copilot or repository dashboards than in
                      raw document search.
                    </Typography>
                  )}
                </Stack>
              ) : (
                <Stack spacing={1.5}>
                  {groupedResults.map(({ item, count }, index) => {
                    const isSelected = selected === item;

                    return (
                      <Paper
                        key={index}
                        elevation={0}
                        onClick={() => setSelected(item)}
                        sx={{
                          p: 2,
                          cursor: "pointer",
                          border: "1px solid",
                          borderColor: isSelected ? "primary.main" : "divider",
                          bgcolor: isSelected ? "action.selected" : "background.default",
                          borderRadius: 3,
                        }}
                      >
                        <Typography sx={{ fontWeight: 700 }} noWrap>
                          {getSourceName(item)}
                        </Typography>

                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            mt: 0.8,
                            display: "-webkit-box",
                            WebkitLineClamp: 3,
                            WebkitBoxOrient: "vertical",
                            overflow: "hidden",
                          }}
                        >
                          {getPreviewText(item)}
                        </Typography>

                        <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap" }}>
                          {count > 1 && (
                            <Chip
                              size="small"
                              variant="outlined"
                              label={`${count} matched chunks`}
                            />
                          )}
                          {item.metadata?.chunk_count && (
                            <Chip
                              size="small"
                              variant="outlined"
                              label={`${item.metadata.chunk_count} indexed chunks`}
                            />
                          )}
                          {item.metadata?.tracked_only && (
                            <Chip
                              size="small"
                              color="warning"
                              label="Tracked, not indexed"
                            />
                          )}
                          {item.metadata?.sync_status && (
                            <Chip
                              size="small"
                              variant="outlined"
                              label={`Status: ${item.metadata.sync_status}`}
                            />
                          )}
                          {item.business_area && (
                            <Chip size="small" label={item.business_area} />
                          )}

                          {item.risk_level && (
                            <Chip
                              size="small"
                              label={item.risk_level}
                              color={
                                item.risk_level.toLowerCase().includes("high")
                                  ? "error"
                                  : item.risk_level.toLowerCase().includes("medium")
                                  ? "warning"
                                  : "success"
                              }
                            />
                          )}

                          {item.score !== undefined && (
                            <Chip
                              size="small"
                              variant="outlined"
                              label={`Score ${Number(item.score).toFixed(2)}`}
                            />
                          )}
                        </Stack>
                      </Paper>
                    );
                  })}
                </Stack>
              )}
            </Box>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, lg: 8 }}>
          <Card
            sx={{
              border: "1px solid",
              borderColor: "divider",
              height: "calc((100vh - 270px) * 0.90)",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <CardContent>
              <Stack
                direction="row"
                sx={{ justifyContent: "space-between", alignItems: "flex-start" }}
              >
                <Box>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                    <SourceIcon color="primary" />
                    <Typography variant="h6">Source Preview</Typography>
                  </Stack>

                  <Typography variant="body2" color="text.secondary">
                    Selected document chunk and metadata
                  </Typography>
                </Box>

                {selected && (
                  <IconButton
                    onClick={() => navigator.clipboard.writeText(getPreviewText(selected))}
                  >
                    <ContentCopyIcon />
                  </IconButton>
                )}
              </Stack>
            </CardContent>

            <Divider />

            <Box sx={{ p: 3, overflowY: "auto", flex: 1 }}>
              {!selected ? (
                <Typography color="text.secondary">
                  Select a matched source to preview its content.
                </Typography>
              ) : (
                <Stack spacing={2.5}>
                  <Box>
                    <Typography variant="h6">{getSourceName(selected)}</Typography>

                    <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap" }}>
                      {selected.business_area && (
                        <Chip label={`Business Area: ${selected.business_area}`} />
                      )}

                      {selected.risk_level && (
                        <Chip label={`Risk: ${selected.risk_level}`} color="warning" />
                      )}

                      {selected.page && <Chip label={`Page: ${selected.page}`} />}

                      {selected.score !== undefined && (
                        <Chip
                          label={`Similarity Score: ${Number(selected.score).toFixed(3)}`}
                          color="primary"
                          variant="outlined"
                        />
                      )}

                      {selected.metadata?.tracked_only && (
                        <Chip color="warning" label="Tracked in repository, not indexed yet" />
                      )}
                    </Stack>
                  </Box>

                  <Paper
                    elevation={0}
                    sx={{
                      p: 3,
                      border: "1px solid",
                      borderColor: "divider",
                      bgcolor: "background.default",
                      borderRadius: 3,
                    }}
                  >
                    <Typography
                      sx={{
                        whiteSpace: "pre-line",
                        lineHeight: 1.9,
                      }}
                    >
                      {getPreviewText(selected)}
                    </Typography>
                  </Paper>

                  {selected.metadata && (
                    <Box>
                      <Typography variant="h6" sx={{ mb: 1 }}>
                        Metadata
                      </Typography>

                      <Paper
                        elevation={0}
                        sx={{
                          p: 2,
                          border: "1px solid",
                          borderColor: "divider",
                          bgcolor: "background.default",
                          borderRadius: 3,
                        }}
                      >
                        <pre
                          style={{
                            margin: 0,
                            whiteSpace: "pre-wrap",
                            fontSize: 13,
                          }}
                        >
                          {JSON.stringify(selected.metadata, null, 2)}
                        </pre>
                      </Paper>
                    </Box>
                  )}
                </Stack>
              )}
            </Box>
          </Card>
        </Grid>
      </Grid>
      </OutletPage>
    </ModuleGuard>
  );
}

