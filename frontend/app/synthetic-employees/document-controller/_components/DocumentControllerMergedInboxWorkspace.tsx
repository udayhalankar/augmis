"use client";

import { useEffect, useState } from "react";
import { Stack } from "@mui/material";

import { DocumentControllerActionRegister } from "@/app/synthetic-employees/document-controller/_components/DocumentControllerActionRegister";
import {
  buildDocumentControllerExceptionRegistry,
  type DocumentControllerExceptionItem,
} from "@/app/synthetic-employees/document-controller/_components/documentControllerExceptions";
import { AppNotificationToast } from "@/components/feedback/AppNotificationToast";
import {
  acknowledgeDocumentControllerCommand,
  approveDocumentControllerCommand,
  dispatchDocumentControllerCommand,
  failDocumentControllerCommand,
  getDocumentControllerCommands,
  getDocumentControllerDocumentDetail,
  getDocumentControllerDocuments,
  openDocumentControllerDocumentFile,
  rejectDocumentControllerCommand,
  rollbackDocumentControllerCommand,
} from "@/services/symployeeService";

type DocumentItem = {
  identity_id: string;
  title?: string | null;
  document_type_code?: string | null;
  status?: string | null;
  recommendation_count?: number | null;
  command_count?: number | null;
  overdue_workflow_task_count?: number | null;
};

type ActionItem = {
  command_id?: string | null;
  document_title?: string | null;
  identity_id?: string | null;
  version_id?: string | null;
  document_type_code?: string | null;
  document_status?: string | null;
  overdue_task_count?: number | null;
  command_type?: string | null;
  source_recommendation_type?: string | null;
  source_recommendation_summary?: string | null;
  source_recommendation_id?: string | null;
  status?: string | null;
  approval_status?: string | null;
  repository_id?: string | null;
  latest_execution?: {
    status?: string | null;
    artifact_path?: string | null;
  } | null;
  failure_reason?: string | null;
  exceptions?: DocumentControllerExceptionItem[];
};

const COMMAND_STATUS_PRIORITY: Record<string, number> = {
  PENDING_APPROVAL: 0,
  ROLLBACK_PENDING: 1,
  APPROVED: 2,
  DISPATCHED: 3,
  FAILED: 4,
  ACKNOWLEDGED: 5,
  ROLLED_BACK: 6,
  REJECTED: 7,
};

function rankCommandForInbox(item: ActionItem) {
  const status = String(item.status || "").toUpperCase();
  return COMMAND_STATUS_PRIORITY[status] ?? 99;
}

export function DocumentControllerMergedInboxWorkspace() {
  const [items, setItems] = useState<ActionItem[] | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [messageSeverity, setMessageSeverity] = useState<"success" | "error">("success");
  const [isPending, setIsPending] = useState(false);

  async function load() {
    const [commandsResult, documentsResult] = await Promise.all([
      getDocumentControllerCommands(),
      getDocumentControllerDocuments(),
    ]);
    const commandItems = commandsResult?.data?.items || [];
    const documentItems = documentsResult?.data?.items || [];
    const documentDetails = (
      await Promise.all(
        documentItems.map((item: DocumentItem) =>
          getDocumentControllerDocumentDetail(item.identity_id)
            .then((result) => result?.data || null)
            .catch(() => null)
        )
      )
    ).filter(Boolean);
    const exceptionRegistry = buildDocumentControllerExceptionRegistry({
      documentDetails,
      commands: commandItems,
    });
    const commandsByIdentity = new Map<string, ActionItem[]>();

    commandItems.forEach((item: ActionItem) => {
      if (!item.identity_id) return;
      const bucket = commandsByIdentity.get(item.identity_id) || [];
      bucket.push(item);
      commandsByIdentity.set(item.identity_id, bucket);
    });

    setItems(
      documentItems.map((document: DocumentItem) => {
        const relatedCommands = commandsByIdentity.get(document.identity_id) || [];
        const selectedCommand = [...relatedCommands].sort(
          (left, right) => rankCommandForInbox(left) - rankCommandForInbox(right)
        )[0];

        return {
          ...selectedCommand,
          command_id: selectedCommand?.command_id ?? null,
          identity_id: document.identity_id,
          document_title:
            selectedCommand?.document_title ?? document.title ?? document.identity_id,
          document_type_code: document.document_type_code ?? null,
          document_status: document.status ?? null,
          overdue_task_count: document.overdue_workflow_task_count ?? 0,
          exceptions: exceptionRegistry.byIdentity.get(document.identity_id) || [],
        };
      })
    );
  }

  useEffect(() => {
    void load();
  }, []);

  async function executeAction(action: () => Promise<unknown>, successMessage: string) {
    setIsPending(true);
    try {
      await action();
      setMessageSeverity("success");
      setMessage(successMessage);
      await load();
    } catch (error) {
      console.error(error);
      setMessageSeverity("error");
      setMessage("The requested action could not be completed.");
    } finally {
      setIsPending(false);
    }
  }

  return (
    <Stack spacing={2.25}>
      <AppNotificationToast
        open={Boolean(message)}
        message={message}
        severity={messageSeverity}
        onClose={() => setMessage(null)}
      />
      <DocumentControllerActionRegister
        items={items || []}
        enableRowSelection
        loading={items === null}
        isPending={isPending}
        onApprove={(commandId) =>
          executeAction(
            () =>
              approveDocumentControllerCommand(commandId, {
                comments: "Approved from Symployee UI",
              }),
            `Connector action ${commandId} approved.`,
          )
        }
        onReject={(commandId) =>
          executeAction(
            () =>
              rejectDocumentControllerCommand(commandId, {
                comments: "Rejected from Symployee UI",
              }),
            `Connector action ${commandId} rejected.`,
          )
        }
        onDispatch={(commandId) =>
          executeAction(
            () =>
              dispatchDocumentControllerCommand(commandId, {
                comments: "Dispatched from Symployee UI",
              }),
            `Connector action ${commandId} dispatched.`,
          )
        }
        onAcknowledge={(commandId) =>
          executeAction(
            () =>
              acknowledgeDocumentControllerCommand(commandId, {
                comments: "Acknowledged from Symployee UI",
              }),
            `Connector action ${commandId} acknowledged.`,
          )
        }
        onFail={(commandId) =>
          executeAction(
            () =>
              failDocumentControllerCommand(commandId, {
                comments: "Failed from Symployee UI",
                failure_reason: "Manual failure recorded from Symployee UI",
              }),
            `Connector action ${commandId} marked failed.`,
          )
        }
        onRollback={(commandId) =>
          executeAction(
            () =>
              rollbackDocumentControllerCommand(commandId, {
                comments: "Rollback requested from Symployee UI",
              }),
            `Rollback requested for ${commandId}.`,
          )
        }
        onOpenFile={openDocumentControllerDocumentFile}
      />
    </Stack>
  );
}
