from typing import Dict, List


def build_structured_context(similar_rfis: List[Dict], safeguards: List[str]) -> Dict:
    if not similar_rfis:
        return {
            "top_answer": "No strong historical RFIs were found.",
            "supporting_evidence": [],
            "conflicts": [],
            "safeguards": safeguards or ["Manual review is required."],
            "context_text": (
                "Top Answer:\n"
                "No strong historical RFIs were found.\n\n"
                "Supporting Evidence:\n"
                "- None\n\n"
                "Conflicts:\n"
                "- None\n\n"
                "Safeguards:\n"
                + "\n".join(f"- {s}" for s in (safeguards or ["Manual review is required."]))
            ),
        }

    top = similar_rfis[0]
    supporting = []
    conflicts = []

    top_trade = str(top.get("trade", "")).strip().lower()
    top_spec = str(top.get("spec_section", "")).strip().lower()

    for rfi in similar_rfis[:5]:
        summary = {
            "rfi_id": rfi.get("rfi_id", ""),
            "subject": rfi.get("subject", ""),
            "response_text": rfi.get("response_text", ""),
            "score": rfi.get("similarity_score", 0),
            "citation": rfi.get("source_citation", ""),
            "reasons": rfi.get("match_reasons", []),
        }
        supporting.append(summary)

        trade = str(rfi.get("trade", "")).strip().lower()
        spec = str(rfi.get("spec_section", "")).strip().lower()
        if (top_trade and trade and trade != top_trade) or (top_spec and spec and spec != top_spec):
            conflicts.append(
                f"RFI {rfi.get('rfi_id', '')} differs in trade/spec context "
                f"({rfi.get('trade', '')} / {rfi.get('spec_section', '')})."
            )

    supporting_lines = []
    for item in supporting:
        reasons = "; ".join(item["reasons"][:3]) if item["reasons"] else "semantic match"
        citation = f" | {item['citation']}" if item["citation"] else ""
        supporting_lines.append(
            f"- RFI {item['rfi_id']} | {item['subject']} | score={item['score']}{citation} | reasons: {reasons}"
        )

    conflict_lines = conflicts if conflicts else ["None"]
    safeguard_lines = safeguards if safeguards else ["Verify project-specific dimensions and approvals before issuance."]

    context_text = (
        "Top Answer:\n"
        f"{top.get('response_text', '').strip()}\n\n"
        "Supporting Evidence:\n"
        + "\n".join(supporting_lines)
        + "\n\nConflicts:\n"
        + "\n".join(f"- {x}" for x in conflict_lines)
        + "\n\nSafeguards:\n"
        + "\n".join(f"- {x}" for x in safeguard_lines)
    )

    return {
        "top_answer": top.get("response_text", "").strip(),
        "supporting_evidence": supporting,
        "conflicts": conflicts,
        "safeguards": safeguard_lines,
        "context_text": context_text,
    }
