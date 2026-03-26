import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Smart RFI Assistant",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root {
    --kahua-orange: #F58220;
    --kahua-orange-dark: #D96A10;
    --kahua-blue: #163A63;
    --kahua-blue-2: #224E7A;
    --kahua-bg: #F7F8FA;
    --kahua-card: #FFFFFF;
    --kahua-border: #E5E7EB;
    --kahua-text: #163A63;
    --kahua-muted: #667085;
    --kahua-success: #13795B;
    --kahua-warning-bg: #FFF7ED;
    --kahua-warning-border: #FDBA74;
}

html, body, [class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1450px;
}

h1, h2, h3 {
    color: var(--kahua-blue);
    letter-spacing: -0.01em;
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid var(--kahua-border);
    border-radius: 16px;
    padding: 0.9rem 1rem;
}

.stButton > button {
    width: 100%;
    border-radius: 12px;
    border: 1px solid var(--kahua-orange);
    background: var(--kahua-orange);
    color: white;
    font-weight: 700;
    min-height: 2.8rem;
}

.stButton > button:hover {
    background: var(--kahua-orange-dark);
    border-color: var(--kahua-orange-dark);
    color: white;
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div {
    border-radius: 12px !important;
}

.hero {
    background: linear-gradient(135deg, #163A63 0%, #224E7A 58%, #F58220 160%);
    color: white;
    border-radius: 22px;
    padding: 1.35rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 14px 34px rgba(22, 58, 99, 0.18);
}

.hero h1 {
    color: white !important;
    font-size: 2rem;
    margin-bottom: 0.35rem;
}

.hero p {
    margin: 0;
    color: rgba(255,255,255,0.92);
}

.card {
    background: var(--kahua-card);
    border: 1px solid var(--kahua-border);
    border-radius: 18px;
    padding: 1rem 1rem 0.9rem 1rem;
    box-shadow: 0 8px 24px rgba(16, 24, 40, 0.05);
    margin-bottom: 1rem;
}

.card-tight {
    background: var(--kahua-card);
    border: 1px solid var(--kahua-border);
    border-radius: 16px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.75rem;
}

.section-label {
    display: inline-block;
    font-size: 0.76rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    color: var(--kahua-orange);
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}

.step-chip-wrap {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin: 0.25rem 0 1rem 0;
}

.step-chip {
    background: white;
    border: 1px solid var(--kahua-border);
    border-radius: 999px;
    padding: 0.6rem 0.95rem;
    color: var(--kahua-blue);
    font-weight: 700;
    font-size: 0.95rem;
}

.note-box {
    background: #F8FAFC;
    border: 1px solid var(--kahua-border);
    border-radius: 14px;
    padding: 0.85rem 1rem;
    color: var(--kahua-muted);
    margin-bottom: 0.9rem;
}

.warning-box {
    background: var(--kahua-warning-bg);
    border: 1px solid var(--kahua-warning-border);
    border-radius: 14px;
    padding: 0.85rem 1rem;
    color: #9A3412;
    margin-bottom: 0.8rem;
}

.good-box {
    background: #ECFDF3;
    border: 1px solid #ABEFC6;
    border-radius: 14px;
    padding: 0.8rem 1rem;
    color: #067647;
    margin-bottom: 0.8rem;
}

.small-muted {
    color: var(--kahua-muted);
    font-size: 0.92rem;
}

.divider-space {
    height: 0.35rem;
}

.sidebar-title {
    font-size: 1rem;
    font-weight: 800;
    color: var(--kahua-blue);
    margin-bottom: 0.4rem;
}

hr {
    border: none;
    border-top: 1px solid var(--kahua-border);
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)


def safe_get(url, params=None, timeout=10):
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Could not load data: {e}")
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
        st.error(f"Request failed: {e}")
        return None


def status_badge(text: str):
    color = "#163A63"
    bg = "#EFF4FF"
    border = "#B2DDFF"

    t = (text or "").lower()
    if "high" in t or "approved" in t:
        color, bg, border = "#067647", "#ECFDF3", "#ABEFC6"
    elif "medium" in t or "review" in t:
        color, bg, border = "#9A3412", "#FFF7ED", "#FDBA74"
    elif "low" in t or "rejected" in t:
        color, bg, border = "#B42318", "#FEF3F2", "#FECDCA"

    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:0.32rem 0.68rem;
            border-radius:999px;
            border:1px solid {border};
            background:{bg};
            color:{color};
            font-weight:700;
            font-size:0.82rem;
            margin-bottom:0.25rem;
        ">{text}</div>
        """,
        unsafe_allow_html=True,
    )


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

st.markdown("""
<div class="hero">
    <h1>Smart RFI Assistant</h1>
    <p>Search past RFIs, review the best evidence, and generate a draft response your team can approve quickly.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="step-chip-wrap">
    <div class="step-chip">1. Enter the issue</div>
    <div class="step-chip">2. Review matching RFIs</div>
    <div class="step-chip">3. Approve, edit, or send to review</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="sidebar-title">Search Options</div>', unsafe_allow_html=True)
    st.caption("Use filters only when you want to narrow results to a specific trade, project, or spec section.")

    trade = st.selectbox("Trade", ["Any"] + filters.get("trades", []))
    project_name = st.selectbox("Project", ["Any"] + filters.get("projects", []))
    spec_section = st.selectbox("Spec Section", ["Any"] + filters.get("spec_sections", []))
    top_k = st.slider("Number of similar RFIs", 1, 5, 3)

    ai_available = bool(health.get("ai_available", False))
    use_ai = st.checkbox("Use AI drafting", value=False, disabled=not ai_available)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">System Status</div>', unsafe_allow_html=True)
    st.caption(f"RFIs loaded: {dataset_info.get('row_count', 0)}")
    st.caption(f"Search engine: {health.get('retrieval_engine', 'hybrid-faiss-rerank-cited')}")
    st.caption(f"Index: {health.get('index_status', 'unknown')}")
    st.caption("Recommended workflow: search first, then review the top matches before approving a draft.")

    with st.expander("Add project data"):
        uploaded_csv = st.file_uploader("Upload RFI CSV", type=["csv"], key="csv_uploader")
        if uploaded_csv is not None and st.button("Upload CSV"):
            files = {"file": (uploaded_csv.name, uploaded_csv.getvalue(), "text/csv")}
            data = safe_post(f"{API_URL}/upload-csv", files=files, timeout=30)
            if data:
                st.success(f"CSV uploaded. Rows: {data.get('row_count', 0)}")
                st.rerun()

        uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"], key="pdf_uploader")
        if uploaded_pdf is not None and st.button("Upload PDF"):
            files = {"file": (uploaded_pdf.name, uploaded_pdf.getvalue(), "application/pdf")}
            data = safe_post(f"{API_URL}/upload-pdf", files=files, timeout=90)
            if data:
                st.success(f"PDF processed. Added rows: {data.get('added_rows', 0)}")
                st.rerun()

        if st.button("Sync approved drafts into dataset"):
            data = safe_post(f"{API_URL}/sync-reviewed-rfis", {})
            if data:
                st.success(f"Synced. Added rows: {data.get('added_rows', 0)}")
                st.rerun()

assistant_tab, workflow_tab, analytics_tab = st.tabs(["Assistant", "Workflow", "Analytics"])

with assistant_tab:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Step 1</div>', unsafe_allow_html=True)
    st.subheader("Describe the issue")

    st.markdown("""
    <div class="note-box">
        Enter a short subject and the field question. Then click <b>Generate Draft Response</b>.
        The assistant will show the best historical matches first so the user can understand why the draft was created.
    </div>
    """, unsafe_allow_html=True)

    subject = st.text_input(
        "Subject",
        placeholder="Example: Door frame clearance at corridor wall"
    )

    question_text = st.text_area(
        "Question",
        placeholder="Describe the issue, conflict, or clarification needed...",
        height=160
    )

    payload = {
        "subject": subject.strip(),
        "question_text": question_text.strip(),
        "top_k": top_k,
        "trade": None if trade == "Any" else trade,
        "project_name": None if project_name == "Any" else project_name,
        "spec_section": None if spec_section == "Any" else spec_section,
        "use_ai": bool(use_ai and ai_available),
    }

    st.markdown('<div class="small-muted">Tip: leave filters on “Any” unless you know you only want results from one part of the project.</div>', unsafe_allow_html=True)

    if st.button("Generate Draft Response", use_container_width=True):
        if not payload["subject"] or not payload["question_text"]:
            st.warning("Please enter both a subject and a question.")
        else:
            result = safe_post(f"{API_URL}/generate", payload)
            if result:
                st.session_state.latest_result = result
                st.session_state.latest_payload = payload

    st.markdown('</div>', unsafe_allow_html=True)

    result = st.session_state.latest_result
    saved_payload = st.session_state.latest_payload

    if result and saved_payload:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Step 2</div>', unsafe_allow_html=True)
        st.subheader("Review the draft and supporting RFIs")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Confidence", result.get("overall_confidence", "Low"))
        with m2:
            st.metric("Confidence Score", f"{result.get('confidence_score', 0.0)}%")
        with m3:
            st.metric("Matches Used", result.get("retrieval_count", 0))
        with m4:
            st.metric("Candidates Reviewed", result.get("candidate_count", 0))

        if result.get("duplicate_warning"):
            st.markdown(f'<div class="warning-box"><b>Duplicate Check:</b> {result["duplicate_warning"]}</div>', unsafe_allow_html=True)

        safeguards = result.get("safeguards", [])
        if safeguards:
            for item in safeguards:
                st.markdown(f'<div class="note-box">{item}</div>', unsafe_allow_html=True)

        st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)
        st.markdown("#### Draft response")
        edited_draft = st.text_area(
            "Edit before approval if needed",
            value=result.get("draft_response", ""),
            height=260,
            key="edited_draft_clean_ui"
        )

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Step 2A</div>', unsafe_allow_html=True)
        st.subheader("Why this answer was suggested")

        similar_rfis = result.get("similar_rfis", [])
        if not similar_rfis:
            st.markdown('<div class="warning-box">No similar RFIs were returned for this search.</div>', unsafe_allow_html=True)
        else:
            for idx, rfi in enumerate(similar_rfis, start=1):
                with st.expander(f"Match {idx}: RFI {rfi.get('rfi_id', '')} — {rfi.get('subject', 'No Subject')}", expanded=(idx == 1)):
                    left, right = st.columns([1, 1])

                    with left:
                        st.markdown("**New incoming RFI**")
                        st.markdown(f"**Subject**  \n{saved_payload['subject']}")
                        st.markdown("**Question**")
                        st.write(saved_payload["question_text"])

                    with right:
                        st.markdown("**Historical RFI used**")
                        st.markdown(f"**RFI ID**  \n{rfi.get('rfi_id', '')}")
                        st.markdown(f"**Subject**  \n{rfi.get('subject', '')}")
                        st.markdown("**Historical Question**")
                        st.write(rfi.get("question_text", ""))

                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        status_badge(rfi.get("confidence", ""))
                    with c2:
                        st.caption(f"Score: {rfi.get('similarity_score', '')}")
                    with c3:
                        st.caption(f"Trade: {rfi.get('trade', '') or '—'}")
                    with c4:
                        st.caption(f"Spec: {rfi.get('spec_section', '') or '—'}")

                    st.markdown("**Historical response**")
                    st.write(rfi.get("response_text", ""))

                    st.markdown("**Source citation**")
                    citation = rfi.get("source_citation", "")
                    if citation:
                        st.code(citation)
                    else:
                        st.write("No source citation available.")

                    reasons = rfi.get("match_reasons", [])
                    if reasons:
                        st.markdown("**Why it matched**")
                        for reason in reasons:
                            st.write(f"- {reason}")

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Step 3</div>', unsafe_allow_html=True)
        st.subheader("Choose what to do next")

        st.markdown("""
        <div class="good-box">
            <b>Recommended use:</b> approve when the draft is ready, save edited approval if you changed the wording,
            or send to review when another team member should look at it before it is used.
        </div>
        """, unsafe_allow_html=True)

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
                    st.success(f"Sent to review. Workflow ID: {resp.get('workflow_id')}")

        with wf2:
            if st.button("Approve Draft"):
                payload2 = dict(base_workflow_payload)
                payload2["status"] = "approved"
                resp = safe_post(f"{API_URL}/workflow", payload2)
                if resp:
                    st.success(f"Draft approved. Workflow ID: {resp.get('workflow_id')}")

        with wf3:
            if st.button("Save Edited Approval"):
                payload2 = dict(base_workflow_payload)
                payload2["status"] = "edited_approved"
                resp = safe_post(f"{API_URL}/workflow", payload2)
                if resp:
                    st.success(f"Edited approval saved. Workflow ID: {resp.get('workflow_id')}")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("#### Save learning feedback")

        f1, f2, f3 = st.columns(3)
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

        with f1:
            if st.button("Accept Draft"):
                data = dict(feedback_base)
                data["action"] = "accepted"
                resp = safe_post(f"{API_URL}/feedback", data)
                if resp:
                    st.success(f"Accepted and saved. Added to dataset: {resp.get('added_to_dataset', 0)}")

        with f2:
            if st.button("Save Edited Draft"):
                data = dict(feedback_base)
                data["action"] = "edited"
                resp = safe_post(f"{API_URL}/feedback", data)
                if resp:
                    st.success(f"Edited draft saved. Added to dataset: {resp.get('added_to_dataset', 0)}")

        with f3:
            if st.button("Reject Draft"):
                data = dict(feedback_base)
                data["action"] = "rejected"
                resp = safe_post(f"{API_URL}/feedback", data)
                if resp:
                    st.success("Rejected draft recorded.")

        st.markdown('</div>', unsafe_allow_html=True)

with workflow_tab:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Workflow Queue</div>', unsafe_allow_html=True)
    st.subheader("Open items and recent approvals")

    wf_summary = workflow_data.get("summary", {})
    s1, s2 = st.columns(2)
    with s1:
        st.metric("Total Workflow Items", wf_summary.get("total_workflow_items", 0))
    with s2:
        st.metric("Avg Confidence", wf_summary.get("avg_confidence_score", "N/A"))

    items = workflow_data.get("items", [])
    if not items:
        st.markdown('<div class="note-box">No workflow items yet. Create one from the Assistant tab after generating a draft.</div>', unsafe_allow_html=True)
    else:
        for item in items:
            with st.expander(f"#{item.get('id')} | {item.get('status')} | {item.get('subject')}"):
                status_badge(item.get("status", ""))
                st.markdown(f"**Question**  \n{item.get('question_text', '')}")
                st.markdown(f"**Confidence**  \n{item.get('overall_confidence', '')} ({item.get('confidence_score', '')})")

                if item.get("duplicate_warning"):
                    st.markdown(f'<div class="warning-box">{item["duplicate_warning"]}</div>', unsafe_allow_html=True)

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
                            {
                                "status": "edited_approved",
                                "final_draft": item.get("final_draft") or item.get("generated_draft")
                            }
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
    st.markdown('</div>', unsafe_allow_html=True)

with analytics_tab:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Analytics</div>', unsafe_allow_html=True)
    st.subheader("Usage and dataset summary")

    metrics = dashboard.get("metrics", {})
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        st.metric("Dataset Rows", metrics.get("dataset_rows", 0))
    with a2:
        st.metric("Unique Projects", metrics.get("unique_projects", 0))
    with a3:
        st.metric("Unique Trades", metrics.get("unique_trades", 0))
    with a4:
        st.metric("Unique Spec Sections", metrics.get("unique_spec_sections", 0))

    b1, b2, b3, b4 = st.columns(4)
    with b1:
        st.metric("Total Feedback", metrics.get("total_feedback", 0))
    with b2:
        st.metric("Reviewed RFIs", metrics.get("reviewed_rfis_count", 0))
    with b3:
        st.metric("Workflow Items", metrics.get("total_workflow_items", 0))
    with b4:
        st.metric("Avg Workflow Confidence", metrics.get("avg_workflow_confidence_score", "N/A"))

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Top trades")
        for item in dashboard.get("top_trades", [])[:10]:
            st.markdown(f'<div class="card-tight"><b>{item.get("trade")}</b><br><span class="small-muted">{item.get("count")} RFIs</span></div>', unsafe_allow_html=True)

        st.markdown("#### Workflow status counts")
        for item in dashboard.get("workflow_summary", {}).get("status_counts", []):
            st.markdown(f'<div class="card-tight"><b>{item.get("status")}</b><br><span class="small-muted">{item.get("count")} items</span></div>', unsafe_allow_html=True)

    with col_right:
        st.markdown("#### Top spec sections")
        for item in dashboard.get("top_spec_sections", [])[:10]:
            st.markdown(f'<div class="card-tight"><b>{item.get("spec_section")}</b><br><span class="small-muted">{item.get("count")} RFIs</span></div>', unsafe_allow_html=True)

        st.markdown("#### Feedback actions")
        for item in dashboard.get("feedback_summary", {}).get("action_counts", []):
            st.markdown(f'<div class="card-tight"><b>{item.get("action")}</b><br><span class="small-muted">{item.get("count")} actions</span></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
