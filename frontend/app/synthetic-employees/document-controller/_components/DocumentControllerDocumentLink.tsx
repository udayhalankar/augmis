"use client";

import Link from "next/link";
import { useState } from "react";

import { Link as MuiLink } from "@mui/material";

import { DocumentControllerDocumentDetailModal } from "@/app/synthetic-employees/document-controller/_components/DocumentControllerDocumentDetailModal";

type SimpleSx = Record<string, any>;

type DocumentControllerDocumentLinkProps = {
  identityId?: string | null;
  label: React.ReactNode;
  sx?: SimpleSx;
};

export function DocumentControllerDocumentLink({
  identityId,
  label,
  sx,
}: DocumentControllerDocumentLinkProps) {
  const [open, setOpen] = useState(false);

  const href = identityId
    ? `/synthetic-employees/document-controller/documents/${encodeURIComponent(identityId)}`
    : "#";

  return (
    <>
      <MuiLink
        component={Link}
        href={href}
        sx={sx}
        onClick={(event) => {
          if (!identityId) {
            event.preventDefault();
            return;
          }
          if (
            event.defaultPrevented ||
            event.button !== 0 ||
            event.metaKey ||
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey
          ) {
            return;
          }
          event.preventDefault();
          setOpen(true);
        }}
      >
        {label}
      </MuiLink>
      <DocumentControllerDocumentDetailModal
        identityId={identityId || null}
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
