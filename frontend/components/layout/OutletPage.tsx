"use client";

import { useEffect } from "react";
import { Box, Stack, Typography } from "@mui/material";

function toPlainText(node: React.ReactNode): string {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(toPlainText).join(" ").replace(/\s+/g, " ").trim();
  if (typeof node === "object" && "props" in node) {
    return toPlainText((node as any).props?.children);
  }
  return "";
}

export function OutletPage({
  title,
  description,
  actions,
  children,
}: {
  title?: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (typeof window === "undefined") return;

    window.dispatchEvent(
      new CustomEvent("augmis:outlet-page-meta", {
        detail: {
          title: title?.trim() || "",
          description: toPlainText(description),
        },
      })
    );

    return () => {
      window.dispatchEvent(
        new CustomEvent("augmis:outlet-page-meta", {
          detail: { title: "", description: "" },
        })
      );
    };
  }, [title, description]);

  return (
    <Box className="outlet-page">
      {actions ? (
        <Stack className="outlet-page__header" direction={{ xs: "column", md: "row" }}>
          <Box sx={{ flex: 1 }} />
          <Box className="outlet-page__actions">{actions}</Box>
        </Stack>
      ) : null}

      <Box className="outlet-page__body">{children}</Box>
    </Box>
  );
}
