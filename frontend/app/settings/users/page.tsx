"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
  IconButton,
} from "@mui/material";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import DeleteOutlineOutlinedIcon from "@mui/icons-material/DeleteOutlineOutlined";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import {
  createTenantUser,
  createUserInvite,
  deleteTenantUser,
  getTenantUsers,
  updateTenantUser,
} from "@/services/authService";

const modulePermissionMap: Record<string, string[]> = {
  dashboard: ["dashboard:view"],
  copilot: ["copilot:use"],
  documents: ["documents:read", "documents:upload"],
  escalations: ["escalation:read", "escalation:manage"],
  augmis_business: [
    "business_development:read",
    "business_development:create",
    "business_development:update",
    "business_development:delete",
    "business_development:scan",
    "business_development:qualify",
    "business_development:outreach",
    "business_development:admin",
  ],
  settings: ["admin:settings", "admin:users"],
};

const roles = [
  "SUPER_ADMIN",
  "TENANT_ADMIN",
  "EXECUTIVE",
  "MANAGER",
  "ANALYST",
  "VIEWER",
];

export default function UserManagementPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [selectedUserId, setSelectedUserId] = useState("");

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "admin123",
    role: "VIEWER",
    status: "ACTIVE",
    allowed_modules: ["dashboard"],
    permissions: ["dashboard:view"],
  });
  const [inviteForm, setInviteForm] = useState({
    email: "",
    role: "VIEWER",
    status: "ACTIVE",
    allowed_modules: ["dashboard"],
    permissions: ["dashboard:view"],
  });
  const [editForm, setEditForm] = useState({
    name: "",
    email: "",
    role: "VIEWER",
    status: "ACTIVE",
    allowed_modules: ["dashboard"],
    permissions: ["dashboard:view"],
  });

  async function loadUsers() {
    setLoading(true);
    try {
      const result = await getTenantUsers();
      if (result.success) {
        setUsers(result.data);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  const allModules = useMemo(() => Object.keys(modulePermissionMap), []);

  function toggleModule(moduleName: string) {
    const exists = form.allowed_modules.includes(moduleName);

    const nextModules = exists
      ? form.allowed_modules.filter((m) => m !== moduleName)
      : [...form.allowed_modules, moduleName];

    const nextPermissions = nextModules.flatMap(
      (m) => modulePermissionMap[m] || []
    );

    setForm({
      ...form,
      allowed_modules: nextModules,
      permissions: Array.from(new Set(nextPermissions)),
    });
  }

  function togglePermission(permission: string) {
    const exists = form.permissions.includes(permission);

    const nextPermissions = exists
      ? form.permissions.filter((p) => p !== permission)
      : [...form.permissions, permission];

    setForm({
      ...form,
      permissions: nextPermissions,
    });
  }

  function toggleEditModule(moduleName: string) {
    const exists = editForm.allowed_modules.includes(moduleName);
    const nextModules = exists
      ? editForm.allowed_modules.filter((m) => m !== moduleName)
      : [...editForm.allowed_modules, moduleName];
    const nextPermissions = nextModules.flatMap(
      (m) => modulePermissionMap[m] || []
    );

    setEditForm({
      ...editForm,
      allowed_modules: nextModules,
      permissions: Array.from(new Set(nextPermissions)),
    });
  }

  function toggleEditPermission(permission: string) {
    const exists = editForm.permissions.includes(permission);
    const nextPermissions = exists
      ? editForm.permissions.filter((p) => p !== permission)
      : [...editForm.permissions, permission];

    setEditForm({
      ...editForm,
      permissions: nextPermissions,
    });
  }

  function applyRolePreset(role: string) {
    let allowed_modules: string[] = [];
    let permissions: string[] = [];

    if (role === "TENANT_ADMIN") {
      allowed_modules = allModules;
      permissions = allModules.flatMap((m) => modulePermissionMap[m]);
    }

    if (role === "EXECUTIVE") {
      allowed_modules = [
        "dashboard",
        "copilot",
        "documents",
        "escalations",
        "augmis_business",
      ];
      permissions = [
        "dashboard:view",
        "copilot:use",
        "documents:read",
        "escalation:read",
        "business_development:read",
      ];
    }

    if (role === "MANAGER") {
      allowed_modules = ["dashboard", "copilot", "documents", "augmis_business"];
      permissions = [
        "dashboard:view",
        "copilot:use",
        "documents:read",
        "business_development:read",
        "business_development:create",
        "business_development:update",
        "business_development:qualify",
      ];
    }

    if (role === "ANALYST") {
      allowed_modules = ["dashboard", "documents", "augmis_business"];
      permissions = [
        "dashboard:view",
        "documents:read",
        "business_development:read",
      ];
    }

    if (role === "VIEWER") {
      allowed_modules = ["dashboard"];
      permissions = ["dashboard:view"];
    }

    setForm({
      ...form,
      role,
      allowed_modules,
      permissions,
    });
  }

  function applyEditRolePreset(role: string) {
    let allowed_modules: string[] = [];
    let permissions: string[] = [];

    if (role === "TENANT_ADMIN") {
      allowed_modules = allModules;
      permissions = allModules.flatMap((m) => modulePermissionMap[m]);
    }
    if (role === "EXECUTIVE") {
      allowed_modules = [
        "dashboard",
        "copilot",
        "documents",
        "escalations",
        "augmis_business",
      ];
      permissions = [
        "dashboard:view",
        "copilot:use",
        "documents:read",
        "escalation:read",
        "business_development:read",
      ];
    }
    if (role === "MANAGER") {
      allowed_modules = ["dashboard", "copilot", "documents", "augmis_business"];
      permissions = [
        "dashboard:view",
        "copilot:use",
        "documents:read",
        "business_development:read",
        "business_development:create",
        "business_development:update",
        "business_development:qualify",
      ];
    }
    if (role === "ANALYST") {
      allowed_modules = ["dashboard", "documents", "augmis_business"];
      permissions = [
        "dashboard:view",
        "documents:read",
        "business_development:read",
      ];
    }
    if (role === "VIEWER") {
      allowed_modules = ["dashboard"];
      permissions = ["dashboard:view"];
    }

    setEditForm({
      ...editForm,
      role,
      allowed_modules,
      permissions,
    });
  }

  async function handleCreateUser() {
    setError("");
    setSuccessMessage("");
    setSaving(true);

    try {
      const result = await createTenantUser(form);

      if (!result.success) {
        setError("Unable to create user");
        return;
      }

      setDialogOpen(false);
      setForm({
        name: "",
        email: "",
        password: "admin123",
        role: "VIEWER",
        status: "ACTIVE",
        allowed_modules: ["dashboard"],
        permissions: ["dashboard:view"],
      });

      await loadUsers();
      setSuccessMessage("Tenant user created successfully.");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to create user");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateInvite() {
    setError("");
    setSuccessMessage("");
    setSaving(true);

    try {
      const result = await createUserInvite(inviteForm);
      if (!result.success) {
        setError("Unable to create invite");
        return;
      }

      setInviteDialogOpen(false);
      setInviteForm({
        email: "",
        role: "VIEWER",
        status: "ACTIVE",
        allowed_modules: ["dashboard"],
        permissions: ["dashboard:view"],
      });
      setSuccessMessage(
        result.accept_url_preview
          ? `Invite created. Demo link: ${result.accept_url_preview}`
          : "Invite created successfully."
      );
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to create invite");
    } finally {
      setSaving(false);
    }
  }

  function openEditDialog(user: any) {
    setSelectedUserId(user.user_id);
    setEditForm({
      name: user.name || "",
      email: user.email || "",
      role: user.role || "VIEWER",
      status: user.status || "ACTIVE",
      allowed_modules: user.allowed_modules || ["dashboard"],
      permissions: user.permissions || ["dashboard:view"],
    });
    setEditDialogOpen(true);
  }

  async function handleUpdateUser() {
    setError("");
    setSuccessMessage("");
    setSaving(true);

    try {
      const result = await updateTenantUser(selectedUserId, editForm);
      if (!result.success) {
        setError("Unable to update user");
        return;
      }

      setEditDialogOpen(false);
      setSelectedUserId("");
      await loadUsers();
      setSuccessMessage("Tenant user updated successfully.");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to update user");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteUser(userId: string) {
    if (!window.confirm("Delete this tenant user?")) return;
    setError("");
    setSuccessMessage("");
    setSaving(true);

    try {
      const result = await deleteTenantUser(userId);
      if (!result.success) {
        setError("Unable to delete user");
        return;
      }

      await loadUsers();
      setSuccessMessage("Tenant user deleted successfully.");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to delete user");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <ModuleGuard moduleName="settings" permission="admin:users">
        <Box sx={{ p: 4, display: "flex", alignItems: "center", gap: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading tenant users...</Typography>
        </Box>
      </ModuleGuard>
    );
  }

  return (
    <ModuleGuard moduleName="settings" permission="admin:users">
      <OutletPage
        title="User Management"
        actions={
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" onClick={() => setInviteDialogOpen(true)}>
              Invite User
            </Button>
            <Button variant="contained" onClick={() => setDialogOpen(true)}>
              Add User
            </Button>
          </Stack>
        }
      >
        {successMessage ? (
          <Alert severity="success" sx={{ mb: 3 }}>
            {successMessage}
          </Alert>
        ) : null}

        {error ? (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        ) : null}

        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
            Tenant Users
          </Typography>

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Modules</TableCell>
                <TableCell>Permissions</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {users.map((u) => (
                <TableRow key={u.user_id} hover>
                  <TableCell>{u.name}</TableCell>
                  <TableCell>{u.email}</TableCell>
                  <TableCell>
                    <Chip size="small" label={u.role} />
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={u.status}
                      color={u.status === "ACTIVE" ? "success" : "default"}
                    />
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" gap={0.5} sx={{ flexWrap: "wrap" }}>
                      {u.allowed_modules?.map((m: string) => (
                        <Chip key={m} size="small" label={m} variant="outlined" />
                      ))}
                    </Stack>
                  </TableCell>
                  <TableCell>{u.permissions?.length || 0}</TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end" }}>
                      <IconButton size="small" onClick={() => openEditDialog(u)}>
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => void handleDeleteUser(u.user_id)}
                      >
                        <DeleteOutlineOutlinedIcon fontSize="small" />
                      </IconButton>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>

        <Dialog
          open={editDialogOpen}
          onClose={() => setEditDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle sx={{ fontWeight: 800 }}>Edit Tenant User</DialogTitle>
          <DialogContent>
            <Grid container spacing={2} sx={{ mt: 0.5 }}>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  fullWidth
                  label="Name"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  fullWidth
                  label="Email"
                  value={editForm.email}
                  onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>Role</InputLabel>
                  <Select
                    label="Role"
                    value={editForm.role}
                    onChange={(e) => applyEditRolePreset(e.target.value)}
                  >
                    {roles.map((role) => (
                      <MenuItem key={role} value={role}>
                        {role}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>Status</InputLabel>
                  <Select
                    label="Status"
                    value={editForm.status}
                    onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                  >
                    <MenuItem value="ACTIVE">ACTIVE</MenuItem>
                    <MenuItem value="INACTIVE">INACTIVE</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
              Module Access
            </Typography>
            <Grid container spacing={1}>
              {allModules.map((moduleName) => (
                <Grid size={{ xs: 12, md: 3 }} key={moduleName}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={editForm.allowed_modules.includes(moduleName)}
                        onChange={() => toggleEditModule(moduleName)}
                      />
                    }
                    label={moduleName}
                  />
                </Grid>
              ))}
            </Grid>

            <Divider sx={{ my: 3 }} />
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
              Permissions
            </Typography>
            <Grid container spacing={1}>
              {Array.from(
                new Set(allModules.flatMap((m) => modulePermissionMap[m]))
              ).map((permission) => (
                <Grid size={{ xs: 12, md: 4 }} key={permission}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={editForm.permissions.includes(permission)}
                        onChange={() => toggleEditPermission(permission)}
                      />
                    }
                    label={permission}
                  />
                </Grid>
              ))}
            </Grid>
          </DialogContent>
          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
            <Button
              variant="contained"
              onClick={handleUpdateUser}
              disabled={saving || !editForm.name || !editForm.email}
            >
              {saving ? <CircularProgress size={22} /> : "Save Changes"}
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle sx={{ fontWeight: 800 }}>Create Tenant User</DialogTitle>

          <DialogContent>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Grid container spacing={2} sx={{ mt: 0.5 }}>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  fullWidth
                  label="Name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  fullWidth
                  label="Email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  fullWidth
                  label="Temporary Password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                />
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>Role</InputLabel>
                  <Select
                    label="Role"
                    value={form.role}
                    onChange={(e) => applyRolePreset(e.target.value)}
                  >
                    {roles.map((role) => (
                      <MenuItem key={role} value={role}>
                        {role}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
              Module Access
            </Typography>

            <Grid container spacing={1}>
              {allModules.map((moduleName) => (
                <Grid size={{ xs: 12, md: 3 }} key={moduleName}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={form.allowed_modules.includes(moduleName)}
                        onChange={() => toggleModule(moduleName)}
                      />
                    }
                    label={moduleName}
                  />
                </Grid>
              ))}
            </Grid>

            <Divider sx={{ my: 3 }} />

            <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
              Permissions
            </Typography>

            <Grid container spacing={1}>
              {Array.from(
                new Set(allModules.flatMap((m) => modulePermissionMap[m]))
              ).map((permission) => (
                <Grid size={{ xs: 12, md: 4 }} key={permission}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={form.permissions.includes(permission)}
                        onChange={() => togglePermission(permission)}
                      />
                    }
                    label={permission}
                  />
                </Grid>
              ))}
            </Grid>
          </DialogContent>

          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button
              variant="contained"
              onClick={handleCreateUser}
              disabled={saving || !form.name || !form.email || !form.password}
            >
              {saving ? <CircularProgress size={22} /> : "Create User"}
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog
          open={inviteDialogOpen}
          onClose={() => setInviteDialogOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle sx={{ fontWeight: 800 }}>Invite User</DialogTitle>
          <DialogContent>
            <Alert severity="info" sx={{ mb: 2 }}>
              Invite-based onboarding sends a secure tokenized link so the user sets their own password instead of receiving a shared temporary credential.
            </Alert>
            <Grid container spacing={2} sx={{ mt: 0.5 }}>
              <Grid size={{ xs: 12 }}>
                <TextField
                  fullWidth
                  label="Invitee Email"
                  value={inviteForm.email}
                  onChange={(e) =>
                    setInviteForm({ ...inviteForm, email: e.target.value })
                  }
                />
              </Grid>
              <Grid size={{ xs: 12 }}>
                <FormControl fullWidth>
                  <InputLabel>Role</InputLabel>
                  <Select
                    label="Role"
                    value={inviteForm.role}
                    onChange={(e) => {
                      const role = e.target.value;
                      let allowed_modules = ["dashboard"];
                      let permissions = ["dashboard:view"];
                      if (role === "TENANT_ADMIN") {
                        allowed_modules = allModules;
                        permissions = allModules.flatMap((m) => modulePermissionMap[m]);
                      }
                      if (role === "EXECUTIVE") {
                        allowed_modules = ["dashboard", "copilot", "documents",  "escalations"];
                        permissions = ["dashboard:view", "copilot:use", "documents:read",  "escalation:read"];
                      }
                      if (role === "MANAGER") {
                        allowed_modules = ["dashboard", "copilot", "documents"];
                        permissions = ["dashboard:view", "copilot:use", "documents:read"];
                      }
                      if (role === "ANALYST") {
                        allowed_modules = ["dashboard", "documents"];
                        permissions = ["dashboard:view", "documents:read"];
                      }
                      setInviteForm({
                        ...inviteForm,
                        role,
                        allowed_modules,
                        permissions,
                      });
                    }}
                  >
                    {roles.map((role) => (
                      <MenuItem key={role} value={role}>
                        {role}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setInviteDialogOpen(false)}>Cancel</Button>
            <Button
              variant="contained"
              onClick={handleCreateInvite}
              disabled={saving || !inviteForm.email}
            >
              {saving ? <CircularProgress size={22} /> : "Send Invite"}
            </Button>
          </DialogActions>
        </Dialog>
      </OutletPage>
    </ModuleGuard>
  );
}

