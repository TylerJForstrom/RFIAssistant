from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel

from app.services.retrieve import RFIRetriever
from app.services.generate_draft import generate_llm_draft
from app.services.analyze import build_issue_analysis

app = FastAPI(title="Smart RFI Assistant")

DATA_PATH = Path("data/raw/rfis.csv")
DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

retriever = RFIRetriever(str(DATA_PATH))


class RFIQuery(BaseModel):
    subject: str
    question_text: str
    top_k: int = 3
    trade: Optional[str] = None
    spec_section: Optional[str] = None
    project_name: Optional[str] = None


def reload_retriever():
    global retriever
    retriever = RFIRetriever(str(DATA_PATH))


@app.get("/")
def root():
    return {"message": "Smart RFI Assistant API is running"}


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
        from io import StringIO
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
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing)}"
        )

    df.to_csv(DATA_PATH, index=False)
    reload_retriever()

    return {
        "message": "CSV uploaded successfully.",
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "saved_to": str(DATA_PATH),
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

    draft = generate_llm_draft(
        new_subject=query.subject,
        new_question=query.question_text,
        similar_rfis=retrieval.get("results", []),
        safeguards=retrieval.get("safeguards", []),
    )

    return {
        "draft_response": draft,
        "similar_rfis": retrieval.get("results", []),
        "duplicate_warning": retrieval.get("duplicate_warning"),
        "overall_confidence": retrieval.get("overall_confidence", "Low"),
        "safeguards": retrieval.get("safeguards", []),
    }
