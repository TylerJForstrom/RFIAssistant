from typing import Dict, List


def detect_query_intent(subject: str, question_text: str) -> Dict:
    text = f"{subject} {question_text}".lower().strip()

    rules = [
        ("location", ["where", "located", "location", "place", "placement", "route", "routing"]),
        ("decision", ["can ", "should ", "approve", "acceptable", "allowed", "permit", "use ", "proceed"]),
        ("clarification", ["clarify", "confirm", "interpret", "meaning", "intent", "explain"]),
        ("coordination", ["coordinate", "coordination", "conflict", "interference", "clearance", "offset"]),
        ("spec", ["spec", "section", "submittal", "detail", "drawing", "sheet", "plan", "elevation"]),
    ]

    matched = []
    for label, keywords in rules:
        if any(k in text for k in keywords):
            matched.append(label)

    if "location" in matched:
        intent = "location"
    elif "decision" in matched:
        intent = "decision"
    elif "coordination" in matched:
        intent = "coordination"
    elif "spec" in matched:
        intent = "spec"
    elif "clarification" in matched:
        intent = "clarification"
    else:
        intent = "general"

    retrieval_weights = {
        "word": 0.28,
        "char": 0.10,
        "svd": 0.17,
        "faiss": 0.25,
        "embedding": 0.20,
    }

    if intent == "location":
        retrieval_weights.update({"word": 0.25, "char": 0.12, "svd": 0.16, "faiss": 0.22, "embedding": 0.25})
    elif intent == "decision":
        retrieval_weights.update({"word": 0.24, "char": 0.08, "svd": 0.18, "faiss": 0.22, "embedding": 0.28})
    elif intent == "coordination":
        retrieval_weights.update({"word": 0.27, "char": 0.10, "svd": 0.18, "faiss": 0.22, "embedding": 0.23})
    elif intent == "spec":
        retrieval_weights.update({"word": 0.33, "char": 0.12, "svd": 0.16, "faiss": 0.22, "embedding": 0.17})

    return {
        "intent": intent,
        "matched_labels": matched or ["general"],
        "retrieval_weights": retrieval_weights,
    }
