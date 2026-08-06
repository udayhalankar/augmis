#!/usr/bin/env python3
"""
Generate purchase order PDFs from the vendor invoice CSV.

This script derives purchase orders from the same transaction dataset used for
invoices and related P2P documents. It groups rows by (PO_Number, Vendor_ID)
because the sample data contains a few repeated PO numbers across different vendors.

Install:
  pip install reportlab tqdm

Example:
  python3 generate_purchase_orders_from_csv.py \
    --csv /mnt/d/AUGMIS/p2p_vendor_invoices_100.csv \
    --out ./purchase_orders
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x, **kwargs: x

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle
except ImportError as exc:
    raise SystemExit("Missing dependency: reportlab. Install with: pip install reportlab tqdm") from exc


BUYER_NAME = "Infomentica Traders"
BUYER_ADDRESS = [
    "Enterprise Procurement & Trade Division",
    "King Fahd Road Business District",
    "Riyadh 12271, Kingdom of Saudi Arabia",
]
BUYER_CONTACT = "procurement.ops@infomentica-traders.com | +966 11 555 0188"


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
class PurchaseOrderLine:
    invoice_id: str
    description: str
    category: str
    quantity: str
    uom: str
    unit_price: str
    line_amount: str
    delivery_location: str
    department: str
    grn_number: str
    ses_number: str


@dataclass
class PurchaseOrderRecord:
    po_number: str
    vendor_id: str
    vendor_name: str
    vendor_country: str
    po_date: str
    payment_terms: str
    buyer_name: str
    requestor: str
    buyer: str
    department: str
    cost_center: str
    delivery_location: str
    approval_status: str
    approver_role: str
    payment_method: str
    currency: str
    source_invoice_ids: List[str]
    line_count: int
    subtotal_amount: str
    discount_amount: str
    taxable_amount: str
    vat_amount: str
    total_amount: str
    payment_block: str
    remarks: str
    group_key: str
    file_path: str
    lines: List[PurchaseOrderLine]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate purchase order PDFs from invoice CSV.")
    parser.add_argument("--csv", type=Path, required=True, help="Source CSV file")
    parser.add_argument("--out", type=Path, default=Path("purchase_orders"), help="Output folder")
    parser.add_argument("--limit", type=int, default=0, help="Optional max source rows to process")
    parser.add_argument("--buyer-name", default=BUYER_NAME, help="Buyer / purchasing organization")
    parser.add_argument("--metadata-only", action="store_true", help="Write JSON/CSV metadata without generating PDFs")
    return parser.parse_args()


def clean_value(value: str) -> str:
    return str(value or "").strip()


def safe_filename(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")
    return cleaned[:180] or "purchase_order"


def parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(clean_value(value) or "0")
    except InvalidOperation:
        return Decimal("0")


def format_money(currency: str, value: str) -> str:
    return f"{currency} {parse_decimal(value):,.2f}"


def format_decimal(value: Decimal) -> str:
    return f"{value:.2f}"


def format_quantity(value: str) -> str:
    amount = parse_decimal(value)
    text = f"{amount:,.2f}"
    return text.rstrip("0").rstrip(".")


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


def build_purchase_orders(rows: List[SourceRow], out_root: Path, buyer_name: str) -> List[PurchaseOrderRecord]:
    grouped: Dict[Tuple[str, str], List[SourceRow]] = {}
    for row in rows:
        key = (row.po_number or f"PO-MISSING-{row.invoice_id}", row.vendor_id or row.vendor_name)
        grouped.setdefault(key, []).append(row)

    records: List[PurchaseOrderRecord] = []
    for (po_number, vendor_key), group_rows in grouped.items():
        first = group_rows[0]
        currency = first.currency or "USD"
        subtotal = sum(parse_decimal(item.subtotal_amount) for item in group_rows)
        discount = sum(parse_decimal(item.discount_amount) for item in group_rows)
        taxable = sum(parse_decimal(item.taxable_amount) for item in group_rows)
        vat = sum(parse_decimal(item.vat_amount) for item in group_rows)
        total = sum(parse_decimal(item.invoice_total) for item in group_rows)
        lines = [
            PurchaseOrderLine(
                invoice_id=item.invoice_id,
                description=item.goods_or_service_supplied,
                category=item.category,
                quantity=item.quantity,
                uom=item.uom,
                unit_price=item.unit_price,
                line_amount=item.subtotal_amount,
                delivery_location=item.delivery_location,
                department=item.department,
                grn_number=item.grn_number,
                ses_number=item.ses_number,
            )
            for item in group_rows
        ]
        output_name = safe_filename(f"{po_number}_{first.vendor_name}.pdf")
        records.append(
            PurchaseOrderRecord(
                po_number=po_number,
                vendor_id=first.vendor_id,
                vendor_name=first.vendor_name,
                vendor_country=first.vendor_country,
                po_date=first.po_date,
                payment_terms=first.payment_terms,
                buyer_name=buyer_name,
                requestor=first.requestor,
                buyer=first.buyer,
                department=first.department,
                cost_center=first.cost_center,
                delivery_location=first.delivery_location,
                approval_status=first.approval_status,
                approver_role=first.approver_role,
                payment_method=first.payment_method,
                currency=currency,
                source_invoice_ids=[item.invoice_id for item in group_rows],
                line_count=len(lines),
                subtotal_amount=format_decimal(subtotal),
                discount_amount=format_decimal(discount),
                taxable_amount=format_decimal(taxable),
                vat_amount=format_decimal(vat),
                total_amount=format_decimal(total),
                payment_block=first.payment_block,
                remarks=first.remarks,
                group_key=f"{po_number}|{vendor_key}",
                file_path=str(out_root / output_name),
                lines=lines,
            )
        )
    records.sort(key=lambda item: (item.po_number, item.vendor_name))
    return records


def styles():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            name="DocTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#163A70"),
            spaceAfter=6,
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
            spaceBefore=7,
            spaceAfter=4,
        )
    )
    base.add(
        ParagraphStyle(
            name="BodySmall",
            parent=base["Normal"],
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#24364B"),
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
    canvas.rect(0, height - 1.2 * cm, width, 1.2 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(doc.leftMargin, height - 0.82 * cm, BUYER_NAME)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - doc.rightMargin, height - 0.84 * cm, "Purchase Order Repository Copy")
    canvas.setStrokeColor(colors.HexColor("#D8E2F0"))
    canvas.line(doc.leftMargin, 1.45 * cm, width - doc.rightMargin, 1.45 * cm)
    canvas.setFillColor(colors.HexColor("#5A6780"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(doc.leftMargin, 1.0 * cm, "Generated from procurement transaction CSV")
    canvas.drawRightString(width - doc.rightMargin, 1.0 * cm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def make_party_table(po: PurchaseOrderRecord, s) -> Table:
    vendor = "<br/>".join([f"<b>{po.vendor_name}</b>", f"Vendor ID: {po.vendor_id}", po.vendor_country or "-"])
    buyer = "<br/>".join([f"<b>{po.buyer_name}</b>", *BUYER_ADDRESS, BUYER_CONTACT])
    table = Table([[Paragraph(vendor, s["BodySmall"]), Paragraph(buyer, s["BodySmall"])]], colWidths=[9.2 * cm, 9.2 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD9E7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def make_summary_table(po: PurchaseOrderRecord) -> Table:
    rows = [
        ["PO Number", po.po_number, "PO Date", format_date(po.po_date)],
        ["Payment Terms", po.payment_terms or "-", "Payment Method", po.payment_method or "-"],
        ["Department", po.department or "-", "Cost Center", po.cost_center or "-"],
        ["Requestor", po.requestor or "-", "Buyer", po.buyer or "-"],
        ["Delivery Location", po.delivery_location or "-", "Line Count", str(po.line_count)],
    ]
    table = Table(rows, colWidths=[3.7 * cm, 5.5 * cm, 3.7 * cm, 5.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5FB")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F1F5FB")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4DCE8")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def make_lines_table(po: PurchaseOrderRecord) -> Table:
    rows: List[List[str]] = [["Line", "Description", "Category", "Qty", "UOM", "Unit Rate", "Line Amount"]]
    for idx, line in enumerate(po.lines, start=1):
        rows.append(
            [
                str(idx),
                line.description or "-",
                line.category or "-",
                format_quantity(line.quantity),
                line.uom or "-",
                format_money(po.currency, line.unit_price),
                format_money(po.currency, line.line_amount),
            ]
        )
    rows.extend(
        [
            ["", "Subtotal", "", "", "", "", format_money(po.currency, po.subtotal_amount)],
            ["", "Discount", "", "", "", "", f"- {format_money(po.currency, po.discount_amount)}"],
            ["", "Taxable Base", "", "", "", "", format_money(po.currency, po.taxable_amount)],
            ["", "VAT", "", "", "", "", format_money(po.currency, po.vat_amount)],
            ["", "Total PO Value", "", "", "", "", format_money(po.currency, po.total_amount)],
        ]
    )
    table = Table(rows, colWidths=[1.0 * cm, 6.6 * cm, 3.0 * cm, 1.8 * cm, 1.6 * cm, 2.9 * cm, 3.0 * cm], repeatRows=1)
    totals_start = len(rows) - 5
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163A70")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4DCE8")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ("BACKGROUND", (0, totals_start), (-1, len(rows) - 1), colors.HexColor("#F8FAFD")),
                ("SPAN", (1, totals_start), (5, totals_start)),
                ("SPAN", (1, totals_start + 1), (5, totals_start + 1)),
                ("SPAN", (1, totals_start + 2), (5, totals_start + 2)),
                ("SPAN", (1, totals_start + 3), (5, totals_start + 3)),
                ("SPAN", (1, totals_start + 4), (5, totals_start + 4)),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def make_control_table(po: PurchaseOrderRecord) -> Table:
    rows = [
        ["Approval Status", po.approval_status or "-"],
        ["Approver Role", po.approver_role or "-"],
        ["Payment Block", po.payment_block or "-"],
        ["Source Invoices", ", ".join(po.source_invoice_ids)],
        ["Remarks", po.remarks or "No remarks recorded."],
    ]
    table = Table(rows, colWidths=[4.2 * cm, 14.2 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5FB")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4DCE8")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build_pdf(po: PurchaseOrderRecord) -> None:
    out = Path(po.file_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    s = styles()
    doc = BaseDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=1.35 * cm,
        rightMargin=1.35 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.7 * cm,
        title=po.po_number,
        author=po.buyer_name,
        subject=f"Purchase order for {po.vendor_name}",
        creator="AUGMIS Purchase Order Generator",
        keywords=f"purchase order,{po.po_number},{po.vendor_name},{po.department}",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="default", frames=[frame], onPage=draw_page_chrome)])

    story = [
        Paragraph("Purchase Order", s["DocTitle"]),
        Paragraph("Generated from transaction-linked procurement data for repository-backed testing.", s["Muted"]),
        Spacer(1, 0.25 * cm),
        make_party_table(po, s),
        Spacer(1, 0.28 * cm),
        Paragraph("Order Summary", s["SectionLabel"]),
        make_summary_table(po),
        Spacer(1, 0.25 * cm),
        Paragraph("Ordered Items and Commercial Value", s["SectionLabel"]),
        make_lines_table(po),
        Spacer(1, 0.25 * cm),
        Paragraph("Approval and Source Linkage", s["SectionLabel"]),
        make_control_table(po),
    ]
    doc.build(story)


def write_sidecar(record: PurchaseOrderRecord) -> None:
    Path(record.file_path).with_suffix(".metadata.json").write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")


def write_metadata(records: Iterable[PurchaseOrderRecord], out_root: Path) -> None:
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
    records = build_purchase_orders(rows, args.out, args.buyer_name)
    if not records:
        raise SystemExit("No purchase orders could be derived from the CSV.")

    write_metadata(records, args.out)
    if args.metadata_only:
        for record in records:
            write_sidecar(record)
        print(f"Generated metadata only for {len(records)} purchase orders in: {args.out.resolve()}")
        print(f"Metadata CSV: {(args.out / 'metadata_index.csv').resolve()}")
        print(f"Metadata JSON: {(args.out / 'metadata_index.json').resolve()}")
        return

    for record in tqdm(records, desc="Generating purchase orders"):
        build_pdf(record)
        write_sidecar(record)

    print(f"Generated {len(records)} purchase orders in: {args.out.resolve()}")
    print(f"Metadata CSV: {(args.out / 'metadata_index.csv').resolve()}")
    print(f"Metadata JSON: {(args.out / 'metadata_index.json').resolve()}")


if __name__ == "__main__":
    main()
