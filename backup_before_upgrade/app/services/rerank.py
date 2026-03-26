from typing import List, Dict
import math


def _tokenize(text: str) -> set:
    text = (text or "").lower()
    for ch in [",", ".", ";", ":", "(", ")", "/", "-", "_", "\n", "\t"]:
        text = text.replace(ch, " ")
    return {tok for tok in text.split() if tok.strip()}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _contains_phrase_bonus(query_text: str, doc_text: str) -> float:
    q = (query_text or "").lower().strip()
    d = (doc_text or "").lower()
    if not q or not d:
        return 0.0

    bonus = 0.0

    words = [w for w in q.split() if len(w) >= 4]
    if len(words) >= 2:
        phrase = " ".join(words[:2])
        if phrase in d:
            bonus += 0.08

    if q[:80] and q[:80] in d:
        bonus += 0.12

    return min(bonus, 0.12)


def _length_balance_bonus(query_text: str, doc_text: str) -> float:
    q_len = max(len((query_text or "").split()), 1)
    d_len = max(len((doc_text or "").split()), 1)
    ratio = min(q_len, d_len) / max(q_len, d_len)
    return 0.05 * ratio


def rerank_results(
    subject: str,
    question_text: str,
    candidates: List[Dict],
    trade: str = None,
    spec_section: str = None,
    project_name: str = None,
) -> List[Dict]:
    query_text = f"{subject or ''} {question_text or ''}".strip()
    query_tokens = _tokenize(query_text)

    reranked = []

    for item in candidates:
        doc_text = f"{item.get('subject', '')} {item.get('question_text', '')} {item.get('response_text', '')}".strip()
        doc_tokens = _tokenize(doc_text)

        base_score = float(item.get("similarity_score", 0.0))
        jaccard_score = _jaccard(query_tokens, doc_tokens)
        phrase_bonus = _contains_phrase_bonus(query_text, doc_text)
        length_bonus = _length_balance_bonus(query_text, doc_text)

        exact_trade_bonus = 0.0
        exact_spec_bonus = 0.0
        exact_project_bonus = 0.0

        if trade and str(item.get("trade", "")).strip().lower() == str(trade).strip().lower():
            exact_trade_bonus = 0.06

        if spec_section and str(spec_section).strip().lower() in str(item.get("spec_section", "")).strip().lower():
            exact_spec_bonus = 0.10

        if project_name and str(project_name).strip().lower() in str(item.get("project_name", "")).strip().lower():
            exact_project_bonus = 0.08

        rerank_bonus = (
            0.18 * jaccard_score +
            phrase_bonus +
            length_bonus +
            exact_trade_bonus +
            exact_spec_bonus +
            exact_project_bonus
        )

        reranked_score = min(1.0, base_score + rerank_bonus)

        score_breakdown = dict(item.get("score_breakdown", {}))
        score_breakdown["rerank_jaccard"] = round(jaccard_score, 4)
        score_breakdown["rerank_phrase_bonus"] = round(phrase_bonus, 4)
        score_breakdown["rerank_length_bonus"] = round(length_bonus, 4)
        score_breakdown["rerank_trade_bonus"] = round(exact_trade_bonus, 4)
        score_breakdown["rerank_spec_bonus"] = round(exact_spec_bonus, 4)
        score_breakdown["rerank_project_bonus"] = round(exact_project_bonus, 4)
        score_breakdown["rerank_total_bonus"] = round(rerank_bonus, 4)

        new_item = dict(item)
        new_item["pre_rerank_score"] = round(base_score, 4)
        new_item["similarity_score"] = round(reranked_score, 4)
        new_item["score_breakdown"] = score_breakdown

        match_reasons = list(new_item.get("match_reasons", []))
        if jaccard_score >= 0.20:
            match_reasons.append("Strong token overlap after reranking")
        if phrase_bonus > 0:
            match_reasons.append("Important query phrase appears in retrieved text")
        if exact_spec_bonus > 0:
            match_reasons.append("Reranker boosted exact spec-section match")
        if exact_project_bonus > 0:
            match_reasons.append("Reranker boosted exact project match")
        if exact_trade_bonus > 0:
            match_reasons.append("Reranker boosted exact trade match")

        seen = set()
        deduped = []
        for reason in match_reasons:
            if reason not in seen:
                seen.add(reason)
                deduped.append(reason)

        new_item["match_reasons"] = deduped
        reranked.append(new_item)

    reranked.sort(key=lambda x: x.get("similarity_score", 0.0), reverse=True)
    return reranked
