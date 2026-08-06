"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  LinearProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

import ModuleGuard from "@/components/auth/ModuleGuard";
import { OutletPage } from "@/components/layout/OutletPage";
import { useSubscription } from "@/context/SubscriptionContext";
import { getPlans } from "@/services/subscriptionService";

function StatCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
        height: "100%",
      }}
    >
      <Typography variant="body2" color="text.secondary">
        {title}
      </Typography>

      <Typography variant="h5" sx={{ fontWeight: 800, mt: 1 }}>
        {value}
      </Typography>

      {subtitle ? (
        <Typography variant="caption" color="text.secondary">
          {subtitle}
        </Typography>
      ) : null}
    </Paper>
  );
}

function UsageBar({
  label,
  used,
  limit,
  suffix = "",
}: {
  label: string;
  used: number;
  limit: number;
  suffix?: string;
}) {
  const percent = limit > 0 ? Math.min((used / limit) * 100, 100) : 0;

  return (
    <Box sx={{ mb: 2.5 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.7 }}>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {label}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {used.toLocaleString()} / {limit.toLocaleString()} {suffix}
        </Typography>
      </Box>

      <LinearProgress
        variant="determinate"
        value={percent}
        sx={{ height: 8, borderRadius: 8 }}
      />
    </Box>
  );
}

export default function SummaryBillingPage() {
  const { tenant, plan, usage, loading, refreshSubscription } = useSubscription();
  const [plans, setPlans] = useState<any[]>([]);
  const [plansLoading, setPlansLoading] = useState(true);

  useEffect(() => {
    getPlans()
      .then((res) => {
        if (res.success) {
          setPlans(res.data);
        }
      })
      .finally(() => setPlansLoading(false));
  }, []);

  if (loading || plansLoading) {
    return (
      <ModuleGuard moduleName="settings" permission="admin:settings">
        <OutletPage title="Summary & Billing">
          <Stack sx={{ p: 4, alignItems: "flex-start" }} direction="row" spacing={2}>
            <CircularProgress size={24} />
            <Typography>Loading summary and billing...</Typography>
          </Stack>
        </OutletPage>
      </ModuleGuard>
    );
  }

  return (
    <ModuleGuard moduleName="settings" permission="admin:settings">
      <OutletPage
        title="Summary & Billing"
      >
        <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
          <Button variant="outlined" onClick={refreshSubscription}>
            Refresh Usage
          </Button>
        </Box>

        {!tenant || !plan || !usage ? (
          <Alert severity="warning">
            Subscription context could not be loaded.
          </Alert>
        ) : (
          <>
            <Grid container spacing={2.5}>
              <Grid size={{ xs: 12, md: 3 }}>
                <StatCard
                  title="Tenant"
                  value={tenant.tenant_name}
                  subtitle={tenant.tenant_id}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <StatCard
                  title="Current Plan"
                  value={plan.plan_name}
                  subtitle={`${plan.currency} ${plan.price_monthly}/month`}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <StatCard
                  title="Subscription"
                  value={tenant.subscription_status}
                  subtitle={`Ends: ${tenant.subscription_end || "Not set"}`}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <StatCard
                  title="Billing"
                  value={tenant.billing_status}
                  subtitle="Payment status"
                />
              </Grid>
            </Grid>

            <Grid container spacing={2.5} sx={{ mt: 1 }}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 2.5,
                    borderRadius: 3,
                    border: "1px solid",
                    borderColor: "divider",
                    height: "100%",
                  }}
                >
                  <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                    Usage Limits
                  </Typography>

                  <UsageBar
                    label="Users"
                    used={Number(usage.users_count || 0)}
                    limit={Number(plan.max_users || 0)}
                  />
                  <UsageBar
                    label="Documents"
                    used={Number(usage.documents_count || 0)}
                    limit={Number(plan.max_documents || 0)}
                  />
                  <UsageBar
                    label="Storage"
                    used={Number(usage.storage_used_mb || 0)}
                    limit={Number(plan.max_storage_mb || 0)}
                    suffix="MB"
                  />
                  <UsageBar
                    label="AI Tokens"
                    used={Number(usage.ai_tokens_used || 0)}
                    limit={Number(plan.monthly_ai_tokens || 0)}
                  />
                </Paper>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 2.5,
                    borderRadius: 3,
                    border: "1px solid",
                    borderColor: "divider",
                    height: "100%",
                  }}
                >
                  <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                    Enabled Modules
                  </Typography>

                  <Stack direction="row" gap={1} sx={{ flexWrap: "wrap" }}>
                    {plan.allowed_modules.map((module: string) => (
                      <Chip
                        key={module}
                        label={module}
                        color="success"
                        variant="outlined"
                      />
                    ))}
                  </Stack>

                  <Divider sx={{ my: 2.5 }} />

                  <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                    Plan Features
                  </Typography>

                  <Stack gap={1}>
                    {plan.features.map((feature: string) => (
                      <Typography key={feature} variant="body2">
                        • {feature}
                      </Typography>
                    ))}
                  </Stack>
                </Paper>
              </Grid>
            </Grid>

            <Paper
              elevation={0}
              sx={{
                mt: 3,
                p: 2.5,
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>
                Available SaaS Plans
              </Typography>

              <Grid container spacing={2.5}>
                {plans.map((p) => (
                  <Grid size={{ xs: 12, md: 4 }} key={p.plan_id}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2.5,
                        borderRadius: 3,
                        border: "1px solid",
                        borderColor:
                          p.plan_id === plan.plan_id ? "primary.main" : "divider",
                        height: "100%",
                      }}
                    >
                      <Typography variant="h6" sx={{ fontWeight: 800 }}>
                        {p.plan_name}
                      </Typography>

                      <Typography variant="h5" sx={{ fontWeight: 800, mt: 1 }}>
                        {p.price_monthly === 0
                          ? "Custom"
                          : `${p.currency} ${p.price_monthly}`}
                      </Typography>

                      <Typography variant="caption" color="text.secondary">
                        Monthly subscription
                      </Typography>

                      <Divider sx={{ my: 2 }} />

                      <Typography variant="body2">
                        Max Users: {p.max_users}
                      </Typography>
                      <Typography variant="body2">
                        Max Documents: {p.max_documents}
                      </Typography>
                      <Typography variant="body2">
                        Storage: {p.max_storage_mb} MB
                      </Typography>
                      <Typography variant="body2">
                        AI Tokens: {p.monthly_ai_tokens.toLocaleString()}
                      </Typography>

                      <Stack direction="row" gap={1} sx={{ mt: 2, flexWrap: "wrap" }}>
                        {p.allowed_modules.map((m: string) => (
                          <Chip key={m} label={m} size="small" />
                        ))}
                      </Stack>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          </>
        )}
      </OutletPage>
    </ModuleGuard>
  );
}

