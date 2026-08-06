"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { AuthShell } from "@/components/auth/AuthShell";
import { useAuth } from "@/context/AuthContext";
import { getAuthCapabilities } from "@/services/authService";

export default function SuperAdminLoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("superadmin@augmis.com");
  const [password, setPassword] = useState("admin123");
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

  async function handleLogin(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password, true, {
        requiredRole: "SUPER_ADMIN",
        redirectTo: "/settings/augmis-admin",
      });
    } catch (loginError: any) {
      setError(
        loginError?.response?.data?.detail || "Unable to sign in as AUGMIS Super Admin"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      eyebrow="AUGMIS Master Administration"
      title="Super Admin Sign In"
      description="Access AUGMIS-wide governance, security controls, tenant registration policy, and platform administration."
      capabilities={capabilities}
      footer={
        <Stack spacing={1}>
          <Typography variant="body2" color="text.secondary">
            Bootstrap super admin: superadmin@augmis.com
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Tenant workspace user? <Link href="/login">Use the tenant login</Link>. Forgot your password? <Link href="/forgot-password">Reset it with OTP</Link>.
          </Typography>
        </Stack>
      }
    >
      <Alert severity="info">
        This route is reserved for AUGMIS master administrators only.
      </Alert>

      {error ? <Alert severity="error">{error}</Alert> : null}

      <Box component="form" onSubmit={handleLogin}>
        <TextField
          fullWidth
          type="email"
          autoComplete="email"
          label="AUGMIS Admin Email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          sx={{ mb: 2 }}
        />

        <TextField
          fullWidth
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          sx={{ mb: 2 }}
        />

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Use this page for AUGMIS platform governance and master-admin controls only.
        </Typography>

        <Button
          fullWidth
          size="large"
          type="submit"
          variant="contained"
          disabled={loading}
        >
          {loading ? <CircularProgress size={22} /> : "Login as Super Admin"}
        </Button>
      </Box>

      <Divider>or</Divider>

      <Button
        fullWidth
        size="large"
        variant="outlined"
        disabled={!capabilities?.google_login?.available}
      >
        Continue with Google
      </Button>

      {!capabilities?.google_login?.available ? (
        <Typography variant="body2" color="text.secondary">
          Google login remains disabled until AUGMIS platform OAuth credentials are configured.
        </Typography>
      ) : null}
    </AuthShell>
  );
}
