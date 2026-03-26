import os
from typing import List, Dict
from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()


def generate_rule_based_draft(new_subject: str, new_question: str, similar_rfis: List[Dict]) -> str:
    if not similar_rfis:
        return (
            "Suggested Response:\n"
            "No strong historical RFIs were found. Additional project-specific review is required.\n\n"
            "Basis:\n"
            "- No comparable RFIs retrieved\n\n"
            "Confidence:\n"
            "- Low\n\n"
            "Notes:\n"
            "- Human review required before issuance."
        )

    best = similar_rfis[0]
    basis_lines = [
        f"- Similar RFI ID: {best.get('rfi_id', 'N/A')}",
        f"- Subject: {best.get('subject', '')}",
        f"- Trade: {best.get('trade', '')}",
        f"- Spec Section: {best.get('spec_section', '')}",
        f"- Similarity Score: {best.get('similarity_score', '')}",
    ]

    for reason in best.get("match_reasons", []):
        basis_lines.append(f"- {reason}")

    return (
        "Suggested Response:\n"
        f"{best.get('response_text', '').strip()}\n\n"
        "Basis:\n"
        + "\n".join(basis_lines)
        + "\n\nConfidence:\n"
        f"- {best.get('confidence', 'Low')}\n\n"
        "Notes:\n"
        "- Verify project-specific dimensions, drawing references, and approvals before issuance."
    )


def generate_llm_draft(
    new_subject: str,
    new_question: str,
    similar_rfis: List[Dict],
    safeguards: List[str],
    use_ai: bool = False,
) -> str:
    env_allows_ai = os.getenv("USE_OPENAI_DRAFTS", "false").lower() == "true"
    api_key_present = bool(os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    should_use_ai = use_ai and env_allows_ai and api_key_present and OpenAI is not None

    if not should_use_ai:
        return generate_rule_based_draft(new_subject, new_question, similar_rfis)

    if not similar_rfis:
        return generate_rule_based_draft(new_subject, new_question, similar_rfis)

    client = OpenAI()

    context_blocks = []
    for i, rfi in enumerate(similar_rfis, start=1):
        reasons = "\n".join(f"- {x}" for x in rfi.get("match_reasons", []))
        context_blocks.append(
            f"Example RFI {i}\n"
            f"RFI ID: {rfi.get('rfi_id', '')}\n"
            f"Project: {rfi.get('project_name', '')}\n"
            f"Trade: {rfi.get('trade', '')}\n"
            f"Spec Section: {rfi.get('spec_section', '')}\n"
            f"Subject: {rfi.get('subject', '')}\n"
            f"Question: {rfi.get('question_text', '')}\n"
            f"Response: {rfi.get('response_text', '')}\n"
            f"Similarity Score: {rfi.get('similarity_score', '')}\n"
            f"Confidence: {rfi.get('confidence', '')}\n"
            f"Match Reasons:\n{reasons}\n"
        )

    system_prompt = (
        "You are assisting with draft construction RFI responses.\n"
        "Use only the retrieved historical RFIs as support.\n"
        "Do not invent dimensions, approvals, code requirements, drawing references, or commitments.\n"
        "Do not introduce new facts that are not supported by the retrieved RFIs.\n"
        "If the retrieved context is weak, say that more project-specific review is required.\n"
        "Return the response in exactly this format:\n\n"
        "Suggested Response:\n"
        "<draft>\n\n"
        "Basis:\n"
        "- <bullet 1>\n"
        "- <bullet 2>\n\n"
        "Confidence:\n"
        "- <High/Medium/Low>\n\n"
        "Notes:\n"
        "- <verification reminder>\n"
    )

    safeguard_text = "\n".join(f"- {s}" for s in safeguards) if safeguards else "- None"

    user_prompt = (
        f"New RFI Subject: {new_subject}\n"
        f"New RFI Question: {new_question}\n\n"
        "Retrieved historical RFIs:\n\n"
        + "\n---\n".join(context_blocks)
        + "\n\nSafeguards:\n"
        + safeguard_text
    )

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[generate_draft] OpenAI draft failed, using fallback: {e}")
        return generate_rule_based_draft(new_subject, new_question, similar_rfis)
