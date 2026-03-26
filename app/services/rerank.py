from copy import deepcopy
from functools import lru_cache
from typing import Dict, List, Optional

import numpy as np


@lru_cache(maxsize=1)
def get_cross_encoder():
    try:
        from sentence_transformers import CrossEncoder
        return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    except Exception as e:
        print(f"[rerank] Cross-encoder unavailable, using heuristic rerank only: {e}")
        return None


def _tokenize(text: str) -> set:
    return {t for t in str(text).lower().replace("/", " ").replace(",", " ").split() if t.strip()}


def _jaccard(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


def rerank_results(
    subject: str,
    question_text: str,
    candidates: List[Dict],
    trade: Optional[str] = None,
    spec_section: Optional[str] = None,
    project_name: Optional[str] = None,
) -> List[Dict]:
    if not candidates:
        return []

    query = f"{subject} {question_text}".strip()
    encoder = get_cross_encoder()

    cross_scores = None
    if encoder is not None:
        try:
            pairs = [(query, f"{c.get('subject', '')} {c.get('question_text', '')} {c.get('response_text', '')}") for c in candidates]
            raw_scores = encoder.predict(pairs)
            raw_scores = np.array(raw_scores, dtype="float32")
            min_s = float(raw_scores.min())
            max_s = float(raw_scores.max())
            if abs(max_s - min_s) < 1e-12:
                cross_scores = np.ones_like(raw_scores) * 0.5
            else:
                cross_scores = (raw_scores - min_s) / (max_s - min_s)
        except Exception as e:
            print(f"[rerank] Cross-encoder prediction failed, using heuristic only: {e}")
            cross_scores = None

    reranked = []
    for idx, item in enumerate(candidates):
        new_item = deepcopy(item)

        doc_text = f"{item.get('subject', '')} {item.get('question_text', '')} {item.get('response_text', '')}".strip()
        base_score = float(item.get("similarity_score", 0.0))
        jaccard_score = _jaccard(query, doc_text)

        phrase_bonus = 0.0
        exact_spec_bonus = 0.0
        exact_project_bonus = 0.0
        exact_trade_bonus = 0.0

        query_lower = query.lower()
        if subject and subject.lower() in doc_text.lower():
            phrase_bonus += 0.03
        if question_text and len(question_text.strip()) > 12 and question_text.lower()[:30] in doc_text.lower():
            phrase_bonus += 0.03

        if trade and str(item.get("trade", "")).strip().lower() == trade.strip().lower():
            exact_trade_bonus = 0.04
        if spec_section and spec_section.strip().lower() in str(item.get("spec_section", "")).strip().lower():
            exact_spec_bonus = 0.05
        if project_name and project_name.strip().lower() in str(item.get("project_name", "")).strip().lower():
            exact_project_bonus = 0.05

        heuristic_score = (
            0.72 * base_score
            + 0.18 * jaccard_score
            + phrase_bonus
            + exact_spec_bonus
            + exact_project_bonus
            + exact_trade_bonus
        )

        if cross_scores is not None:
            cross_score = float(cross_scores[idx])
            final_score = 0.55 * heuristic_score + 0.45 * cross_score
        else:
            cross_score = None
            final_score = heuristic_score

        final_score = max(0.0, min(1.0, final_score))

        score_breakdown = dict(new_item.get("score_breakdown", {}))
        score_breakdown.update({
            "rerank_jaccard": round(jaccard_score, 4),
            "rerank_phrase_bonus": round(phrase_bonus, 4),
            "rerank_trade_bonus": round(exact_trade_bonus, 4),
            "rerank_spec_bonus": round(exact_spec_bonus, 4),
            "rerank_project_bonus": round(exact_project_bonus, 4),
        })
        if cross_score is not None:
            score_breakdown["cross_encoder"] = round(cross_score, 4)

        match_reasons = list(new_item.get("match_reasons", []))
        if cross_score is not None and cross_score >= 0.65:
            match_reasons.append("Learned reranker found strong query-document relevance")
        if jaccard_score >= 0.20:
            match_reasons.append("Reranker found meaningful token overlap")
        if phrase_bonus > 0:
            match_reasons.append("Reranker boosted phrase overlap")
        if exact_spec_bonus > 0:
            match_reasons.append("Reranker boosted exact spec-section match")
        if exact_project_bonus > 0:
            match_reasons.append("Reranker boosted exact project match")
        if exact_trade_bonus > 0:
            match_reasons.append("Reranker boosted exact trade match")

        deduped = []
        seen = set()
        for reason in match_reasons:
            if reason not in seen:
                seen.add(reason)
                deduped.append(reason)

        new_item["pre_rerank_score"] = round(base_score, 4)
        new_item["similarity_score"] = round(final_score, 4)
        new_item["score_breakdown"] = score_breakdown
        new_item["match_reasons"] = deduped
        reranked.append(new_item)

    reranked.sort(key=lambda x: x.get("similarity_score", 0.0), reverse=True)
    return reranked
