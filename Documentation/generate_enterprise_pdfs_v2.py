#!/usr/bin/env python3
"""
Synthetic Enterprise PDF Generator for Oil & Gas RAG Testing

Generates realistic synthetic enterprise PDFs with:
- 5-20 pages each
- metadata CSV + per-document JSON metadata
- revision history
- approval workflow
- tables
- realistic oil & gas content across departments and document types

Install:
  pip install reportlab faker tqdm

Run:
  python generate_enterprise_pdfs.py --count 2000 --out ./synthetic_enterprise_pdfs

Optional:
  python generate_enterprise_pdfs.py --count 2000 --min-pages 5 --max-pages 20 --seed 42
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import textwrap
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from faker import Faker
except ImportError as exc:
    raise SystemExit("Missing dependency: faker. Install with: pip install faker reportlab tqdm") from exc

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x, **kwargs: x

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
        ListFlowable,
        ListItem,
        KeepTogether,
    )
except ImportError as exc:
    raise SystemExit("Missing dependency: reportlab. Install with: pip install reportlab faker tqdm") from exc

COMPANY = "AUGMIS Energy Services Ltd."
REGION = "Enterprise and Industrial Operations"

FUNCTION_DISTRIBUTION = {
    "HR": 140,
    "Finance & Accounting": 160,
    "Procurement / Supply Chain": 190,
    "Legal Affairs": 80,
    "Information Technology (IT)": 90,
    "Cybersecurity": 80,
    "Project Management Office (PMO)": 80,
    "Engineering": 110,
    "Operations": 120,
    "Maintenance": 110,
    "HSE": 130,
    "Quality Assurance / Quality Control": 90,
    "Sales": 120,
    "Marketing": 60,
    "Customer Service": 60,
    "Corporate Strategy": 40,
    "Executive Management": 40,
    "Drilling": 70,
    "Reservoir Engineering": 50,
    "Production": 70,
    "Integrity Management": 50,
    "Marine Operations": 30,
    "Logistics": 30,
}

FUNCTION_BLUEPRINTS = {
    "HR": {
        "doc_types": [
            "Employment Contract", "Leave Request", "Training Record",
            "Performance Review", "Organization Chart",
            "Onboarding Checklist", "Exit Clearance",
            "Talent Acquisition Dossier", "Employee Lifecycle Change"
        ],
        "topics": [
            "recruitment and hiring", "employee onboarding", "training and development",
            "performance management", "succession planning", "workforce planning",
            "compensation and benefits", "employee relations", "exit management"
        ],
    },
    "Finance & Accounting": {
        "doc_types": [
            "Invoice", "Financial Statement", "Budget Report",
            "Tax Filing", "Payment Voucher", "Accounts Receivable Statement",
            "Accounts Payable Statement", "Sales Invoice"
        ],
        "topics": [
            "accounts payable", "accounts receivable", "general ledger", "budgeting",
            "cost control", "financial reporting", "treasury management",
            "tax compliance", "audit coordination", "capital planning"
        ],
    },
    "Procurement / Supply Chain": {
        "doc_types": [
            "Purchase Order", "Vendor Contract", "Bid Evaluation",
            "Supplier Audit", "Delivery Note", "RFQ", "RFP", "Tender Evaluation"
        ],
        "topics": [
            "vendor management", "rfq processing", "tendering", "purchase orders",
            "supplier evaluation", "inventory planning", "material tracking",
            "contract negotiation"
        ],
    },
    "Legal Affairs": {
        "doc_types": [
            "Legal Opinion", "Contract", "NDA", "Court Filing", "Compliance Report"
        ],
        "topics": [
            "contract review", "litigation management", "regulatory compliance",
            "legal advisory", "intellectual property", "corporate governance"
        ],
    },
    "Information Technology (IT)": {
        "doc_types": [
            "SOP", "Change Request", "Incident Report",
            "Architecture Document", "Security Policy", "Backup Recovery Report"
        ],
        "topics": [
            "service desk", "infrastructure management", "cloud operations",
            "application support", "backup and recovery", "identity management"
        ],
    },
    "Cybersecurity": {
        "doc_types": [
            "Risk Assessment", "Security Audit", "Incident Report", "Security Policy"
        ],
        "topics": [
            "security operations", "threat hunting", "incident response",
            "vulnerability management", "iam", "dlp", "security awareness"
        ],
    },
    "Project Management Office (PMO)": {
        "doc_types": [
            "Project Charter", "Schedule", "Status Report", "Risk Register"
        ],
        "topics": [
            "project planning", "portfolio management", "scheduling",
            "resource allocation", "risk management", "project reporting"
        ],
    },
    "Engineering": {
        "doc_types": [
            "Drawing", "Specification", "Design Calculation", "Technical Report"
        ],
        "topics": [
            "design engineering", "process engineering", "mechanical engineering",
            "electrical engineering", "civil engineering", "technical review"
        ],
    },
    "Operations": {
        "doc_types": [
            "Operating Procedure", "Shift Report", "Daily Production Report"
        ],
        "topics": [
            "plant operations", "production planning", "process monitoring",
            "shift management", "operational excellence"
        ],
    },
    "Maintenance": {
        "doc_types": [
            "Work Order", "Maintenance Report", "Inspection Report"
        ],
        "topics": [
            "preventive maintenance", "corrective maintenance",
            "shutdown planning", "asset management", "reliability engineering"
        ],
    },
    "HSE": {
        "doc_types": [
            "Risk Assessment", "JSA", "PTW", "Incident Report", "Environmental Report"
        ],
        "topics": [
            "safety management", "incident investigation", "environmental compliance",
            "occupational health", "emergency response"
        ],
    },
    "Quality Assurance / Quality Control": {
        "doc_types": [
            "Inspection Report", "Quality Plan", "NCR", "Audit Report"
        ],
        "topics": [
            "audits", "inspection", "testing", "ncr management", "quality improvement"
        ],
    },
    "Sales": {
        "doc_types": [
            "Quotation", "Proposal", "Sales Report", "Sales Order", "Sales Invoice"
        ],
        "topics": [
            "lead generation", "opportunity management", "proposal development",
            "customer engagement", "account growth"
        ],
    },
    "Marketing": {
        "doc_types": [
            "Marketing Plan", "Campaign Report", "Market Research Report"
        ],
        "topics": [
            "branding", "campaign management", "digital marketing", "market research"
        ],
    },
    "Customer Service": {
        "doc_types": [
            "Service Request", "Customer Feedback Report", "Complaint Resolution Report"
        ],
        "topics": [
            "complaint handling", "support management", "customer satisfaction"
        ],
    },
    "Corporate Strategy": {
        "doc_types": [
            "Strategic Plan", "Business Case", "Transformation Report"
        ],
        "topics": [
            "strategic planning", "business transformation", "market analysis"
        ],
    },
    "Executive Management": {
        "doc_types": [
            "Board Minutes", "Executive Dashboard", "Decision Memo"
        ],
        "topics": [
            "corporate governance", "board reporting", "decision making"
        ],
    },
    "Drilling": {
        "doc_types": [
            "Well Plan", "Rig Operations Report", "Drilling Daily Report"
        ],
        "topics": ["well planning", "rig operations", "drilling execution"]
    },
    "Reservoir Engineering": {
        "doc_types": [
            "Reservoir Model Update", "Production Forecast", "Reservoir Study"
        ],
        "topics": ["reservoir modelling", "production forecasting"]
    },
    "Production": {
        "doc_types": [
            "Production Report", "Optimization Report", "Production Deferment Note"
        ],
        "topics": ["hydrocarbon production", "production optimization"]
    },
    "Integrity Management": {
        "doc_types": [
            "Corrosion Monitoring Report", "Pipeline Integrity Report", "Asset Integrity Review"
        ],
        "topics": ["corrosion monitoring", "pipeline integrity", "asset integrity"]
    },
    "Marine Operations": {
        "doc_types": [
            "Vessel Mobilization Report", "Offshore Logistics Report", "Marine Risk Assessment"
        ],
        "topics": ["vessel management", "offshore logistics"]
    },
    "Logistics": {
        "doc_types": [
            "Warehouse Report", "Transportation Note", "Material Control Register"
        ],
        "topics": ["warehousing", "transportation", "material control"]
    },
}

SECTION_LIBRARY = {
    "commercial_buy": ["Counterparty Summary", "Commercial Terms", "Line Items", "Delivery and Acceptance", "Payment Terms", "Approvals"],
    "commercial_sell": ["Client Summary", "Scope and Pricing", "Line Items", "Commercial Terms", "Billing Milestones", "Approvals"],
    "people": ["Profile Summary", "Request Context", "Role and Responsibilities", "Workflow and Approvals", "Effective Dates", "Attachments"],
    "finance": ["Financial Summary", "Supporting References", "Cost Breakdown", "Tax and Compliance", "Approvals", "Accounting Notes"],
    "risk": ["Activity Summary", "Hazard Identification", "Risk Evaluation", "Control Measures", "Residual Risk", "Approvals"],
    "project": ["Executive Summary", "Milestones", "Status and Variance", "Risks and Issues", "Actions", "Governance"],
    "technical": ["Scope", "Technical Basis", "Parameters and Conditions", "Inspection or Review", "Exceptions", "Recommendations"],
    "governance": ["Purpose", "Scope", "Key Decisions", "Obligations", "Controls", "Approvals"],
}

DOC_TYPE_FAMILY = {
    "Purchase Order": "commercial_buy",
    "Vendor Contract": "commercial_buy",
    "Bid Evaluation": "commercial_buy",
    "Supplier Audit": "commercial_buy",
    "Delivery Note": "commercial_buy",
    "RFQ": "commercial_buy",
    "RFP": "commercial_buy",
    "Tender Evaluation": "commercial_buy",
    "Quotation": "commercial_sell",
    "Proposal": "commercial_sell",
    "Sales Report": "commercial_sell",
    "Sales Order": "commercial_sell",
    "Sales Invoice": "commercial_sell",
    "Employment Contract": "people",
    "Leave Request": "people",
    "Training Record": "people",
    "Performance Review": "people",
    "Organization Chart": "people",
    "Onboarding Checklist": "people",
    "Exit Clearance": "people",
    "Talent Acquisition Dossier": "people",
    "Employee Lifecycle Change": "people",
    "Invoice": "finance",
    "Financial Statement": "finance",
    "Budget Report": "finance",
    "Tax Filing": "finance",
    "Payment Voucher": "finance",
    "Accounts Receivable Statement": "finance",
    "Accounts Payable Statement": "finance",
    "Risk Assessment": "risk",
    "JSA": "risk",
    "PTW": "risk",
    "Incident Report": "risk",
    "Environmental Report": "risk",
    "Security Audit": "risk",
    "Project Charter": "project",
    "Schedule": "project",
    "Status Report": "project",
    "Risk Register": "project",
    "SOP": "technical",
    "Change Request": "technical",
    "Architecture Document": "technical",
    "Backup Recovery Report": "technical",
    "Drawing": "technical",
    "Specification": "technical",
    "Design Calculation": "technical",
    "Technical Report": "technical",
    "Operating Procedure": "technical",
    "Shift Report": "technical",
    "Daily Production Report": "technical",
    "Work Order": "technical",
    "Maintenance Report": "technical",
    "Inspection Report": "technical",
    "Quality Plan": "technical",
    "NCR": "technical",
    "Audit Report": "technical",
    "Production Report": "technical",
    "Optimization Report": "technical",
    "Production Deferment Note": "technical",
    "Corrosion Monitoring Report": "technical",
    "Pipeline Integrity Report": "technical",
    "Asset Integrity Review": "technical",
    "Vessel Mobilization Report": "technical",
    "Offshore Logistics Report": "technical",
    "Marine Risk Assessment": "technical",
    "Warehouse Report": "technical",
    "Transportation Note": "technical",
    "Material Control Register": "technical",
    "Legal Opinion": "governance",
    "Contract": "governance",
    "NDA": "governance",
    "Court Filing": "governance",
    "Compliance Report": "governance",
    "Security Policy": "governance",
    "Marketing Plan": "governance",
    "Campaign Report": "governance",
    "Market Research Report": "governance",
    "Service Request": "governance",
    "Customer Feedback Report": "governance",
    "Complaint Resolution Report": "governance",
    "Strategic Plan": "governance",
    "Business Case": "governance",
    "Transformation Report": "governance",
    "Board Minutes": "governance",
    "Executive Dashboard": "governance",
    "Decision Memo": "governance",
    "Well Plan": "technical",
    "Rig Operations Report": "technical",
    "Drilling Daily Report": "technical",
    "Reservoir Model Update": "technical",
    "Production Forecast": "technical",
    "Reservoir Study": "technical",
}

APPROVAL_ROLES = [
    "Document Owner", "Functional Manager", "Finance Reviewer",
    "Legal Reviewer", "Operations Reviewer", "Executive Approver"
]

STATUSES = ["Draft", "Issued for Review", "Approved", "Controlled Copy"]
RISK_LEVELS = ["Low", "Medium", "High", "Critical"]
SITES = ["Doha HQ", "Terminal 3", "North Field", "West Yard", "Offshore Alpha", "Main Warehouse"]








@dataclass
class DocMeta:
    doc_id: str
    title: str
    department: str
    document_type: str
    topic: str
    status: str
    revision: str
    issue_date: str
    owner: str
    approver: str
    site: str
    confidentiality: str
    pages_target: int
    file_path: str
    doc_family: str
    attributes: Dict[str, str]

class NumberedCanvas:
    """Canvas wrapper for footer and page numbers."""
    def __init__(self, canvas, doc_meta: DocMeta):
        self.canvas = canvas
        self.meta = doc_meta

    def __call__(self, canvas, doc):
        width, height = A4
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#555555"))
        footer = f"{COMPANY} | {self.meta.doc_id} | Rev {self.meta.revision} | {self.meta.confidentiality}"
        canvas.drawString(1.5 * cm, 1.0 * cm, footer[:110])
        canvas.drawRightString(width - 1.5 * cm, 1.0 * cm, f"Page {doc.page}")
        canvas.restoreState()


def safe_filename(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")
    return text[:160]


def random_date(fake: Faker) -> date:
    start = date(2022, 1, 1)
    end = date.today()
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 1)))


def money() -> str:
    return f"USD {random.randint(5_000, 2_500_000):,}.00"

def safe_folder(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")

def build_generation_plan(count: int) -> List[str]:
    weighted = []
    for dept, qty in FUNCTION_DISTRIBUTION.items():
        weighted.extend([dept] * qty)

    if count == len(weighted):
        random.shuffle(weighted)
        return weighted

    departments = list(FUNCTION_DISTRIBUTION.keys())
    weights = list(FUNCTION_DISTRIBUTION.values())

    if count < len(weighted):
        random.shuffle(weighted)
        return weighted[:count]

    while len(weighted) < count:
        weighted.extend(random.choices(departments, weights=weights, k=min(100, count - len(weighted))))
    random.shuffle(weighted)
    return weighted[:count]

def make_doc_attributes(fake: Faker, dept: str, doc_type: str, topic: str) -> Dict[str, str]:
    attrs = {
        "business_unit": dept,
        "cost_center": f"CC-{random.randint(1000,9999)}",
        "reference_number": f"REF-{random.randint(100000,999999)}",
        "topic": topic,
    }

    if doc_type in {"Purchase Order", "Vendor Contract", "Bid Evaluation", "Supplier Audit", "Delivery Note", "RFQ", "RFP", "Tender Evaluation", "Invoice", "Payment Voucher", "Accounts Payable Statement"}:
        attrs["vendor_name"] = fake.company()
        attrs["vendor_code"] = f"VND-{random.randint(1000,9999)}"
        attrs["vendor_address"] = fake.address().replace("\n", ", ")

    if doc_type in {"Sales Order", "Sales Invoice", "Quotation", "Proposal", "Sales Report", "Accounts Receivable Statement"}:
        attrs["client_name"] = fake.company()
        attrs["client_id"] = f"CLI-{random.randint(1000,9999)}"
        attrs["billing_address"] = fake.address().replace("\n", ", ")
        attrs["opportunity_id"] = f"OPP-{random.randint(10000,99999)}"

    if doc_type in {"Employment Contract", "Leave Request", "Training Record", "Performance Review", "Onboarding Checklist", "Exit Clearance", "Employee Lifecycle Change"}:
        attrs["employee_name"] = fake.name()
        attrs["employee_id"] = f"EMP-{random.randint(10000,99999)}"
        attrs["designation"] = random.choice(["Engineer", "Analyst", "Supervisor", "Coordinator", "Manager"])
        attrs["manager_name"] = fake.name()

    if doc_type == "Talent Acquisition Dossier":
        attrs["candidate_name"] = fake.name()
        attrs["candidate_email"] = fake.email()
        attrs["requisition_id"] = f"REQ-{random.randint(10000,99999)}"
        attrs["position_title"] = random.choice(["HR Analyst", "Procurement Lead", "Project Engineer", "IT Specialist", "Operations Manager"])

    if doc_type == "Leave Request":
        attrs["leave_type"] = random.choice(["Annual Leave", "Sick Leave", "Emergency Leave", "Maternity Leave"])
        attrs["leave_days"] = str(random.randint(1, 21))

    if doc_type == "Exit Clearance":
        attrs["exit_type"] = random.choice(["Resignation", "Termination", "Retirement", "End of Contract"])
        attrs["last_working_day"] = str(random_date(fake))

    if doc_type in {"Project Charter", "Status Report", "Risk Register", "Proposal", "Sales Order", "Sales Invoice"}:
        attrs["project_name"] = random.choice(["Orion Upgrade", "Falcon EPC", "North Field Revamp", "Terminal 3 Expansion", "Warehouse Digitization"])
        attrs["project_code"] = f"PRJ-{random.randint(1000,9999)}"

    if doc_type in {"Incident Report", "Risk Assessment", "JSA", "PTW", "Security Audit", "Environmental Report", "Marine Risk Assessment"}:
        attrs["risk_level"] = random.choice(RISK_LEVELS)
        attrs["activity_area"] = random.choice(["Operations", "Warehouse", "Drilling", "Logistics", "Office", "Marine"])

    return attrs


def make_doc_meta(i: int, fake: Faker, out_root: Path, dept: str) -> DocMeta:
    blueprint = FUNCTION_BLUEPRINTS[dept]
    doc_type = random.choice(blueprint["doc_types"])
    topic = random.choice(blueprint["topics"])
    rev_num = random.randint(0, 8)
    issue = random_date(fake)
    folder = out_root / safe_folder(dept) / safe_folder(doc_type)
    doc_id = f"AES-{safe_folder(dept)[:3].upper()}-{safe_folder(doc_type)[:4].upper()}-{i:05d}"
    title = f"{doc_type}: {topic.title()} - {random.choice(SITES)}"
    file_path = str(folder / safe_filename(f"{doc_id}_{title}.pdf"))
    attrs = make_doc_attributes(fake, dept, doc_type, topic)

    return DocMeta(
        doc_id=doc_id,
        title=title,
        department=dept,
        document_type=doc_type,
        topic=topic,
        status=random.choice(STATUSES),
        revision=f"{rev_num:02d}",
        issue_date=issue.isoformat(),
        owner=fake.name(),
        approver=fake.name(),
        site=random.choice(SITES),
        confidentiality=random.choice(["Internal", "Confidential", "Restricted"]),
        pages_target=random.randint(5, 20),
        file_path=file_path,
        doc_family=DOC_TYPE_FAMILY[doc_type],
        attributes=attrs,
    )



def styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(name="CoverTitle", parent=base["Title"], alignment=TA_CENTER, fontSize=22, leading=28, spaceAfter=20))
    base.add(ParagraphStyle(name="DocSubTitle", parent=base["Normal"], alignment=TA_CENTER, fontSize=11, leading=15, textColor=colors.HexColor("#444444")))
    base.add(ParagraphStyle(name="SectionHeading", parent=base["Heading1"], fontSize=14, leading=18, spaceBefore=12, spaceAfter=8, textColor=colors.HexColor("#1F4E79")))
    base.add(ParagraphStyle(name="Small", parent=base["Normal"], fontSize=8, leading=10))
    base.add(ParagraphStyle(name="Body", parent=base["BodyText"], fontSize=9.5, leading=13, alignment=TA_LEFT))
    return base


def paragraph(fake: Faker, meta: DocMeta, section: str) -> str:
    a = meta.attributes
    vendor = a.get("vendor_name", "the approved vendor")
    client = a.get("client_name", "the client")
    employee = a.get("employee_name") or a.get("candidate_name", "the employee")
    project = a.get("project_name", "the assigned project")

    if meta.doc_family == "commercial_buy":
        return (
            f"This section documents {meta.document_type.lower()} controls for {vendor}. "
            f"The document supports {meta.topic}, defines commercial obligations, and records traceable approval, delivery, and payment requirements for {project}. "
            f"Procurement, Finance, and Operations shall validate quantity, pricing, delivery milestones, and evidence before closure."
        )

    if meta.doc_family == "commercial_sell":
        return (
            f"This section documents {meta.document_type.lower()} terms for {client}. "
            f"It supports {meta.topic} and establishes the commercial basis for pricing, scope, billing references, and client approvals related to {project}. "
            f"Sales, Finance, and Delivery teams shall maintain traceable customer communication and milestone evidence."
        )

    if meta.doc_family == "people":
        return (
            f"This section governs {meta.document_type.lower()} processing for {employee}. "
            f"It supports {meta.topic} and records approvals, effective dates, supporting documents, and responsibilities across HR, the line manager, and the employee record owner."
        )

    if meta.doc_family == "finance":
        return (
            f"This section records {meta.document_type.lower()} controls for {meta.department}. "
            f"It supports {meta.topic} and ensures traceable evidence for accounting treatment, budget impact, tax handling, and payment authorization."
        )

    if meta.doc_family == "risk":
        return (
            f"This section addresses {meta.document_type.lower()} requirements for {a.get('activity_area', meta.site)}. "
            f"It supports {meta.topic} and defines hazards, controls, approvals, and evidence retention for safe and compliant execution."
        )

    if meta.doc_family == "project":
        return (
            f"This section documents project governance for {project}. "
            f"It supports {meta.topic} and records milestones, status, risks, resource alignment, and executive reporting expectations."
        )

    if meta.doc_family == "technical":
        return (
            f"This section captures technical and operational requirements for {meta.document_type.lower()} in {meta.site}. "
            f"It supports {meta.topic} and provides parameters, review points, inspection expectations, and recommended actions."
        )

    return (
        f"This section governs {meta.document_type.lower()} requirements for {meta.department}. "
        f"It supports {meta.topic} and maintains formal traceability, approvals, and evidence in the controlled repository."
    )




def metadata_table(meta: DocMeta):
    a = meta.attributes
    rows = [
        ["Document ID", meta.doc_id, "Department", meta.department],
        ["Document Type", meta.document_type, "Status", meta.status],
        ["Revision", meta.revision, "Issue Date", meta.issue_date],
        ["Owner", meta.owner, "Approver", meta.approver],
        ["Site", meta.site, "Confidentiality", meta.confidentiality],
    ]

    for left_key, right_key in [
        ("vendor_name", "vendor_code"),
        ("client_name", "client_id"),
        ("employee_name", "employee_id"),
        ("candidate_name", "requisition_id"),
        ("project_name", "project_code"),
        ("designation", "manager_name"),
        ("leave_type", "leave_days"),
        ("exit_type", "last_working_day"),
        ("risk_level", "activity_area"),
    ]:
        if a.get(left_key) or a.get(right_key):
            rows.append([
                left_key.replace("_", " ").title(), a.get(left_key, "-"),
                right_key.replace("_", " ").title(), a.get(right_key, "-"),
            ])

    table = Table(rows, colWidths=[3.2*cm, 5.8*cm, 3.2*cm, 5.8*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#F2F2F2")),
        ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#F2F2F2")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    return table


def revision_table(meta: DocMeta, fake: Faker):
    rev_count = max(2, min(6, int(meta.revision) + 1))
    rows = [["Rev", "Date", "Description", "Prepared By", "Approved By"]]
    issue = date.fromisoformat(meta.issue_date)
    for r in range(rev_count):
        d = issue - timedelta(days=(rev_count-r-1) * random.randint(15, 90))
        desc = random.choice([
            "Initial issue for internal review", "Updated responsibilities and control requirements",
            "Added approval workflow and record retention requirements", "Aligned with latest operational audit findings",
            "Updated references and implementation timeline", "Approved for controlled use",
        ])
        rows.append([f"{r:02d}", d.isoformat(), desc, fake.name(), meta.approver if r == rev_count-1 else fake.name()])
    table = Table(rows, colWidths=[1.5*cm, 2.4*cm, 7.2*cm, 3.7*cm, 3.7*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7.5),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    return table


def approval_table(meta: DocMeta, fake: Faker):
    roles = random.sample(APPROVAL_ROLES, 4)
    rows = [["Step", "Role", "Name", "Decision", "Date"]]
    base = date.fromisoformat(meta.issue_date) - timedelta(days=random.randint(2, 14))
    for idx, role in enumerate(roles, 1):
        rows.append([str(idx), role, meta.owner if idx == 1 else fake.name(), random.choice(["Reviewed", "Approved", "Approved with Comments"]), (base + timedelta(days=idx)).isoformat()])
    table = Table(rows, colWidths=[1.2*cm, 4.4*cm, 5.2*cm, 4.2*cm, 3.0*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#385723")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    return table


def operational_table(meta: DocMeta, fake: Faker):
    a = meta.attributes

    if meta.doc_family == "commercial_buy":
        rows = [["Line", "Item / Service", "Vendor", "Qty", "Unit Price", "Total"]]
        for n in range(random.randint(5, 10)):
            qty = random.randint(1, 25)
            price = random.randint(500, 15000)
            rows.append([
                str(n + 1),
                random.choice(["Valve Assembly", "PPE Supply", "Calibration Service", "Cabling", "Scaffolding", "Inspection Service"]),
                a.get("vendor_name", fake.company()),
                str(qty),
                f"USD {price:,}",
                f"USD {qty * price:,}",
            ])
    elif meta.doc_family == "commercial_sell":
        rows = [["Line", "Description", "Client", "Qty", "Rate", "Amount"]]
        for n in range(random.randint(5, 10)):
            qty = random.randint(1, 20)
            price = random.randint(1000, 25000)
            rows.append([
                str(n + 1),
                random.choice(["Consulting Services", "Engineering Support", "Inspection Scope", "Annual Service Package", "Implementation Milestone"]),
                a.get("client_name", fake.company()),
                str(qty),
                f"USD {price:,}",
                f"USD {qty * price:,}",
            ])
    elif meta.doc_family == "people":
        rows = [["Step", "Activity", "Owner", "Status", "Date", "Remarks"]]
        for n in range(random.randint(5, 9)):
            rows.append([
                str(n + 1),
                random.choice(["Interview Scheduled", "Offer Released", "Documents Verified", "Training Completed", "Manager Review", "Asset Return"]),
                fake.name(),
                random.choice(["Pending", "Completed", "In Review"]),
                (date.today() + timedelta(days=random.randint(1, 45))).isoformat(),
                random.choice(["Evidence attached", "Awaiting approval", "HR updated", "Employee informed"]),
            ])
    elif meta.doc_family == "finance":
        rows = [["Line", "Reference", "Description", "Base Amount", "Tax", "Total"]]
        for n in range(random.randint(5, 10)):
            base = random.randint(2000, 30000)
            rows.append([
                str(n + 1),
                f"ACC-{random.randint(10000,99999)}",
                random.choice(["Consultancy Fee", "Asset Purchase", "Travel Expense", "Vendor Settlement", "Service Revenue"]),
                f"USD {base:,}",
                f"USD {int(base * 0.15):,}",
                f"USD {int(base * 1.15):,}",
            ])
    elif meta.doc_family == "risk":
        rows = [["Hazard", "Cause", "Consequence", "Initial Risk", "Control", "Residual Risk"]]
        for _ in range(random.randint(5, 10)):
            rows.append([
                random.choice(["Dropped Object", "Gas Exposure", "Cyber Breach", "Permit Failure", "Vehicle Collision"]),
                random.choice(["Human Error", "Equipment Failure", "Poor Isolation", "Unauthorized Change"]),
                random.choice(["Injury", "Downtime", "Data Loss", "Regulatory Breach"]),
                random.choice(RISK_LEVELS),
                random.choice(["LOTO", "Permit Review", "Monitoring", "Access Control", "Supervisor Check"]),
                random.choice(["Low", "Medium", "High"]),
            ])
    elif meta.doc_family == "project":
        rows = [["Workstream", "Planned", "Actual", "Variance", "Owner", "Next Action"]]
        for _ in range(random.randint(5, 9)):
            rows.append([
                random.choice(["Engineering", "Procurement", "Construction", "Testing", "Approval"]),
                f"{random.randint(20,100)}%",
                f"{random.randint(10,100)}%",
                f"{random.randint(-15,20)}%",
                fake.name(),
                random.choice(["Escalate", "Recover schedule", "Close action", "Await approval"]),
            ])
    else:
        rows = [["Item", "Parameter / Task", "Responsible", "Status", "Date", "Remarks"]]
        for n in range(random.randint(5, 10)):
            rows.append([
                str(n + 1),
                random.choice(["Review drawing", "Inspect asset", "Verify setting", "Close NCR", "Check inventory", "Issue permit"]),
                fake.name(),
                random.choice(["Open", "In Progress", "Closed", "Pending Review"]),
                (date.today() + timedelta(days=random.randint(1, 60))).isoformat(),
                random.choice(["Record retained", "Follow-up needed", "Approved", "No deviation"]),
            ])

    table = Table(rows, repeatRows=1, colWidths=[2.4*cm, 4.0*cm, 4.0*cm, 2.6*cm, 2.8*cm, 3.0*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    return table

def bullets(fake: Faker, meta: DocMeta, count: int = 6):
    items = []
    verbs = ["Verify", "Maintain", "Escalate", "Document", "Review", "Approve", "Monitor", "Retain"]
    objects = ["permit conditions", "contract deliverables", "inspection records", "budget variance", "risk controls", "vendor evidence", "engineering drawings", "audit trail"]
    for _ in range(count):
        items.append(ListItem(Paragraph(f"{random.choice(verbs)} {random.choice(objects)} for {meta.topic} and record the outcome in the controlled repository.", styles()["Body"])))
    return ListFlowable(items, bulletType="bullet", leftIndent=16)


def build_pdf(meta: DocMeta, fake: Faker) -> None:
    out = Path(meta.file_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    s = styles()

    doc = BaseDocTemplate(
        str(out),
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.7*cm,
        title=meta.title,
        author=COMPANY,
        subject=f"Synthetic {meta.document_type} for {meta.department}",
        creator="Synthetic Enterprise PDF Generator",
        keywords=f"{meta.department}, {meta.document_type}, {meta.doc_family}, synthetic, enterprise, {meta.topic}",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="default", frames=[frame], onPage=NumberedCanvas(None, meta))])

    story = []
    story.append(Spacer(1, 2.0*cm))
    story.append(Paragraph(COMPANY, s["DocSubTitle"]))
    story.append(Paragraph(REGION, s["DocSubTitle"]))
    story.append(Spacer(1, 1.0*cm))
    story.append(Paragraph(meta.title, s["CoverTitle"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(metadata_table(meta))
    story.append(Spacer(1, 0.8*cm))
    story.append(Paragraph("Document Control", s["SectionHeading"]))
    story.append(revision_table(meta, fake))
    story.append(PageBreak())

    story.append(Paragraph("Approval Workflow", s["SectionHeading"]))
    story.append(approval_table(meta, fake))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("Workflow Notes", s["SectionHeading"]))
    story.append(Paragraph(paragraph(fake, meta, "Workflow Notes"), s["Body"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(bullets(fake, meta, 5))

    for idx, section in enumerate(SECTION_LIBRARY[meta.doc_family], 1):
        story.append(Paragraph(f"{idx}. {section}", s["SectionHeading"]))
        for _ in range(random.randint(2, 4)):
            story.append(Paragraph(paragraph(fake, meta, section), s["Body"]))
            story.append(Spacer(1, 0.15*cm))
        if idx in [2, 4, 6] or random.random() < 0.35:
            story.append(Spacer(1, 0.25*cm))
            story.append(KeepTogether([Paragraph(f"{section} Register", s["Heading3"]), operational_table(meta, fake)]))
            story.append(Spacer(1, 0.3*cm))
        if idx % 3 == 0:
            story.append(PageBreak())

    # Add appendices until target page count is approximately met.
    # ReportLab cannot know final page count before build, so we pad content proportionally.
    appendix_count = max(2, meta.pages_target // 3)
    for a in range(1, appendix_count + 1):
        story.append(Paragraph(f"Appendix {a}: Supporting Evidence", s["SectionHeading"]))
        story.append(Paragraph(paragraph(fake, meta, "Appendix"), s["Body"]))
        story.append(Spacer(1, 0.2*cm))
        story.append(operational_table(meta, fake))
        story.append(Spacer(1, 0.3*cm))
        if a % 2 == 0:
            story.append(PageBreak())

    doc.build(story)


def write_metadata(meta_list: List[DocMeta], out_root: Path) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    csv_path = out_root / "metadata_index.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(meta_list[0]).keys()))
        writer.writeheader()
        for m in meta_list:
            writer.writerow(asdict(m))
    json_path = out_root / "metadata_index.json"
    json_path.write_text(json.dumps([asdict(m) for m in meta_list], indent=2), encoding="utf-8")


def validate_args(args):
    if args.count < 1:
        raise SystemExit("--count must be at least 1")
    if args.min_pages < 1 or args.max_pages < args.min_pages:
        raise SystemExit("Invalid page range")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic oil and gas enterprise PDFs for RAG testing.")
    parser.add_argument("--count", type=int, default=2000, help="Number of PDFs to generate. Default: 2000")
    parser.add_argument("--out", type=Path, default=Path("synthetic_enterprise_pdfs"), help="Output folder")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--min-pages", type=int, default=5, help="Approximate minimum pages per PDF")
    parser.add_argument("--max-pages", type=int, default=20, help="Approximate maximum pages per PDF")
    parser.add_argument("--metadata-only", action="store_true", help="Create metadata files only, without PDFs")
    args = parser.parse_args()
    validate_args(args)

    random.seed(args.seed)
    fake = Faker("en_US")
    Faker.seed(args.seed)

    out_root: Path = args.out
    out_root.mkdir(parents=True, exist_ok=True)

    plan = build_generation_plan(args.count)

    meta_list: List[DocMeta] = []
    for i, dept in enumerate(plan, start=1):
        meta = make_doc_meta(i, fake, out_root, dept)
        meta.pages_target = random.randint(args.min_pages, args.max_pages)
        meta_list.append(meta)

    write_metadata(meta_list, out_root)

    if args.metadata_only:
        print(f"Metadata generated: {out_root}")
        return

    for meta in tqdm(meta_list, desc="Generating PDFs"):
        build_pdf(meta, fake)
        # Per-file sidecar metadata for ingestion tests
        sidecar = Path(meta.file_path).with_suffix(".metadata.json")
        sidecar.write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")

    print(f"Done. Generated {len(meta_list)} PDFs in: {out_root.resolve()}")
    print(f"Metadata CSV: {(out_root / 'metadata_index.csv').resolve()}")
    print(f"Metadata JSON: {(out_root / 'metadata_index.json').resolve()}")

if __name__ == "__main__":
    main()
