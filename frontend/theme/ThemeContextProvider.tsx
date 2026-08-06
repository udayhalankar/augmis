"use client";

import { createContext, useEffect, useMemo, useState } from "react";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { getEnterpriseTheme, type ShellMode } from "./theme";

const SHELL_MODE_STORAGE_KEY = "augmis_shell_mode";

export const ColorModeContext = createContext({
  mode: "light",
  toggleMode: () => {},
  shellMode: "SIMPLE" as ShellMode,
  setShellMode: (_value: ShellMode) => {},
  toggleShellMode: () => {},
});

export default function ThemeContextProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mode, setMode] = useState<"light" | "dark">("light");
  const [shellMode, setShellModeState] = useState<ShellMode>("SIMPLE");
  const [mounted, setMounted] = useState(false);

  const theme = useMemo(
    () => getEnterpriseTheme(mode, shellMode),
    [mode, shellMode]
  );

  useEffect(() => {
    const savedShellMode =
      typeof window !== "undefined"
        ? window.localStorage.getItem(SHELL_MODE_STORAGE_KEY)
        : null;

    if (savedShellMode === "COOL" || savedShellMode === "SIMPLE") {
      setShellModeState(savedShellMode);
    }

    setMounted(true);
  }, []);

  function setShellMode(value: ShellMode) {
    setShellModeState(value);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SHELL_MODE_STORAGE_KEY, value);
    }
  }

  const value = {
    mode,
    toggleMode: () => {
      setMode((prev) => (prev === "dark" ? "light" : "dark"));
    },
    shellMode,
    setShellMode,
    toggleShellMode: () => {
      setShellMode(shellMode === "COOL" ? "SIMPLE" : "COOL");
    },
  };

  if (!mounted) {
    return null;
  }

  return (
    <ColorModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}
