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
import {
  getAuthCapabilities,
  requestPasswordResetOtp,
  requestPasswordResetLink,
  resetPasswordWithOtp,
} from "@/services/authService";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [otpPreview, setOtpPreview] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [requestLoading, setRequestLoading] = useState(false);
  const [linkLoading, setLinkLoading] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [capabilities, setCapabilities] = useState<any>(null);
  const [cooldownUntil, setCooldownUntil] = useState<number>(0);
  const [linkPreview, setLinkPreview] = useState("");
  const [nowMs, setNowMs] = useState(() => Date.now());

  const remainingCooldownSeconds =
    cooldownUntil > nowMs
      ? Math.max(0, Math.ceil((cooldownUntil - nowMs) / 1000))
      : 0;

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

  useEffect(() => {
    if (remainingCooldownSeconds <= 0) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);
    return () => window.clearInterval(timer);
  }, [remainingCooldownSeconds]);

  async function handleRequestOtp(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLinkPreview("");
    setRequestLoading(true);

    try {
      const result = await requestPasswordResetOtp(email);
      setChallengeId(result.challenge_id || "");
      setOtpPreview(result.otp_preview || "");
      setMessage(result.message || "OTP issued.");
      setCooldownUntil(Date.now() + 60000);
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail || "Unable to issue OTP.";
      setError(detail);
      const match = String(detail).match(/Retry after (\d+) seconds/i);
      if (match) {
        setCooldownUntil(Date.now() + Number(match[1]) * 1000);
      }
    } finally {
      setRequestLoading(false);
    }
  }

  async function handleRequestLink() {
    setError("");
    setMessage("");
    setLinkPreview("");
    setLinkLoading(true);
    try {
      const result = await requestPasswordResetLink(email);
      setMessage(result.message || "Reset link issued.");
      setLinkPreview(result.reset_link_preview || "");
    } catch (requestError: any) {
      setError(
        requestError?.response?.data?.detail ||
          "Unable to issue reset link."
      );
    } finally {
      setLinkLoading(false);
    }
  }

  async function handleResetPassword(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (newPassword !== confirmPassword) {
      setError("New password and confirm password must match.");
      return;
    }

    setResetLoading(true);
    try {
      const result = await resetPasswordWithOtp({
        challenge_id: challengeId,
        otp,
        new_password: newPassword,
      });
      setMessage(result.message || "Password reset completed.");
      setOtp("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (resetError: any) {
      setError(
        resetError?.response?.data?.detail ||
          "Unable to reset password."
      );
    } finally {
      setResetLoading(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Account Recovery"
      title="Forgot Password"
      description="Recover tenant access using a one-time passcode flow."
      capabilities={capabilities}
      footer={
        <Typography variant="body2" color="text.secondary">
          Return to <Link href="/login">login</Link> or create a new workspace from <Link href="/register">registration</Link>.
        </Typography>
      }
    >
      {message ? <Alert severity="success">{message}</Alert> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Box component="form" onSubmit={handleRequestOtp}>
        <TextField
          fullWidth
          type="email"
          autoComplete="email"
          label="Account Email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          sx={{ mb: 2 }}
        />
        <Button
          fullWidth
          type="submit"
          variant="contained"
          disabled={requestLoading || remainingCooldownSeconds > 0}
        >
          {requestLoading ? <CircularProgress size={22} /> : remainingCooldownSeconds > 0 ? `Resend OTP in ${remainingCooldownSeconds}s` : "Send OTP"}
        </Button>
      </Box>

      {remainingCooldownSeconds > 0 ? (
        <Typography variant="body2" color="text.secondary">
          OTP resend cooldown is active for {remainingCooldownSeconds} more seconds.
        </Typography>
      ) : null}

      <Button
        fullWidth
        variant="outlined"
        disabled={linkLoading || !capabilities?.reset_link?.available}
        onClick={() => void handleRequestLink()}
      >
        {linkLoading ? <CircularProgress size={22} /> : "Email Reset Link"}
      </Button>

      {linkPreview ? (
        <Alert severity="info">
          Demo reset link preview: <Link href={linkPreview}>Open reset page</Link>
        </Alert>
      ) : null}

      <Divider />

      {challengeId ? (
        <Alert severity="info">
          Challenge ID: {challengeId}
          {otpPreview ? ` • Demo OTP: ${otpPreview}` : ""}
        </Alert>
      ) : (
        <Typography variant="body2" color="text.secondary">
          Request an OTP first, then complete the password reset below.
        </Typography>
      )}

      <Box component="form" onSubmit={handleResetPassword}>
        <TextField
          fullWidth
          label="Challenge ID"
          value={challengeId}
          onChange={(event) => setChallengeId(event.target.value)}
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          slotProps={{ htmlInput: { inputMode: "numeric", pattern: "[0-9]*" } }}
          label="OTP"
          value={otp}
          onChange={(event) => setOtp(event.target.value)}
          sx={{ mb: 2 }}
        />
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
        <Button fullWidth type="submit" variant="outlined" disabled={resetLoading}>
          {resetLoading ? <CircularProgress size={22} /> : "Reset Password"}
        </Button>
      </Box>
    </AuthShell>
  );
}
