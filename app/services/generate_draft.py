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
            "Unable to draft a response because no similar historical RFIs were found. "
            "Please review manually and provide project-specific direction."
        )

    best = similar_rfis[0]

    return (
        "Suggested draft response:\n\n"
        f"{best['response_text']}\n\n"
        "Basis used:\n"
        f"- Similar RFI: {best['subject']}\n"
        f"- Trade: {best['trade']}\n"
        f"- Spec Section: {best['spec_section']}\n\n"
        "Human review required before issuance."
    )


def generate_llm_draft(new_subject: str, new_question: str, similar_rfis: List[Dict], safeguards: List[str]) -> str:
    use_openai_drafts = os.getenv("USE_OPENAI_DRAFTS", "false").lower() == "true"
    api_key_present = bool(os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    if not use_openai_drafts or not api_key_present or OpenAI is None:
        return generate_rule_based_draft(new_subject, new_question, similar_rfis)

    if not similar_rfis:
        return (
            "No strong historical RFIs were retrieved. More project-specific review is required "
            "before drafting a response."
        )

    client = OpenAI()

    context_blocks = []
    for i, rfi in enumerate(similar_rfis, start=1):
        context_blocks.append(
            f"Example RFI {i}\n"
            f"RFI ID: {rfi['rfi_id']}\n"
            f"Project: {rfi['project_name']}\n"
            f"Trade: {rfi['trade']}\n"
            f"Spec Section: {rfi['spec_section']}\n"
            f"Subject: {rfi['subject']}\n"
            f"Question: {rfi['question_text']}\n"
            f"Response: {rfi['response_text']}\n"
            f"Similarity Score: {rfi['similarity_score']}\n"
        )

    system_prompt = (
        "You are assisting with draft construction RFI responses.\n"
        "Write a professional, concise draft response.\n"
        "Use only the retrieved historical RFIs as support.\n"
        "Do not invent drawing references, dimensions, approvals, or code requirements.\n"
        "If context is weak, say that additional project-specific review is required.\n"
        "End with a short note reminding the user to verify before issuance."
    )

    user_prompt = (
        f"New RFI Subject: {new_subject}\n"
        f"New RFI Question: {new_question}\n\n"
        "Retrieved historical RFIs:\n\n"
        + "\n---\n".join(context_blocks)
        + "\n\nSafeguards:\n- "
        + "\n- ".join(safeguards)
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
