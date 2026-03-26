from pathlib import Path
from typing import List, Dict

import pandas as pd

REQUIRED_COLUMNS = [
    "rfi_id",
    "project_name",
    "trade",
    "spec_section",
    "subject",
    "question_text",
    "response_text",
    "source_type",
    "source_file",
    "source_page",
    "source_chunk",
]


def ensure_dataset_exists(csv_path: str):
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        df.to_csv(path, index=False)


def load_dataset(csv_path: str) -> pd.DataFrame:
    ensure_dataset_exists(csv_path)
    df = pd.read_csv(csv_path)
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[REQUIRED_COLUMNS]


def save_dataset(df: pd.DataFrame, csv_path: str):
    df = df.copy()
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df[REQUIRED_COLUMNS].to_csv(csv_path, index=False)


def append_rows(csv_path: str, rows: List[Dict]) -> int:
    if not rows:
        return 0

    base_df = load_dataset(csv_path)
    new_df = pd.DataFrame(rows)

    for col in REQUIRED_COLUMNS:
        if col not in new_df.columns:
            new_df[col] = ""

    new_df = new_df[REQUIRED_COLUMNS].fillna("")

    existing_keys = set(
        (
            str(r["subject"]).strip().lower(),
            str(r["question_text"]).strip().lower(),
            str(r["response_text"]).strip().lower(),
            str(r["source_file"]).strip().lower(),
            str(r["source_page"]).strip().lower(),
            str(r["source_chunk"]).strip().lower(),
        )
        for _, r in base_df.iterrows()
    )

    rows_to_add = []
    for _, r in new_df.iterrows():
        key = (
            str(r["subject"]).strip().lower(),
            str(r["question_text"]).strip().lower(),
            str(r["response_text"]).strip().lower(),
            str(r["source_file"]).strip().lower(),
            str(r["source_page"]).strip().lower(),
            str(r["source_chunk"]).strip().lower(),
        )
        if key not in existing_keys:
            rows_to_add.append(r.to_dict())
            existing_keys.add(key)

    if not rows_to_add:
        return 0

    merged = pd.concat([base_df, pd.DataFrame(rows_to_add)], ignore_index=True)
    save_dataset(merged, csv_path)
    return len(rows_to_add)
