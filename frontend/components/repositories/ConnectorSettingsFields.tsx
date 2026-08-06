"use client";

import { Alert, Box, MenuItem, TextField, Typography } from "@mui/material";


type CapabilityField = {
  key: string;
  label: string;
  type: string;
  placeholder?: string;
  required?: boolean;
  options?: string[];
};

type Capability = {
  status: string;
  settings_enabled: boolean;
  required_fields?: CapabilityField[];
  message: string;
};


export default function ConnectorSettingsFields({
  sourceType,
  capabilities,
  config,
  setConfig,
}: {
  sourceType: string;
  capabilities: Record<string, Capability>;
  config: Record<string, string>;
  setConfig: (value: Record<string, string>) => void;
}) {
  const capability = capabilities?.[sourceType];

  if (!sourceType || !capability) {
    return null;
  }

  const updateValue = (key: string, value: string) => {
    setConfig({
      ...config,
      [key]: value,
    });
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle2" fontWeight={800} sx={{ mb: 1 }}>
        Connector Settings
      </Typography>

      <Alert
        severity={capability.status === "operational" ? "success" : "info"}
        sx={{ mb: 2 }}
      >
        {capability.message}
      </Alert>

      {capability.required_fields?.map((field) => {
        if (field.type === "select") {
          return (
            <TextField
              key={field.key}
              select
              fullWidth
              label={field.label}
              value={config?.[field.key] || ""}
              onChange={(e) => updateValue(field.key, e.target.value)}
              required={field.required}
              disabled={!capability.settings_enabled}
              sx={{ mb: 2 }}
            >
              {(field.options || []).map((option) => (
                <MenuItem key={option} value={option}>
                  {option}
                </MenuItem>
              ))}
            </TextField>
          );
        }

        return (
          <TextField
            key={field.key}
            fullWidth
            type={field.type === "password" ? "password" : "text"}
            label={field.label}
            placeholder={field.placeholder || ""}
            value={config?.[field.key] || ""}
            onChange={(e) => updateValue(field.key, e.target.value)}
            required={field.required}
            disabled={!capability.settings_enabled}
            sx={{ mb: 2 }}
          />
        );
      })}
    </Box>
  );
}
