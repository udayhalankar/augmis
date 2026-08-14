"use client";

import type { ReactNode } from "react";

import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import { InputAdornment, Stack, TextField } from "@mui/material";

type BusinessTableHeaderToolbarProps = {
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  searchWidth?: number;
  searchMinWidth?: number;
  actions?: ReactNode;
};

export default function BusinessTableHeaderToolbar({
  searchValue,
  onSearchChange,
  searchPlaceholder = "Search",
  searchWidth = 360,
  searchMinWidth = 320,
  actions,
}: BusinessTableHeaderToolbarProps) {
  return (
    <Stack
      direction={{ xs: "column", lg: "row" }}
      spacing={1}
      sx={{
        width: { xs: "100%", md: "auto" },
        minWidth: 0,
        alignItems: { xs: "stretch", md: "center" },
        justifyContent: "flex-end",
        "& .MuiButton-root": {
          minHeight: 36,
          px: 1.6,
          borderRadius: "8px",
          textTransform: "none",
          fontWeight: 700,
          whiteSpace: "nowrap",
        },
        "& .MuiButton-outlined": {
          color: "#FFFFFF",
          borderColor: "rgba(255,255,255,0.45)",
          bgcolor: "rgba(255,255,255,0.08)",
        },
        "& .MuiButton-outlined:hover": {
          borderColor: "rgba(255,255,255,0.7)",
          bgcolor: "rgba(255,255,255,0.14)",
        },
        "& .MuiButton-outlined.Mui-disabled": {
          color: "rgba(255,255,255,0.48)",
          borderColor: "rgba(255,255,255,0.2)",
        },
      }}
    >
      {typeof searchValue === "string" && onSearchChange ? (
        <TextField
          size="small"
          value={searchValue}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={searchPlaceholder}
          sx={{
            width: { xs: "100%", lg: searchWidth },
            minWidth: { xs: "100%", lg: searchMinWidth },
            "& .MuiOutlinedInput-root": {
              bgcolor: "#FFFFFF",
            },
          }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchRoundedIcon fontSize="small" sx={{ color: "#64748B" }} />
                </InputAdornment>
              ),
            },
          }}
        />
      ) : null}
      {actions ? (
        <Stack
          direction="row"
          spacing={1}
          sx={{
            alignItems: "center",
            justifyContent: { xs: "stretch", md: "flex-end" },
            flexWrap: "wrap",
          }}
        >
          {actions}
        </Stack>
      ) : null}
    </Stack>
  );
}
