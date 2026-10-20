from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def build_invoice_pdf(invoice):
    """Take an Invoice from the database and return the PDF as bytes in memory."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=invoice.invoice_no)
    styles = getSampleStyleSheet()

    story = [
        Paragraph("Braud Clothing", styles["Title"]),
        Paragraph(f"Invoice {invoice.invoice_no}", styles["Heading2"]),
        Paragraph(f"Date: {invoice.date.strftime('%d %b %Y, %H:%M')}", styles["Normal"]),
        # escape() stops characters like < or & in a name from breaking the PDF
        Paragraph(f"Customer: {escape(invoice.customer_name)}", styles["Normal"]),
        Paragraph(f"Phone: {escape(invoice.phone or '-')}", styles["Normal"]),
        Spacer(1, 20),
    ]
    if invoice.status == "Cancelled":
        story.insert(2, Paragraph("<font color='red'>CANCELLED</font>", styles["Heading2"]))
    rows = [["#", "Model", "Size", "Qty", "Price", "Amount"]]
    for i, item in enumerate(invoice.items, start=1):
        rows.append([
            i,
            item.product.name,
            item.size,
            item.quantity,
            f"{item.unit_price:.2f}",
            f"{item.quantity * item.unit_price:.2f}",
        ])
        discount = invoice.discount or 0
    if discount > 0:
        subtotal = sum(i.quantity * i.unit_price for i in invoice.items)
        rows.append(["", "", "", "", "Subtotal", f"{subtotal:.2f}"])
        rows.append(["", "", "", "", "Discount", f"-{discount:.2f}"])
    rows.append(["", "", "", "", "Total", f"{invoice.total:.2f}"])

    table = Table(rows, colWidths=[30, 150, 50, 50, 80, 90])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16243b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.lightgrey),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 30))
    story.append(Paragraph("Thank you for your business.", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer