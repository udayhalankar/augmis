"use client";

import { useContext, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  AppBar,
  Avatar,
  Box,
  Button,
  Chip,
  Toolbar,
  Typography,
} from "@mui/material";

import { ColorModeContext } from "@/theme/ThemeContextProvider";
import { getShellTokens } from "@/theme/theme";
import { useAuth } from "@/context/AuthContext";
import { useSubscription } from "@/context/SubscriptionContext";

export default function Topbar() {
  const { shellMode, setShellMode } = useContext(ColorModeContext);
  const { user, logout } = useAuth();
  const { plan, tenant } = useSubscription();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const shell = getShellTokens(shellMode);
  const isCool = shellMode === "COOL";
  const sidebarWidth = 225;
  const [pageMeta, setPageMeta] = useState({ title: "", description: "" });
  const [searchText, setSearchText] = useState(
    pathname === "/search" ? searchParams.get("q") || "" : ""
  );

  const topbarTitle = useMemo(() => pageMeta.title || "Workspace", [pageMeta.title]);
  const topbarDescription = useMemo(() => pageMeta.description || "", [pageMeta.description]);

  useEffect(() => {
    if (pathname === "/search") {
      setSearchText(searchParams.get("q") || "");
      return;
    }

    setSearchText("");
  }, [pathname, searchParams]);

  useEffect(() => {
    function handlePageMeta(event: Event) {
      const detail = (event as CustomEvent<{ title?: string; description?: string }>).detail;
      setPageMeta({
        title: detail?.title?.trim() || "",
        description: detail?.description?.trim() || "",
      });
    }

    window.addEventListener("augmis:outlet-page-meta", handlePageMeta as EventListener);
    return () => {
      window.removeEventListener("augmis:outlet-page-meta", handlePageMeta as EventListener);
    };
  }, []);

  function runSearch() {
    const query = searchText.trim();
    if (!query) return;
    router.push(`/search?q=${encodeURIComponent(query)}`);
  }

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        left: isCool ? `${sidebarWidth}px` : 0,
        width: isCool ? `calc(100% - ${sidebarWidth}px)` : "100%",
        bgcolor: shell.topbarBg,
        color: shell.topbarText,
        borderBottom: "1px solid",
        borderColor: shell.topbarBorder,
        boxShadow: shell.topbarShadow,
        transition: "left 220ms ease, width 220ms ease",
      }}
    >
      <Toolbar
        sx={{
          justifyContent: "space-between",
          gap: 1.25,
          minHeight: shell.topbarHeight,
          position: "relative",
          px: shellMode === "COOL" ? 1.5 : undefined,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.75, minWidth: isCool ? 0 : 208, flex: 1 }}>
          {!isCool ? (
            <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <Link href="/home" aria-label="Go to home page">
                <Box
                  component="img"
                  src="/augmis-logocombined1-26june2026.png"
                  alt="Augmis branding logo"
                  sx={{
                    height: 48,
                    width: "auto",
                    display: "block",
                    mt: "1px",
                  }}
                />
              </Link>
            </Box>
          ) : null}

          <Box sx={{ minWidth: 0 }}>
            <Typography
              component="div"
              sx={{
                fontWeight: 700,
                letterSpacing: "-0.02em",
                color: shell.topbarText,
                fontSize: isCool ? "1rem" : "1.05rem",
                lineHeight: 1.1,
                mb: 0.6,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {topbarTitle}
            </Typography>
            {topbarDescription ? (
              <Typography
                component="div"
                sx={{
                  color: shellMode === "COOL" ? "#61748E" : "#64748B",
                  fontSize: 12,
                  lineHeight: 1.2,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  maxWidth: isCool ? "44vw" : "32vw",
                }}
              >
                {topbarDescription}
              </Typography>
            ) : null}
          </Box>
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, pl: 1 }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 0.5,
              p: 0.25,
              borderRadius: 999,
              bgcolor: shellMode === "COOL" ? "#E8EEF8" : "#F8FAFC",
              border: `1px solid ${shell.topbarBorder}`,
            }}
          >
            {(["SIMPLE", "COOL"] as const).map((value) => {
              const selected = shellMode === value;
              return (
                <Button
                  key={value}
                  size="small"
                  variant={selected ? "contained" : "text"}
                  onClick={() => setShellMode(value)}
                  sx={{
                    minWidth: 62,
                    minHeight: 28,
                    px: 1.15,
                    py: 0.35,
                    fontSize: 10.5,
                    fontWeight: 700,
                    color: selected
                      ? "#FFFFFF"
                      : shellMode === "COOL"
                        ? "#49617F"
                        : "#475569",
                    bgcolor: selected
                      ? shellMode === "COOL"
                        ? "#17335C"
                        : "#2563EB"
                      : "transparent",
                    boxShadow: "none",
                    "&:hover": {
                      bgcolor: selected
                        ? shellMode === "COOL"
                          ? "#17335C"
                          : "#2563EB"
                        : shellMode === "COOL"
                          ? "rgba(23, 51, 92, 0.06)"
                          : "rgba(37, 99, 235, 0.06)",
                      boxShadow: "none",
                    },
                  }}
                >
                  {value}
                </Button>
              );
            })}
          </Box>

          {user ? (
            <Box sx={{ textAlign: "right", mr: shellMode === "COOL" ? 0.15 : 0.6 }}>
              <Typography
                variant="body2"
                sx={{ fontWeight: 700, lineHeight: 1.05, color: shell.topbarText, fontSize: 13 }}
              >
                {user.name}
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  display: "block",
                  color: shellMode === "COOL" ? "#8AA0BC" : "#475569",
                  fontSize: 10.5,
                  lineHeight: 1.05,
                }}
              >
                {tenant?.tenant_name} {plan?.plan_name ? `· ${plan.plan_name}` : ""}
              </Typography>
            </Box>
          ) : null}

          {shellMode === "COOL" && user ? (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.7,
                px: 0.9,
                py: 0.35,
                borderRadius: 999,
                bgcolor: shell.topbarMetaBg,
                color: shell.topbarMetaText,
              }}
            >
              <Avatar sx={{ width: 26, height: 26, bgcolor: "#334E77", color: "#ffffff", fontSize: 13 }}>
                {(user?.name || "I").charAt(0).toUpperCase()}
              </Avatar>
              <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1, fontSize: 12.5 }}>
                {user.name}
              </Typography>
              <Chip
                label={plan?.plan_name || "ACTIVE"}
                size="small"
                sx={{
                  height: 18,
                  bgcolor: shell.topbarMetaBadgeBg,
                  color: shell.topbarMetaBadgeText,
                  fontWeight: 700,
                  fontSize: 10,
                  "& .MuiChip-label": {
                    px: 0.7,
                  },
                }}
              />
            </Box>
          ) : (
            <Avatar sx={{ width: 28, height: 28, bgcolor: "#94a3b8", color: "#ffffff", fontSize: 13 }}>
              {(user?.name || "I").charAt(0).toUpperCase()}
            </Avatar>
          )}

          <Button
            variant="outlined"
            size="small"
            onClick={logout}
            sx={{
              borderColor: shellMode === "COOL" ? "#CBD6E6" : "#cbd5e1",
              color: shell.topbarText,
              minHeight: 30,
              px: 1.2,
              fontSize: 12,
              "&:hover": {
                borderColor: shellMode === "COOL" ? "#9FB3CF" : "#94a3b8",
                bgcolor: shellMode === "COOL" ? "#F8FBFF" : "#f8fafc",
              },
            }}
          >
            Logout
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
