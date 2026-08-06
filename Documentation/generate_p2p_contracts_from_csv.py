#!/usr/bin/env python3
"""
Generate vendor contract PDFs from the P2P invoice CSV.

This script creates contract-style documents, not invoice-style documents. It derives
multiple contracts per vendor from actual invoice spend and produces a mix of:
- expired contracts
- contracts expiring within a few days
- contracts with about 70% utilization

Install:
  pip install reportlab tqdm

Example:
  python3 generate_p2p_contracts_from_csv.py \
    --csv /mnt/d/AUGMIS/p2p_vendor_invoices_100.csv \
    --out ./p2p_contracts
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Iterable, List

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x, **kwargs: x

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle
except ImportError as exc:
    raise SystemExit("Missing dependency: reportlab. Install with: pip install reportlab tqdm") from exc


BUYER_NAME = "Infomentica Traders"
BUYER_ADDRESS = [
    "Enterprise Procurement & Trade Division",
    "King Fahd Road Business District",
    "Riyadh 12271, Kingdom of Saudi Arabia",
]
BUYER_CONTACT = "contracts.office@infomentica-traders.com | +966 11 555 0194"
BUYER_ENTITY_LINE = "Commercial Contracts and Strategic Sourcing Office"
TODAY = date(2026, 6, 16)
UTILIZATION_TARGETS = {
    "expired": Decimal("0.92"),
    "expiring_soon": Decimal("0.83"),
    "utilized_70": Decimal("0.70"),
    "active_buffer": Decimal("0.46"),
}
PERIOD_YEARS = (1, 3, 5)
CONTRACT_TYPES = (
    "Master Service Agreement",
    "Call-Off Supply Agreement",
    "Framework Purchase Agreement",
    "Rate Contract",
    "Service Retainer Agreement",
)
PAYMENT_TERMS_LIBRARY = (
    "Net 30 from approved invoice",
    "Net 45 from GRN or SES acceptance",
    "Net 60 from document and tax validation",
)


@dataclass
class SourceRow:
    invoice_id: str
    vendor_id: str
    vendor_name: str
    vendor_country: str
    invoice_date: str
    payment_terms: str
    due_date: str
    po_number: str
    po_date: str
    grn_number: str
    grn_date: str
    ses_number: str
    goods_or_service_supplied: str
    category: str
    delivery_location: str
    department: str
    cost_center: str
    requestor: str
    buyer: str
    quantity: str
    uom: str
    unit_price: str
    currency: str
    subtotal_amount: str
    discount_percent: str
    discount_amount: str
    taxable_amount: str
    vat_percent: str
    vat_amount: str
    invoice_total: str
    amount_paid: str
    outstanding_amount: str
    invoice_status: str
    aging_days: str
    payment_method: str
    approval_status: str
    approver_role: str
    three_way_match: str
    payment_block: str
    remarks: str


@dataclass
class ContractLine:
    invoice_id: str
    po_number: str
    description: str
    category: str
    delivery_location: str
    department: str
    value: str


@dataclass
class ContractRecord:
    contract_id: str
    vendor_id: str
    vendor_name: str
    vendor_country: str
    buyer_name: str
    contract_type: str
    contract_title: str
    category_summary: str
    primary_department: str
    requestor: str
    buyer: str
    cost_center: str
    contract_currency: str
    start_date: str
    end_date: str
    term_years: int
    status: str
    utilization_band: str
    contract_value: str
    utilized_value: str
    unutilized_value: str
    utilization_percent: str
    payment_terms: str
    commercial_model: str
    renewal_option: str
    linked_invoice_count: int
    linked_po_count: int
    source_invoice_ids: List[str]
    source_po_numbers: List[str]
    remarks: str
    file_path: str
    lines: List[ContractLine]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate vendor contracts from invoice CSV.")
    parser.add_argument("--csv", type=Path, required=True, help="Source CSV file")
    parser.add_argument("--out", type=Path, default=Path("p2p_contracts"), help="Output folder")
    parser.add_argument("--limit", type=int, default=0, help="Optional max source rows to process")
    parser.add_argument("--buyer-name", default=BUYER_NAME, help="Buyer / contracting organization")
    parser.add_argument("--metadata-only", action="store_true", help="Write JSON/CSV metadata without generating PDFs")
    return parser.parse_args()


def clean_value(value: str) -> str:
    return str(value or "").strip()


def safe_filename(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")
    return cleaned[:180] or "contract"


def parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(clean_value(value) or "0")
    except InvalidOperation:
        return Decimal("0")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_money(currency: str, value: str) -> str:
    return f"{currency} {parse_decimal(value):,.2f}"


def format_decimal(value: Decimal) -> str:
    return f"{quantize_money(value):.2f}"


def format_percent(value: str) -> str:
    return f"{parse_decimal(value):,.2f}%"


def format_date(value: str) -> str:
    text = clean_value(value)
    if not text:
        return "-"
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return text


def normalize_row(row: Dict[str, str]) -> SourceRow:
    aging_key = next((key for key in row if key.startswith("Aging_Days_As_Of_")), "")
    return SourceRow(
        invoice_id=clean_value(row.get("Invoice_ID")),
        vendor_id=clean_value(row.get("Vendor_ID")),
        vendor_name=clean_value(row.get("Vendor_Name")),
        vendor_country=clean_value(row.get("Vendor_Country")),
        invoice_date=clean_value(row.get("Invoice_Date")),
        payment_terms=clean_value(row.get("Payment_Terms")),
        due_date=clean_value(row.get("Due_Date")),
        po_number=clean_value(row.get("PO_Number")),
        po_date=clean_value(row.get("PO_Date")),
        grn_number=clean_value(row.get("GRN_Number")),
        grn_date=clean_value(row.get("GRN_Date")),
        ses_number=clean_value(row.get("SES_Number")),
        goods_or_service_supplied=clean_value(row.get("Goods_or_Service_Supplied")),
        category=clean_value(row.get("Category")),
        delivery_location=clean_value(row.get("Delivery_Location")),
        department=clean_value(row.get("Department")),
        cost_center=clean_value(row.get("Cost_Center")),
        requestor=clean_value(row.get("Requestor")),
        buyer=clean_value(row.get("Buyer")),
        quantity=clean_value(row.get("Quantity")),
        uom=clean_value(row.get("UOM")),
        unit_price=clean_value(row.get("Unit_Price")),
        currency=clean_value(row.get("Currency")) or "USD",
        subtotal_amount=clean_value(row.get("Subtotal_Amount")),
        discount_percent=clean_value(row.get("Discount_Percent")),
        discount_amount=clean_value(row.get("Discount_Amount")),
        taxable_amount=clean_value(row.get("Taxable_Amount")),
        vat_percent=clean_value(row.get("VAT_Percent")),
        vat_amount=clean_value(row.get("VAT_Amount")),
        invoice_total=clean_value(row.get("Invoice_Total")),
        amount_paid=clean_value(row.get("Amount_Paid")),
        outstanding_amount=clean_value(row.get("Outstanding_Amount")),
        invoice_status=clean_value(row.get("Invoice_Status")),
        aging_days=clean_value(row.get(aging_key)),
        payment_method=clean_value(row.get("Payment_Method")),
        approval_status=clean_value(row.get("Approval_Status")),
        approver_role=clean_value(row.get("Approver_Role")),
        three_way_match=clean_value(row.get("Three_Way_Match")),
        payment_block=clean_value(row.get("Payment_Block")),
        remarks=clean_value(row.get("Remarks")),
    )


def read_rows(csv_path: Path, limit: int) -> List[SourceRow]:
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if limit > 0:
        rows = rows[:limit]
    return [normalize_row(row) for row in rows]


def group_by_vendor(rows: List[SourceRow]) -> Dict[str, List[SourceRow]]:
    grouped: Dict[str, List[SourceRow]] = {}
    for row in rows:
        key = row.vendor_id or row.vendor_name
        grouped.setdefault(key, []).append(row)
    return grouped


def choose_contract_count(rows: List[SourceRow]) -> int:
    if len(rows) >= 6:
        return 3
    if len(rows) >= 3:
        return 2
    return 2


def status_for_contract(vendor_index: int, contract_index: int, contract_count: int) -> str:
    if contract_count >= 3:
        cycle = ("expired", "expiring_soon", "utilized_70")
        return cycle[contract_index]
    if vendor_index % 2 == 0:
        cycle = ("expired", "utilized_70")
    else:
        cycle = ("expiring_soon", "utilized_70")
    return cycle[contract_index]


def weights_for_count(contract_count: int) -> List[Decimal]:
    if contract_count == 3:
        return [Decimal("0.23"), Decimal("0.31"), Decimal("0.46")]
    return [Decimal("0.38"), Decimal("0.62")]


def allocate_utilized_amounts(total: Decimal, contract_count: int) -> List[Decimal]:
    weights = weights_for_count(contract_count)
    allocated: List[Decimal] = []
    running = Decimal("0")
    for idx, weight in enumerate(weights):
        if idx == len(weights) - 1:
            amount = total - running
        else:
            amount = quantize_money(total * weight)
            running += amount
        allocated.append(amount)
    return allocated


def term_years_for(vendor_index: int, contract_index: int) -> int:
    return PERIOD_YEARS[(vendor_index + contract_index) % len(PERIOD_YEARS)]


def contract_dates(status: str, years: int, vendor_index: int, contract_index: int) -> tuple[str, str]:
    if status == "expired":
        end_date = TODAY - timedelta(days=12 + vendor_index + contract_index * 5)
    elif status == "expiring_soon":
        end_date = TODAY + timedelta(days=4 + ((vendor_index + contract_index) % 8))
    elif status == "utilized_70":
        end_date = TODAY + timedelta(days=180 + vendor_index * 3 + contract_index * 21)
    else:
        end_date = TODAY + timedelta(days=365)
    start_date = end_date - timedelta(days=years * 365)
    return start_date.isoformat(), end_date.isoformat()


def build_contract_title(contract_type: str, categories: List[str], vendor_name: str) -> str:
    category_phrase = ", ".join(categories[:2]) if categories else "strategic sourcing"
    return f"{contract_type} for {category_phrase} with {vendor_name}"


def renewal_option_for(status: str, years: int) -> str:
    if status == "expired":
        return "Renewal lapsed pending commercial revalidation."
    if years == 5:
        return "Two optional one-year extensions subject to utilization review."
    if years == 3:
        return "One optional one-year extension subject to performance and budget approval."
    return "Renewal subject to annual sourcing review and revised rates."


def commercial_model_for(categories: List[str]) -> str:
    lower = " ".join(categories).lower()
    if any(term in lower for term in ("service", "consult", "inspection", "training", "maintenance")):
        return "Rate-based service contract with call-off work orders and milestone-backed invoices."
    return "Framework supply agreement with release orders against approved unit rates and delivery schedules."


def contract_type_for(categories: List[str], vendor_index: int, contract_index: int) -> str:
    lower = " ".join(categories).lower()
    if any(term in lower for term in ("service", "consult", "inspection", "training", "maintenance")):
        candidates = ("Master Service Agreement", "Service Retainer Agreement", "Rate Contract")
    else:
        candidates = ("Framework Purchase Agreement", "Call-Off Supply Agreement", "Rate Contract")
    return candidates[(vendor_index + contract_index) % len(candidates)]


def distribute_rows(rows: List[SourceRow], contract_count: int) -> List[List[SourceRow]]:
    sorted_rows = sorted(rows, key=lambda row: parse_decimal(row.invoice_total), reverse=True)
    buckets = [[] for _ in range(contract_count)]
    totals = [Decimal("0") for _ in range(contract_count)]
    for row in sorted_rows:
        idx = min(range(contract_count), key=lambda i: totals[i])
        buckets[idx].append(row)
        totals[idx] += parse_decimal(row.invoice_total)
    return buckets


def build_contracts(rows: List[SourceRow], out_root: Path, buyer_name: str) -> List[ContractRecord]:
    vendor_groups = group_by_vendor(rows)
    records: List[ContractRecord] = []
    for vendor_index, vendor_key in enumerate(sorted(vendor_groups.keys())):
        vendor_rows = vendor_groups[vendor_key]
        contract_count = choose_contract_count(vendor_rows)
        buckets = distribute_rows(vendor_rows, contract_count)
        vendor_total = sum(parse_decimal(row.invoice_total) for row in vendor_rows)
        utilized_allocations = allocate_utilized_amounts(vendor_total, contract_count)

        for contract_index, bucket in enumerate(buckets):
            if not bucket:
                continue
            first = bucket[0]
            status = status_for_contract(vendor_index, contract_index, contract_count)
            years = term_years_for(vendor_index, contract_index)
            start_date, end_date = contract_dates(status, years, vendor_index, contract_index)
            utilized_value = utilized_allocations[contract_index]
            utilization_target = UTILIZATION_TARGETS[status]
            contract_value = quantize_money(utilized_value / utilization_target) if utilization_target > 0 else utilized_value
            if contract_value < utilized_value:
                contract_value = utilized_value
            unutilized = quantize_money(contract_value - utilized_value)
            utilization_percent = quantize_money((utilized_value / contract_value) * Decimal("100")) if contract_value > 0 else Decimal("0")
            categories = sorted({row.category for row in bucket if row.category})
            source_pos = sorted({row.po_number for row in bucket if row.po_number})
            source_invoices = [row.invoice_id for row in bucket]
            contract_type = contract_type_for(categories, vendor_index, contract_index)
            contract_id = f"CTR-{TODAY.year}-{vendor_index + 1:02d}{contract_index + 1:02d}-{(first.vendor_id or 'VND')[-4:]}"
            title = build_contract_title(contract_type, categories, first.vendor_name)
            currency = first.currency or "USD"
            lines = [
                ContractLine(
                    invoice_id=row.invoice_id,
                    po_number=row.po_number,
                    description=row.goods_or_service_supplied,
                    category=row.category,
                    delivery_location=row.delivery_location,
                    department=row.department,
                    value=row.invoice_total,
                )
                for row in bucket
            ]
            output_name = safe_filename(f"{contract_id}_{first.vendor_name}.pdf")
            records.append(
                ContractRecord(
                    contract_id=contract_id,
                    vendor_id=first.vendor_id,
                    vendor_name=first.vendor_name,
                    vendor_country=first.vendor_country,
                    buyer_name=buyer_name,
                    contract_type=contract_type,
                    contract_title=title,
                    category_summary=", ".join(categories[:4]) if categories else "General supply and services",
                    primary_department=first.department,
                    requestor=first.requestor,
                    buyer=first.buyer,
                    cost_center=first.cost_center,
                    contract_currency=currency,
                    start_date=start_date,
                    end_date=end_date,
                    term_years=years,
                    status=status.replace("_", " ").title(),
                    utilization_band={
                        "expired": "Utilization above 90%",
                        "expiring_soon": "Utilization above 80%",
                        "utilized_70": "Utilization near 70%",
                        "active_buffer": "Utilization under 50%",
                    }[status],
                    contract_value=format_decimal(contract_value),
                    utilized_value=format_decimal(utilized_value),
                    unutilized_value=format_decimal(unutilized),
                    utilization_percent=format_decimal(utilization_percent),
                    payment_terms=first.payment_terms or PAYMENT_TERMS_LIBRARY[(vendor_index + contract_index) % len(PAYMENT_TERMS_LIBRARY)],
                    commercial_model=commercial_model_for(categories),
                    renewal_option=renewal_option_for(status, years),
                    linked_invoice_count=len(source_invoices),
                    linked_po_count=len(source_pos),
                    source_invoice_ids=source_invoices,
                    source_po_numbers=source_pos,
                    remarks=first.remarks or "Performance and commercial terms remain subject to contract governance procedures.",
                    file_path=str(out_root / safe_filename(first.vendor_name) / output_name),
                    lines=lines,
                )
            )
    records.sort(key=lambda record: (record.vendor_name, record.contract_id))
    return records


def styles():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            name="ContractTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            textColor=colors.HexColor("#163A70"),
            spaceAfter=6,
        )
    )
    base.add(
        ParagraphStyle(
            name="ContractSubtitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#52627A"),
            spaceAfter=10,
        )
    )
    base.add(
        ParagraphStyle(
            name="SectionLabel",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#163A70"),
            spaceBefore=8,
            spaceAfter=4,
        )
    )
    base.add(
        ParagraphStyle(
            name="BodySmall",
            parent=base["Normal"],
            fontSize=8.5,
            leading=11.2,
            textColor=colors.HexColor("#22374C"),
        )
    )
    base.add(
        ParagraphStyle(
            name="ClauseBody",
            parent=base["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#22374C"),
            spaceAfter=6,
        )
    )
    base.add(
        ParagraphStyle(
            name="Muted",
            parent=base["BodySmall"],
            textColor=colors.HexColor("#6A778B"),
        )
    )
    return base


def draw_page_chrome(canvas, doc):
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#163A70"))
    canvas.rect(0, height - 1.25 * cm, width, 1.25 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(doc.leftMargin, height - 0.84 * cm, BUYER_NAME)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - doc.rightMargin, height - 0.86 * cm, "Vendor Contract Repository Copy")
    canvas.setStrokeColor(colors.HexColor("#D8E2F0"))
    canvas.line(doc.leftMargin, 1.45 * cm, width - doc.rightMargin, 1.45 * cm)
    canvas.setFillColor(colors.HexColor("#5A6780"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(doc.leftMargin, 1.0 * cm, "Generated from procurement transaction data for contract intelligence testing")
    canvas.drawRightString(width - doc.rightMargin, 1.0 * cm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def make_parties_table(contract: ContractRecord, s) -> Table:
    vendor_block = "<br/>".join(
        [
            f"<b>{contract.vendor_name}</b>",
            f"Vendor ID: {contract.vendor_id}",
            contract.vendor_country or "-",
        ]
    )
    buyer_block = "<br/>".join(
        [
            f"<b>{contract.buyer_name}</b>",
            BUYER_ENTITY_LINE,
            *BUYER_ADDRESS,
            BUYER_CONTACT,
        ]
    )
    table = Table(
        [[Paragraph(vendor_block, s["BodySmall"]), Paragraph(buyer_block, s["BodySmall"])]],
        colWidths=[9.2 * cm, 9.2 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.45, colors.HexColor("#CFD9E7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def make_contract_summary(contract: ContractRecord) -> Table:
    rows = [
        ["Contract ID", contract.contract_id, "Status", contract.status],
        ["Contract Type", contract.contract_type, "Term", f"{contract.term_years} year(s)"],
        ["Start Date", format_date(contract.start_date), "End Date", format_date(contract.end_date)],
        ["Payment Terms", contract.payment_terms, "Commercial Model", contract.commercial_model],
        ["Primary Department", contract.primary_department, "Cost Center", contract.cost_center or "-"],
    ]
    table = Table(rows, colWidths=[3.6 * cm, 5.8 * cm, 3.6 * cm, 5.4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5FB")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F1F5FB")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4DCE8")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def make_utilization_table(contract: ContractRecord) -> Table:
    rows = [
        ["Contract Value", format_money(contract.contract_currency, contract.contract_value)],
        ["Utilized Value", format_money(contract.contract_currency, contract.utilized_value)],
        ["Available Value", format_money(contract.contract_currency, contract.unutilized_value)],
        ["Utilization", format_percent(contract.utilization_percent)],
        ["Linked Invoices", str(contract.linked_invoice_count)],
        ["Linked POs", str(contract.linked_po_count)],
        ["Utilization Band", contract.utilization_band],
    ]
    table = Table(rows, colWidths=[4.4 * cm, 6.0 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F7FAFD")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4DCE8")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def scope_paragraph(contract: ContractRecord) -> str:
    return (
        f"The supplier shall provide goods and services associated with {contract.category_summary.lower()} "
        f"for the benefit of {contract.primary_department}. Contract releases may be issued by "
        f"{contract.buyer_name} through purchase orders, call-offs, service requests, or release schedules "
        f"subject to approved budgets, performance expectations, and site access procedures."
    )


def obligations_paragraph(contract: ContractRecord) -> str:
    return (
        f"The supplier shall maintain qualified personnel, material traceability, statutory licenses, "
        f"and delivery readiness throughout the contract term. {contract.buyer_name} shall evaluate supplier "
        f"performance against delivery, quality, documentation, HSE compliance, and invoice accuracy before "
        f"certifying invoices for payment."
    )


def commercial_paragraph(contract: ContractRecord) -> str:
    return (
        f"The contract shall be administered as a {contract.commercial_model.lower()} Payment shall be governed by "
        f"{contract.payment_terms.lower()}. Contract value drawdown is monitored against approved invoices linked to "
        f"release orders and receiving evidence, with current utilization at {format_percent(contract.utilization_percent)}."
    )


def governance_paragraph(contract: ContractRecord) -> str:
    return (
        f"The contracting parties acknowledge that renewal, suspension, change management, and termination rights are "
        f"subject to procurement governance, delegated authority limits, and documented performance records. "
        f"{contract.renewal_option}"
    )


def make_cross_reference_table(contract: ContractRecord) -> Table:
    rows: List[List[str]] = [["Ref Type", "Reference", "Description", "Value"]]
    for idx, line in enumerate(contract.lines[:8], start=1):
        rows.append(
            [
                "Invoice",
                line.invoice_id,
                f"{line.description} ({line.category})",
                format_money(contract.contract_currency, line.value),
            ]
        )
    table = Table(rows, colWidths=[2.3 * cm, 3.8 * cm, 9.0 * cm, 3.3 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163A70")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4DCE8")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def make_signature_table(contract: ContractRecord) -> Table:
    rows = [
        ["For Infomentica Traders", "For Supplier"],
        [f"Buyer: {contract.buyer or '-'}", f"Authorized Signatory: {contract.vendor_name}"],
        [f"Requestor: {contract.requestor or '-'}", "Name: ________________________"],
        ["Signature: ____________________", "Signature: ____________________"],
        ["Date: _________________________", "Date: _________________________"],
    ]
    table = Table(rows, colWidths=[9.2 * cm, 9.2 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5FB")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4DCE8")),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return table


def build_pdf(contract: ContractRecord) -> None:
    out = Path(contract.file_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    s = styles()
    doc = BaseDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=1.35 * cm,
        rightMargin=1.35 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.7 * cm,
        title=contract.contract_id,
        author=contract.buyer_name,
        subject=f"Vendor contract with {contract.vendor_name}",
        creator="AUGMIS Contract Generator",
        keywords=f"contract,{contract.vendor_name},{contract.contract_type},{contract.category_summary}",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="default", frames=[frame], onPage=draw_page_chrome)])

    story = [
        Paragraph(contract.contract_title, s["ContractTitle"]),
        Paragraph(f"{contract.contract_type} | {contract.status} | {contract.term_years}-year term", s["ContractSubtitle"]),
        make_parties_table(contract, s),
        Spacer(1, 0.28 * cm),
        Paragraph("Contract Summary", s["SectionLabel"]),
        make_contract_summary(contract),
        Spacer(1, 0.25 * cm),
        Paragraph("Parties and Purpose", s["SectionLabel"]),
        Paragraph(
            f"This agreement is entered into between {contract.buyer_name} and {contract.vendor_name} for the provision "
            f"of controlled procurement support covering {contract.category_summary.lower()}. The agreement establishes "
            f"the legal and commercial framework for purchase releases, service requests, and invoicing discipline over the contract term.",
            s["ClauseBody"],
        ),
        Paragraph("Scope of Supply and Services", s["SectionLabel"]),
        Paragraph(scope_paragraph(contract), s["ClauseBody"]),
        Paragraph("Commercial Terms", s["SectionLabel"]),
        Paragraph(commercial_paragraph(contract), s["ClauseBody"]),
        Paragraph("Supplier Obligations and Performance", s["SectionLabel"]),
        Paragraph(obligations_paragraph(contract), s["ClauseBody"]),
        Paragraph("Governance, Renewal, and Termination", s["SectionLabel"]),
        Paragraph(governance_paragraph(contract), s["ClauseBody"]),
        Spacer(1, 0.1 * cm),
        Table([[make_utilization_table(contract)]], colWidths=[10.8 * cm]),
        PageBreak(),
        Paragraph("Utilization and Linked Commercial References", s["SectionLabel"]),
        Paragraph(
            f"The utilization metrics below are derived from linked source invoices and release orders associated with this contract. "
            f"They provide an analytical contract-spend view to support monitoring, renewal planning, and value consumption checks.",
            s["ClauseBody"],
        ),
        make_cross_reference_table(contract),
        Spacer(1, 0.28 * cm),
        Paragraph("Execution and Sign-Off", s["SectionLabel"]),
        Paragraph(
            f"This contract record reflects a repository-style controlled copy. Formal execution, amendments, and extensions shall be "
            f"administered through the contracts office with supporting approvals retained in the contract dossier.",
            s["ClauseBody"],
        ),
        make_signature_table(contract),
    ]
    doc.build(story)


def write_sidecar(record: ContractRecord) -> None:
    Path(record.file_path).with_suffix(".metadata.json").write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")


def write_metadata(records: Iterable[ContractRecord], out_root: Path) -> None:
    record_list = list(records)
    if not record_list:
        return
    csv_path = out_root / "metadata_index.csv"
    json_path = out_root / "metadata_index.json"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(record_list[0]).keys()))
        writer.writeheader()
        for record in record_list:
            writer.writerow(asdict(record))
    json_path.write_text(json.dumps([asdict(record) for record in record_list], indent=2), encoding="utf-8")


def validate_input(csv_path: Path) -> None:
    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")
    if csv_path.suffix.lower() != ".csv":
        raise SystemExit(f"Expected a .csv file, got: {csv_path}")


def main() -> None:
    args = parse_args()
    validate_input(args.csv)
    args.out.mkdir(parents=True, exist_ok=True)
    rows = read_rows(args.csv, args.limit)
    if not rows:
        raise SystemExit("No rows found in CSV.")
    contracts = build_contracts(rows, args.out, args.buyer_name)
    if not contracts:
        raise SystemExit("No contracts could be derived from the CSV.")

    write_metadata(contracts, args.out)
    if args.metadata_only:
        for contract in contracts:
            write_sidecar(contract)
        print(f"Generated metadata only for {len(contracts)} contracts in: {args.out.resolve()}")
        print(f"Metadata CSV: {(args.out / 'metadata_index.csv').resolve()}")
        print(f"Metadata JSON: {(args.out / 'metadata_index.json').resolve()}")
        return

    for contract in tqdm(contracts, desc="Generating P2P contracts"):
        build_pdf(contract)
        write_sidecar(contract)

    print(f"Generated {len(contracts)} contracts in: {args.out.resolve()}")
    print(f"Metadata CSV: {(args.out / 'metadata_index.csv').resolve()}")
    print(f"Metadata JSON: {(args.out / 'metadata_index.json').resolve()}")


if __name__ == "__main__":
    main()
