import re
from typing import List, Dict, Tuple

import fitz

from app.services.chunking import chunk_text


def extract_pages_from_pdf_bytes(pdf_bytes: bytes) -> List[Tuple[int, str]]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page_index, page in enumerate(doc, start=1):
        text = page.get_text("text")
        pages.append((page_index, text))
    return pages


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    pages = extract_pages_from_pdf_bytes(pdf_bytes)
    return "\n".join(text for _, text in pages)


def _clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_rfi_blocks_from_text(text: str) -> List[Dict]:
    text = _clean_text(text)

    block_pattern = re.compile(
        r"(?:RFI\s*(?:#|No\.?|Number)?\s*[:\-]?\s*(?P<rfi_id>[A-Za-z0-9\-_]+))?"
        r"(?P<body>.*?)(?=(?:\n\s*RFI\s*(?:#|No\.?|Number)?\s*[:\-]?\s*[A-Za-z0-9\-_]+)|\Z)",
        re.IGNORECASE | re.DOTALL
    )

    subject_pattern = re.compile(r"(?:Subject|Re)\s*[:\-]\s*(.+)", re.IGNORECASE)
    question_pattern = re.compile(
        r"(?:Question|Request|Description)\s*[:\-]\s*(.+?)(?=\n[A-Z][A-Za-z ]{1,30}\s*[:\-]|\Z)",
        re.IGNORECASE | re.DOTALL
    )
    response_pattern = re.compile(
        r"(?:Response|Answer|Reply)\s*[:\-]\s*(.+?)(?=\n[A-Z][A-Za-z ]{1,30}\s*[:\-]|\Z)",
        re.IGNORECASE | re.DOTALL
    )
    trade_pattern = re.compile(r"(?:Trade|Discipline)\s*[:\-]\s*(.+)", re.IGNORECASE)
    spec_pattern = re.compile(r"(?:Spec(?:ification)?\s*Section)\s*[:\-]\s*(.+)", re.IGNORECASE)
    project_pattern = re.compile(r"(?:Project|Job)\s*[:\-]\s*(.+)", re.IGNORECASE)

    rows = []
    found_any_structured = False

    for idx, match in enumerate(block_pattern.finditer(text), start=1):
        body = match.group("body").strip()
        if not body:
            continue

        subject_match = subject_pattern.search(body)
        question_match = question_pattern.search(body)
        response_match = response_pattern.search(body)
        trade_match = trade_pattern.search(body)
        spec_match = spec_pattern.search(body)
        project_match = project_pattern.search(body)

        subject = subject_match.group(1).strip() if subject_match else ""
        question = question_match.group(1).strip() if question_match else ""
        response = response_match.group(1).strip() if response_match else ""
        trade = trade_match.group(1).strip() if trade_match else ""
        spec = spec_match.group(1).strip() if spec_match else ""
        project = project_match.group(1).strip() if project_match else ""
        rfi_id = match.group("rfi_id") or f"pdf-{idx}"

        if subject or question or response:
            found_any_structured = True
            question_chunks = chunk_text(question or body[:2000], chunk_size=900, overlap=150)
            response_chunks = chunk_text(response, chunk_size=900, overlap=150) if response else [""]

            max_len = max(len(question_chunks), len(response_chunks))
            for chunk_idx in range(max_len):
                q_chunk = question_chunks[chunk_idx] if chunk_idx < len(question_chunks) else ""
                r_chunk = response_chunks[chunk_idx] if chunk_idx < len(response_chunks) else ""
                rows.append({
                    "rfi_id": f"{rfi_id}-chunk-{chunk_idx + 1}",
                    "project_name": project,
                    "trade": trade,
                    "spec_section": spec,
                    "subject": subject if subject else f"Imported RFI {idx}",
                    "question_text": q_chunk,
                    "response_text": r_chunk,
                    "source_type": "pdf_import",
                    "source_file": "",
                    "source_page": "",
                    "source_chunk": chunk_idx + 1,
                })

    if found_any_structured:
        return rows

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    rows = []

    for idx, para in enumerate(paragraphs, start=1):
        pieces = chunk_text(para, chunk_size=900, overlap=150)
        for chunk_idx, piece in enumerate(pieces, start=1):
            rows.append({
                "rfi_id": f"pdf-{idx}-chunk-{chunk_idx}",
                "project_name": "",
                "trade": "",
                "spec_section": "",
                "subject": f"Imported PDF Block {idx}",
                "question_text": piece,
                "response_text": "",
                "source_type": "pdf_import",
                "source_file": "",
                "source_page": "",
                "source_chunk": chunk_idx,
            })

    return rows


def parse_pdf_pages_to_rows(pdf_bytes: bytes, filename: str) -> List[Dict]:
    pages = extract_pages_from_pdf_bytes(pdf_bytes)
    rows: List[Dict] = []

    for page_num, page_text in pages:
        clean = _clean_text(page_text)
        if not clean:
            continue

        chunks = chunk_text(clean, chunk_size=900, overlap=150)
        for chunk_idx, chunk in enumerate(chunks, start=1):
            rows.append({
                "rfi_id": f"{filename}-p{page_num}-c{chunk_idx}",
                "project_name": "",
                "trade": "",
                "spec_section": "",
                "subject": f"PDF Import: {filename}",
                "question_text": chunk,
                "response_text": "",
                "source_type": "pdf_page_chunk",
                "source_file": filename,
                "source_page": page_num,
                "source_chunk": chunk_idx,
            })

    return rows
