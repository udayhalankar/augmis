"use client";

import React from "react";
import { Alert, Box, Button, Stack, Typography } from "@mui/material";

import { getCurrentBrowserRoute, reportFrontendLog } from "@/services/clientLogService";


type Props = {
  children: React.ReactNode;
};

type State = {
  hasError: boolean;
};


export default class FrontendErrorBoundary extends React.Component<Props, State> {
  state: State = {
    hasError: false,
  };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    void reportFrontendLog({
      message: error.message || "React render error",
      category: "react_error_boundary",
      level: "ERROR",
      route: getCurrentBrowserRoute(),
      stack: `${error.stack || ""}\n${errorInfo.componentStack || ""}`.trim(),
      component: "app_error_boundary",
      is_critical: true,
      metadata: {
        component_stack: errorInfo.componentStack,
      },
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 3 }}>
          <Stack spacing={2} sx={{ width: "100%", maxWidth: 520 }}>
            <Alert severity="error">
              A frontend rendering error occurred. The incident has been logged for investigation.
            </Alert>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>
              Something went wrong
            </Typography>
            <Typography color="text.secondary">
              Reload the page to recover. If the issue repeats, review AUGMIS Admin Server Logs.
            </Typography>
            <Button variant="contained" onClick={() => window.location.reload()}>
              Reload Page
            </Button>
          </Stack>
        </Box>
      );
    }

    return this.props.children;
  }
}
