import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Smart RFI Assistant", layout="centered")

st.title("Smart RFI Assistant")
st.write("Ask a question and get a draft response based on past RFIs.")


def safe_get(url):
    try:
        response = requests.get(url, timeout=3)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def safe_post(url, payload):
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


health = safe_get(f"{API_URL}/health")

if not health:
    st.info("Backend is starting up. Wait a few seconds and refresh if needed.")
    st.stop()

filters = safe_get(f"{API_URL}/filters") or {"trades": [], "projects": [], "spec_sections": []}
dataset_info = safe_get(f"{API_URL}/dataset-info") or {}
feedback_summary = safe_get(f"{API_URL}/feedback-summary") or {}

if dataset_info:
    st.caption(f"Loaded RFIs: {dataset_info.get('row_count', 0)}")

st.caption(
    f"Retrieval engine: {health.get('retrieval_engine', 'intent-aware-hybrid-faiss-rerank')} | "
    f"Index: {health.get('index_status', 'unknown')}"
)

if feedback_summary:
    st.caption(
        f"Saved feedback: {feedback_summary.get('total_feedback', 0)} | "
        f"Reviewed drafts saved: {feedback_summary.get('reviewed_rfis_count', 0)}"
    )

with st.expander("Add data"):
    uploaded_csv = st.file_uploader("Upload RFI CSV", type=["csv"])
    if uploaded_csv is not None:
        if st.button("Upload CSV"):
            try:
                files = {"file": (uploaded_csv.name, uploaded_csv.getvalue(), "text/csv")}
                response = requests.post(f"{API_URL}/upload-csv", files=files, timeout=30)
                response.raise_for_status()
                data = response.json()
                st.success(f"CSV uploaded. Rows: {data.get('row_count', 0)}")
                st.rerun()
            except Exception as e:
                st.error(f"CSV upload failed: {e}")

    uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"])
    if uploaded_pdf is not None:
        if st.button("Upload PDF"):
            try:
                files = {"file": (uploaded_pdf.name, uploaded_pdf.getvalue(), "application/pdf")}
                response = requests.post(f"{API_URL}/upload-pdf", files=files, timeout=60)
                response.raise_for_status()
                data = response.json()
                st.success(
                    f"PDF processed. Parsed: {data.get('parsed_rows', 0)} | Added: {data.get('added_rows', 0)}"
                )
                st.rerun()
            except Exception as e:
                st.error(f"PDF upload failed: {e}")

    if st.button("Sync Approved Drafts Into Search Dataset"):
        data = safe_post(f"{API_URL}/sync-reviewed-rfis", {})
        if data:
            st.success(f"Synced. Added rows: {data.get('added_rows', 0)}")
            st.rerun()

subject = st.text_input("Subject", placeholder="Example: Door frame clearance")
question_text = st.text_area(
    "Question",
    placeholder="Type the RFI question here...",
    height=140
)

trade_options = ["Any"] + filters.get("trades", [])
project_options = ["Any"] + filters.get("projects", [])
spec_options = ["Any"] + filters.get("spec_sections", [])

st.subheader("Optional filters")
trade = st.selectbox("Trade", trade_options)
project_name = st.selectbox("Project", project_options)
spec_section = st.selectbox("Spec Section", spec_options)
top_k = st.slider("Number of final matches", min_value=1, max_value=5, value=3)

ai_available = bool(health.get("ai_available", False))
use_ai = st.checkbox("Use AI drafting", value=False, disabled=not ai_available)

if not ai_available:
    st.caption("AI drafting is currently unavailable. Standard drafting will be used.")

payload = {
    "subject": subject.strip(),
    "question_text": question_text.strip(),
    "top_k": top_k,
    "trade": None if trade == "Any" else trade,
    "project_name": None if project_name == "Any" else project_name,
    "spec_section": None if spec_section == "Any" else spec_section,
    "use_ai": bool(use_ai and ai_available),
}

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None

if "latest_payload" not in st.session_state:
    st.session_state.latest_payload = None

if st.button("Generate Draft Response", use_container_width=True):
    if not payload["subject"] or not payload["question_text"]:
        st.warning("Please fill in both Subject and Question.")
    else:
        result = safe_post(f"{API_URL}/generate", payload)
        if result:
            st.session_state.latest_result = result
            st.session_state.latest_payload = payload

result = st.session_state.latest_result
saved_payload = st.session_state.latest_payload

if result and saved_payload:
    st.divider()
    st.subheader("Draft Response")

    mode = "AI" if result.get("used_ai") else "Standard"
    engine = result.get("retrieval_engine", "intent-aware-hybrid-faiss-rerank")
    index_status = result.get("index_status", "unknown")
    st.caption(f"Draft mode: {mode} | Retrieval engine: {engine} | Index: {index_status}")

    edited_draft = st.text_area(
        "Generated Draft",
        value=result.get("draft_response", ""),
        height=260,
        key="edited_draft"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Confidence Label", result.get("overall_confidence", "Low"))
    with col2:
        st.metric("Confidence Score", f"{result.get('confidence_score', 0.0)}%")
    with col3:
        st.metric("Final Matches", result.get("retrieval_count", 0))

    col4, col5 = st.columns(2)
    with col4:
        st.metric("Candidates Reranked", result.get("candidate_count", 0))
    with col5:
        st.metric("Intent", result.get("query_intent", "general").title())

    duplicate_warning = result.get("duplicate_warning")
    if duplicate_warning:
        st.warning(duplicate_warning)

    safeguards = result.get("safeguards", [])
    if safeguards:
        st.subheader("Review Notes")
        for item in safeguards:
            st.write(f"- {item}")

    expanded_queries = result.get("expanded_queries", [])
    if expanded_queries:
        with st.expander("Expanded Queries Used"):
            for q in expanded_queries:
                st.write(f"- {q}")

    structured_context = result.get("structured_context", {})
    if structured_context:
        with st.expander("Structured Context Used for Drafting"):
            st.write("**Top Answer**")
            st.write(structured_context.get("top_answer", ""))

            evidence = structured_context.get("supporting_evidence", [])
            if evidence:
                st.write("**Supporting Evidence**")
                for item in evidence:
                    st.write(
                        f"- RFI {item.get('rfi_id', '')} | {item.get('subject', '')} | "
                        f"score={item.get('score', '')}"
                    )

            conflicts = structured_context.get("conflicts", [])
            if conflicts:
                st.write("**Potential Conflicts**")
                for item in conflicts:
                    st.write(f"- {item}")

    st.subheader("Save Review")
    c1, c2, c3 = st.columns(3)

    feedback_base = {
        "subject": saved_payload["subject"],
        "question_text": saved_payload["question_text"],
        "generated_draft": result.get("draft_response", ""),
        "final_draft": edited_draft,
        "overall_confidence": result.get("overall_confidence"),
        "duplicate_warning": result.get("duplicate_warning"),
        "trade": saved_payload["trade"],
        "spec_section": saved_payload["spec_section"],
        "project_name": saved_payload["project_name"],
    }

    with c1:
        if st.button("Accept"):
            data = dict(feedback_base)
            data["action"] = "accepted"
            resp = safe_post(f"{API_URL}/feedback", data)
            if resp:
                st.success(f"Accepted and saved. Added to dataset: {resp.get('added_to_dataset', 0)}")

    with c2:
        if st.button("Save Edited"):
            data = dict(feedback_base)
            data["action"] = "edited"
            resp = safe_post(f"{API_URL}/feedback", data)
            if resp:
                st.success(f"Edited draft saved. Added to dataset: {resp.get('added_to_dataset', 0)}")

    with c3:
        if st.button("Reject"):
            data = dict(feedback_base)
            data["action"] = "rejected"
            resp = safe_post(f"{API_URL}/feedback", data)
            if resp:
                st.success("Rejected draft recorded.")

    similar_rfis = result.get("similar_rfis", [])
    if similar_rfis:
        st.subheader("Similar RFIs Used")

        for rfi in similar_rfis:
            title = f"RFI {rfi.get('rfi_id', 'N/A')} — {rfi.get('subject', 'No Subject')}"
            with st.expander(title):
                st.write(f"**Project:** {rfi.get('project_name', '')}")
                st.write(f"**Trade:** {rfi.get('trade', '')}")
                st.write(f"**Spec Section:** {rfi.get('spec_section', '')}")
                st.write(f"**Score Before Rerank:** {rfi.get('pre_rerank_score', '')}")
                st.write(f"**Final Similarity Score:** {rfi.get('similarity_score', '')}")
                st.write(f"**Confidence:** {rfi.get('confidence', '')}")

                citation = rfi.get("source_citation", "")
                if citation:
                    st.write(f"**Source Citation:** {citation}")

                st.write("**Question**")
                st.write(rfi.get("question_text", ""))

                st.write("**Historical Response**")
                st.write(rfi.get("response_text", ""))

                match_reasons = rfi.get("match_reasons", [])
                if match_reasons:
                    st.write("**Why this matched**")
                    for reason in match_reasons:
                        st.write(f"- {reason}")

                score_breakdown = rfi.get("score_breakdown", {})
                if score_breakdown:
                    st.write("**Score Breakdown**")
                    for key, value in score_breakdown.items():
                        st.write(f"- {key}: {value}")
