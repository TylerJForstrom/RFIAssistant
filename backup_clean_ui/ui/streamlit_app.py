import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Smart RFI Assistant", layout="wide")
st.title("Smart RFI Assistant")


def safe_get(url, params=None):
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"GET failed: {e}")
        return None


def safe_post(url, payload=None, files=None, timeout=60):
    try:
        if files is not None:
            response = requests.post(url, files=files, timeout=timeout)
        else:
            response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"POST failed: {e}")
        return None


health = safe_get(f"{API_URL}/health")
if not health:
    st.stop()

filters = safe_get(f"{API_URL}/filters") or {"trades": [], "projects": [], "spec_sections": []}
dataset_info = safe_get(f"{API_URL}/dataset-info") or {}
dashboard = safe_get(f"{API_URL}/dashboard") or {}
workflow_data = safe_get(f"{API_URL}/workflow") or {"items": [], "summary": {}}

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None
if "latest_payload" not in st.session_state:
    st.session_state.latest_payload = None

tab1, tab2, tab3 = st.tabs(["Assistant", "Analytics", "Workflow"])

with tab1:
    st.caption(
        f"Loaded RFIs: {dataset_info.get('row_count', 0)} | "
        f"Engine: {health.get('retrieval_engine', 'hybrid-faiss-rerank-cited')} | "
        f"Index: {health.get('index_status', 'unknown')}"
    )

    with st.expander("Add data"):
        uploaded_csv = st.file_uploader("Upload RFI CSV", type=["csv"])
        if uploaded_csv is not None and st.button("Upload CSV"):
            files = {"file": (uploaded_csv.name, uploaded_csv.getvalue(), "text/csv")}
            data = safe_post(f"{API_URL}/upload-csv", files=files, timeout=30)
            if data:
                st.success(f"CSV uploaded. Rows: {data.get('row_count', 0)}")
                st.rerun()

        uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"])
        if uploaded_pdf is not None and st.button("Upload PDF"):
            files = {"file": (uploaded_pdf.name, uploaded_pdf.getvalue(), "application/pdf")}
            data = safe_post(f"{API_URL}/upload-pdf", files=files, timeout=90)
            if data:
                st.success(f"PDF processed. Parsed: {data.get('parsed_rows', 0)} | Added: {data.get('added_rows', 0)}")
                st.rerun()

        if st.button("Sync Approved Drafts Into Search Dataset"):
            data = safe_post(f"{API_URL}/sync-reviewed-rfis", {})
            if data:
                st.success(f"Synced. Added rows: {data.get('added_rows', 0)}")
                st.rerun()

    subject = st.text_input("Subject", placeholder="Example: Door frame clearance")
    question_text = st.text_area("Question", placeholder="Type the RFI question here...", height=140)

    trade = st.selectbox("Trade", ["Any"] + filters.get("trades", []))
    project_name = st.selectbox("Project", ["Any"] + filters.get("projects", []))
    spec_section = st.selectbox("Spec Section", ["Any"] + filters.get("spec_sections", []))
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

        st.caption(
            f"Draft mode: {'AI' if result.get('used_ai') else 'Standard'} | "
            f"Confidence Score: {result.get('confidence_score', 0.0)}% | "
            f"Matches: {result.get('retrieval_count', 0)}"
        )

        edited_draft = st.text_area(
            "Generated Draft",
            value=result.get("draft_response", ""),
            height=260,
            key="edited_draft"
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Confidence", result.get("overall_confidence", "Low"))
        m2.metric("Confidence Score", f"{result.get('confidence_score', 0.0)}%")
        m3.metric("Final Matches", result.get("retrieval_count", 0))
        m4.metric("Candidates Reranked", result.get("candidate_count", 0))

        if result.get("duplicate_warning"):
            st.warning(result["duplicate_warning"])

        duplicate_candidates = result.get("duplicate_candidates", [])
        if duplicate_candidates:
            with st.expander("Possible Duplicate RFIs"):
                for dup in duplicate_candidates:
                    st.write(
                        f"- RFI {dup.get('rfi_id')} | {dup.get('subject')} | "
                        f"score={dup.get('score')} | {dup.get('source_citation', '')}"
                    )

        safeguards = result.get("safeguards", [])
        if safeguards:
            st.subheader("Review Notes")
            for item in safeguards:
                st.write(f"- {item}")

        st.subheader("Side-by-Side Comparison")
        similar_rfis = result.get("similar_rfis", [])
        for idx, rfi in enumerate(similar_rfis, start=1):
            st.markdown(f"### Match {idx}")
            left, right = st.columns(2)

            with left:
                st.markdown("**Incoming RFI**")
                st.write(f"**Subject:** {saved_payload['subject']}")
                st.write("**Question:**")
                st.write(saved_payload["question_text"])

            with right:
                st.markdown("**Historical Match**")
                st.write(f"**RFI ID:** {rfi.get('rfi_id', '')}")
                st.write(f"**Subject:** {rfi.get('subject', '')}")
                st.write("**Question:**")
                st.write(rfi.get("question_text", ""))

            st.markdown("**Evidence Used / Citation**")
            citation = rfi.get("source_citation", "")
            if citation:
                st.code(citation)
            else:
                st.write("No source citation available for this item.")

            st.markdown("**Historical Response Used**")
            st.write(rfi.get("response_text", ""))

            reasons = rfi.get("match_reasons", [])
            if reasons:
                st.markdown("**Why this matched**")
                for reason in reasons:
                    st.write(f"- {reason}")

            score_breakdown = rfi.get("score_breakdown", {})
            if score_breakdown:
                with st.expander(f"Score Breakdown for Match {idx}"):
                    for key, value in score_breakdown.items():
                        st.write(f"- {key}: {value}")

        st.subheader("Approval Workflow")
        base_workflow_payload = {
            "subject": saved_payload["subject"],
            "question_text": saved_payload["question_text"],
            "generated_draft": result.get("draft_response", ""),
            "final_draft": edited_draft,
            "trade": saved_payload["trade"],
            "spec_section": saved_payload["spec_section"],
            "project_name": saved_payload["project_name"],
            "overall_confidence": result.get("overall_confidence"),
            "confidence_score": result.get("confidence_score"),
            "duplicate_warning": result.get("duplicate_warning"),
        }

        wf1, wf2, wf3 = st.columns(3)

        with wf1:
            if st.button("Send to Review"):
                payload2 = dict(base_workflow_payload)
                payload2["status"] = "under_review"
                resp = safe_post(f"{API_URL}/workflow", payload2)
                if resp:
                    st.success(f"Workflow item created. ID: {resp.get('workflow_id')}")

        with wf2:
            if st.button("Approve Draft"):
                payload2 = dict(base_workflow_payload)
                payload2["status"] = "approved"
                resp = safe_post(f"{API_URL}/workflow", payload2)
                if resp:
                    st.success(f"Approved workflow item created. ID: {resp.get('workflow_id')}")

        with wf3:
            if st.button("Save Edited Approval"):
                payload2 = dict(base_workflow_payload)
                payload2["status"] = "edited_approved"
                resp = safe_post(f"{API_URL}/workflow", payload2)
                if resp:
                    st.success(f"Edited approval saved. ID: {resp.get('workflow_id')}")

        st.subheader("Save Review Feedback")
        c1, c2, c3 = st.columns(3)

        feedback_base = {
            "subject": saved_payload["subject"],
            "question_text": saved_payload["question_text"],
            "generated_draft": result.get("draft_response", ""),
            "final_draft": edited_draft,
            "overall_confidence": result.get("overall_confidence"),
            "confidence_score": result.get("confidence_score"),
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

with tab2:
    st.subheader("Analytics Dashboard")
    metrics = dashboard.get("metrics", {})

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Dataset Rows", metrics.get("dataset_rows", 0))
    a2.metric("Unique Projects", metrics.get("unique_projects", 0))
    a3.metric("Unique Trades", metrics.get("unique_trades", 0))
    a4.metric("Unique Spec Sections", metrics.get("unique_spec_sections", 0))

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Total Feedback", metrics.get("total_feedback", 0))
    b2.metric("Reviewed RFIs", metrics.get("reviewed_rfis_count", 0))
    b3.metric("Workflow Items", metrics.get("total_workflow_items", 0))
    b4.metric("Avg Workflow Confidence", metrics.get("avg_workflow_confidence_score", "N/A"))

    st.markdown("### Top Trades")
    for item in dashboard.get("top_trades", [])[:10]:
        st.write(f"- {item.get('trade')}: {item.get('count')}")

    st.markdown("### Top Spec Sections")
    for item in dashboard.get("top_spec_sections", [])[:10]:
        st.write(f"- {item.get('spec_section')}: {item.get('count')}")

    st.markdown("### Top Subjects")
    for item in dashboard.get("top_subjects", [])[:10]:
        st.write(f"- {item.get('subject')}: {item.get('count')}")

    st.markdown("### Feedback Action Counts")
    for item in dashboard.get("feedback_summary", {}).get("action_counts", []):
        st.write(f"- {item.get('action')}: {item.get('count')}")

    st.markdown("### Workflow Status Counts")
    for item in dashboard.get("workflow_summary", {}).get("status_counts", []):
        st.write(f"- {item.get('status')}: {item.get('count')}")

with tab3:
    st.subheader("Workflow Queue")

    wf_summary = workflow_data.get("summary", {})
    s1, s2 = st.columns(2)
    s1.metric("Total Workflow Items", wf_summary.get("total_workflow_items", 0))
    s2.metric("Avg Confidence", wf_summary.get("avg_confidence_score", "N/A"))

    items = workflow_data.get("items", [])
    if not items:
        st.info("No workflow items yet.")
    else:
        for item in items:
            with st.expander(
                f"#{item.get('id')} | {item.get('status')} | {item.get('subject')}"
            ):
                st.write(f"**Question:** {item.get('question_text', '')}")
                st.write(f"**Confidence:** {item.get('overall_confidence', '')}")
                st.write(f"**Confidence Score:** {item.get('confidence_score', '')}")
                if item.get("duplicate_warning"):
                    st.warning(item["duplicate_warning"])

                st.markdown("**Generated Draft**")
                st.write(item.get("generated_draft", ""))

                if item.get("final_draft"):
                    st.markdown("**Final Draft**")
                    st.write(item.get("final_draft", ""))

                u1, u2, u3, u4 = st.columns(4)

                with u1:
                    if st.button(f"Mark Review #{item['id']}"):
                        resp = safe_post(
                            f"{API_URL}/workflow/{item['id']}/status",
                            {"status": "under_review"}
                        )
                        if resp:
                            st.success("Updated.")
                            st.rerun()

                with u2:
                    if st.button(f"Approve #{item['id']}"):
                        resp = safe_post(
                            f"{API_URL}/workflow/{item['id']}/status",
                            {"status": "approved"}
                        )
                        if resp:
                            st.success("Updated.")
                            st.rerun()

                with u3:
                    if st.button(f"Edited Approve #{item['id']}"):
                        resp = safe_post(
                            f"{API_URL}/workflow/{item['id']}/status",
                            {"status": "edited_approved", "final_draft": item.get("final_draft") or item.get("generated_draft")}
                        )
                        if resp:
                            st.success("Updated.")
                            st.rerun()

                with u4:
                    if st.button(f"Reject #{item['id']}"):
                        resp = safe_post(
                            f"{API_URL}/workflow/{item['id']}/status",
                            {"status": "rejected"}
                        )
                        if resp:
                            st.success("Updated.")
                            st.rerun()
