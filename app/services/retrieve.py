import os
from typing import List, Dict, Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()


def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


class RFIRetriever:
    def __init__(self, csv_path: str = "data/raw/rfis.csv"):
        self.df = pd.read_csv(csv_path)

        for col in ["subject", "question_text", "response_text", "trade", "spec_section", "project_name"]:
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
        )

        # ===== WORD TF-IDF =====
        self.word_vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1
        )
        self.word_matrix = self.word_vectorizer.fit_transform(self.df["combined_text"])

        # ===== CHAR TF-IDF =====
        self.char_vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=1
        )
        self.char_matrix = self.char_vectorizer.fit_transform(self.df["combined_text"])

        # ===== SVD (Latent Semantic Analysis) =====
        n_components = min(50, self.word_matrix.shape[1] - 1) if self.word_matrix.shape[1] > 1 else 1
        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        self.svd_matrix = self.svd.fit_transform(self.word_matrix)

        # ===== OpenAI Embeddings (optional) =====
        self.use_openai_embeddings = os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true"
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.client = None
        self.doc_embeddings = None

        if self.use_openai_embeddings and OpenAI is not None and os.getenv("OPENAI_API_KEY"):
            try:
                self.client = OpenAI()
                self.doc_embeddings = self._build_doc_embeddings()
            except Exception as e:
                print(f"[retrieve] Embeddings disabled: {e}")

    def _build_doc_embeddings(self):
        texts = self.df["combined_text"].tolist()
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        return np.array([r.embedding for r in response.data])

    def _embed_query(self, text):
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=[text]
        )
        return np.array(response.data[0].embedding)

    def _normalize(self, scores):
        if len(scores) == 0:
            return scores
        min_s, max_s = scores.min(), scores.max()
        if abs(max_s - min_s) < 1e-12:
            return np.ones_like(scores) * 0.5
        return (scores - min_s) / (max_s - min_s)

    def _confidence_label(self, score):
        if score >= 0.72:
            return "High"
        if score >= 0.45:
            return "Medium"
        return "Low"

    def search(self, subject, question_text, top_k=3,
               trade=None, spec_section=None, project_name=None):

        query = f"{subject} {question_text}".strip()
        filtered_df = self.df.copy()

        if trade:
            filtered_df = filtered_df[filtered_df["trade"].str.lower() == trade.lower()]
        if spec_section:
            filtered_df = filtered_df[filtered_df["spec_section"].str.contains(spec_section, case=False)]
        if project_name:
            filtered_df = filtered_df[filtered_df["project_name"].str.contains(project_name, case=False)]

        if filtered_df.empty:
            return {"results": [], "overall_confidence": "Low"}

        idxs = filtered_df.index.tolist()

        # ===== WORD TF-IDF =====
        word_query_vec = self.word_vectorizer.transform([query])
        word_scores = cosine_similarity(word_query_vec, self.word_matrix).flatten()[idxs]

        # ===== CHAR TF-IDF =====
        char_query_vec = self.char_vectorizer.transform([query])
        char_scores = cosine_similarity(char_query_vec, self.char_matrix).flatten()[idxs]

        # ===== SVD =====
        svd_query_vec = self.svd.transform(word_query_vec)
        svd_scores = cosine_similarity(svd_query_vec, self.svd_matrix).flatten()[idxs]

        # Normalize
        word_scores = self._normalize(word_scores)
        char_scores = self._normalize(char_scores)
        svd_scores = self._normalize(svd_scores)

        # ===== Embeddings =====
        emb_scores = np.zeros(len(idxs))
        if self.doc_embeddings is not None:
            try:
                q_emb = self._embed_query(query)
                emb_all = np.dot(self.doc_embeddings, q_emb) / (
                    np.linalg.norm(self.doc_embeddings, axis=1) * np.linalg.norm(q_emb) + 1e-12
                )
                emb_scores = self._normalize(emb_all[idxs])
            except Exception as e:
                print("[retrieve] embedding failed", e)

        # ===== Final Score =====
        final_scores = (
            0.35 * word_scores +
            0.10 * char_scores +
            0.25 * svd_scores +
            0.20 * emb_scores
        )

        ranked = np.argsort(final_scores)[::-1][:top_k]
        results = []

        for i in ranked:
            row = filtered_df.iloc[i]
            score = float(final_scores[i])
            results.append({
                "rfi_id": int(row["rfi_id"]),
                "subject": row["subject"],
                "question_text": row["question_text"],
                "response_text": row["response_text"],
                "trade": row["trade"],
                "spec_section": row["spec_section"],
                "similarity_score": round(score, 4),
                "confidence": self._confidence_label(score),
            })

        return {
            "results": results,
            "overall_confidence": self._confidence_label(max(final_scores))
        }
