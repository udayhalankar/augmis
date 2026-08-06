import { createTheme } from "@mui/material/styles";
import type { Theme, TypographyVariant } from "@mui/material/styles";

const OUTLET_TEXT_PRIMARY = "#4b5563";
const OUTLET_TEXT_SECONDARY = "#6b7280";
const OUTLET_FONT_SCALE = 0.805;
const OUTLET_CARD_RADIUS = 13.5;
const OUTLET_CARD_SHADOW = "0 1px 7px rgba(15, 23, 42, 0.1)";

const TYPOGRAPHY_VARIANTS: TypographyVariant[] = [
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "subtitle1",
  "subtitle2",
  "body1",
  "body2",
  "button",
  "caption",
  "overline",
];

export type ShellMode = "SIMPLE" | "COOL";

type ShellTokens = {
  appBg: string;
  mainBg: string;
  mainBorder: string;
  mainShadow: string;
  topbarBg: string;
  topbarText: string;
  topbarBorder: string;
  topbarShadow: string;
  topbarHeight: number;
  topbarAccent: string;
  topbarMetaBg: string;
  topbarMetaText: string;
  topbarMetaBadgeBg: string;
  topbarMetaBadgeText: string;
  sidebarBg: string;
  sidebarBorder: string;
  sidebarText: string;
  sidebarMuted: string;
  sidebarSectionLabel: string;
  sidebarHover: string;
  sidebarSelectedBg: string;
  sidebarSelectedText: string;
  sidebarSelectedBorder: string;
  sidebarBrandBg: string;
  sidebarBrandBorder: string;
  sidebarCollapseBorder: string;
  outletTextPrimary: string;
  outletTextSecondary: string;
  outletFontScale: number;
  outletCardRadius: number;
  outletCardShadow: string;
  contentTopPadding: string;
  contentHorizontalPadding: number;
  fontFamily: string;
};

const SIMPLE_SHELL_TOKENS: ShellTokens = {
  appBg: "#FFFFFF",
  mainBg: "#FFFFFF",
  mainBorder: "#E6EAF0",
  mainShadow: "none",
  topbarBg: "#FFFFFF",
  topbarText: "#0c1b2d",
  topbarBorder: "#e2e8f0",
  topbarShadow: "0 2px 12px rgba(15, 23, 42, 0.06)",
  topbarHeight: 34,
  topbarAccent: "#2563EB",
  topbarMetaBg: "#FFFFFF",
  topbarMetaText: "#0c1b2d",
  topbarMetaBadgeBg: "#E2E8F0",
  topbarMetaBadgeText: "#0c1b2d",
  sidebarBg: "#FFFFFF",
  sidebarBorder: "#E6EAF0",
  sidebarText: "#102A43",
  sidebarMuted: "#64748B",
  sidebarSectionLabel: "#64748B",
  sidebarHover: "#F5F7FA",
  sidebarSelectedBg: "#EEF4FF",
  sidebarSelectedText: "#174EA6",
  sidebarSelectedBorder: "#174EA6",
  sidebarBrandBg: "#FFFFFF",
  sidebarBrandBorder: "#E6EAF0",
  sidebarCollapseBorder: "#E6EAF0",
  outletTextPrimary: OUTLET_TEXT_PRIMARY,
  outletTextSecondary: OUTLET_TEXT_SECONDARY,
  outletFontScale: OUTLET_FONT_SCALE,
  outletCardRadius: OUTLET_CARD_RADIUS,
  outletCardShadow: OUTLET_CARD_SHADOW,
  contentTopPadding: "110px",
  contentHorizontalPadding: 3,
  fontFamily: "Inter, Roboto, sans-serif",
};

const COOL_SHELL_TOKENS: ShellTokens = {
  appBg: "#EEF4F8",
  mainBg: "#EEF4F8",
  mainBorder: "#D7E3F4",
  mainShadow: "inset 0 1px 0 rgba(255,255,255,0.7)",
  topbarBg: "#FFFFFF",
  topbarText: "#10233C",
  topbarBorder: "#DCE5F0",
  topbarShadow: "0 8px 24px rgba(15, 23, 42, 0.08)",
  topbarHeight: 45,
  topbarAccent: "#1D4ED8",
  topbarMetaBg: "#17335C",
  topbarMetaText: "#F8FAFC",
  topbarMetaBadgeBg: "#EF4444",
  topbarMetaBadgeText: "#FFFFFF",
  sidebarBg: "#131C30",
  sidebarBorder: "#1F2A44",
  sidebarText: "#E6EDF7",
  sidebarMuted: "#8EA2C0",
  sidebarSectionLabel: "#4D5C79",
  sidebarHover: "#1C2943",
  sidebarSelectedBg: "#2C4A76",
  sidebarSelectedText: "#6FC7FF",
  sidebarSelectedBorder: "#38BDF8",
  sidebarBrandBg: "#131C30",
  sidebarBrandBorder: "#1F2A44",
  sidebarCollapseBorder: "#334155",
  outletTextPrimary: "#20324B",
  outletTextSecondary: "#61748E",
  outletFontScale: 0.86,
  outletCardRadius: 18,
  outletCardShadow: "0 10px 30px rgba(15, 23, 42, 0.08)",
  contentTopPadding: "108px",
  contentHorizontalPadding: 3,
  fontFamily: "\"Segoe UI\", Inter, Roboto, sans-serif",
};

export function getShellTokens(shellMode: ShellMode) {
  return shellMode === "COOL" ? COOL_SHELL_TOKENS : SIMPLE_SHELL_TOKENS;
}

function scaleTypographySize(fontSize: unknown, scale: number) {
  if (typeof fontSize !== "string") return fontSize;

  const match = fontSize.trim().match(/^(-?\d*\.?\d+)(px|rem|em)$/);
  if (!match) return fontSize;

  const value = Number(match[1]);
  const unit = match[2];

  return `${Number((value * scale).toFixed(3))}${unit}`;
}

export function getOutletTheme(baseTheme: Theme, shellMode: ShellMode = "SIMPLE") {
  const shell = getShellTokens(shellMode);
  const scaledTypography = TYPOGRAPHY_VARIANTS.reduce<Record<string, any>>(
    (acc, variant) => {
      const variantConfig = baseTheme.typography[variant];

      if (!variantConfig || typeof variantConfig !== "object") {
        return acc;
      }

      acc[variant] = {
        ...variantConfig,
        fontSize: scaleTypographySize(variantConfig.fontSize, shell.outletFontScale),
      };

      return acc;
    },
    {}
  );

  return createTheme(baseTheme, {
    palette: {
      background: {
        default: shell.mainBg,
        paper: "#FFFFFF",
      },
      text: {
        primary: shell.outletTextPrimary,
        secondary: shell.outletTextSecondary,
      },
    },
    typography: {
      ...scaledTypography,
      fontFamily: shell.fontFamily,
      allVariants: {
        color: shell.outletTextPrimary,
      },
    },
    components: {
      MuiTypography: {
        styleOverrides: {
          root: {
            color: shell.outletTextPrimary,
          },
        },
      },
      MuiCard: {
        defaultProps: {
          elevation: 0,
        },
        styleOverrides: {
          root: {
            borderRadius: `${shell.outletCardRadius}px !important`,
            boxShadow: `${shell.outletCardShadow} !important`,
            border: shellMode === "COOL" ? `1px solid ${shell.mainBorder}` : undefined,
          },
        },
      },
      MuiPaper: {
        defaultProps: {
          elevation: 0,
        },
        styleOverrides: {
          root: {
            boxShadow: `${shell.outletCardShadow} !important`,
            border: shellMode === "COOL" ? `1px solid ${shell.mainBorder}` : undefined,
          },
          rounded: {
            borderRadius: `${shell.outletCardRadius}px !important`,
          },
        },
      },
      MuiInputBase: {
        styleOverrides: {
          root: {
            color: shell.outletTextPrimary,
          },
          input: {
            color: shell.outletTextPrimary,
            fontSize: scaleTypographySize("0.805rem", shell.outletFontScale),
          },
        },
      },
      MuiFormLabel: {
        styleOverrides: {
          root: {
            color: shell.outletTextSecondary,
            fontSize: scaleTypographySize("0.805rem", shell.outletFontScale),
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            fontSize: scaleTypographySize("0.704rem", shell.outletFontScale),
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          label: {
            fontSize: scaleTypographySize("0.704rem", shell.outletFontScale),
          },
        },
      },
      MuiMenuItem: {
        styleOverrides: {
          root: {
            color: shell.outletTextPrimary,
            fontSize: scaleTypographySize("0.805rem", shell.outletFontScale),
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          root: {
            color: shell.outletTextPrimary,
            fontSize: scaleTypographySize("0.805rem", shell.outletFontScale),
          },
        },
      },
    },
  });
}

export const getEnterpriseTheme = (
  mode: "light" | "dark",
  shellMode: ShellMode = "SIMPLE"
) => {
  const shell = getShellTokens(shellMode);

  return createTheme({
    palette: {
      mode,
      background: {
        default: shell.appBg,
        paper: "#FFFFFF",
      },
      primary: {
        main: shellMode === "COOL" ? "#1D4ED8" : "#2563EB",
      },
      success: {
        main: "#10B981",
      },
      warning: {
        main: "#F59E0B",
      },
      error: {
        main: "#EF4444",
      },
      text: {
        primary: shell.topbarText,
        secondary: shell.outletTextSecondary,
      },
    },
    typography: {
      fontFamily: shell.fontFamily,
      h5: {
        fontWeight: shellMode === "COOL" ? 800 : 700,
        letterSpacing: shellMode === "COOL" ? "-0.02em" : undefined,
      },
      h6: {
        fontWeight: shellMode === "COOL" ? 800 : 700,
        letterSpacing: shellMode === "COOL" ? "-0.01em" : undefined,
      },
      button: {
        fontWeight: 600,
      },
    },
    shape: {
      borderRadius: shellMode === "COOL" ? 16 : 14,
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: shell.appBg,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: shellMode === "COOL" ? 20 : 18,
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: "none",
            borderRadius: shellMode === "COOL" ? 12 : 10,
            fontWeight: 600,
          },
        },
      },
    },
  });
};
