from pathlib import Path


def detect_business_area(file_path: Path, text: str = "") -> str:
    combined = f"{file_path.parent.name} {file_path.name} {text[:1000]}".lower()

    if any(k in combined for k in ["proposal", "quotation", "quote", "tender", "rfq", "enquiry"]):
        return "Proposals"

    if any(k in combined for k in ["project", "milestone", "commissioning", "installation", "manufacturing"]):
        return "Projects"

    if any(k in combined for k in ["vendor", "supplier", "purchase", "po", "procurement", "material"]):
        return "Suppliers & Vendors"

    if any(k in combined for k in ["invoice", "payment", "receivable", "payable", "advance"]):
        return "Finance"

    if any(k in combined for k in ["meeting", "review", "minutes", "mom"]):
        return "Management Review"

    return "General"


def detect_risk_level(text: str) -> str:
    t = text.lower()

    high = [
        "critical", "urgent", "high", "overdue", "delayed",
        "penalty", "escalation", "not responding"
    ]

    medium = [
        "pending", "awaiting", "clarification", "follow-up",
        "risk", "approval", "hold"
    ]

    if any(k in t for k in high):
        return "High"

    if any(k in t for k in medium):
        return "Medium"

    return "Low"