export function normalize(value?: string | null, fallback = "UNSET") {
  return String(value || fallback).toUpperCase();
}

export const RETENTION_QUEUE_STATUSES = [
  "SCHEDULED",
  "ELIGIBLE_FOR_DISPOSITION",
  "ON_HOLD",
];

export function buildActiveHoldBuckets(holds: any[]) {
  const active = (holds || []).filter((item: any) => normalize(item.hold_status) === "ACTIVE");
  const legal = active.filter((item: any) => normalize(item.hold_category, "OTHER") === "LEGAL");
  const other = active.filter((item: any) => normalize(item.hold_category, "OTHER") !== "LEGAL");
  return {
    active,
    legal,
    other,
    legalIdentitySet: new Set(legal.map((item: any) => item.identity_id).filter(Boolean)),
    otherIdentitySet: new Set(other.map((item: any) => item.identity_id).filter(Boolean)),
  };
}

export function buildOpenDispositionBuckets(cases: any[]) {
  const active = (cases || []).filter(
    (item: any) => !["COMPLETED", "CANCELLED"].includes(normalize(item.case_status))
  );
  return {
    active,
    identitySet: new Set(active.map((item: any) => item.identity_id).filter(Boolean)),
  };
}

export function buildArchiveBuckets(transfers: any[]) {
  const items = (transfers || []).filter(
    (item: any) => normalize(item.transfer_status) !== "CANCELLED"
  );
  return {
    items,
    pending: items.filter((item: any) => normalize(item.transfer_status) === "PENDING"),
    completed: items.filter((item: any) => normalize(item.transfer_status) === "COMPLETED"),
  };
}

export function buildRetentionQueue(declarations: any[]) {
  return (declarations || []).filter((item: any) =>
    RETENTION_QUEUE_STATUSES.includes(normalize(item.retention_status))
  );
}
