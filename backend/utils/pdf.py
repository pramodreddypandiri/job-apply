"""WeasyPrint resume PDF generation."""

import tempfile
from pathlib import Path
from weasyprint import HTML
from loguru import logger


RESUME_CSS = """
@page {
    size: letter;
    margin: 0.5in 0.6in;
}
body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.4;
    color: #333;
}
h1 { font-size: 16pt; margin: 0 0 4pt 0; }
h2 { font-size: 12pt; margin: 12pt 0 4pt 0; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
h3 { font-size: 10pt; margin: 8pt 0 2pt 0; }
p { margin: 2pt 0; }
ul { margin: 2pt 0; padding-left: 16pt; }
li { margin: 1pt 0; }
.header { text-align: center; margin-bottom: 8pt; }
.header p { margin: 1pt 0; font-size: 9pt; color: #666; }
.section { margin-bottom: 6pt; }
.job-title { font-weight: bold; }
.company { color: #555; }
.dates { float: right; color: #777; font-size: 9pt; }
"""


def generate_resume_pdf(html_content: str) -> bytes:
    """Generate a PDF from resume HTML content."""
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head><style>{RESUME_CSS}</style></head>
    <body>{html_content}</body>
    </html>
    """
    pdf_bytes = HTML(string=full_html).write_pdf()
    logger.info(f"Generated resume PDF: {len(pdf_bytes)} bytes")
    return pdf_bytes


def save_resume_pdf(html_content: str, output_path: str | None = None) -> str:
    """Generate and save resume PDF, returning the file path."""
    pdf_bytes = generate_resume_pdf(html_content)
    if output_path is None:
        fd = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        output_path = fd.name
        fd.close()
    Path(output_path).write_bytes(pdf_bytes)
    return output_path
