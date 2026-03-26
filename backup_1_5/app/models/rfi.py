from typing import Optional, Literal
from pydantic import BaseModel


class RFIQuery(BaseModel):
    subject: str
    question_text: str
    top_k: int = 3
    trade: Optional[str] = None
    spec_section: Optional[str] = None
    project_name: Optional[str] = None
    use_ai: bool = False


class FeedbackPayload(BaseModel):
    subject: str
    question_text: str
    generated_draft: str
    final_draft: Optional[str] = None
    action: Literal["accepted", "edited", "rejected"]
    overall_confidence: Optional[str] = None
    duplicate_warning: Optional[str] = None
    trade: Optional[str] = None
    spec_section: Optional[str] = None
    project_name: Optional[str] = None
