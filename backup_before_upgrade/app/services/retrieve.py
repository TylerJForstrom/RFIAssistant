import hashlib
import json
import os
from pathlib import Path
from typing import Optional, List, Dict

import faiss
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.rerank import rerank_results

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()


class RFIRetriever:
    def __init__(self, csv_path: str = "data/raw/rfis.csv"):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)

        for col in [
            "rfi_id",
            "subject",
            "question_text",
            "response_text",
            "trade",
            "spec_section",
            "project_name",
            "source_type",
            "source_file",
            "source_page",
            "source_chunk",
        ]:
            if col not in self.df.columns:
                self.df[col] = ""
            self.df[col] = self.df[col].fillna("").astype(str)

        self.df["combined_text"] = (
            self.df["subject"] + " " +
            self.df["question_text"] + " " +
            self.df["response_text"] + " " +
            self.df["trade"] + " " +
            self.df["spec_section"] + " " +
            self.df["project_name"]
        ).str.strip()

        self.cache_dir = Path("data/processed/faiss_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.dataset_hash = self._compute_dataset_hash()

        self.word_vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1
        )
        self.word_matrix = self.word_vectorizer.fit_transform(self.df["combined_text"])

        self.char_vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=1
        )
        self.char_matrix = self.char_vectorizer.fit_transform(self.df["combined_text"])

        n_features = self.word_matrix.shape[1]
        n_components = min(50, max(1, n_features - 1))
        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        self.svd_matrix = self.svd.fit_transform(self.word_matrix).astype("float32")

        self.faiss_index = None
        self.svd_matrix_normalized = None
        self.index_status = "rebuilt"
        self._load_or_build_faiss_index()

        self.use_openai_embeddings = os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true"
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.client = None
        self.doc_embeddings = None

        if self.use_openai_embeddings and OpenAI is not None and os.getenv("OPENAI_API_KEY"):
            try:
                self.client = OpenAI()
                self.doc_embeddings = self._build_doc_embeddings()
            except Exception as e:
                print(f"[retrieve] OpenAI embeddings disabled: {e}")

    def _compute_dataset_hash(self) -> str:
        h = hashlib.sha256()
        with open(self.csv_path, "rb") as f:
            h.update(f.read())
        return h.hexdigest()

    def _faiss_paths(self):
        base = self.cache_dir / self.dataset_hash
        return {
            "index": str(base.with_suffix(".faiss")),
            "svd": str(base.with_suffix(".svd.npy")),
            "meta": str(base.with_suffix(".json")),
        }

    def _build_faiss_index(self):
        vectors = self.svd_matrix.copy().astype("float32")
        faiss.normalize_L2(vectors)
        self.svd_matrix_normalized = vectors

        dim = vectors.shape[1]
        self.faiss_index = faiss.IndexFlatIP(dim)
        self.faiss_index.add(vectors)

    def _save_faiss_index(self):
        paths = self._faiss_paths()
        faiss.write_index(self.faiss_index, paths["index"])
        np.save(paths["svd"], self.svd_matrix_normalized)
        with open(paths["meta"], "w") as f:
            json.dump(
                {
                    "dataset_hash": self.dataset_hash,
                    "rows": int(len(self.df)),
                    "dim": int(self.svd_matrix_normalized.shape[1]),
                },
                f
            )

    def _load_or_build_faiss_index(self):
        paths = self._faiss_paths()

        if (
            os.path.exists(paths["index"]) and
            os.path.exists(paths["svd"]) and
            os.path.exists(paths["meta"])
        ):
            try:
                self.faiss_index = faiss.read_index(paths["index"])
                self.svd_matrix_normalized = np.load(paths["svd"]).astype("float32")
                self.index_status = "loaded"
                return
            except Exception as e:
                print(f"[retrieve] Failed to load cached FAISS index, rebuilding: {e}")

        self._build_faiss_index()
        self._save_faiss_index()
        self.index_status = "rebuilt"

    def _build_doc_embeddings(self) -> np.ndarray:
        texts = self.df["combined_text"].tolist()
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        return np.array([item.embedding for item in response.data], dtype="float32")

    def _embed_query(self, text: str) -> np.ndarray:
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=[text]
        )
        return np.array(response.data[0].embedding, dtype="float32")

    @staticmethod
    def _normalize(scores: np.ndarray) -> np.ndarray:
        if len(scores) == 0:
            return scores
        min_s, max_s = scores.min(), scores.max()
        if abs(max_s - min_s) < 1e-12:
            return np.ones_like(scores) * 0.5
        return (scores - min_s) / (max_s - min_s)

    @staticmethod
    def _confidence_label(score: float) -> str:
        if score >= 0.80:
            return "High"
        if score >= 0.50:
            return "Medium"
        return "Low"

    @staticmethod
    def _safe_contains(series: pd.Series, value: str) -> pd.Series:
        return series.astype(str).str.contains(value, case=False, na=False)

    @staticmethod
    def _tokenize(text: str) -> set:
        return {t for t in str(text).lower().replace("/", " ").replace(",", " ").split() if t.strip()}

    def _build_match_reasons(
        self,
        query_subject: str,
        query_question: str,
        row: pd.Series,
        word_score: float,
        char_score: float,
        svd_score: float,
        faiss_score: float,
        emb_score: float,
        trade: Optional[str],
        spec_section: Optional[str],
        project_name: Optional[str],
    ) -> List[str]:
        reasons: List[str] = []
        query_text = f"{query_subject} {query_question}".strip()
        query_tokens = self._tokenize(query_text)
        row_tokens = self._tokenize(f"{row['subject']} {row['question_text']}")

        overlap = sorted(list(query_tokens.intersection(row_tokens)))[:6]
        if overlap:
            reasons.append(f"Keyword overlap: {', '.join(overlap)}")

        if trade and str(row["trade"]).strip().lower() == trade.strip().lower():
            reasons.append(f"Same trade: {row['trade']}")

        if spec_section and spec_section.lower() in str(row["spec_section"]).lower():
            reasons.append(f"Matched spec section: {row['spec_section']}")

        if project_name and project_name.lower() in str(row["project_name"]).lower():
            reasons.append(f"Matched project: {row['project_name']}")

        if str(row.get("source_file", "")).strip():
            page = str(row.get("source_page", "")).strip()
            if page:
                reasons.append(f"Source citation: {row['source_file']} page {page}")

        if word_score >= 0.65:
            reasons.append("Strong lexical similarity")
        if char_score >= 0.65:
            reasons.append("Strong phrasing similarity")
        if svd_score >= 0.65:
            reasons.append("Strong semantic topic similarity")
        if faiss_score >= 0.65:
            reasons.append("Strong FAISS semantic match")
        if emb_score >= 0.65:
            reasons.append("Strong embedding similarity")

        if not reasons:
            reasons.append("General semantic similarity")

        return reasons

    def _faiss_scores_for_query(self, query: str) -> np.ndarray:
        if self.faiss_index is None or self.svd_matrix_normalized is None:
            return np.zeros(len(self.df), dtype="float32")

        word_query_vec = self.word_vectorizer.transform([query])
        svd_query_vec = self.svd.transform(word_query_vec).astype("float32")
        faiss.normalize_L2(svd_query_vec)

        distances, indices = self.faiss_index.search(svd_query_vec, len(self.df))
        scores = np.zeros(len(self.df), dtype="float32")

        if len(indices) > 0:
            for rank_idx, doc_idx in enumerate(indices[0]):
                if doc_idx >= 0:
                    scores[doc_idx] = distances[0][rank_idx]

        return self._normalize(scores)

    def search(
        self,
        subject: str,
        question_text: str,
        top_k: int = 3,
        trade: Optional[str] = None,
        spec_section: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> Dict:
        query = f"{subject} {question_text}".strip()
        filtered_df = self.df.copy()

        if trade:
            filtered_df = filtered_df[filtered_df["trade"].str.lower() == trade.lower()]
        if spec_section:
            filtered_df = filtered_df[self._safe_contains(filtered_df["spec_section"], spec_section)]
        if project_name:
            filtered_df = filtered_df[self._safe_contains(filtered_df["project_name"], project_name)]

        if filtered_df.empty:
            return {
                "results": [],
                "overall_confidence": "Low",
                "duplicate_warning": None,
                "safeguards": ["No RFIs matched the selected filters."],
                "retrieval_engine": "hybrid-faiss-rerank-cited",
                "index_status": self.index_status,
            }

        idxs = filtered_df.index.tolist()

        word_query_vec = self.word_vectorizer.transform([query])
        word_scores_all = cosine_similarity(word_query_vec, self.word_matrix).flatten()
        word_scores = self._normalize(word_scores_all[idxs])

        char_query_vec = self.char_vectorizer.transform([query])
        char_scores_all = cosine_similarity(char_query_vec, self.char_matrix).flatten()
        char_scores = self._normalize(char_scores_all[idxs])

        svd_query_vec = self.svd.transform(word_query_vec)
        svd_scores_all = cosine_similarity(svd_query_vec, self.svd_matrix).flatten()
        svd_scores = self._normalize(svd_scores_all[idxs])

        faiss_scores_all = self._faiss_scores_for_query(query)
        faiss_scores = faiss_scores_all[idxs]

        emb_scores = np.zeros(len(idxs), dtype="float32")
        if self.doc_embeddings is not None and self.client is not None:
            try:
                q_emb = self._embed_query(query)
                emb_all = np.dot(self.doc_embeddings, q_emb) / (
                    np.linalg.norm(self.doc_embeddings, axis=1) * np.linalg.norm(q_emb) + 1e-12
                )
                emb_scores = self._normalize(emb_all[idxs])
            except Exception as e:
                print(f"[retrieve] embedding query failed: {e}")

        candidate_scores = (
            0.32 * word_scores +
            0.10 * char_scores +
            0.18 * svd_scores +
            0.25 * faiss_scores +
            0.15 * emb_scores
        )

        candidate_k = min(max(top_k * 5, 10), len(filtered_df))
        ranked_candidate_positions = np.argsort(candidate_scores)[::-1][:candidate_k]

        candidates: List[Dict] = []
        for i in ranked_candidate_positions:
            row = filtered_df.iloc[i]
            score = float(candidate_scores[i])

            word_score = float(word_scores[i])
            char_score = float(char_scores[i])
            svd_score = float(svd_scores[i])
            faiss_score = float(faiss_scores[i])
            emb_score = float(emb_scores[i]) if len(emb_scores) else 0.0

            spec_boost = 0.0
            if spec_section and spec_section.lower() in str(row["spec_section"]).lower():
                spec_boost = 0.08
                score = min(1.0, score + spec_boost)

            source_file = str(row.get("source_file", "")).strip()
            source_page = str(row.get("source_page", "")).strip()
            source_chunk = str(row.get("source_chunk", "")).strip()

            candidates.append({
                "rfi_id": row["rfi_id"],
                "project_name": row["project_name"],
                "subject": row["subject"],
                "question_text": row["question_text"],
                "response_text": row["response_text"],
                "trade": row["trade"],
                "spec_section": row["spec_section"],
                "source_type": row.get("source_type", ""),
                "source_file": source_file,
                "source_page": source_page,
                "source_chunk": source_chunk,
                "source_citation": (
                    f"{source_file} | page {source_page} | chunk {source_chunk}"
                    if source_file and source_page else ""
                ),
                "similarity_score": round(score, 4),
                "confidence": self._confidence_label(score),
                "score_breakdown": {
                    "word_tfidf": round(word_score, 4),
                    "char_tfidf": round(char_score, 4),
                    "svd_semantic": round(svd_score, 4),
                    "faiss_semantic": round(faiss_score, 4),
                    "embedding": round(emb_score, 4),
                    "spec_boost": round(spec_boost, 4),
                },
                "match_reasons": self._build_match_reasons(
                    query_subject=subject,
                    query_question=question_text,
                    row=row,
                    word_score=word_score,
                    char_score=char_score,
                    svd_score=svd_score,
                    faiss_score=faiss_score,
                    emb_score=emb_score,
                    trade=trade,
                    spec_section=spec_section,
                    project_name=project_name,
                ),
            })

        reranked = rerank_results(
            subject=subject,
            question_text=question_text,
            candidates=candidates,
            trade=trade,
            spec_section=spec_section,
            project_name=project_name,
        )

        results = reranked[:top_k]

        for item in results:
            item["confidence"] = self._confidence_label(float(item.get("similarity_score", 0.0)))

        max_score = max((float(r["similarity_score"]) for r in results), default=0.0)
        safeguards: List[str] = []

        if max_score < 0.50:
            safeguards.append("Low-confidence retrieval after reranking. Manual review is strongly recommended.")
        elif max_score < 0.80:
            safeguards.append("Moderate-confidence retrieval after reranking. Verify project-specific details before issuance.")

        if not trade:
            safeguards.append("No trade filter applied.")
        if not spec_section:
            safeguards.append("No spec section filter applied.")
        if not project_name:
            safeguards.append("No project filter applied.")

        duplicate_warning = None
        if max_score >= 0.92 and results:
            duplicate_warning = (
                f"Possible duplicate RFI detected. Closest historical match: "
                f"RFI {results[0]['rfi_id']} ({results[0]['subject']})."
            )

        return {
            "results": results,
            "overall_confidence": self._confidence_label(max_score),
            "duplicate_warning": duplicate_warning,
            "safeguards": safeguards,
            "retrieval_engine": "hybrid-faiss-rerank-cited",
            "index_status": self.index_status,
            "candidate_count": len(candidates),
        }
