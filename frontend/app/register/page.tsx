"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { AuthShell } from "@/components/auth/AuthShell";
import { useAuth } from "@/context/AuthContext";
import { getAuthCapabilities } from "@/services/authService";

export default function RegisterPage() {
  const { register } = useAuth();
  const [form, setForm] = useState({
    tenant_name: "",
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    plan_id: "PLAN-ENTERPRISE",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [capabilities, setCapabilities] = useState<any>(null);

  useEffect(() => {
    async function loadCapabilities() {
      try {
        const data = await getAuthCapabilities();
        setCapabilities(data?.data || null);
      } catch {
        setCapabilities(null);
      }
    }

    void loadCapabilities();
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");

    if (form.password !== form.confirmPassword) {
      setError("Password and confirm password must match.");
      return;
    }

    setLoading(true);
    try {
      await register({
        tenant_name: form.tenant_name,
        name: form.name,
        email: form.email,
        password: form.password,
        plan_id: form.plan_id,
      });
    } catch (registerError: any) {
      setError(
        registerError?.response?.data?.detail ||
          "Unable to create workspace."
      );
    } finally {
      setLoading(false);
    }
  }

  function updateField(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <AuthShell
      eyebrow="New Tenant Onboarding"
      title="Create Workspace"
      description="Register a new Augmis workspace and create the first tenant administrator in one secure flow."
      capabilities={capabilities}
      footer={
        <Typography variant="body2" color="text.secondary">
          Already have an account? <Link href="/login">Back to login</Link>.
        </Typography>
      }
    >
      <Alert severity="info">
        This first version creates an Enterprise trial workspace and signs in the initial tenant administrator immediately after registration.
      </Alert>

      {capabilities && !capabilities?.registration?.available ? (
        <Alert severity="warning">
          Self-registration is currently disabled for this deployment. Ask the AUGMIS master administrator to enable it.
        </Alert>
      ) : null}

      {error ? <Alert severity="error">{error}</Alert> : null}

      <Box component="form" onSubmit={handleSubmit}>
        <TextField
          fullWidth
          label="Workspace Name"
          autoComplete="organization"
          value={form.tenant_name}
          onChange={(event) => updateField("tenant_name", event.target.value)}
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          label="Administrator Name"
          autoComplete="name"
          value={form.name}
          onChange={(event) => updateField("name", event.target.value)}
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          type="email"
          autoComplete="email"
          label="Business Email"
          value={form.email}
          onChange={(event) => updateField("email", event.target.value)}
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          type="password"
          label="Password"
          autoComplete="new-password"
          value={form.password}
          onChange={(event) => updateField("password", event.target.value)}
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          type="password"
          label="Confirm Password"
          autoComplete="new-password"
          value={form.confirmPassword}
          onChange={(event) => updateField("confirmPassword", event.target.value)}
          sx={{ mb: 3 }}
        />

        <Button
          fullWidth
          size="large"
          type="submit"
          variant="contained"
          disabled={loading || capabilities?.registration?.available === false}
        >
          {loading ? <CircularProgress size={22} /> : "Create Workspace"}
        </Button>
      </Box>

      <Stack spacing={0.75}>
        <Typography variant="body2" color="text.secondary">
          Included in this rollout:
        </Typography>
        <Typography variant="body2" color="text.secondary">
          1. Self-registration for a new tenant workspace.
        </Typography>
        <Typography variant="body2" color="text.secondary">
          2. Immediate admin sign-in after successful registration.
        </Typography>
        <Typography variant="body2" color="text.secondary">
          3. Capability-gated Google login and MFA placeholders for future secure provider setup.
        </Typography>
      </Stack>
    </AuthShell>
  );
}
