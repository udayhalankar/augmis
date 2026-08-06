"use client";

import { useContext, useEffect, useMemo, useState } from "react";
import { Box, ThemeProvider, useTheme } from "@mui/material";
import { usePathname } from "next/navigation";
import Topbar from "./Topbar";
import { ColorModeContext } from "@/theme/ThemeContextProvider";
import { getOutletTheme, getShellTokens } from "@/theme/theme";
import UnifiedSidebar from "./sidebar/UnifiedSideBar";

const SIDEBAR_EXPANDED_WIDTH = 213;
const SIDEBAR_COLLAPSED_WIDTH = 67;
const SIDEBAR_STORAGE_KEY = "augmis_sidebar_collapsed";

export default function EnterpriseShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const theme = useTheme();
  const { shellMode } = useContext(ColorModeContext);
  const shell = useMemo(() => getShellTokens(shellMode), [shellMode]);
  const outletTheme = useMemo(
    () => getOutletTheme(theme, shellMode),
    [theme, shellMode]
  );
  const isCool = shellMode === "COOL";
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const hideSidebar = pathname === "/home";

  useEffect(() => {
    const savedState =
      typeof window !== "undefined"
        ? window.localStorage.getItem(SIDEBAR_STORAGE_KEY)
        : null;
    setSidebarCollapsed(savedState === "true");
  }, []);

  function handleToggleSidebar() {
    setSidebarCollapsed((current) => {
      const next = !current;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next));
      }
      return next;
    });
  }

  const sidebarWidth = sidebarCollapsed
    ? SIDEBAR_COLLAPSED_WIDTH
    : SIDEBAR_EXPANDED_WIDTH;
  const mainOffset = hideSidebar ? 0 : sidebarWidth;
  const topPadding = isCool
    ? `calc(${shell.contentTopPadding} + 12px)`
    : shell.contentTopPadding;

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: shell.appBg }}>
      {!hideSidebar ? (
        <UnifiedSidebar
          collapsed={sidebarCollapsed}
          onToggleCollapse={handleToggleSidebar}
        />
      ) : null}
      <Topbar />

      <ThemeProvider theme={outletTheme}>
        <Box
          component="main"
          sx={{
            "--outlet-grid-gap": "16px",
            ml: `${mainOffset}px`,
            width: hideSidebar ? "100%" : `calc(100% - ${mainOffset}px)`,
            boxSizing: "border-box",
            pt: topPadding,
            px: shell.contentHorizontalPadding,
            pb: 2,
            bgcolor: shell.mainBg,
            color: "text.primary",
            overflowX: "hidden",
            boxShadow: shell.mainShadow,
            transition:
              "margin-left 220ms ease, width 220ms ease, background-color 220ms ease",
            "& .outlet-page": {
              px: shellMode === "COOL" ? 2 : 3,
            },
            "& .outlet-page__header": {
              mb: 3,
              justifyContent: "space-between",
              alignItems: { xs: "flex-start", md: "flex-start" },
              gap: 2,
            },
            "& .outlet-page__copy": {
              minWidth: 0,
            },
            "& .outlet-page__title": {
              fontWeight: shellMode === "COOL" ? 700 : 500,
              lineHeight: shellMode === "COOL" ? 1.02 : 1.1,
              letterSpacing: shellMode === "COOL" ? "-0.02em" : undefined,
              mb: 0.75,
            },
            "& .outlet-page__description": {
              color: "text.secondary",
              maxWidth: "72ch",
            },
            "& .MuiPaper-root": {
              borderColor: shell.mainBorder,
            },
            "& .outlet-page__actions": {
              display: "flex",
              alignItems: "flex-start",
              gap: 1.5,
              flexShrink: 0,
            },
            "& .copilot-chat__message": {
              fontSize: (currentTheme) => currentTheme.typography.body1.fontSize,
              lineHeight: 1.6,
              color: "text.primary",
            },
            "& .copilot-chat__message p": {
              fontSize: "inherit",
              lineHeight: "inherit",
            },
            "& .copilot-chat__message li": {
              fontSize: "inherit",
              lineHeight: "inherit",
            },
            "& .MuiGrid-container": {
              "--Grid-rowSpacing": "var(--outlet-grid-gap)",
              "--Grid-columnSpacing": "var(--outlet-grid-gap)",
            },
            "& .work-area-page .work-area-metric-card__title": {
              fontSize: (currentTheme) => currentTheme.typography.body2.fontSize,
            },
            "& .work-area-page .work-area-metric-card__value": {
              fontSize: (currentTheme) => currentTheme.typography.h4.fontSize,
            },
            "& .work-area-page .work-area-metric-card__subtitle": {
              fontSize: (currentTheme) => currentTheme.typography.body2.fontSize,
            },
            "& .work-area-page .work-area-chart-card__title, & .work-area-page .work-area-insights-card__title, & .work-area-page .work-area-register-card__title":
              {
                fontSize: (currentTheme) => currentTheme.typography.h6.fontSize,
              },
            "& .work-area-page .work-area-chart-card__subtitle, & .work-area-page .work-area-insights-card__subtitle, & .work-area-page .work-area-register-card__loading, & .work-area-page .work-area-register-card__footer":
              {
                fontSize: (currentTheme) => currentTheme.typography.body2.fontSize,
              },
            "& .work-area-page .work-area-insights-card__item": {
              fontSize: (currentTheme) => currentTheme.typography.body1.fontSize,
              lineHeight: 1.6,
            },
          }}
        >
          {children}
        </Box>
      </ThemeProvider>
    </Box>
  );
}
