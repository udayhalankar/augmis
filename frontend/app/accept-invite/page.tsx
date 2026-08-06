"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
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
import { acceptInvite, getInvite } from "@/services/authService";

export default function AcceptInvitePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = useMemo(() => searchParams.get("token") || "", [searchParams]);
  const [invite, setInvite] = useState<any>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingInvite, setLoadingInvite] = useState(true);
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });

  useEffect(() => {
    async function loadInvite() {
      if (!token) {
        setLoadingInvite(false);
        return;
      }
      try {
        const result = await getInvite(token);
        setInvite(result.data);
        setForm((current) => ({
          ...current,
          email: result.data?.email || "",
        }));
      } catch (inviteError: any) {
        setError(
          inviteError?.response?.data?.detail || "Unable to validate invite."
        );
      } finally {
        setLoadingInvite(false);
      }
    }

    void loadInvite();
  }, [token]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!token) {
      setError("Invite token is missing from the URL.");
      return;
    }
    if (form.password !== form.confirmPassword) {
      setError("Password and confirm password must match.");
      return;
    }

    setLoading(true);
    try {
      const result = await acceptInvite(token, {
        name: form.name,
        email: form.email,
        password: form.password,
      });
      localStorage.setItem("infomentica_token", result.access_token);
      localStorage.setItem("infomentica_refresh_token", result.refresh_token);
      localStorage.setItem("infomentica_user", JSON.stringify(result.user));
      setMessage(result.success ? "Invite accepted. Redirecting to your workspace..." : "Invite accepted.");
      window.setTimeout(() => {
        router.push("/");
      }, 800);
    } catch (inviteError: any) {
      setError(
        inviteError?.response?.data?.detail || "Unable to accept invite."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Guided Onboarding"
      title="Accept Workspace Invite"
      description="Finish your invited user setup with a secure self-service password flow."
      footer={
        <Typography variant="body2" color="text.secondary">
          Already onboarded? Continue to <Link href="/login">login</Link>.
        </Typography>
      }
    >
      {message ? <Alert severity="success">{message}</Alert> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}

      {loadingInvite ? (
        <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
          <CircularProgress size={22} />
          <Typography color="text.secondary">Validating invite...</Typography>
        </Stack>
      ) : (
        <>
          {invite ? (
            <Alert severity="info">
              Invited to <strong>{invite.tenant_name || "workspace"}</strong> as{" "}
              <strong>{invite.role}</strong>. The invite is reserved for{" "}
              <strong>{invite.email}</strong>.
            </Alert>
          ) : null}

          <Box component="form" onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Full Name"
              value={form.name}
              onChange={(event) =>
                setForm({ ...form, name: event.target.value })
              }
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Email"
              value={form.email}
              disabled
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              type="password"
              label="Password"
              autoComplete="new-password"
              value={form.password}
              onChange={(event) =>
                setForm({ ...form, password: event.target.value })
              }
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              type="password"
              label="Confirm Password"
              autoComplete="new-password"
              value={form.confirmPassword}
              onChange={(event) =>
                setForm({ ...form, confirmPassword: event.target.value })
              }
              sx={{ mb: 3 }}
            />
            <Button
              fullWidth
              type="submit"
              variant="contained"
              disabled={loading || !token || !invite}
            >
              {loading ? <CircularProgress size={22} /> : "Accept Invite"}
            </Button>
          </Box>
        </>
      )}
    </AuthShell>
  );
}
