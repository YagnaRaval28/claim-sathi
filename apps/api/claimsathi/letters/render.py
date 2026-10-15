"""PDF rendering with WeasyPrint (HarfBuzz shaping, so Gujarati and Devanagari render correctly). Imported lazily.

Fonts: the container installs Noto fonts (Dockerfile). All text is HTML-escaped; letters never contain markup.
"""

from __future__ import annotations

from html import escape
from typing import Any

CSS = """
@page { size: A4; margin: 25mm; @bottom-center { content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt; color: #5F6A67; } }
body { font-family: "Noto Serif", "Noto Serif Gujarati", "Noto Serif Devanagari", serif; font-size: 11.5pt;
       line-height: 1.6; color: #1C2321; }
.meta { margin: 0; }
.subject { font-weight: 600; margin: 14pt 0; }
blockquote { margin: 8pt 0 8pt 12pt; padding-left: 8pt; border-left: 2pt solid #1E6B40; }
sup { font-size: 8pt; }
ol, ul { padding-left: 16pt; list-style: none; }
.footnotes { margin-top: 18pt; border-top: 0.5pt solid #D8D4CB; padding-top: 6pt; font-size: 9pt; }
.disclaimer { margin-top: 10pt; font-size: 8.5pt; color: #5F6A67; }
"""


def letter_html(doc: dict[str, Any]) -> str:
    parts: list[str] = []
    for b in doc["blocks"]:
        t = b["type"]
        if t == "meta":
            parts.append(f'<p class="meta">{escape(b["text"])}</p>')
        elif t == "subject":
            parts.append(f'<p class="subject">{escape(b["text"])}</p>')
        elif t == "quote":
            parts.append(f'<blockquote lang="en">{escape(b["text"])}<sup>[{int(b["footnote"])}]</sup></blockquote>')
        elif t == "list":
            parts.append("<ul>" + "".join(f"<li>{escape(i)}</li>" for i in b["items"]) + "</ul>")
        else:
            parts.append(f"<p>{escape(b['text'])}</p>")
    notes = "".join(
        f"<p>[{int(n['n'])}] {escape(n['source_title'])}, {escape(n.get('clause_ref') or '')}, version "
        f"{escape(n['version'])}{' (SYNTHETIC test source)' if n.get('synthetic') else ''}</p>"
        for n in doc.get("footnotes", [])
    )
    return (
        f"<!doctype html><html lang='en'><head><meta charset='utf-8'><style>{CSS}</style></head><body>"
        f"{''.join(parts)}<div class='footnotes'>{notes}</div>"
        f"<p class='disclaimer'>{escape(doc.get('disclaimer', ''))}</p></body></html>"
    )


def render_pdf(doc: dict[str, Any]) -> bytes:
    from weasyprint import HTML

    pdf: bytes = HTML(string=letter_html(doc)).write_pdf()
    return pdf
