from typing import List


def expand_query(subject: str, question_text: str) -> List[str]:
    base = f"{subject} {question_text}".strip()
    text = base.lower()

    expansions = [base]

    replacements = {
        "rfi": ["request for information"],
        "conduit": ["electrical conduit", "routing conduit"],
        "clearance": ["required clearance", "minimum clearance"],
        "door frame": ["frame opening", "door jamb"],
        "hvac": ["mechanical", "ductwork"],
        "plumbing": ["pipe routing", "piping"],
        "electrical": ["power", "electrical work"],
        "spec": ["specification", "spec section"],
        "drawing": ["plan", "detail"],
    }

    for key, values in replacements.items():
        if key in text:
            for value in values:
                expansions.append(f"{subject} {question_text} {value}".strip())

    if "where" in text or "location" in text or "placement" in text:
        expansions.append(f"{base} location placement routing")
    if "can" in text or "should" in text or "approve" in text:
        expansions.append(f"{base} approval acceptability")
    if "spec" in text or "drawing" in text or "sheet" in text:
        expansions.append(f"{base} specification drawing detail section")

    deduped = []
    seen = set()
    for q in expansions:
        normalized = " ".join(q.split()).lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(" ".join(q.split()))

    return deduped[:6]
