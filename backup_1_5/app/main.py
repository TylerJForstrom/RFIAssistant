from io import StringIO
from pathlib import Path
import os

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException

from app.db.database import (
    init_db,
    save_feedback,
    save_reviewed_rfi,
    get_feedback_summary,
    list_recent_feedback,
    list_reviewed_rfis,
)
from app.models.rfi import RFIQuery, FeedbackPayload
from app.services.retrieve import RFIRetriever
from app.services.generate_draft import generate_llm_draft
from app.services.analyze import build_issue_analysis
from app.services.pdf_ingest import parse_pdf_pages_to_rows
from app.services.dataset_manager import ensure_dataset_exists, append_rows
from app.services.context_builder import build_structured_context

app = FastAPI(title="Smart RFI Assistant")

DATA_PATH = Path("data/raw/rfis.csv")
DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
ensure_dataset_exists(str(DATA_PATH))

retriever = RFIRetriever(str(DATA_PATH))
init_db()


def reload_retriever():
    global retriever
    retriever = RFIRetriever(str(DATA_PATH))


def ai_available() -> bool:
    return (
        os.getenv("USE_OPENAI_DRAFTS", "false").lower() == "true"
        and bool(os.getenv("OPENAI_API_KEY"))
    )


@app.get("/")
def root():
    return {"message": "Smart RFI Assistant API is running"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "dataset_exists": DATA_PATH.exists(),
        "dataset_path": str(DATA_PATH),
        "row_count": int(len(retriever.df)),
        "ai_available": ai_available(),
        "retrieval_engine": "intent-aware-hybrid-faiss-rerank",
        "index_status": retriever.index_status,
    }


@app.get("/filters")
def get_filters():
    df = retriever.df
    return {
        "trades": sorted([x for x in df["trade"].dropna().unique().tolist() if str(x).strip()]),
        "projects": sorted([x for x in df["project_name"].dropna().unique().tolist() if str(x).strip()]),
        "spec_sections": sorted([x for x in df["spec_section"].dropna().unique().tolist() if str(x).strip()]),
    }


@app.get("/dashboard")
def get_dashboard():
    return build_issue_analysis(str(DATA_PATH))


@app.get("/dataset-info")
def dataset_info():
    df = retriever.df
    return {
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "path": str(DATA_PATH),
    }


@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    contents = await file.read()

    try:
        df = pd.read_csv(StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {e}")

    required_columns = [
        "rfi_id",
        "project_name",
        "trade",
        "spec_section",
        "subject",
        "question_text",
        "response_text",
    ]

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing)}")

    for extra_col in ["source_type", "source_file", "source_page", "source_chunk"]:
        if extra_col not in df.columns:
            df[extra_col] = ""

    df.to_csv(DATA_PATH, index=False)
    reload_retriever()

    return {
        "message": "CSV uploaded successfully.",
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "saved_to": str(DATA_PATH),
    }


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    pdf_bytes = await file.read()

    try:
        rows = parse_pdf_pages_to_rows(pdf_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not process PDF: {e}")

    added = append_rows(str(DATA_PATH), rows)
    reload_retriever()

    return {
        "message": "PDF processed successfully.",
        "parsed_rows": len(rows),
        "added_rows": added,
        "dataset_path": str(DATA_PATH),
    }


@app.post("/sync-reviewed-rfis")
def sync_reviewed_rfis():
    reviewed = list_reviewed_rfis(limit=100000)
    rows = []

    for idx, item in enumerate(reviewed, start=1):
        rows.append({
            "rfi_id": f"reviewed-{item['id']}",
            "project_name": item.get("project_name", "") or "",
            "trade": item.get("trade", "") or "",
            "spec_section": item.get("spec_section", "") or "",
            "subject": item.get("subject", "") or f"Reviewed RFI {idx}",
            "question_text": item.get("question_text", "") or "",
            "response_text": item.get("final_response_text", "") or "",
            "source_type": "reviewed_feedback",
            "source_file": "",
            "source_page": "",
            "source_chunk": "",
        })

    added = append_rows(str(DATA_PATH), rows)
    reload_retriever()

    return {
        "message": "Reviewed RFIs synced.",
        "reviewed_count": len(reviewed),
        "added_rows": added,
    }


@app.post("/search")
def search_rfis(query: RFIQuery):
    return retriever.search(
        subject=query.subject,
        question_text=query.question_text,
        top_k=query.top_k,
        trade=query.trade,
        spec_section=query.spec_section,
        project_name=query.project_name,
    )


@app.post("/generate")
def generate_response(query: RFIQuery):
    retrieval = retriever.search(
        subject=query.subject,
        question_text=query.question_text,
        top_k=query.top_k,
        trade=query.trade,
        spec_section=query.spec_section,
        project_name=query.project_name,
    )

    requested_ai = query.use_ai and ai_available()
    structured_context = build_structured_context(
        retrieval.get("results", []),
        retrieval.get("safeguards", []),
    )

    draft = generate_llm_draft(
        new_subject=query.subject,
        new_question=query.question_text,
        similar_rfis=retrieval.get("results", []),
        safeguards=retrieval.get("safeguards", []),
        use_ai=requested_ai,
    )

    return {
        "draft_response": draft,
        "similar_rfis": retrieval.get("results", []),
        "duplicate_warning": retrieval.get("duplicate_warning"),
        "overall_confidence": retrieval.get("overall_confidence", "Low"),
        "confidence_score": retrieval.get("confidence_score", 0.0),
        "safeguards": retrieval.get("safeguards", []),
        "retrieval_count": len(retrieval.get("results", [])),
        "candidate_count": retrieval.get("candidate_count", len(retrieval.get("results", []))),
        "used_ai": bool(requested_ai),
        "retrieval_engine": retrieval.get("retrieval_engine", "intent-aware-hybrid-faiss-rerank"),
        "index_status": retrieval.get("index_status", "unknown"),
        "ai_available": ai_available(),
        "query_intent": retrieval.get("query_intent", "general"),
        "intent_labels": retrieval.get("intent_labels", []),
        "expanded_queries": retrieval.get("expanded_queries", []),
        "structured_context": structured_context,
    }


@app.post("/feedback")
def submit_feedback(payload: FeedbackPayload):
    save_feedback(
        subject=payload.subject,
        question_text=payload.question_text,
        generated_draft=payload.generated_draft,
        final_draft=payload.final_draft,
        action=payload.action,
        overall_confidence=payload.overall_confidence,
        duplicate_warning=payload.duplicate_warning,
    )

    added_to_dataset = 0

    if payload.action in {"accepted", "edited"}:
        final_response = payload.final_draft if payload.final_draft else payload.generated_draft

        save_reviewed_rfi(
            subject=payload.subject,
            question_text=payload.question_text,
            final_response_text=final_response,
            trade=payload.trade,
            spec_section=payload.spec_section,
            project_name=payload.project_name,
        )

        added_to_dataset = append_rows(str(DATA_PATH), [{
            "rfi_id": f"feedback-{payload.subject[:20]}-{payload.question_text[:20]}",
            "project_name": payload.project_name or "",
            "trade": payload.trade or "",
            "spec_section": payload.spec_section or "",
            "subject": payload.subject,
            "question_text": payload.question_text,
            "response_text": final_response,
            "source_type": "feedback_accepted",
            "source_file": "",
            "source_page": "",
            "source_chunk": "",
        }])

        reload_retriever()

    return {
        "message": "Feedback saved successfully.",
        "added_to_dataset": added_to_dataset,
    }


@app.get("/feedback-summary")
def feedback_summary():
    return get_feedback_summary()


@app.get("/feedback-recent")
def feedback_recent(limit: int = 20):
    return {"items": list_recent_feedback(limit=limit)}
