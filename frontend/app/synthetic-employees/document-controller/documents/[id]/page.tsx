"use client";

import { useEffect, useState, useTransition } from "react";
import { useParams } from "next/navigation";

import { CircularProgress } from "@mui/material";

import { DocumentControllerDocumentDetailContent } from "@/app/synthetic-employees/document-controller/_components/DocumentControllerDocumentDetailContent";
import { OutletPage } from "@/components/layout/OutletPage";
import {
  createDocumentControllerCommand,
  getDocumentControllerDocumentDetail,
  openDocumentControllerDocumentFile,
} from "@/services/symployeeService";

export default function DocumentControllerDocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const [detail, setDetail] = useState<any>(null);
  const [message, setMessage] = useState<string>("");
  const [isPending, startTransition] = useTransition();

  function load() {
    if (!params?.id) return;
    getDocumentControllerDocumentDetail(params.id).then((result) => {
      setDetail(result?.data || null);
    });
  }

  useEffect(() => {
    load();
  }, [params]);

  return (
    <OutletPage
      title="Document Detail"
      description="Logical document identity, versions, recommendations, source objects, and pending actions."
    >
      {!detail ? <CircularProgress /> : (
        <DocumentControllerDocumentDetailContent
          detail={detail}
          message={message}
          isPending={isPending}
          mode="page"
          onOpenCurrentDocument={() =>
            openDocumentControllerDocumentFile(
              detail.identity?.identity_id,
              detail.identity?.current_version_id
            )
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
              load();
            })
          }
        />
      )}
    </OutletPage>
  );
}
