"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  TextField,
  Typography,
} from "@mui/material";

import { AuthShell } from "@/components/auth/AuthShell";
import { resetPasswordWithLink } from "@/services/authService";

export default function ResetPasswordPage() {
  const searchParams = useSearchParams();
  const token = useMemo(() => searchParams.get("token") || "", [searchParams]);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!token) {
      setError("Reset token is missing from the link.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("New password and confirm password must match.");
      return;
    }

    setLoading(true);
    try {
      const result = await resetPasswordWithLink({
        token,
        new_password: newPassword,
      });
      setMessage(result.message || "Password reset completed.");
      setNewPassword("");
      setConfirmPassword("");
    } catch (resetError: any) {
      setError(
        resetError?.response?.data?.detail || "Unable to reset password."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Tokenized Recovery"
      title="Reset Password"
      description="Use the secure email link to set a new password for your workspace account."
      footer={
        <Typography variant="body2" color="text.secondary">
          Need a fresh link? Go back to <Link href="/forgot-password">forgot password</Link>.
        </Typography>
      }
    >
      {message ? <Alert severity="success">{message}</Alert> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}
      {!token ? (
        <Alert severity="warning">
          This page needs a valid reset token in the URL.
        </Alert>
      ) : null}

      <Box component="form" onSubmit={handleSubmit}>
        <TextField
          fullWidth
          type="password"
          label="New Password"
          autoComplete="new-password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          type="password"
          label="Confirm New Password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          sx={{ mb: 3 }}
        />
        <Button fullWidth type="submit" variant="contained" disabled={loading || !token}>
          {loading ? <CircularProgress size={22} /> : "Set New Password"}
        </Button>
      </Box>
    </AuthShell>
  );
}
