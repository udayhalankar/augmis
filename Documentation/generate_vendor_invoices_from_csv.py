#!/usr/bin/env python3
"""
Generate polished vendor invoice PDFs from a CSV source.

Designed for the attached P2P vendor invoice dataset where the buyer/customer is
Infomentica Traders and each CSV row represents one invoice.

Install:
  pip install reportlab tqdm

Example:
  python3 generate_vendor_invoices_from_csv.py \
    --csv /mnt/d/AUGMIS/p2p_vendor_invoices_100.csv \
    --out ./vendor_invoice_pdfs
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
from typing import Dict, Iterable, List

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x, **kwargs: x

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError as exc:
    raise SystemExit("Missing dependency: reportlab. Install with: pip install reportlab tqdm") from exc


BUYER_NAME = "Infomentica Traders"
BUYER_ADDRESS = [
    "Enterprise Procurement & Trade Division",
    "King Fahd Road Business District",
    "Riyadh 12271, Kingdom of Saudi Arabia",
]
BUYER_TAX_ID = "VAT: SA-INF-TRD-482910"
BUYER_CONTACT = "ap@infomentica-traders.com | +966 11 555 0188"


@dataclass
class InvoiceRecord:
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
    file_path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate vendor invoice PDFs from CSV.")
    parser.add_argument("--csv", type=Path, required=True, help="Source CSV file")
    parser.add_argument("--out", type=Path, default=Path("vendor_invoice_pdfs"), help="Output folder")
    parser.add_argument("--limit", type=int, default=0, help="Optional max rows to generate")
    parser.add_argument("--buyer-name", default=BUYER_NAME, help="Buyer / bill-to name")
    parser.add_argument("--metadata-only", action="store_true", help="Write JSON/CSV metadata without generating PDFs")
    return parser.parse_args()


def safe_filename(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")
    return cleaned[:180] or "invoice"


def clean_value(value: str) -> str:
    return str(value or "").strip()


def parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(clean_value(value) or "0")
    except InvalidOperation:
        return Decimal("0")


def format_money(currency: str, value: str) -> str:
    amount = parse_decimal(value)
    return f"{currency} {amount:,.2f}"


def format_percent(value: str) -> str:
    amount = parse_decimal(value)
    return f"{amount:,.2f}%"


def format_date(value: str) -> str:
    text = clean_value(value)
    if not text:
        return "-"
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return text


def normalize_row(row: Dict[str, str], out_root: Path) -> InvoiceRecord:
    invoice_id = clean_value(row.get("Invoice_ID"))
    vendor_name = clean_value(row.get("Vendor_Name"))
    output_name = safe_filename(f"{invoice_id}_{vendor_name}.pdf")
    aging_key = next((key for key in row if key.startswith("Aging_Days_As_Of_")), "")

    return InvoiceRecord(
        invoice_id=invoice_id,
        vendor_id=clean_value(row.get("Vendor_ID")),
        vendor_name=vendor_name,
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
        file_path=str(out_root / output_name),
    )


def read_records(csv_path: Path, out_root: Path, limit: int) -> List[InvoiceRecord]:
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if limit > 0:
        rows = rows[:limit]
    return [normalize_row(row, out_root) for row in rows]


def styles():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            name="InvoiceTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#163A70"),
            spaceAfter=8,
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
            spaceAfter=4,
            spaceBefore=6,
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
            name="BodySmallRight",
            parent=base["BodySmall"],
            alignment=TA_RIGHT,
        )
    )
    base.add(
        ParagraphStyle(
            name="Muted",
            parent=base["BodySmall"],
            textColor=colors.HexColor("#6A778B"),
        )
    )
    base.add(
        ParagraphStyle(
            name="KpiValue",
            parent=base["Normal"],
            fontSize=10,
            leading=12,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#102542"),
            alignment=TA_LEFT,
        )
    )
    return base


def build_header(record: InvoiceRecord, s, buyer_name: str) -> List:
    vendor_block = "<br/>".join(
        [
            f"<b>{record.vendor_name}</b>",
            f"Vendor ID: {record.vendor_id}",
            record.vendor_country or "-",
        ]
    )
    buyer_block = "<br/>".join([f"<b>{buyer_name}</b>", *BUYER_ADDRESS, BUYER_TAX_ID, BUYER_CONTACT])

    summary_rows = [
        ["Invoice No.", record.invoice_id],
        ["Invoice Date", format_date(record.invoice_date)],
        ["Due Date", format_date(record.due_date)],
        ["Terms", record.payment_terms or "-"],
        ["Status", record.invoice_status or "-"],
    ]

    summary_table = Table(summary_rows, colWidths=[3.1 * cm, 4.1 * cm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5FB")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1F2F46")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4DCE8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    parties = Table(
        [
            [
                Paragraph("<b>Vendor / Supplier</b><br/>" + vendor_block, s["BodySmall"]),
                Paragraph("<b>Bill To</b><br/>" + buyer_block, s["BodySmall"]),
                summary_table,
            ]
        ],
        colWidths=[6.2 * cm, 6.2 * cm, 7.0 * cm],
    )
    parties.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CFD9E7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    return [
        Paragraph("Vendor Invoice", s["InvoiceTitle"]),
        Paragraph("Accounts Payable document prepared for repository-backed testing and retrieval.", s["Muted"]),
        Spacer(1, 0.25 * cm),
        parties,
    ]


def build_reference_strip(record: InvoiceRecord, s) -> Table:
    rows = [
        [
            Paragraph("<b>PO Reference</b><br/>" + (record.po_number or "-"), s["BodySmall"]),
            Paragraph("<b>PO Date</b><br/>" + format_date(record.po_date), s["BodySmall"]),
            Paragraph("<b>GRN Reference</b><br/>" + (record.grn_number or "-"), s["BodySmall"]),
            Paragraph("<b>GRN Date</b><br/>" + format_date(record.grn_date), s["BodySmall"]),
            Paragraph("<b>SES Reference</b><br/>" + (record.ses_number or "-"), s["BodySmall"]),
        ]
    ]
    table = Table(rows, colWidths=[4.0 * cm, 3.2 * cm, 4.1 * cm, 3.2 * cm, 5.0 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFD")),
                ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#D4DCE8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E9F2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def build_line_items(record: InvoiceRecord, s) -> Table:
    qty = parse_decimal(record.quantity)
    price = parse_decimal(record.unit_price)
    subtotal = parse_decimal(record.subtotal_amount)
    discount = parse_decimal(record.discount_amount)
    taxable = parse_decimal(record.taxable_amount)
    vat = parse_decimal(record.vat_amount)
    total = parse_decimal(record.invoice_total)

    rows = [
        ["Line", "Description", "Category", "Qty", "UOM", "Unit Price", "Line Amount"],
        [
            "1",
            record.goods_or_service_supplied or "-",
            record.category or "-",
            f"{qty:,.2f}".rstrip("0").rstrip("."),
            record.uom or "-",
            f"{record.currency} {price:,.2f}",
            f"{record.currency} {subtotal:,.2f}",
        ],
        [
            "",
            "Discount",
            "",
            "",
            "",
            format_percent(record.discount_percent),
            f"- {record.currency} {discount:,.2f}",
        ],
        [
            "",
            "Taxable Base",
            "",
            "",
            "",
            "",
            f"{record.currency} {taxable:,.2f}",
        ],
        [
            "",
            f"VAT @ {format_percent(record.vat_percent)}",
            "",
            "",
            "",
            "",
            f"{record.currency} {vat:,.2f}",
        ],
        [
            "",
            "<b>Total Invoice Amount</b>",
            "",
            "",
            "",
            "",
            f"<b>{record.currency} {total:,.2f}</b>",
        ],
    ]

    table = Table(rows, colWidths=[1.0 * cm, 6.3 * cm, 3.2 * cm, 1.7 * cm, 1.7 * cm, 3.1 * cm, 3.4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163A70")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4DCE8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ("SPAN", (1, 5), (5, 5)),
                ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#EEF4FB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def kpi_card_rows(record: InvoiceRecord, s) -> Table:
    cards = [
        ("Department", record.department or "-"),
        ("Cost Center", record.cost_center or "-"),
        ("Requestor", record.requestor or "-"),
        ("Buyer", record.buyer or "-"),
        ("Delivery Location", record.delivery_location or "-"),
        ("Payment Method", record.payment_method or "-"),
    ]

    rows = []
    current = []
    for label, value in cards:
        cell = Paragraph(f"<b>{label}</b><br/>{value}", s["BodySmall"])
        current.append(cell)
        if len(current) == 3:
            rows.append(current)
            current = []
    if current:
        while len(current) < 3:
            current.append(Paragraph("", s["BodySmall"]))
        rows.append(current)

    table = Table(rows, colWidths=[6.1 * cm, 6.1 * cm, 6.1 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFD")),
                ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#D4DCE8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E9F2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def build_controls_table(record: InvoiceRecord, s) -> Table:
    rows = [
        ["Approval Status", record.approval_status or "-"],
        ["Approver Role", record.approver_role or "-"],
        ["Three-Way Match", record.three_way_match or "-"],
        ["Payment Block", record.payment_block or "-"],
        ["Amount Paid", format_money(record.currency, record.amount_paid)],
        ["Outstanding", format_money(record.currency, record.outstanding_amount)],
        ["Aging Days", record.aging_days or "0"],
    ]
    table = Table(rows, colWidths=[4.2 * cm, 14.1 * cm])
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


def build_footer_note(record: InvoiceRecord, s) -> List:
    narrative = (
        f"This invoice relates to {record.goods_or_service_supplied.lower()} under procurement category "
        f"{record.category}. It was raised against {record.po_number or 'the referenced purchase order'} "
        f"for {record.department or 'the requesting department'} and is routed through the accounts payable "
        f"process for {BUYER_NAME}."
    )
    remarks = record.remarks or "No additional remarks recorded."
    return [
        Paragraph("Processing Notes", s["SectionLabel"]),
        Paragraph(narrative, s["BodySmall"]),
        Spacer(1, 0.12 * cm),
        Paragraph(f"<b>Remarks:</b> {remarks}", s["BodySmall"]),
    ]


def draw_page_chrome(canvas, doc):
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#163A70"))
    canvas.rect(0, height - 1.25 * cm, width, 1.25 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(doc.leftMargin, height - 0.85 * cm, BUYER_NAME)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - doc.rightMargin, height - 0.87 * cm, "Accounts Payable Repository Copy")
    canvas.setStrokeColor(colors.HexColor("#D8E2F0"))
    canvas.line(doc.leftMargin, 1.45 * cm, width - doc.rightMargin, 1.45 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#5A6780"))
    canvas.drawString(doc.leftMargin, 1.0 * cm, "Generated for invoice repository testing")
    canvas.drawRightString(width - doc.rightMargin, 1.0 * cm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def build_invoice_pdf(record: InvoiceRecord, buyer_name: str) -> None:
    out_path = Path(record.file_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    s = styles()

    doc = BaseDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=1.35 * cm,
        rightMargin=1.35 * cm,
        topMargin=1.85 * cm,
        bottomMargin=1.7 * cm,
        title=record.invoice_id,
        author=record.vendor_name,
        subject=f"Vendor invoice for {buyer_name}",
        creator="AUGMIS CSV Invoice Generator",
        keywords=f"invoice,{record.vendor_name},{record.department},{record.category},{record.invoice_status}",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="invoice", frames=[frame], onPage=draw_page_chrome)])

    story = []
    story.extend(build_header(record, s, buyer_name))
    story.append(Spacer(1, 0.35 * cm))
    story.append(build_reference_strip(record, s))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Invoice Line and Commercial Value", s["SectionLabel"]))
    story.append(build_line_items(record, s))
    story.append(Spacer(1, 0.28 * cm))
    story.append(Paragraph("Operational Context", s["SectionLabel"]))
    story.append(kpi_card_rows(record, s))
    story.append(Spacer(1, 0.28 * cm))
    story.append(Paragraph("Workflow and Control Status", s["SectionLabel"]))
    story.append(build_controls_table(record, s))
    story.append(Spacer(1, 0.24 * cm))
    story.extend(build_footer_note(record, s))
    doc.build(story)


def write_metadata(records: Iterable[InvoiceRecord], out_root: Path) -> None:
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


def write_sidecar(record: InvoiceRecord) -> None:
    sidecar_path = Path(record.file_path).with_suffix(".metadata.json")
    sidecar_path.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")


def validate_input(csv_path: Path) -> None:
    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")
    if csv_path.suffix.lower() != ".csv":
        raise SystemExit(f"Expected a .csv file, got: {csv_path}")


def main() -> None:
    args = parse_args()
    validate_input(args.csv)
    args.out.mkdir(parents=True, exist_ok=True)
    records = read_records(args.csv, args.out, args.limit)
    if not records:
        raise SystemExit("No invoice rows found in CSV.")

    write_metadata(records, args.out)
    if args.metadata_only:
        for record in records:
            write_sidecar(record)
        print(f"Generated metadata only for {len(records)} vendor invoices in: {args.out.resolve()}")
        print(f"Metadata CSV: {(args.out / 'metadata_index.csv').resolve()}")
        print(f"Metadata JSON: {(args.out / 'metadata_index.json').resolve()}")
        return

    for record in tqdm(records, desc="Generating vendor invoices"):
        build_invoice_pdf(record, args.buyer_name)
        write_sidecar(record)

    print(f"Generated {len(records)} vendor invoice PDFs in: {args.out.resolve()}")
    print(f"Metadata CSV: {(args.out / 'metadata_index.csv').resolve()}")
    print(f"Metadata JSON: {(args.out / 'metadata_index.json').resolve()}")


if __name__ == "__main__":
    main()
