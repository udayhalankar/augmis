from datetime import datetime, date


TODAY = date.today()


def _parse_date(value: str):
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _days_overdue(due_date: str) -> int:
    parsed = _parse_date(due_date)
    if not parsed:
        return 0

    delta = (TODAY - parsed).days
    return max(delta, 0)


def _severity_from_overdue(days: int, risk_level: str = "", priority: str = "") -> str:
    risk_level = (risk_level or "").lower()
    priority = (priority or "").lower()

    if days >= 30:
        return "Critical"

    if days >= 15:
        return "High"

    if days >= 8:
        if risk_level in ["high", "critical"] or priority == "critical":
            return "High"
        return "Medium"

    if days >= 1:
        if risk_level == "critical" or priority == "critical":
            return "High"
        return "Medium"

    return "Low"


def build_proposal_escalations(proposals: list[dict]) -> list[dict]:
    escalations = []

    active_statuses = {"Pending Approval", "Draft", "Escalated"}

    for p in proposals:
        status = p.get("status", "")
        due_date = p.get("due_date", "")
        overdue_days = _days_overdue(due_date)

        if status not in active_statuses:
            continue

        if overdue_days <= 0:
            continue

        severity = _severity_from_overdue(
            overdue_days,
            p.get("risk_level", ""),
            p.get("priority", ""),
        )

        escalation = {
            "escalation_id": f"ESC-PROP-{p.get('proposal_id')}",
            "source_module": "Proposal",
            "source_id": p.get("proposal_id"),
            "title": f"Proposal overdue: {p.get('title')}",
            "department": p.get("department"),
            "owner": p.get("owner"),
            "escalation_type": "Proposal Delay",
            "status": "Open" if status != "Escalated" else "Escalated",
            "severity": severity,
            "created_at": TODAY.isoformat(),
            "due_date": due_date,
            "aging_days": overdue_days,
            "sla_breached": "Yes",
            "related_party": p.get("vendor"),
            "priority": p.get("priority"),
            "estimated_impact": float(p.get("estimated_value") or 0),
            "source_status": status,
            "approval_stage": p.get("approval_stage"),
        }

        escalations.append(escalation)

    return escalations


def build_procurement_escalations(procurement_items: list[dict]) -> list[dict]:
    escalations = []

    active_statuses = {"Pending Approval", "Draft", "Escalated"}

    for item in procurement_items:
        status = item.get("status", "")
        due_date = item.get("due_date", "")
        overdue_days = _days_overdue(due_date)

        if status not in active_statuses:
            continue

        if overdue_days <= 0:
            continue

        severity = _severity_from_overdue(
            overdue_days,
            item.get("risk_level", ""),
            item.get("priority", ""),
        )

        escalation = {
            "escalation_id": f"ESC-PROC-{item.get('procurement_id')}",
            "source_module": "Procurement",
            "source_id": item.get("procurement_id"),
            "title": f"Procurement overdue: {item.get('item_name')}",
            "department": item.get("department"),
            "owner": item.get("requestor"),
            "escalation_type": "Procurement Delay",
            "status": "Open" if status != "Escalated" else "Escalated",
            "severity": severity,
            "created_at": TODAY.isoformat(),
            "due_date": due_date,
            "aging_days": overdue_days,
            "sla_breached": "Yes",
            "related_party": item.get("vendor"),
            "priority": item.get("priority"),
            "estimated_impact": float(item.get("estimated_value") or 0),
            "source_status": status,
            "approval_stage": item.get("approval_stage"),
        }

        escalations.append(escalation)

    return escalations


def build_vendor_escalations(vendors: list[dict]) -> list[dict]:
    escalations = []

    for vendor in vendors:
        compliance = vendor.get("compliance_status", "")
        risk_level = vendor.get("risk_level", "")
        delivery = float(vendor.get("on_time_delivery_percent") or 0)
        open_issues = int(vendor.get("open_issues") or 0)

        should_escalate = (
            compliance == "Non-Compliant"
            or risk_level == "Critical"
            or delivery < 70
            or open_issues >= 5
        )

        if not should_escalate:
            continue

        if risk_level == "Critical" or compliance == "Non-Compliant":
            severity = "Critical"
        elif open_issues >= 5 or delivery < 70:
            severity = "High"
        else:
            severity = "Medium"

        reasons = []

        if compliance == "Non-Compliant":
            reasons.append("non-compliance")

        if risk_level == "Critical":
            reasons.append("critical risk rating")

        if delivery < 70:
            reasons.append("delivery performance below 70%")

        if open_issues >= 5:
            reasons.append("high number of open issues")

        escalation = {
            "escalation_id": f"ESC-VEND-{vendor.get('vendor_id')}",
            "source_module": "Vendor",
            "source_id": vendor.get("vendor_id"),
            "title": f"Vendor risk escalation: {vendor.get('vendor_name')}",
            "department": vendor.get("department"),
            "owner": "Vendor Management",
            "escalation_type": "Vendor Risk",
            "status": "Open",
            "severity": severity,
            "created_at": TODAY.isoformat(),
            "due_date": vendor.get("last_audit_date"),
            "aging_days": open_issues,
            "sla_breached": "Yes" if severity in ["High", "Critical"] else "No",
            "related_party": vendor.get("vendor_name"),
            "priority": vendor.get("criticality"),
            "estimated_impact": float(vendor.get("total_value") or 0),
            "source_status": vendor.get("compliance_status"),
            "approval_stage": vendor.get("contract_status"),
            "reason": ", ".join(reasons),
        }

        escalations.append(escalation)

    return escalations