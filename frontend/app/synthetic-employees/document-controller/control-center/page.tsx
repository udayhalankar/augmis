"use client";

import Link from "next/link";

import {
  Button,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";

import { AdminTableCard } from "@/components/data-display/AdminTableCard";
import { OutletPage } from "@/components/layout/OutletPage";
import { DocumentControllerAdminMenu } from "../_components/DocumentControllerAdminMenu";
import { useDocumentControllerOperationalData } from "../_components/useDocumentControllerOperationalData";

export default function DocumentControllerControlCenterPage() {
  const data = useDocumentControllerOperationalData();

  return (
    <OutletPage
      title="Control Center"
      description="Operational cockpit for lifecycle visibility, review health, records posture, and intervention priorities."
    >
      {!data ? (
        <CircularProgress />
      ) : (
        <Stack spacing={0}>
          <DocumentControllerAdminMenu
            value="overview"
            actions={
              <Button component={Link} href="/synthetic-employees/document-controller/inbox" variant="outlined">
                Open Work Queue
              </Button>
            }
          />

          <Stack spacing={3} sx={{ pt: 2 }}>
            <AdminTableCard
              title="Control Center"
              description="Detailed operational section cards now live on Overview to keep the document-controller workspace consolidated in one landing page."
              accentLabel="Control Center"
              bodySx={{ p: 3 }}
            >
              <Typography sx={{ color: "#475569", fontSize: 14, lineHeight: 1.7 }}>
                Use the shared overview workspace for Document Lifecycle, Records Posture, Attention Required,
                Review Health, Transmittal Control, and Handover readiness section lists.
              </Typography>
            </AdminTableCard>
          </Stack>
        </Stack>
      )}
    </OutletPage>
  );
}
