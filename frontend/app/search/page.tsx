"use client";

import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import DescriptionIcon from "@mui/icons-material/Description";
import { useSearchParams } from "next/navigation";
import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import apiClient from "@/services/apiClient";
import { getBusinessAreaCatalog } from "@/services/businessAreaService";

type SearchResult = {
  source?: string;
  file_name?: string;
  document?: string;
  file_path?: string;
  business_area?: string;
  risk_level?: string;
  chunk_no?: number;
  score?: number;
  modified?: string;
  similarity?: number;
  snippet?: string;
  text?: string;
  chunk?: string;
  chunk_text?: string;
  metadata?: Record<string, any>;
};

type SearchStatus = {
  query?: string;
  search_mode?: string;
  result_count?: number;
  allowed_repository_count?: number | null;
  allowed_business_areas?: string[];
  intelligence_pattern?: string | null;
  rule_finding_count?: number;
  message?: string | null;
};

export default function EnterpriseSearchPage() {
  const searchParams = useSearchParams();
  const [query, setQuery] = useState("");
  const [businessArea, setBusinessArea] = useState("All");
  const [businessAreas, setBusinessAreas] = useState<Array<{ label: string; value: string }>>([
    { label: "All", value: "All" },
  ]);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<SearchStatus | null>(null);

  function getErrorMessage(error: any) {
    const detail = error?.response?.data?.detail;
    const topLevel = error?.response?.data?.message;

    if (typeof detail === "string" && detail.trim()) return detail;
    if (detail?.message) return detail.message;
    if (typeof topLevel === "string" && topLevel.trim()) return topLevel;
    return "Search is unavailable right now. Please try again.";
  }

  function getResultTitle(item: SearchResult, index: number) {
    return (
      item.file_name ||
      item.document ||
      item.source ||
      item.metadata?.source ||
      item.metadata?.external_file_id ||
      `Result ${index + 1}`
    );
  }

  function getPreviewText(item: SearchResult) {
    return (
      item.snippet ||
      item.text ||
      item.chunk_text ||
      item.chunk ||
      item.metadata?.text ||
      "No preview available."
    );
  }

  async function handleSearch(explicitQuery?: string) {
    const queryInput =
      typeof explicitQuery === "string"
        ? explicitQuery
        : query;
    const finalQuery = queryInput.trim();
    if (!finalQuery || loading) return;

    setLoading(true);
    setHasSearched(true);
    setMessage("");
    setStatus(null);

    try {
      const response = await apiClient.get("/api/search", {
        params: {
          q: finalQuery,
          top_k: 10,
          business_area: businessArea,
        },
      });

      const data =
        response.data.results ||
        response.data.data ||
        response.data.matches ||
        response.data.sources ||
        response.data ||
        [];

      setResults(Array.isArray(data) ? data : []);
      setMessage(response.data.message || "");
      setStatus(response.data.status || null);
    } catch (error) {
      console.error("Enterprise search failed:", error);
      setResults([]);
      const fallbackMessage = getErrorMessage(error);
      setMessage(fallbackMessage);
      setStatus({
        query: finalQuery,
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
        console.error("Failed to load business areas for search", error);
      }
    }
    void loadBusinessAreas();

    const urlQuery = (searchParams.get("q") || "").trim();
    if (!urlQuery) return;
    setQuery(urlQuery);
    void handleSearch(urlQuery);
    return () => {
      active = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  return (
    <ModuleGuard moduleName="documents" permission="documents:read">
      <OutletPage title="Enterprise Search">
        <Card sx={{ border: "1px solid", borderColor: "divider", mb: 3 }}>
        <CardContent>
          <Stack spacing={2}>
            <TextField
              fullWidth
              placeholder="Search indexed enterprise content, contracts, invoices, exceptions..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  handleSearch();
                }
              }}
            />

            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={2}
              sx={{ alignItems: { xs: "stretch", sm: "center" } }}
            >
              <TextField
                select
                label="Business Area"
                value={businessArea}
                onChange={(event) => setBusinessArea(event.target.value)}
                sx={{ minWidth: 220 }}
              >
                {businessAreas.map((area) => (
                  <MenuItem key={area.value} value={area.value}>
                    {area.label}
                  </MenuItem>
                ))}
              </TextField>

              <Button
                variant="contained"
                startIcon={<SearchIcon />}
                onClick={() => {
                  void handleSearch();
                }}
                disabled={loading || !query.trim()}
              >
                {loading ? "Searching..." : "Search"}
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {loading && (
        <Box sx={{ display: "grid", placeItems: "center", minHeight: "20vh" }}>
          <CircularProgress />
        </Box>
      )}

      {!loading && hasSearched && results.length === 0 && (
        <Card sx={{ border: "1px solid", borderColor: "divider" }}>
          <CardContent>
            {message && (
              <Typography color="text.secondary" sx={{ mb: 1 }}>
                {message}
              </Typography>
            )}
            {status && (
              <>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Status: mode `{status.search_mode || "unknown"}`, results {status.result_count ?? 0},
                  accessible repositories {status.allowed_repository_count ?? "unknown"}.
                </Typography>
                {(status.intelligence_pattern || typeof status.rule_finding_count === "number") && (
                  <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: "wrap" }}>
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
            <Typography>No results found for your search.</Typography>
          </CardContent>
        </Card>
      )}

      {!loading && results.length > 0 && (
        <Stack spacing={2}>
          {(message || status) && (
            <Card sx={{ border: "1px solid", borderColor: "divider" }}>
              <CardContent>
                {message && <Typography color="text.secondary">{message}</Typography>}
                {status && (
                  <>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: message ? 0.5 : 0 }}>
                      Status: mode `{status.search_mode || "unknown"}`, results {status.result_count ?? 0},
                      accessible repositories {status.allowed_repository_count ?? "unknown"}.
                    </Typography>
                    {(status.intelligence_pattern || typeof status.rule_finding_count === "number") && (
                      <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap" }}>
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
              </CardContent>
            </Card>
          )}
          {results.map((result, index) => (
            <Card
              key={`${result.file_path || result.file_name || "result"}-${index}`}
              sx={{ border: "1px solid", borderColor: "divider" }}
            >
              <CardContent>
                <Stack spacing={1.5}>
                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    spacing={1}
                    sx={{
                      justifyContent: "space-between",
                      alignItems: { xs: "flex-start", md: "center" },
                    }}
                  >
                    <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                      <DescriptionIcon color="primary" />
                      <Typography variant="h6">
                        {getResultTitle(result, index)}
                      </Typography>
                    </Stack>

                    <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                      {result.business_area && (
                        <Chip label={result.business_area} color="primary" variant="outlined" />
                      )}
                      {result.risk_level && (
                        <Chip label={result.risk_level} color="warning" variant="outlined" />
                      )}
                      {result.score !== undefined && (
                        <Chip
                          label={`Score ${Number(result.score).toFixed(2)}`}
                          color="success"
                          variant="outlined"
                        />
                      )}
                      {result.similarity !== undefined && (
                        <Chip
                          label={`Similarity ${result.similarity}`}
                          color="success"
                          variant="outlined"
                        />
                      )}
                    </Stack>
                  </Stack>

                  {result.file_path && (
                    <Typography variant="body2" color="text.secondary">
                      {result.file_path}
                    </Typography>
                  )}

                  <Divider />

                    <Typography
                      color="text.secondary"
                      sx={{ whiteSpace: "pre-line", lineHeight: 1.8 }}
                    >
                    {getPreviewText(result)}
                    </Typography>

                  <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                    {result.chunk_no !== undefined && (
                      <Chip size="small" label={`Chunk ${result.chunk_no}`} />
                    )}
                    {result.modified && (
                      <Chip size="small" label={`Modified ${result.modified}`} />
                    )}
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>
      )}
      </OutletPage>
    </ModuleGuard>
  );
}

