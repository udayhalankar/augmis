"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";

import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  IconButton,
  Stack,
  Avatar,
  Chip,
  Divider,
  Paper,
  Drawer,
  Tooltip,
  CircularProgress,
  Button,
} from "@mui/material";

import SendIcon from "@mui/icons-material/Send";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import PersonIcon from "@mui/icons-material/Person";
import SourceIcon from "@mui/icons-material/Source";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";

import CloseIcon from "@mui/icons-material/Close";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import apiClient from "@/services/apiClient";
const COPILOT_STORAGE_KEY = "infomentica_copilot_messages";

type SourceItem = {
  source?: string;
  file_name?: string;
  document?: string;
  chunk_id?: string;
  document_id?: string;
  repository_id?: string;
  business_area?: string;
  metadata?: Record<string, any>;
  preview?: string;
  page?: number;
  chunk?: string;
  snippet?: string;
  text?: string;
  score?: number;
  chunk_count?: number;
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: SourceItem[];
};

export default function CopilotPage() {
  return (
    <ModuleGuard moduleName="copilot" permission="copilot:use">
      <Suspense
        fallback={
          <Box sx={{ display: "grid", placeItems: "center", minHeight: "60vh" }}>
            <CircularProgress />
          </Box>
        }
      >
        <CopilotPageContent />
      </Suspense>
    </ModuleGuard>
  );
}

function CopilotPageContent() {
  const searchParams = useSearchParams();

  const initialMessage: ChatMessage = {
  role: "assistant",
  content:
    "Hello. I am your Infomentica Enterprise Copilot. Ask me about specific documents, business areas, indexed risks, delays, escalations, or executive summaries.",
  sources: [],
};

  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeSources, setActiveSources] = useState<SourceItem[]>([]);
  const [sourceDrawerOpen, setSourceDrawerOpen] = useState(false);
  const [selectedSource, setSelectedSource] = useState<SourceItem | null>(null);


  useEffect(() => {
  try {
    const saved = localStorage.getItem(COPILOT_STORAGE_KEY);

    if (saved) {
      const parsed = JSON.parse(saved);

      if (Array.isArray(parsed) && parsed.length > 0) {
        setMessages(parsed);

        const lastAssistantWithSources = [...parsed]
          .reverse()
          .find(
            (msg: ChatMessage) =>
              msg.role === "assistant" &&
              msg.sources &&
              msg.sources.length > 0
          );

        if (lastAssistantWithSources?.sources) {
          setActiveSources(lastAssistantWithSources.sources);
        }
      }
    }
  } catch (err) {
    console.error("Failed to load copilot history:", err);
  }
}, []);

useEffect(() => {
  try {
    localStorage.setItem(COPILOT_STORAGE_KEY, JSON.stringify(messages));
  } catch (err) {
    console.error("Failed to save copilot history:", err);
  }
}, [messages]);

  useEffect(() => {
    const promptFromUrl = searchParams.get("prompt");

    if (promptFromUrl) {
      setInput(promptFromUrl);
    }
  }, [searchParams]);

  async function sendMessage() {
  if (!input.trim() || loading) return;

  const userMessage: ChatMessage = {
    role: "user",
    content: input.trim(),
  };

  const assistantMessage: ChatMessage = {
    role: "assistant",
    content: "",
    sources: [],
  };

  setMessages((prev) => [...prev, userMessage, assistantMessage]);
  setInput("");
  setLoading(true);
  setActiveSources([]);

  try {
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("infomentica_token")
        : null;

    const response = await fetch(`${apiClient.defaults.baseURL}/api/ai/ask/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        query: userMessage.content,
        business_area: "All",
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Streaming request failed (${response.status}): ${errorText}`);
    }

    if (!response.body) {
      throw new Error("No response stream received.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let fullAnswer = "";
    let pendingChunk = "";

    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        pendingChunk += decoder.decode();
      } else {
        pendingChunk += decoder.decode(value, { stream: true });
      }

      const events = pendingChunk.split("\n\n");

      if (!done) {
        pendingChunk = events.pop() || "";
      } else {
        pendingChunk = "";
      }

      for (const event of events) {
        const dataLines = event
          .split("\n")
          .map((line) => line.trim())
          .filter((line) => line.startsWith("data:"));

        const jsonString = dataLines
          .map((line) => line.slice(5).trim())
          .join("");

        if (!jsonString) continue;

        const data = JSON.parse(jsonString);

        if (data.type === "token") {
          fullAnswer += data.content;

          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: fullAnswer,
            };
            return updated;
          });
        }

        if (data.type === "sources") {
          setActiveSources(data.sources || []);

          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              sources: data.sources || [],
            };
            return updated;
          });
        }

        if (data.type === "error") {
          throw new Error(data.message);
        }
      }

      if (done) break;
    }
  } catch (err) {
    console.error("Streaming AI failed:", err);

    setMessages((prev) => {
      const updated = [...prev];
      updated[updated.length - 1] = {
        role: "assistant",
        content:
          "Streaming failed. Please check if FastAPI is running and the streaming endpoint is mounted correctly.",
        sources: [],
      };
      return updated;
    });
  } finally {
    setLoading(false);
  }
}

  function clearChat() {
  const resetMessages = [
    {
      role: "assistant" as const,
      content:
        "Conversation cleared. Ask me anything from your enterprise knowledge base.",
      sources: [],
    },
  ];

  setMessages(resetMessages);
  setActiveSources([]);
  localStorage.setItem(COPILOT_STORAGE_KEY, JSON.stringify(resetMessages));
}

function getSourceName(src: SourceItem) {
  return (
    src.file_name ||
    src.source ||
    src.document ||
    "Unknown Source"
  );
}

function getSourceText(src: SourceItem) {
  return src.chunk || src.text || src.preview || src.snippet || "No source preview available.";
}

function formatMetadataLabel(key: string) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatMetadataValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function getReadableSourceMetadata(src: SourceItem) {
  const details: Array<{ label: string; value: string }> = [];
  const technical: Array<{ label: string; value: string }> = [];

  const pushIfPresent = (
    target: Array<{ label: string; value: string }>,
    label: string,
    value: unknown
  ) => {
    if (value === null || value === undefined || value === "") return;
    target.push({ label, value: formatMetadataValue(value) });
  };

  pushIfPresent(details, "Document Name", src.file_name || src.document || src.source);
  pushIfPresent(details, "Business Area", src.business_area);
  pushIfPresent(details, "Page", src.page);
  pushIfPresent(details, "Repository", src.repository_id);
  pushIfPresent(details, "Match Score", src.score !== undefined ? Number(src.score).toFixed(3) : undefined);

  if (src.metadata) {
    const preferredDetailKeys = [
      "version_number",
      "source_modified_at",
      "source",
      "file_type",
      "sync_status",
    ];

    const preferredTechnicalKeys = [
      "parser",
      "text_status",
      "chunk_count",
    ];

    for (const key of preferredDetailKeys) {
      pushIfPresent(details, formatMetadataLabel(key), src.metadata[key]);
    }

    for (const key of preferredTechnicalKeys) {
      pushIfPresent(technical, formatMetadataLabel(key), src.metadata[key]);
    }

    Object.entries(src.metadata).forEach(([key, value]) => {
      if (
        preferredDetailKeys.includes(key) ||
        preferredTechnicalKeys.includes(key)
      ) {
        return;
      }

      pushIfPresent(technical, formatMetadataLabel(key), value);
    });
  }

  return { details, technical };
}

function openSourceDrawer(src: SourceItem) {
  setSelectedSource(src);
  setSourceDrawerOpen(true);
}

function copySourceText() {
  if (!selectedSource) return;
  navigator.clipboard.writeText(getSourceText(selectedSource));
}

function openSourceDocument() {
  if (!selectedSource) return;

  const sourceName = getSourceName(selectedSource);

  // Future backend file-viewer route can replace this.
  alert(`Open document action prepared for: ${sourceName}`);
}

const dedupedActiveSources = useMemo(() => {
  const grouped = new Map<string, SourceItem>();

  for (const src of activeSources) {
    const key = [
      src.repository_id || "",
      src.document_id || "",
      src.file_name || src.source || src.document || "",
    ].join("::");

    const existing = grouped.get(key);
    if (!existing) {
      grouped.set(key, {
        ...src,
        chunk_count: 1,
      });
      continue;
    }

    grouped.set(key, {
      ...existing,
      score:
        existing.score !== undefined && src.score !== undefined
          ? Math.max(existing.score, src.score)
          : existing.score ?? src.score,
      chunk_count: (existing.chunk_count || 1) + 1,
      chunk: existing.chunk || src.chunk,
      text: existing.text || src.text,
      preview: existing.preview || src.preview,
      snippet: existing.snippet || src.snippet,
      page: existing.page ?? src.page,
    });
  }

  return Array.from(grouped.values());
}, [activeSources]);

  const selectedSourceMetadata = useMemo(
    () => (selectedSource ? getReadableSourceMetadata(selectedSource) : null),
    [selectedSource]
  );

  return (
    <OutletPage
      title="AI Co-Pilot"
      actions={
        <Button
          variant="contained"
          startIcon={<DeleteOutlineIcon />}
          onClick={clearChat}
          sx={{
            bgcolor: "#bce58f",
            color: "#12336b",
            borderRadius: "6px",
            boxShadow: "none",
            px: 1.35,
            py: 0.45,
            minHeight: 0,
            fontSize: "0.7rem",
            fontWeight: 700,
            "&:hover": {
              bgcolor: "#acd97a",
              boxShadow: "none",
            },
          }}
        >
          New Chat
        </Button>
      }
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) 380px" },
          gap: 2.5,
          minHeight: "calc(100vh - 190px)",
        }}
      >
        <Card
          sx={{
            border: "1px solid",
            borderColor: "divider",
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
          }}
        >
          <CardContent
            sx={{
              flex: 1,
              overflowY: "auto",
              p: 3,
            }}
          >
            <Stack spacing={2.5}>
              {messages.map((msg, index) => {
                const isUser = msg.role === "user";

                return (
                  <Stack
                    key={index}
                    direction="row"
                    spacing={1.5}
                    sx={{
                      justifyContent: isUser ? "flex-end" : "flex-start",
                      alignItems: "flex-start",
                    }}
                  >
                    {!isUser && (
                      <Avatar
                        src="/augmis_logo_transparent_bg.png"
                        alt="Augmis copilot"
                        sx={{ bgcolor: "#ffffff", border: "1px solid", borderColor: "divider" }}
                      >
                        <SmartToyIcon />
                      </Avatar>
                    )}

                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        maxWidth: "78%",
                        bgcolor: isUser ? "primary.main" : "background.default",
                        color: isUser ? "#fff" : "text.primary",
                        border: "1px solid",
                        borderColor: isUser ? "primary.main" : "divider",
                        borderRadius: 3,
                      }}
                    >
                      <Box
                        className="copilot-chat__message"
                        sx={{
                          "& p": { m: 0, mb: 1 },
                          "& ul": { mt: 1 },
                          "& code": {
                            px: 0.6,
                            py: 0.2,
                            borderRadius: 1,
                            bgcolor: "rgba(128,128,128,0.18)",
                          },
                        }}
                      >
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </Box>

                      {!isUser && msg.sources && msg.sources.length > 0 && (
                        <Stack
                          direction="row"
                          spacing={1}
                          sx={{ mt: 1, flexWrap: "wrap" }}
                        >
                          {msg.sources.slice(0, 3).map((src, i) => (
                            <Chip
                              key={i}
                              size="small"
                              icon={<SourceIcon />}
                              label={getSourceName(src)}
                              onClick={() => openSourceDrawer(src)}
                              variant="outlined"
                            />
                          ))}
                        </Stack>
                      )}
                    </Paper>

                    {isUser && (
                      <Avatar sx={{ bgcolor: "success.main" }}>
                        <PersonIcon />
                      </Avatar>
                    )}
                  </Stack>
                );
              })}

              {loading && (
                <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
                  <Avatar
                    src="/augmis_logo_transparent_bg.png"
                    alt="Augmis copilot"
                    sx={{ bgcolor: "#ffffff", border: "1px solid", borderColor: "divider" }}
                  >
                    <SmartToyIcon />
                  </Avatar>
                  <Paper
                    elevation={0}
                    sx={{
                      p: 2,
                      border: "1px solid",
                      borderColor: "divider",
                      borderRadius: 3,
                    }}
                  >
                    <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
                      <CircularProgress size={18} />
                      <Typography color="text.secondary">
                        Streaming enterprise answer...
                      </Typography>
                    </Stack>
                  </Paper>
                </Stack>
              )}
            </Stack>
          </CardContent>

          <Divider />

          <Box sx={{ p: 2 }}>
            <Stack direction="row" spacing={1.5}>
              <TextField
                fullWidth
                multiline
                maxRows={4}
                placeholder="Ask about proposals, vendors, procurement bottlenecks, risks..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
              />

              <IconButton
                color="primary"
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                sx={{
                  alignSelf: "flex-end",
                  width: 52,
                  height: 52,
                  bgcolor: "primary.main",
                  color: "#fff",
                  "&:hover": {
                    bgcolor: "primary.dark",
                  },
                  "&.Mui-disabled": {
                    bgcolor: "action.disabledBackground",
                  },
                }}
              >
                <SendIcon />
              </IconButton>
            </Stack>
          </Box>
        </Card>

        <Card
          sx={{
            border: "1px solid",
            borderColor: "divider",
            minHeight: 0,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <CardContent sx={{ pb: 1 }}>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <SourceIcon color="primary" />
              <Typography variant="h6">Citations Panel</Typography>
            </Stack>

            <Typography variant="body2" color="text.secondary">
              Source chunks used by the AI answer.
            </Typography>
          </CardContent>

          <Divider />

          <Box sx={{ p: 2, overflowY: "auto", flex: 1 }}>
            {dedupedActiveSources.length === 0 ? (
              <Typography color="text.secondary">
                Citations will appear here after an AI answer is generated.
              </Typography>
            ) : (
              <Stack spacing={2}>
                {dedupedActiveSources.map((src, index) => (
                  <Paper
                      key={index}
                      elevation={0}
                      onClick={() => openSourceDrawer(src)}
                      sx={{
                        p: 2,
                        border: "1px solid",
                        borderColor: "divider",
                        borderRadius: 3,
                        bgcolor: "background.default",
                        cursor: "pointer",
                        "&:hover": {
                          borderColor: "primary.main",
                        },
                      }}
                    >
                      <Stack
                        direction="row"
                        spacing={1}
                        sx={{ justifyContent: "space-between" }}
                      >
                        <Typography sx={{ fontWeight: 700 }} noWrap>
                          {getSourceName(src)}
                        </Typography>

                        {src.score !== undefined && (
                          <Chip
                            size="small"
                            label={`Score ${Number(src.score).toFixed(2)}`}
                            color="primary"
                            variant="outlined"
                          />
                        )}
                      </Stack>

                      {(src.chunk_count || 1) > 1 && (
                        <Typography variant="caption" color="text.secondary">
                          {src.chunk_count} matching chunks combined
                        </Typography>
                      )}

                      {src.page && (
                        <Typography variant="caption" color="text.secondary">
                          Page: {src.page}
                        </Typography>
                      )}

                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{
                          mt: 1,
                          lineHeight: 1.7,
                          display: "-webkit-box",
                          WebkitLineClamp: 4,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                        }}
                      >
                        {getSourceText(src)}
                      </Typography>

                      <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
                        <Chip size="small" label="View Source" color="primary" />
                        <Chip size="small" label="Copy" variant="outlined" />
                      </Stack>
                    </Paper>
                ))}
              </Stack>
            )}


            <Drawer
                  anchor="right"
                  open={sourceDrawerOpen}
                  onClose={() => setSourceDrawerOpen(false)}
                  slotProps={{
                    paper: {
                      sx: {
                        width: { xs: "100%", sm: 520 },
                        bgcolor: "background.paper",
                      },
                    },
                  }}
                >
                  <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
                    <Box
                      sx={{
                        p: 2,
                        borderBottom: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Stack
                        direction="row"
                        sx={{ justifyContent: "space-between", alignItems: "flex-start" }}
                      >
                        <Box>
                          <Typography variant="h6">Source Viewer</Typography>
                          <Typography variant="body2" color="text.secondary">
                            Full retrieved chunk used by the AI answer
                          </Typography>
                        </Box>

                        <IconButton onClick={() => setSourceDrawerOpen(false)}>
                          <CloseIcon />
                        </IconButton>
                      </Stack>
                    </Box>

                    {selectedSource && (
                      <>
                        <Box sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider" }}>
                          <Typography sx={{ fontWeight: 800 }}>{getSourceName(selectedSource)}</Typography>

                          <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap" }}>
                            {selectedSource.page && (
                              <Chip size="small" label={`Page ${selectedSource.page}`} />
                            )}

                            {selectedSource.score !== undefined && (
                              <Chip
                                size="small"
                                label={`Score ${Number(selectedSource.score).toFixed(3)}`}
                                color="primary"
                                variant="outlined"
                              />
                            )}
                          </Stack>

                          <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
                            <Tooltip title="Copy source text">
                              <Button
                                size="small"
                                variant="outlined"
                                startIcon={<ContentCopyIcon />}
                                onClick={copySourceText}
                              >
                                Copy
                              </Button>
                            </Tooltip>

                            <Tooltip title="Backend file viewer can be connected later">
                              <Button
                                size="small"
                                variant="contained"
                                startIcon={<OpenInNewIcon />}
                                onClick={openSourceDocument}
                              >
                                Open Document
                              </Button>
                            </Tooltip>
                          </Stack>
                        </Box>

                        <Box sx={{ p: 2, overflowY: "auto", flex: 1 }}>
                          <Paper
                            elevation={0}
                            sx={{
                              p: 2,
                              border: "1px solid",
                              borderColor: "divider",
                              borderRadius: 3,
                              bgcolor: "background.default",
                            }}
                          >
                            <Typography
                              sx={{
                                whiteSpace: "pre-line",
                                lineHeight: 1.9,
                              }}
                            >
                              {getSourceText(selectedSource)}
                            </Typography>
                          </Paper>

                          <Box sx={{ mt: 2 }}>
                            <Typography variant="subtitle2" sx={{ mb: 1 }}>
                              Source Details
                            </Typography>

                            <Paper
                              elevation={0}
                              sx={{
                                p: 2,
                                border: "1px solid",
                                borderColor: "divider",
                                borderRadius: 3,
                                bgcolor: "background.default",
                              }}
                            >
                              <Stack spacing={1.25}>
                                {selectedSourceMetadata?.details.map((item) => (
                                  <Box
                                    key={`detail-${item.label}`}
                                    sx={{
                                      display: "grid",
                                      gridTemplateColumns: "160px minmax(0, 1fr)",
                                      gap: 1.5,
                                      alignItems: "start",
                                    }}
                                  >
                                    <Typography variant="body2" color="text.secondary">
                                      {item.label}
                                    </Typography>
                                    <Typography variant="body2" sx={{ wordBreak: "break-word" }}>
                                      {item.value}
                                    </Typography>
                                  </Box>
                                ))}

                                {selectedSourceMetadata?.technical.length ? (
                                  <>
                                    <Divider sx={{ my: 0.5 }} />
                                    {/* <Typography variant="subtitle2">
                                      Technical Metadata
                                    </Typography>

                                    {selectedSourceMetadata.technical.map((item) => (
                                      <Box
                                        key={`technical-${item.label}`}
                                        sx={{
                                          display: "grid",
                                          gridTemplateColumns: "160px minmax(0, 1fr)",
                                          gap: 1.5,
                                          alignItems: "start",
                                        }}
                                      >
                                        <Typography variant="body2" color="text.secondary">
                                          {item.label}
                                        </Typography>
                                        <Typography
                                          variant="body2"
                                          sx={{ wordBreak: "break-word" }}
                                        >
                                          {item.value}
                                        </Typography>
                                      </Box>
                                    ))} */}
                                  </>
                                ) : null}
                              </Stack>
                            </Paper>
                          </Box>
                        </Box>
                      </>
                    )}
                  </Box>
                </Drawer>
          </Box>
        </Card>
      </Box>
    </OutletPage>
  );
}
