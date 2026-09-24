"""Turn resume / job-description files into text (and, for PDFs, a document block
that vision-capable backends can read directly)."""

import base64
from dataclasses import dataclass
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

SUPPORTED = {".pdf", ".docx", ".txt", ".md"}


@dataclass
class LoadedDocument:
    path: Path
    text: str                 # visible text; empty for scanned PDFs
    pdf_base64: str | None    # set for PDFs, so backends that read pages can use them
    hidden_text: str = ""     # PDF text a reader can't see (white or tiny): a prompt-injection vector

    def content_blocks(self) -> list[dict]:
        """Content for a backend that accepts documents: the PDF itself when available."""
        if self.pdf_base64:
            return [{"type": "document",
                     "source": {"type": "base64", "media_type": "application/pdf", "data": self.pdf_base64}}]
        return [{"type": "text", "text": self.text}]


# Text below this effective size (points) is unreadable when printed; resumes don't use it legitimately.
MIN_VISIBLE_PT = 4.0
_WHITE = {b"g": [1.0], b"rg": [1.0, 1.0, 1.0], b"k": [0.0, 0.0, 0.0, 0.0]}


def _pdf_text(path: Path) -> tuple[str, str]:
    """Split a PDF's text layer into what a reader sees and what they don't.

    Hidden = drawn in white or below MIN_VISIBLE_PT, the usual tricks for planting instructions
    or keywords that only a parser will read. Invisible OCR layers (render mode 3) are kept: they
    mirror the visible scan. Known gap: white text on a dark background also counts as hidden,
    which is why hidden text is flagged for review rather than silently dropped.
    """
    visible, hidden = [], []
    for page in PdfReader(path).pages:
        fill: list = [False]  # stack of "fill colour is white", following q/Q

        def before(op, args, cm, tm):
            if op == b"q":
                fill.append(fill[-1])
            elif op == b"Q" and len(fill) > 1:
                fill.pop()
            elif op in _WHITE:
                try:
                    fill[-1] = [float(a) for a in args] == _WHITE[op]
                except (TypeError, ValueError):
                    fill[-1] = False

        def on_text(text, cm, tm, font, size):
            scale = abs(tm[3] * cm[3]) or 1.0
            tiny = size and size * scale < MIN_VISIBLE_PT
            (hidden if fill[-1] or tiny else visible).append(text)

        page.extract_text(visitor_operand_before=before, visitor_text=on_text)
        visible.append("\n")
    return "".join(visible).strip(), " ".join(t.strip() for t in hidden if t.strip())


def load_document(path: Path) -> LoadedDocument:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError(f"Unsupported file type: {suffix} (supported: {', '.join(sorted(SUPPORTED))})")

    if suffix == ".pdf":
        visible, hidden = _pdf_text(path)
        return LoadedDocument(path, visible, base64.standard_b64encode(path.read_bytes()).decode(), hidden)

    if suffix == ".docx":
        doc = DocxDocument(path)
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:  # many resume templates put content in tables
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        text = "\n".join(p for p in parts if p.strip())
    else:
        text = path.read_text(encoding="utf-8", errors="replace")

    if not text.strip():
        raise ValueError(f"No text found in {path}")
    return LoadedDocument(path, text, None)
