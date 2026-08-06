"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";

import AccessDenied from "@/components/auth/AccessDenied";
import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import { useAuth } from "@/context/AuthContext";
import {
  createMilestone,
  createPhase,
  createScopeItem,
  deleteMilestone,
  deletePhase,
  deleteScopeItem,
  getScopeTracker,
  updateMilestone,
  updatePhase,
  updateScopeItem,
} from "@/services/scopeService";

const statusOptions = [
  "pending",
  "in_progress",
  "completed",
  "partial",
  "blocked",
  "parked",
];

const itemTypeOptions = [
  "phase-item",
  "milestone-item",
  "task",
  "bug",
  "decision",
  "risk",
  "feature",
];

type ScopeTrack = "augmis" | "symployee";

type ScopeDialogState = {
  open: boolean;
  mode: "create" | "edit";
  entity: "phase" | "milestone" | "item";
  phaseId?: string;
  milestoneId?: string;
  itemId?: string;
  form: {
    title: string;
    description: string;
    status: string;
    item_type: string;
    owner: string;
    due_date: string;
  };
};

function StatusChip({ status }: { status: string }) {
  const color =
    status === "completed"
      ? "success"
      : status === "in_progress"
        ? "primary"
        : status === "partial"
          ? "warning"
          : status === "blocked"
            ? "error"
            : status === "parked"
              ? "secondary"
              : "default";

  return <Chip size="small" label={status} color={color} variant="outlined" />;
}

export default function ScopeTrackerPage() {
  const { user } = useAuth();
  const [scope, setScope] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [activeTrack, setActiveTrack] = useState<ScopeTrack>("augmis");
  const [dialog, setDialog] = useState<ScopeDialogState>({
    open: false,
    mode: "create",
    entity: "phase",
    form: {
      title: "",
      description: "",
      status: "pending",
      item_type: "task",
      owner: "",
      due_date: "",
    },
  });

  const tracks = useMemo(() => scope?.tracks || {}, [scope]);
  const currentTrack = tracks[activeTrack] || null;

  async function loadScope() {
    setLoading(true);
    setError("");
    try {
      const result = await getScopeTracker();
      if (result.success) {
        setScope(result.data);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to load scope tracker");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (user) {
      loadScope();
    } else {
      setLoading(false);
    }
  }, [user]);

  function openCreateDialog(
    entity: "phase" | "milestone" | "item",
    phaseId?: string,
    milestoneId?: string
  ) {
    setDialog({
      open: true,
      mode: "create",
      entity,
      phaseId,
      milestoneId,
      form: {
        title: "",
        description: "",
        status: "pending",
        item_type: "task",
        owner: "",
        due_date: "",
      },
    });
  }

  function openEditDialog(
    entity: "phase" | "milestone" | "item",
    values: any,
    phaseId?: string,
    milestoneId?: string
  ) {
    setDialog({
      open: true,
      mode: "edit",
      entity,
      phaseId,
      milestoneId,
      itemId: values.item_id,
      form: {
        title: values.title || "",
        description: values.description || "",
        status: values.status || "pending",
        item_type: values.item_type || "task",
        owner: values.owner || "",
        due_date: values.due_date || "",
      },
    });
  }

  async function handleSave() {
    setSaving(true);
    setError("");

    try {
      if (dialog.entity === "phase") {
        if (dialog.mode === "create") {
          await createPhase(
            {
              title: dialog.form.title,
              description: dialog.form.description,
              status: dialog.form.status,
            },
            activeTrack
          );
        } else if (dialog.phaseId) {
          await updatePhase(
            dialog.phaseId,
            {
              title: dialog.form.title,
              description: dialog.form.description,
              status: dialog.form.status,
            },
            activeTrack
          );
        }
      }

      if (dialog.entity === "milestone" && dialog.phaseId) {
        if (dialog.mode === "create") {
          await createMilestone(
            dialog.phaseId,
            {
              title: dialog.form.title,
              description: dialog.form.description,
              status: dialog.form.status,
            },
            activeTrack
          );
        } else if (dialog.milestoneId) {
          await updateMilestone(
            dialog.phaseId,
            dialog.milestoneId,
            {
              title: dialog.form.title,
              description: dialog.form.description,
              status: dialog.form.status,
            },
            activeTrack
          );
        }
      }

      if (dialog.entity === "item" && dialog.phaseId && dialog.milestoneId) {
        if (dialog.mode === "create") {
          await createScopeItem(
            dialog.phaseId,
            dialog.milestoneId,
            {
              title: dialog.form.title,
              description: dialog.form.description,
              status: dialog.form.status,
              item_type: dialog.form.item_type,
              owner: dialog.form.owner,
              due_date: dialog.form.due_date,
            },
            activeTrack
          );
        } else if (dialog.itemId) {
          await updateScopeItem(
            dialog.phaseId,
            dialog.milestoneId,
            dialog.itemId,
            {
              title: dialog.form.title,
              description: dialog.form.description,
              status: dialog.form.status,
              item_type: dialog.form.item_type,
              owner: dialog.form.owner,
              due_date: dialog.form.due_date,
            },
            activeTrack
          );
        }
      }

      setDialog((prev) => ({ ...prev, open: false }));
      await loadScope();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to save scope changes");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(
    entity: "phase" | "milestone" | "item",
    phaseId: string,
    milestoneId?: string,
    itemId?: string
  ) {
    setError("");
    try {
      if (entity === "phase") {
        await deletePhase(phaseId, activeTrack);
      }
      if (entity === "milestone" && milestoneId) {
        await deleteMilestone(phaseId, milestoneId, activeTrack);
      }
      if (entity === "item" && milestoneId && itemId) {
        await deleteScopeItem(phaseId, milestoneId, itemId, activeTrack);
      }
      await loadScope();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to delete item");
    }
  }

  if (!user) {
    return (
      <ModuleGuard moduleName="settings" permission="admin:settings">
        <AccessDenied />
      </ModuleGuard>
    );
  }

  if (loading) {
    return (
      <ModuleGuard moduleName="settings" permission="admin:settings">
        <Box sx={{ p: 4, display: "flex", alignItems: "center", gap: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading project scope tracker...</Typography>
        </Box>
      </ModuleGuard>
    );
  }

  return (
    <ModuleGuard moduleName="settings" permission="admin:settings">
      <OutletPage
        title="Scope Tracker"
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => openCreateDialog("phase")}
          >
            Add Phase
          </Button>
        }
      >
        

        <Box
  sx={{
    mb: 3,
    p: 1.5,
    display: "flex",
    gap: 1.5,
    alignItems: "center",
    border: "1px solid #d7e0f0",
    borderRadius: 3,
    background: "#f8fafc",
    position: "relative",
    zIndex: 5,
  }}
>
  <Button
    variant={activeTrack === "augmis" ? "contained" : "outlined"}
    onClick={() => setActiveTrack("augmis")}
    sx={{
      minWidth: 150,
      fontWeight: 800,
      borderRadius: 999,
      bgcolor: activeTrack === "augmis" ? "#082f73" : "#ffffff",
      color: activeTrack === "augmis" ? "#ffffff" : "#082f73",
      borderColor: "#9db5ff",
      "&:hover": {
        bgcolor: activeTrack === "augmis" ? "#0a3b8f" : "#eef4ff",
      },
    }}
  >
    AUGMIS
  </Button>

  <Button
    variant={activeTrack === "symployee" ? "contained" : "outlined"}
    onClick={() => setActiveTrack("symployee")}
    sx={{
      minWidth: 150,
      fontWeight: 800,
      borderRadius: 999,
      bgcolor: activeTrack === "symployee" ? "#082f73" : "#ffffff",
      color: activeTrack === "symployee" ? "#ffffff" : "#082f73",
      borderColor: "#9db5ff",
      "&:hover": {
        bgcolor: activeTrack === "symployee" ? "#0a3b8f" : "#eef4ff",
      },
    }}
  >
    SYMPLOYEE
  </Button>
  {/* <Typography variant="caption">
  Active Track: {activeTrack}
</Typography> */}
</Box>


{/* <Box sx={{ mb: 3 }}>
          <Typography color="text.secondary">
            Admin-only project management page for phases, milestones, tasks,
            and status tracking. Use tabs to manage the broader AUGMIS scope and
            the detailed Symployee sprint action items separately.
          </Typography>
        </Box> */}

        {/* <Paper
          elevation={0}
          sx={{
            mb: 3,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            overflow: "hidden",
            bgcolor: "#ffffff",
          }}
        >
          <Stack
            direction="row"
            spacing={1.5}
            sx={{
              p: 2,
              bgcolor: "#f8fafc",
              borderBottom: "1px solid",
              borderColor: "divider",
            }}
          >
            <Button
              variant={activeTrack === "augmis" ? "contained" : "outlined"}
              onClick={() => setActiveTrack("augmis")}
              sx={{
                minWidth: 140,
                fontWeight: 800,
                borderRadius: 999,
                ...(activeTrack === "augmis"
                  ? {
                      bgcolor: "#082f73",
                      color: "#ffffff",
                      "&:hover": { bgcolor: "#0a3b8f" },
                    }
                  : {
                      color: "#082f73",
                      borderColor: "#9db5ff",
                      bgcolor: "#ffffff",
                    }),
              }}
            >
              AUGMIS
            </Button>
            <Button
              variant={activeTrack === "symployee" ? "contained" : "outlined"}
              onClick={() => setActiveTrack("symployee")}
              sx={{
                minWidth: 140,
                fontWeight: 800,
                borderRadius: 999,
                ...(activeTrack === "symployee"
                  ? {
                      bgcolor: "#082f73",
                      color: "#ffffff",
                      "&:hover": { bgcolor: "#0a3b8f" },
                    }
                  : {
                      color: "#082f73",
                      borderColor: "#9db5ff",
                      bgcolor: "#ffffff",
                    }),
              }}
            >
              SYMPLOYEE
            </Button>
          </Stack>
          <Box sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
              {currentTrack?.name || activeTrack.toUpperCase()}
            </Typography>
            <Typography color="text.secondary">
              {currentTrack?.description || "Track description not available."}
            </Typography>
          </Box>
        </Paper> */}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Stack spacing={2.5}>
          {(currentTrack?.phases || []).map((phase: any) => (
            <Paper
              key={phase.phase_id}
              elevation={0}
              sx={{
                p: 2.5,
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 2,
                  alignItems: "flex-start",
                  mb: 2,
                }}
              >
                <Box>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1 }}>
                    <Typography variant="h5" sx={{ fontWeight: 800 }}>
                      {phase.title}
                    </Typography>
                    <StatusChip status={phase.status} />
                  </Stack>
                  {phase.description && (
                    <Typography color="text.secondary">
                      {phase.description}
                    </Typography>
                  )}
                </Box>

                <Stack direction="row" spacing={1}>
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<AddIcon />}
                    onClick={() => openCreateDialog("milestone", phase.phase_id)}
                  >
                    Add Milestone
                  </Button>
                  <IconButton onClick={() => openEditDialog("phase", phase, phase.phase_id)}>
                    <EditOutlinedIcon />
                  </IconButton>
                  <IconButton
                    color="error"
                    onClick={() => handleDelete("phase", phase.phase_id)}
                  >
                    <DeleteOutlineIcon />
                  </IconButton>
                </Stack>
              </Box>

              <Stack spacing={2}>
                {(phase.milestones || []).map((milestone: any) => (
                  <Paper
                    key={milestone.milestone_id}
                    elevation={0}
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      border: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 2,
                        alignItems: "flex-start",
                        mb: 2,
                      }}
                    >
                      <Box>
                        <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1 }}>
                          <Typography variant="h6" sx={{ fontWeight: 700 }}>
                            {milestone.title}
                          </Typography>
                          <StatusChip status={milestone.status} />
                        </Stack>
                        {milestone.description && (
                          <Typography variant="body2" color="text.secondary">
                            {milestone.description}
                          </Typography>
                        )}
                      </Box>

                      <Stack direction="row" spacing={1}>
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<AddIcon />}
                          onClick={() =>
                            openCreateDialog("item", phase.phase_id, milestone.milestone_id)
                          }
                        >
                          Add Item
                        </Button>
                        <IconButton
                          onClick={() =>
                            openEditDialog(
                              "milestone",
                              milestone,
                              phase.phase_id,
                              milestone.milestone_id
                            )
                          }
                        >
                          <EditOutlinedIcon />
                        </IconButton>
                        <IconButton
                          color="error"
                          onClick={() =>
                            handleDelete("milestone", phase.phase_id, milestone.milestone_id)
                          }
                        >
                          <DeleteOutlineIcon />
                        </IconButton>
                      </Stack>
                    </Box>

                    <Grid container spacing={1.5}>
                      {(milestone.items || []).map((item: any) => (
                        <Grid size={{ xs: 12, md: 6 }} key={item.item_id}>
                          <Paper
                            elevation={0}
                            sx={{
                              p: 1.5,
                              borderRadius: 2,
                              border: "1px solid",
                              borderColor: "divider",
                              height: "100%",
                            }}
                          >
                            <Box
                              sx={{
                                display: "flex",
                                justifyContent: "space-between",
                                gap: 1,
                                mb: 1,
                              }}
                            >
                              <Box>
                                <Typography sx={{ fontWeight: 700 }}>
                                  {item.title}
                                </Typography>
                                <Stack
                                  direction="row"
                                  spacing={1}
                                  sx={{ mt: 0.8, alignItems: "center", flexWrap: "wrap" }}
                                >
                                  <Chip size="small" label={item.item_type || "task"} />
                                  <StatusChip status={item.status} />
                                </Stack>
                              </Box>

                              <Stack direction="row" spacing={0.5}>
                                <IconButton
                                  size="small"
                                  onClick={() =>
                                    openEditDialog(
                                      "item",
                                      item,
                                      phase.phase_id,
                                      milestone.milestone_id
                                    )
                                  }
                                >
                                  <EditOutlinedIcon fontSize="small" />
                                </IconButton>
                                <IconButton
                                  size="small"
                                  color="error"
                                  onClick={() =>
                                    handleDelete(
                                      "item",
                                      phase.phase_id,
                                      milestone.milestone_id,
                                      item.item_id
                                    )
                                  }
                                >
                                  <DeleteOutlineIcon fontSize="small" />
                                </IconButton>
                              </Stack>
                            </Box>

                            {item.description && (
                              <Typography variant="body2" color="text.secondary">
                                {item.description}
                              </Typography>
                            )}

                            {(item.owner || item.due_date) && (
                              <>
                                <Divider sx={{ my: 1.2 }} />
                                <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                                  {item.owner && (
                                    <Chip
                                      size="small"
                                      variant="outlined"
                                      label={`Owner: ${item.owner}`}
                                    />
                                  )}
                                  {item.due_date && (
                                    <Chip
                                      size="small"
                                      variant="outlined"
                                      label={`Due: ${item.due_date}`}
                                    />
                                  )}
                                </Stack>
                              </>
                            )}
                          </Paper>
                        </Grid>
                      ))}
                    </Grid>
                  </Paper>
                ))}
              </Stack>
            </Paper>
          ))}
        </Stack>

        <Dialog
          open={dialog.open}
          onClose={() => setDialog((prev) => ({ ...prev, open: false }))}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle sx={{ fontWeight: 800 }}>
            {dialog.mode === "create" ? "Add" : "Edit"} {dialog.entity} -{" "}
            {activeTrack.toUpperCase()}
          </DialogTitle>
          <DialogContent>
            <TextField
              fullWidth
              label="Title"
              value={dialog.form.title}
              onChange={(e) =>
                setDialog((prev) => ({
                  ...prev,
                  form: { ...prev.form, title: e.target.value },
                }))
              }
              sx={{ mt: 1, mb: 2 }}
            />

            <TextField
              fullWidth
              multiline
              minRows={3}
              label="Description"
              value={dialog.form.description}
              onChange={(e) =>
                setDialog((prev) => ({
                  ...prev,
                  form: { ...prev.form, description: e.target.value },
                }))
              }
              sx={{ mb: 2 }}
            />

            <TextField
              select
              fullWidth
              label="Status"
              value={dialog.form.status}
              onChange={(e) =>
                setDialog((prev) => ({
                  ...prev,
                  form: { ...prev.form, status: e.target.value },
                }))
              }
              sx={{ mb: dialog.entity === "item" ? 2 : 0 }}
            >
              {statusOptions.map((status) => (
                <MenuItem key={status} value={status}>
                  {status}
                </MenuItem>
              ))}
            </TextField>

            {dialog.entity === "item" && (
              <Stack spacing={2}>
                <TextField
                  select
                  fullWidth
                  label="Item Type"
                  value={dialog.form.item_type}
                  onChange={(e) =>
                    setDialog((prev) => ({
                      ...prev,
                      form: { ...prev.form, item_type: e.target.value },
                    }))
                  }
                >
                  {itemTypeOptions.map((type) => (
                    <MenuItem key={type} value={type}>
                      {type}
                    </MenuItem>
                  ))}
                </TextField>

                <TextField
                  fullWidth
                  label="Owner"
                  value={dialog.form.owner}
                  onChange={(e) =>
                    setDialog((prev) => ({
                      ...prev,
                      form: { ...prev.form, owner: e.target.value },
                    }))
                  }
                />

                <TextField
                  fullWidth
                  label="Due Date"
                  placeholder="YYYY-MM-DD"
                  value={dialog.form.due_date}
                  onChange={(e) =>
                    setDialog((prev) => ({
                      ...prev,
                      form: { ...prev.form, due_date: e.target.value },
                    }))
                  }
                />
              </Stack>
            )}
          </DialogContent>
          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setDialog((prev) => ({ ...prev, open: false }))}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleSave}
              disabled={saving || !dialog.form.title.trim()}
            >
              {saving ? <CircularProgress size={20} /> : "Save"}
            </Button>
          </DialogActions>
        </Dialog>
      </OutletPage>
    </ModuleGuard>
  );
}

