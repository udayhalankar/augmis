"use client";

import { type ReactNode, useEffect } from "react";
import { Box, CircularProgress, Typography } from "@mui/material";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/context/AuthContext";
import { isAuthRoute, isPublicRoute } from "./authRouteConfig";

export default function ProtectedRoute({
  children,
}: {
  children: ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get("redirectTo") || "/home";

  useEffect(() => {
    if (!loading && !user && !isPublicRoute(pathname)) {
      router.push("/login");
    }
    if (!loading && user && isAuthRoute(pathname)) {
      router.push(redirectTo);
    }
  }, [loading, pathname, redirectTo, router, user]);

  if (isPublicRoute(pathname)) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <Box
        sx={{
          height: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 2,
        }}
      >
        <CircularProgress size={24} />
        <Typography>Checking secure session...</Typography>
      </Box>
    );
  }

  if (!user) {
    return null;
  }

  return <>{children}</>;
}
