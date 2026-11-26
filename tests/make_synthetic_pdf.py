#!/usr/bin/env python3
"""Create a synthetic two-page, mixed-width/two-column PDF for integration tests.

Development-only dependency: reportlab (`python -m pip install reportlab`).
This file is not a formal contest case and contains no scientific claims.
"""
from pathlib import Path


def make_pdf(path: Path) -> None:
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(path), pagesize=(612, 792))
    for page_number in (1, 2):
        pdf.setFont("Helvetica", 9)
        pdf.drawString(42, 770, "SYNTHETIC HEADER")
        pdf.drawRightString(570, 22, f"Page {page_number}")
        if page_number == 1:
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawCentredString(306, 730, "Synthetic Reading Order Fixture")
            pdf.setFont("Helvetica", 10)
            pdf.drawString(48, 700, "ABSTRACT: This entirely synthetic fixture verifies block ordering across a mixed-width page layout.")
            pdf.setFont("Helvetica", 11)
            pdf.drawString(50, 650, "LEFT_ONE alpha")
            pdf.drawString(50, 620, "LEFT_TWO beta")
            pdf.drawString(324, 650, "RIGHT_ONE gamma")
            pdf.drawString(324, 620, "RIGHT_TWO delta")
        else:
            pdf.setFont("Helvetica", 11)
            pdf.drawString(50, 700, "LEFT_THREE epsilon")
            pdf.drawString(324, 700, "RIGHT_THREE zeta")
        pdf.showPage()
    pdf.save()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    make_pdf(args.output)
    print(args.output)
