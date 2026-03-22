"""Resume PDF generation using fpdf2 (pure Python, no system deps)."""

from fpdf import FPDF
from loguru import logger


class ResumePDF(FPDF):
    """Custom PDF with resume-appropriate formatting."""

    def header(self):
        pass

    def footer(self):
        pass


def generate_resume_pdf(html_or_text: str) -> bytes:
    """Generate a PDF from resume text/HTML content.

    Strips HTML tags and renders clean plain-text PDF with proper formatting.
    """
    import re
    # Strip HTML tags to get clean text
    text = re.sub(r"<[^>]+>", "", html_or_text)
    text = text.strip()

    pdf = ResumePDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)

    # Sanitize text: replace Unicode chars that latin-1 can't handle
    text = (text.replace("\u2022", "-").replace("\u2013", "-").replace("\u2014", "-")
            .replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
            .replace("\u2026", "...").replace("\u00b7", "-"))

    lines = text.split("\n")
    section_keywords = {
        "summary", "objective", "experience", "work experience",
        "education", "skills", "projects", "certifications",
        "technical skills", "professional experience", "achievements",
    }
    usable_w = pdf.w - pdf.l_margin - pdf.r_margin

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            pdf.ln(3)
            continue

        # Encode-safe: drop any remaining non-latin1 chars
        stripped = stripped.encode("latin-1", "replace").decode("latin-1")

        clean = stripped.rstrip(":")
        is_section = clean.lower() in section_keywords or (clean.isupper() and len(clean) > 2)

        if i == 0:
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 8, stripped, new_x="LMARGIN", new_y="NEXT", align="C")
        elif i <= 2 and ("@" in stripped or "|" in stripped):
            pdf.set_font("Helvetica", size=9)
            pdf.cell(0, 5, stripped, new_x="LMARGIN", new_y="NEXT", align="C")
        elif is_section:
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, clean, new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(180, 180, 180)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(2)
        elif stripped.startswith(("-", "*")):
            pdf.set_font("Helvetica", size=10)
            bullet_text = stripped.lstrip("-* ").strip()
            pdf.cell(4, 5, "")  # indent
            pdf.multi_cell(usable_w - 4, 5, f"- {bullet_text}")
        elif re.search(r"\b(20\d{2}|present|current)\b", stripped, re.IGNORECASE):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(usable_w, 5, stripped)
        else:
            pdf.set_font("Helvetica", size=10)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(usable_w, 5, stripped)

    result = pdf.output()
    logger.info(f"Generated resume PDF: {len(result)} bytes")
    return bytes(result)
