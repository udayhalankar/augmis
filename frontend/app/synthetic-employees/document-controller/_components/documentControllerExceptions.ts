"use client";

export type DocumentControllerExceptionItem = {
  id: string;
  identityId?: string | null;
  type: string;
  subject: string;
  status: string;
  source: string;
  detail: string;
};

type ExceptionRegistryInput = {
  documentDetails: any[];
  commands?: any[];
  recommendations?: any[];
};

function normalize(value?: string | null, fallback = "UNSET") {
  return String(value || fallback).toUpperCase();
}

export function buildDocumentControllerExceptionRegistry({
  documentDetails,
  commands = [],
  recommendations = [],
}: ExceptionRegistryInput) {
  const rows: DocumentControllerExceptionItem[] = [];
  const byIdentity = new Map<string, DocumentControllerExceptionItem[]>();
  const identities = documentDetails.map((item: any) => item.identity).filter(Boolean);
  const currentVersions = documentDetails.map((item: any) => item.current_version).filter(Boolean);
  const documentNumbers = new Map<string, any[]>();
  const seenRecommendationIds = new Set<string>();

  const appendRow = (row: DocumentControllerExceptionItem) => {
    rows.push(row);
    if (!row.identityId) return;
    const bucket = byIdentity.get(row.identityId) || [];
    bucket.push(row);
    byIdentity.set(row.identityId, bucket);
  };

  identities.forEach((item: any) => {
    const number = String(item.canonical_document_number || "").trim();
    if (!number) return;
    const bucket = documentNumbers.get(number) || [];
    bucket.push(item);
    documentNumbers.set(number, bucket);
  });

  identities.forEach((item: any, index: number) => {
    const subject = item.title || item.identity_id;
    const identityId = item.identity_id;

    if (!item.canonical_document_number || !item.originator_code) {
      appendRow({
        id: `meta-${identityId}`,
        identityId,
        type: "Metadata Gap",
        subject,
        status: "Open",
        source: "Document Identity",
        detail: "Mandatory document number or originator code is missing.",
      });
    }

    if (
      normalize(item.document_lifecycle_stage, item.status) === "ISSUED" &&
      normalize(currentVersions[index]?.revision_status) === "SUPERSEDED"
    ) {
      appendRow({
        id: `rev-${identityId}`,
        identityId,
        type: "Superseded Issue",
        subject,
        status: "Open",
        source: "Current Revision",
        detail: "Document is issued while the current revision status is superseded.",
      });
    }
  });

  Array.from(documentNumbers.entries())
    .filter(([, items]) => items.length > 1)
    .forEach(([number, items]) => {
      items.forEach((item: any) => {
        appendRow({
          id: `dup-${item.identity_id}`,
          identityId: item.identity_id,
          type: "Duplicate Number",
          subject: item.title || item.identity_id,
          status: "Open",
          source: "Document Identity",
          detail: `Document number ${number} appears on multiple identities.`,
        });
      });
    });

  documentDetails.forEach((detail: any) => {
    const identityId = detail?.identity?.identity_id;
    const subject = detail?.identity?.title || identityId || "-";
    (detail?.recommendations || [])
      .filter((item: any) => normalize(item.status) === "NEEDS_REVIEW")
      .forEach((item: any) => {
        if (item.recommendation_id) {
          seenRecommendationIds.add(item.recommendation_id);
        }
        appendRow({
          id: `rec-${item.recommendation_id}`,
          identityId,
          type: "Pending Recommendation",
          subject,
          status: "Needs Review",
          source: "AI Recommendation",
          detail: `Recommendation remains pending review${item.model_name ? ` from ${item.model_name}` : ""}.`,
        });
      });
  });

  commands
    .filter((item: any) => normalize(item.status) === "FAILED")
    .forEach((item: any) => {
      appendRow({
        id: `cmd-${item.command_id}`,
        identityId: item.identity_id,
        type: "Action Failure",
        subject: item.document_title || item.identity_id || item.command_id,
        status: "Open",
        source: "Connector Action",
        detail: item.failure_reason || "Connector action execution failed.",
      });
    });

  recommendations
    .filter(
      (item: any) =>
        normalize(item.status) === "NEEDS_REVIEW" &&
        item.recommendation_id &&
        !seenRecommendationIds.has(item.recommendation_id)
    )
    .forEach((item: any) => {
      appendRow({
        id: `rec-${item.recommendation_id}`,
        identityId: item.identity_id || null,
        type: "Pending Recommendation",
        subject: item.recommendation_type || item.recommendation_id,
        status: "Needs Review",
        source: "AI Recommendation",
        detail: `Recommendation remains pending review${item.model_name ? ` from ${item.model_name}` : ""}.`,
      });
    });

  return { rows, byIdentity };
}
