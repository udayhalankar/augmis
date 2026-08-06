"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Divider,
  FormControlLabel,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { AuthShell } from "@/components/auth/AuthShell";
import { useAuth } from "@/context/AuthContext";
import { getAuthCapabilities } from "@/services/authService";

export default function LoginPage() {
  const { login } = useAuth();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("admin@infomentica.com");
  const [password, setPassword] = useState("admin123");
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [capabilities, setCapabilities] = useState<any>(null);
  const redirectTo = searchParams.get("redirectTo") || "/home";

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
      await login(email, password, rememberMe, { redirectTo });
    } catch (loginError: any) {
      setError(
        loginError?.response?.data?.detail || "Invalid email or password"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Sign In"
      description="Access your tenant workspace, repository-backed dashboards, and governed AI copilots."
      capabilities={capabilities}
      footer={
        <Stack spacing={1}>
          <Typography variant="body2" color="text.secondary">
            Demo users: admin@infomentica.com / vendor@infomentica.com
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Need a workspace? <Link href="/register">Create one here</Link>. Forgot your password? <Link href="/forgot-password">Reset it with OTP</Link>.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            AUGMIS platform admin? <Link href="/super-admin/login">Use the Super Admin login</Link>.
          </Typography>
        </Stack>
      }
    >
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Box component="form" onSubmit={handleLogin}>
        <TextField
          fullWidth
          type="email"
          autoComplete="email"
          label="Email"
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
          sx={{ mb: 1.5 }}
        />

        <Stack direction="row" sx={{ justifyContent: "space-between", mb: 3 }}>
          <Typography variant="body2" color="text.secondary">
            Use enterprise credentials for your tenant workspace.
          </Typography>
          <Link href="/forgot-password">Forgot password?</Link>
        </Stack>

        <FormControlLabel
          control={
            <Checkbox
              checked={rememberMe}
              onChange={(event) => setRememberMe(event.target.checked)}
            />
          }
          label="Remember this device"
          sx={{ mb: 2 }}
        />

        <Button
          fullWidth
          size="large"
          type="submit"
          variant="contained"
          disabled={loading}
        >
          {loading ? <CircularProgress size={22} /> : "Login"}
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
          Google login is shown here for design uniformity, but remains disabled until OAuth client credentials are configured.
        </Typography>
      ) : null}
    </AuthShell>
  );
}
