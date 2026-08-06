#!/usr/bin/env python3
"""
Generate related P2P documents from the vendor invoice CSV:
- Delivery Note
- Goods Receipt Note (GRN)
- Service Entry Sheet (SES)

This complements the invoice generator without creating duplicate invoices.

Install:
  pip install reportlab tqdm

Example:
  python3 generate_p2p_related_documents.py \
    --csv /mnt/d/AUGMIS/p2p_vendor_invoices_100.csv \
    --out ./p2p_related_documents
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
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

DOC_FOLDER_MAP = {
    "delivery_note": "Delivery_Note",
    "grn": "Goods_Receipt_Note",
    "ses": "Service_Entry_Sheet",
}
DOC_LABEL_MAP = {
    "delivery_note": "Delivery Note",
    "grn": "Goods Receipt Note",
    "ses": "Service Entry Sheet",
}
SERVICE_KEYWORDS = (
    "service",
    "consult",
    "maintenance",
    "inspection",
    "calibration",
    "logistics",
    "support",
    "review",
    "audit",
    "engineering",
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
class RelatedDocument:
    doc_type: str
    document_number: str
    source_invoice_id: str
    vendor_name: str
    vendor_id: str
    buyer_name: str
    po_number: str
    grn_number: str
    ses_number: str
    activity_date: str
    department: str
    delivery_location: str
    requestor: str
    buyer: str
    goods_or_service_supplied: str
    category: str
    quantity: str
    uom: str
    currency: str
    unit_price: str
    line_amount: str
    approval_status: str
    three_way_match: str
    payment_block: str
    remarks: str
    file_path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate related P2P documents from invoice CSV.")
    parser.add_argument("--csv", type=Path, required=True, help="Source CSV file")
    parser.add_argument("--out", type=Path, default=Path("p2p_related_documents"), help="Output folder")
    parser.add_argument("--limit", type=int, default=0, help="Optional max rows to process")
    parser.add_argument(
        "--docs",
        default="delivery-note,grn,ses",
        help="Comma-separated list from: delivery-note, grn, ses",
    )
    parser.add_argument("--buyer-name", default=BUYER_NAME, help="Buyer / receiving organization")
    parser.add_argument("--metadata-only", action="store_true", help="Write JSON/CSV metadata without generating PDFs")
    return parser.parse_args()


def clean_value(value: str) -> str:
    return str(value or "").strip()


def safe_filename(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")
    return cleaned[:180] or "document"


def parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(clean_value(value) or "0")
    except InvalidOperation:
        return Decimal("0")


def format_money(currency: str, value: str) -> str:
    return f"{currency} {parse_decimal(value):,.2f}"


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


def add_days(value: str, days: int) -> str:
    text = clean_value(value)
    if not text:
        return ""
    try:
        return (datetime.strptime(text, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")
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


def is_service_row(row: SourceRow) -> bool:
    text = row.goods_or_service_supplied.lower()
    return bool(row.ses_number) or any(keyword in text for keyword in SERVICE_KEYWORDS)


def derive_delivery_note_number(row: SourceRow) -> str:
    return f"DN-{row.invoice_id.replace('INV-', '')}"


def derive_grn_number(row: SourceRow) -> str:
    return row.grn_number or f"GRN-{row.invoice_id.replace('INV-', '')}"


def derive_ses_number(row: SourceRow) -> str:
    return row.ses_number or f"SES-{row.invoice_id.replace('INV-', '')}"


def parse_docs_arg(raw: str) -> List[str]:
    mapping = {"delivery-note": "delivery_note", "grn": "grn", "ses": "ses"}
    result = []
    for part in raw.split(","):
        key = part.strip().lower()
        if not key:
            continue
        if key not in mapping:
            raise SystemExit(f"Unsupported document type: {key}")
        result.append(mapping[key])
    if not result:
        raise SystemExit("No document types requested.")
    return result


def build_documents(rows: List[SourceRow], out_root: Path, docs_to_generate: List[str], buyer_name: str) -> List[RelatedDocument]:
    documents: List[RelatedDocument] = []
    for row in rows:
        common = {
            "source_invoice_id": row.invoice_id,
            "vendor_name": row.vendor_name,
            "vendor_id": row.vendor_id,
            "buyer_name": buyer_name,
            "po_number": row.po_number,
            "grn_number": row.grn_number,
            "ses_number": row.ses_number,
            "department": row.department,
            "delivery_location": row.delivery_location,
            "requestor": row.requestor,
            "buyer": row.buyer,
            "goods_or_service_supplied": row.goods_or_service_supplied,
            "category": row.category,
            "quantity": row.quantity,
            "uom": row.uom,
            "currency": row.currency,
            "unit_price": row.unit_price,
            "line_amount": row.subtotal_amount,
            "approval_status": row.approval_status,
            "three_way_match": row.three_way_match,
            "payment_block": row.payment_block,
            "remarks": row.remarks,
        }

        if "delivery_note" in docs_to_generate:
            number = derive_delivery_note_number(row)
            path = out_root / DOC_FOLDER_MAP["delivery_note"] / safe_filename(f"{number}_{row.vendor_name}.pdf")
            documents.append(
                RelatedDocument(
                    doc_type="delivery_note",
                    document_number=number,
                    activity_date=row.invoice_date or add_days(row.po_date, 12),
                    file_path=str(path),
                    **common,
                )
            )

        if "grn" in docs_to_generate:
            number = derive_grn_number(row)
            path = out_root / DOC_FOLDER_MAP["grn"] / safe_filename(f"{number}_{row.vendor_name}.pdf")
            documents.append(
                RelatedDocument(
                    doc_type="grn",
                    document_number=number,
                    activity_date=row.grn_date or row.invoice_date or add_days(row.po_date, 18),
                    file_path=str(path),
                    **common,
                )
            )

        if "ses" in docs_to_generate and is_service_row(row):
            number = derive_ses_number(row)
            path = out_root / DOC_FOLDER_MAP["ses"] / safe_filename(f"{number}_{row.vendor_name}.pdf")
            documents.append(
                RelatedDocument(
                    doc_type="ses",
                    document_number=number,
                    activity_date=row.grn_date or row.invoice_date or add_days(row.po_date, 20),
                    file_path=str(path),
                    **common,
                )
            )

    return documents


def styles():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            name="DocTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#173A72"),
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
            textColor=colors.HexColor("#173A72"),
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
            textColor=colors.HexColor("#68778E"),
        )
    )
    return base


def draw_page_chrome(canvas, doc):
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#173A72"))
    canvas.rect(0, height - 1.2 * cm, width, 1.2 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(doc.leftMargin, height - 0.82 * cm, BUYER_NAME)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - doc.rightMargin, height - 0.84 * cm, "P2P Repository Control Copy")
    canvas.setStrokeColor(colors.HexColor("#D8E2F0"))
    canvas.line(doc.leftMargin, 1.45 * cm, width - doc.rightMargin, 1.45 * cm)
    canvas.setFillColor(colors.HexColor("#5B6980"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(doc.leftMargin, 1.0 * cm, "Generated from procurement transaction CSV")
    canvas.drawRightString(width - doc.rightMargin, 1.0 * cm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def make_party_table(doc: RelatedDocument, s) -> Table:
    vendor = "<br/>".join([f"<b>{doc.vendor_name}</b>", f"Vendor ID: {doc.vendor_id}", doc.delivery_location or "-"])
    buyer = "<br/>".join([f"<b>{doc.buyer_name}</b>", *BUYER_ADDRESS, BUYER_CONTACT])
    rows = [[Paragraph(vendor, s["BodySmall"]), Paragraph(buyer, s["BodySmall"])]]
    table = Table(rows, colWidths=[9.2 * cm, 9.2 * cm])
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


def make_summary_table(doc: RelatedDocument) -> Table:
    label = DOC_LABEL_MAP[doc.doc_type]
    rows = [
        [f"{label} No.", doc.document_number, "Activity Date", format_date(doc.activity_date)],
        ["Source Invoice", doc.source_invoice_id, "PO Number", doc.po_number or "-"],
        ["Department", doc.department or "-", "Delivery Location", doc.delivery_location or "-"],
    ]
    if doc.doc_type == "grn":
        rows.append(["GRN Reference", doc.document_number, "Three-Way Match", doc.three_way_match or "-"])
    elif doc.doc_type == "ses":
        rows.append(["SES Reference", doc.document_number, "Approver Status", doc.approval_status or "-"])
    else:
        rows.append(["Vendor Reference", doc.vendor_id or "-", "Receiver", doc.requestor or "-"])

    table = Table(rows, colWidths=[3.5 * cm, 5.7 * cm, 3.7 * cm, 5.5 * cm])
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


def make_line_table(doc: RelatedDocument) -> Table:
    descriptor = {
        "delivery_note": "Delivered Item / Service",
        "grn": "Received Item / Service",
        "ses": "Verified Service Scope",
    }[doc.doc_type]
    rows = [
        ["Line", descriptor, "Category", "Qty", "UOM", "Unit Rate", "Amount"],
        [
            "1",
            doc.goods_or_service_supplied or "-",
            doc.category or "-",
            format_quantity(doc.quantity),
            doc.uom or "-",
            format_money(doc.currency, doc.unit_price),
            format_money(doc.currency, doc.line_amount),
        ],
    ]
    table = Table(rows, colWidths=[1.0 * cm, 6.8 * cm, 3.1 * cm, 1.8 * cm, 1.6 * cm, 2.8 * cm, 2.9 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173A72")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4DCE8")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def make_control_table(doc: RelatedDocument) -> Table:
    rows = [
        ["Requestor", doc.requestor or "-"],
        ["Buyer", doc.buyer or "-"],
        ["Approval Status", doc.approval_status or "-"],
        ["Three-Way Match", doc.three_way_match or "-"],
        ["Payment Block", doc.payment_block or "-"],
        ["Remarks", doc.remarks or "No remarks recorded."],
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


def make_type_note(doc: RelatedDocument, s) -> str:
    if doc.doc_type == "delivery_note":
        return (
            f"This delivery note confirms that {doc.vendor_name} dispatched the stated item or service "
            f"to {doc.delivery_location} against purchase order {doc.po_number} for the attention of "
            f"{doc.department}."
        )
    if doc.doc_type == "grn":
        return (
            f"This goods receipt note records receiving confirmation for the referenced supply at "
            f"{doc.delivery_location}. It establishes receipt evidence linked to invoice {doc.source_invoice_id} "
            f"and supports downstream three-way match validation."
        )
    return (
        f"This service entry sheet records completion and service verification for the supplied scope under "
        f"{doc.po_number}. It provides service acceptance evidence for Accounts Payable and the requesting function."
    )


def build_pdf(doc_meta: RelatedDocument) -> None:
    out = Path(doc_meta.file_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    s = styles()
    doc = BaseDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=1.35 * cm,
        rightMargin=1.35 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.7 * cm,
        title=doc_meta.document_number,
        author=doc_meta.vendor_name,
        subject=f"{DOC_LABEL_MAP[doc_meta.doc_type]} for {doc_meta.buyer_name}",
        creator="AUGMIS P2P Related Document Generator",
        keywords=f"p2p,{doc_meta.doc_type},{doc_meta.vendor_name},{doc_meta.po_number},{doc_meta.source_invoice_id}",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="default", frames=[frame], onPage=draw_page_chrome)])

    story = [
        Paragraph(DOC_LABEL_MAP[doc_meta.doc_type], s["DocTitle"]),
        Paragraph("Generated from a linked P2P transaction row for repository-backed retrieval testing.", s["Muted"]),
        Spacer(1, 0.25 * cm),
        make_party_table(doc_meta, s),
        Spacer(1, 0.28 * cm),
        Paragraph("Reference Summary", s["SectionLabel"]),
        make_summary_table(doc_meta),
        Spacer(1, 0.25 * cm),
        Paragraph("Line Details", s["SectionLabel"]),
        make_line_table(doc_meta),
        Spacer(1, 0.25 * cm),
        Paragraph("Workflow Controls", s["SectionLabel"]),
        make_control_table(doc_meta),
        Spacer(1, 0.22 * cm),
        Paragraph("Document Note", s["SectionLabel"]),
        Paragraph(make_type_note(doc_meta, s), s["BodySmall"]),
    ]
    doc.build(story)


def write_metadata(records: Iterable[RelatedDocument], out_root: Path) -> None:
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


def write_sidecar(record: RelatedDocument) -> None:
    Path(record.file_path).with_suffix(".metadata.json").write_text(
        json.dumps(asdict(record), indent=2),
        encoding="utf-8",
    )


def validate_input(csv_path: Path) -> None:
    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")
    if csv_path.suffix.lower() != ".csv":
        raise SystemExit(f"Expected a .csv file, got: {csv_path}")


def main() -> None:
    args = parse_args()
    validate_input(args.csv)
    args.out.mkdir(parents=True, exist_ok=True)
    docs_to_generate = parse_docs_arg(args.docs)
    rows = read_rows(args.csv, args.limit)
    if not rows:
        raise SystemExit("No rows found in CSV.")

    documents = build_documents(rows, args.out, docs_to_generate, args.buyer_name)
    if not documents:
        raise SystemExit("No related documents matched the requested criteria.")

    write_metadata(documents, args.out)
    if args.metadata_only:
        for doc_meta in documents:
            write_sidecar(doc_meta)
        print(f"Generated metadata only for {len(documents)} related P2P documents in: {args.out.resolve()}")
        print(f"Metadata CSV: {(args.out / 'metadata_index.csv').resolve()}")
        print(f"Metadata JSON: {(args.out / 'metadata_index.json').resolve()}")
        return

    for doc_meta in tqdm(documents, desc="Generating P2P related docs"):
        build_pdf(doc_meta)
        write_sidecar(doc_meta)

    print(f"Generated {len(documents)} related P2P documents in: {args.out.resolve()}")
    print(f"Metadata CSV: {(args.out / 'metadata_index.csv').resolve()}")
    print(f"Metadata JSON: {(args.out / 'metadata_index.json').resolve()}")


if __name__ == "__main__":
    main()
