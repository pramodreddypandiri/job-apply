"""Convert plain-text resume into structured HTML for PDF generation."""

import re


def text_to_resume_html(text: str) -> str:
    """Parse plain-text resume into semantic HTML sections."""
    lines = text.strip().split("\n")
    html_parts: list[str] = []
    in_list = False

    # Common section headers
    section_keywords = {
        "summary", "objective", "experience", "work experience",
        "education", "skills", "projects", "certifications",
        "technical skills", "professional experience", "achievements",
        "awards", "publications", "languages", "interests",
        "volunteer", "professional summary",
    }

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue

        # First non-empty line is likely the name
        if i == 0 or (i <= 2 and not any(c in stripped for c in ["•", "-", "·", "|"])):
            # Check if it's a section header or the person's name
            if stripped.lower().rstrip(":") in section_keywords:
                html_parts.append(f'<h2>{_escape(stripped.rstrip(":")):}</h2>')
                continue
            if i == 0:
                html_parts.append(f'<div class="header"><h1>{_escape(stripped)}</h1>')
                continue
            if i <= 2 and ("@" in stripped or "|" in stripped or "linkedin" in stripped.lower()):
                html_parts.append(f'<p>{_escape(stripped)}</p></div>')
                continue

        # Section headers (all caps, or ends with colon, or matches known sections)
        clean = stripped.rstrip(":")
        if clean.lower() in section_keywords or (clean.isupper() and len(clean) > 2):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f'<h2>{_escape(clean)}</h2>')
            continue

        # Bullet points
        if stripped.startswith(("•", "-", "·", "*", "–")):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            bullet_text = stripped.lstrip("•-·*– ").strip()
            html_parts.append(f"<li>{_escape(bullet_text)}</li>")
            continue

        # Job title lines (heuristic: contains date range like 2020-2023 or "Present")
        if re.search(r"\b(20\d{2}|present|current)\b", stripped, re.IGNORECASE):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            # Try to split role | company | dates
            html_parts.append(f'<h3>{_escape(stripped)}</h3>')
            continue

        # Regular paragraph
        if in_list:
            html_parts.append("</ul>")
            in_list = False
        html_parts.append(f"<p>{_escape(stripped)}</p>")

    if in_list:
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def _escape(text: str) -> str:
    """Basic HTML escaping."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
