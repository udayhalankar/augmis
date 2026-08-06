"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { buildDocumentControllerExceptionRegistry } from "@/app/synthetic-employees/document-controller/_components/documentControllerExceptions";
import {
  Button,
  CircularProgress,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import { OutletPage } from "@/components/layout/OutletPage";
import {
  getDocumentControllerCommands,
  getDocumentControllerDocumentDetail,
  getDocumentControllerDocuments,
  getDocumentControllerRecommendations,
} from "@/services/symployeeService";
type ExceptionRow = {
  id: string;
  type: string;
  subject: string;
  status: string;
  source: string;
  detail: string;
};

export default function ExceptionsPage() {
  const [rows, setRows] = useState<ExceptionRow[] | null>(null);

  useEffect(() => {
    async function load() {
      const [documentsResult, commandsResult, recommendationsResult] = await Promise.all([
        getDocumentControllerDocuments(),
        getDocumentControllerCommands(),
        getDocumentControllerRecommendations(),
      ]);

      const documentItems = documentsResult?.data?.items || [];
      const details = (
        await Promise.all(
          documentItems.map((item: any) =>
            getDocumentControllerDocumentDetail(item.identity_id)
              .then((result) => result?.data || null)
              .catch(() => null)
          )
        )
      ).filter(Boolean);
      const commands = commandsResult?.data?.items || [];
      const recommendations = recommendationsResult?.data?.items || [];
      setRows(
        buildDocumentControllerExceptionRegistry({
          documentDetails: details,
          commands,
          recommendations,
        }).rows
      );
    }

    void load();
  }, []);

  const metrics = useMemo(() => {
    const items = rows || [];
    return {
      total: items.length,
      metadata: items.filter((item) => item.type === "Metadata Gap").length,
      duplicates: items.filter((item) => item.type === "Duplicate Number").length,
      failures: items.filter((item) => item.type === "Action Failure").length,
    };
  }, [rows]);

  return (
    <OutletPage
      title="Exceptions"
      description="Operational exception register for document-control breaches, failed automation, and pending interventions."
      actions={
        <Button
          component={Link}
          href="/synthetic-employees/document-controller/control-center"
          variant="outlined"
        >
          Open Control Center
        </Button>
      }
    >
      {rows === null ? (
        <CircularProgress />
      ) : (
        <Stack spacing={3}>
          <Grid container spacing={2}>
            {[
              ["Open Exceptions", metrics.total],
              ["Metadata Gaps", metrics.metadata],
              ["Duplicate Numbers", metrics.duplicates],
              ["Action Failures", metrics.failures],
            ].map(([label, value]) => (
              <Grid key={String(label)} size={{ xs: 12, md: 6, xl: 3 }}>
                <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, height: "100%" }}>
                  <Stack spacing={1}>
                    <Typography color="text.secondary">{label}</Typography>
                    <Typography variant="h4" fontWeight={800}>
                      {value as number}
                    </Typography>
                  </Stack>
                </Paper>
              </Grid>
            ))}
          </Grid>

          <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
            <Stack spacing={1.5}>
              <Typography variant="h6" fontWeight={700}>
                Exception Register
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell>Subject</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Source</TableCell>
                    <TableCell>Detail</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.length ? (
                    rows.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>{item.type}</TableCell>
                        <TableCell>{item.subject}</TableCell>
                        <TableCell>{item.status}</TableCell>
                        <TableCell>{item.source}</TableCell>
                        <TableCell>{item.detail}</TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={5}>No open exceptions are currently detected.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </Stack>
          </Paper>
        </Stack>
      )}
    </OutletPage>
  );
}
