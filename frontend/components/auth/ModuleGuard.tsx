"use client";

import { type ReactNode } from "react";
import { Box, CircularProgress, Typography } from "@mui/material";

import { useAuth } from "@/context/AuthContext";
import AccessDenied from "./AccessDenied";

type ModuleGuardProps = {
  moduleName: string;
  permission?: string;
  children: ReactNode;
};

export default function ModuleGuard({
  moduleName,
  permission,
  children,
}: ModuleGuardProps) {
  const { loading, hasModule, hasPermission } = useAuth();

  if (loading) {
    return (
      <Box sx={{ p: 4, display: "flex", alignItems: "center", gap: 2 }}>
        <CircularProgress size={24} />
        <Typography>Checking module access...</Typography>
      </Box>
    );
  }

  const moduleAllowed = hasModule(moduleName);
  const permissionAllowed = permission ? hasPermission(permission) : true;

  if (!moduleAllowed || !permissionAllowed) {
    return <AccessDenied />;
  }

  return <>{children}</>;
}
