"use client";

import { useEffect, useState, useTransition } from "react";

import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import DescriptionRoundedIcon from "@mui/icons-material/DescriptionRounded";
import {
  Box,
  CircularProgress,
  Dialog,
  DialogContent,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";

import { DocumentControllerDocumentDetailContent } from "@/app/synthetic-employees/document-controller/_components/DocumentControllerDocumentDetailContent";
import {
  createDocumentControllerCommand,
  getDocumentControllerDocumentDetail,
  openDocumentControllerDocumentFile,
} from "@/services/symployeeService";

type DocumentControllerDocumentDetailModalProps = {
  identityId: string | null;
  open: boolean;
  onClose: () => void;
};

export function DocumentControllerDocumentDetailModal({
  identityId,
  open,
  onClose,
}: DocumentControllerDocumentDetailModalProps) {
  const [detail, setDetail] = useState<any>(null);
  const [message, setMessage] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (!open || !identityId) {
      return;
    }

    setLoading(true);
    getDocumentControllerDocumentDetail(identityId)
      .then((result) => {
        setDetail(result?.data || null);
      })
      .finally(() => setLoading(false));
  }, [identityId, open]);

  const handleClose = () => {
    setMessage("");
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      fullWidth
      maxWidth={false}
      scroll="paper"
      slotProps={{
        paper: {
          sx: {
            width: "min(1180px, calc(100vw - 40px))",
            maxHeight: "calc(100vh - 36px)",
            borderRadius: 6,
            overflow: "hidden",
            background:
              "linear-gradient(180deg, rgba(249,251,255,0.98) 0%, rgba(244,248,252,0.98) 100%)",
            boxShadow: "0 28px 80px rgba(15, 23, 42, 0.28)",
          },
        },
        backdrop: {
          sx: {
            backgroundColor: "rgba(15, 23, 42, 0.48)",
            backdropFilter: "blur(8px)",
          },
        },
      }}
    >
      <Box
        sx={{
          px: { xs: 2.5, md: 3.2 },
          py: { xs: 2.2, md: 2.6 },
          background: "linear-gradient(135deg, #3155A6 0%, #274674 55%, #1D355D 100%)",
          color: "#FFFFFF",
        }}
      >
        <Stack
          direction="row"
          spacing={2}
          sx={{ justifyContent: "space-between", alignItems: "flex-start" }}
        >
          <Stack spacing={0.65} sx={{ minWidth: 0 }}>
            <Stack direction="row" spacing={1.1} sx={{ alignItems: "center" }}>
              <DescriptionRoundedIcon sx={{ fontSize: 24 }} />
              <Typography sx={{ fontSize: 27, fontWeight: 800, letterSpacing: "-0.02em" }}>
                Document Detail
              </Typography>
            </Stack>
            <Typography sx={{ fontSize: 13, color: "rgba(229,238,248,0.84)" }}>
              Logical document identity, versions, recommendations, source objects, workflow, and
              linked connector actions.
            </Typography>
          </Stack>
          <IconButton
            onClick={handleClose}
            sx={{
              color: "rgba(255,255,255,0.86)",
              border: "1px solid rgba(255,255,255,0.18)",
              backgroundColor: "rgba(255,255,255,0.08)",
              "&:hover": {
                backgroundColor: "rgba(255,255,255,0.14)",
              },
            }}
          >
            <CloseRoundedIcon />
          </IconButton>
        </Stack>
      </Box>

      <DialogContent sx={{ p: { xs: 2, md: 2.5 }, backgroundColor: "transparent" }}>
        {loading || !detail ? (
          <Stack sx={{ minHeight: 320, alignItems: "center", justifyContent: "center" }}>
            <CircularProgress />
          </Stack>
        ) : (
          <DocumentControllerDocumentDetailContent
            detail={detail}
            message={message}
            isPending={isPending}
            mode="modal"
            onOpenCurrentDocument={() =>
              openDocumentControllerDocumentFile(detail.identity?.identity_id, detail.identity?.current_version_id)
            }
            onOpenVersionDocument={(versionId) =>
              openDocumentControllerDocumentFile(detail.identity?.identity_id, versionId)
            }
            onDraftManualAction={() =>
              startTransition(async () => {
                const result = await createDocumentControllerCommand({
                  repository_id: detail.identity?.repository_id,
                  identity_id: detail.identity?.identity_id,
                  version_id: detail.identity?.current_version_id,
                  command_type: "manual_document_update",
                  payload: {
                    operation: "manual_review_update",
                    document_title: detail.identity?.title,
                    document_number: detail.identity?.canonical_document_number,
                    reason: "Manual command drafted from document detail",
                  },
                });
                setMessage(`Manual connector action ${result?.data?.command_id} created.`);
                const refreshed = await getDocumentControllerDocumentDetail(detail.identity?.identity_id);
                setDetail(refreshed?.data || detail);
              })
            }
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
