import pandas as pd
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Smart RFI Assistant", layout="wide")

PRIMARY_NAVY = "#143A5B"
PRIMARY_NAVY_DARK = "#0D2942"
PRIMARY_NAVY_MID = "#1F4D73"
ACCENT_ORANGE = "#F28C28"
BG = "#F5F7FA"
CARD = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"
BORDER = "#D9E2EC"
WARN = "#B45309"
SOFT_BLUE = "#EAF2FB"

st.markdown(
    f"""
    <style>
        .stApp {{
            background: linear-gradient(180deg, {BG} 0%, #EEF2F7 100%);
            color: {TEXT};
        }}

        .main .block-container {{
            max-width: 1320px;
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }}

        h1, h2, h3 {{
            color: {PRIMARY_NAVY_DARK};
            letter-spacing: -0.02em;
        }}

        p, span, div, label {{
            color: {TEXT};
        }}

        .stMarkdown, .stText, .stCaption {{
            color: {TEXT} !important;
        }}

        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stMarkdownContainer"] span,
        [data-testid="stSidebar"] * {{
            color: {TEXT};
        }}

        .stAlert p, .stAlert div {{
            color: {TEXT} !important;
        }}

        /* Better text selection contrast */
        ::selection {{
            background: #CFE3FA;
            color: {PRIMARY_NAVY_DARK};
        }}

        /* Hero */
        .hero {{
            background: linear-gradient(135deg, {PRIMARY_NAVY_DARK} 0%, {PRIMARY_NAVY} 55%, {PRIMARY_NAVY_MID} 100%);
            border-radius: 18px;
            padding: 1.35rem 1.5rem;
            color: white;
            box-shadow: 0 12px 28px rgba(13, 41, 66, 0.20);
            margin-bottom: 1rem;
            border: 1px solid rgba(255,255,255,0.08);
        }}

        .hero-title {{
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 0.35rem;
            letter-spacing: -0.03em;
            color: white !important;
        }}

        .hero-subtitle {{
            font-size: 0.98rem;
            color: rgba(255,255,255,0.86) !important;
            line-height: 1.5;
            margin-bottom: 0.9rem;
        }}

        .hero-pill-row {{
            display: flex;
            gap: 0.6rem;
            flex-wrap: wrap;
        }}

        .hero-pill {{
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.16);
            color: white !important;
            border-radius: 999px;
            padding: 0.38rem 0.8rem;
            font-size: 0.82rem;
            font-weight: 600;
        }}

        /* Cards */
        .kahua-card {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 1rem 1rem 0.8rem 1rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
            margin-bottom: 1rem;
        }}

        .card-title {{
            color: {PRIMARY_NAVY_DARK} !important;
            font-weight: 800;
            font-size: 1rem;
            margin-bottom: 0.25rem;
        }}

        .card-subtitle {{
            color: {MUTED} !important;
            font-size: 0.9rem;
            margin-bottom: 0.4rem;
        }}

        .field-label {{
            color: {PRIMARY_NAVY_DARK};
            font-weight: 800;
            font-size: 0.95rem;
            margin-bottom: 0.35rem;
            margin-top: 0.2rem;
        }}

        .field-help {{
            color: {MUTED};
            font-size: 0.85rem;
            margin-bottom: 0.55rem;
        }}

        /* Buttons */
        .stButton > button {{
            background: linear-gradient(180deg, {ACCENT_ORANGE} 0%, #E6790C 100%);
            color: white !important;
            border: none;
            border-radius: 12px;
            font-weight: 700;
            padding: 0.65rem 1rem;
            box-shadow: 0 8px 18px rgba(242, 140, 40, 0.25);
        }}

        .stButton > button:hover,
        .stButton > button:focus,
        .stButton > button:focus-visible {{
            background: linear-gradient(180deg, #FF9A34 0%, {ACCENT_ORANGE} 100%);
            color: white !important;
            border: none !important;
            outline: none !important;
            box-shadow: 0 0 0 0.18rem rgba(242, 140, 40, 0.22) !important;
        }}

        /* Inputs */
        .stTextInput label,
        .stTextArea label,
        .stSelectbox label,
        .stSlider label {{
            color: {PRIMARY_NAVY_DARK} !important;
            font-weight: 700 !important;
        }}

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div {{
            border-radius: 12px !important;
            border: 1px solid {BORDER} !important;
            background: white !important;
            color: {TEXT} !important;
        }}

        .stTextInput input:focus,
        .stTextArea textarea:focus {{
            border: 1px solid #9FC2E8 !important;
            box-shadow: 0 0 0 0.18rem rgba(31, 77, 115, 0.10) !important;
            color: {TEXT} !important;
        }}

        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {{
            color: #94A3B8 !important;
        }}

        /* Baseweb selected/focused states */
        div[data-baseweb="select"] * {{
            color: {TEXT} !important;
        }}

        div[data-baseweb="select"] > div:focus-within {{
            border-color: #9FC2E8 !important;
            box-shadow: 0 0 0 0.18rem rgba(31, 77, 115, 0.10) !important;
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #EEF3F8 0%, #E7EEF6 100%);
            border-right: 1px solid {BORDER};
        }}

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] div {{
            color: {PRIMARY_NAVY_DARK} !important;
        }}

        /* Tabs */
        button[data-baseweb="tab"] {{
            border-radius: 999px !important;
            padding: 0.45rem 0.95rem !important;
            font-weight: 700 !important;
            color: {PRIMARY_NAVY_DARK} !important;
            background: #F2F6FA !important;
        }}

        button[data-baseweb="tab"]:hover {{
            background: #E7EEF6 !important;
            color: {PRIMARY_NAVY_DARK} !important;
        }}

        button[data-baseweb="tab"][aria-selected="true"] {{
            background: {PRIMARY_NAVY} !important;
            color: white !important;
        }}

        button[data-baseweb="tab"][aria-selected="true"] * {{
            color: white !important;
        }}

        /* Streamlit radio/segmented/toggle-like selected chips */
        [role="radiogroup"] label,
        [role="radiogroup"] div {{
            color: {TEXT} !important;
        }}

        /* Expanders */
        .streamlit-expanderHeader {{
            font-weight: 700;
            color: {PRIMARY_NAVY_DARK} !important;
        }}

        /* Alerts */
        div[data-testid="stAlert"] {{
            border-radius: 14px;
            border: 1px solid {BORDER};
        }}

        /* Dataframes */
        div[data-testid="stDataFrame"] {{
            background: white;
            border: 1px solid {BORDER};
            border-radius: 14px;
            padding: 0.25rem;
        }}

        div[data-testid="stDataFrame"] * {{
            color: {TEXT} !important;
        }}

        /* Tables / dataframe selected headers */
        thead tr th {{
            background: {SOFT_BLUE} !important;
            color: {PRIMARY_NAVY_DARK} !important;
        }}

        tbody tr td {{
            background: white !important;
            color: {TEXT} !important;
        }}

        /* Chips */
        .stat-chip {{
            display: inline-block;
            background: #FFF4E8;
            color: {WARN} !important;
            border: 1px solid #F8D2A8;
            border-radius: 999px;
            padding: 0.25rem 0.6rem;
            font-size: 0.78rem;
            font-weight: 700;
            margin-right: 0.45rem;
            margin-bottom: 0.35rem;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">Smart RFI Assistant</div>
        <div class="hero-subtitle">
            Search historical RFIs, surface recurring issue patterns, and generate grounded draft responses
            in a secure, analytics-forward workflow.
        </div>
        <div class="hero-pill-row">
            <span class="hero-pill">Historical Retrieval</span>
            <span class="hero-pill">Duplicate Detection</span>
            <span class="hero-pill">Issue Analytics</span>
            <span class="hero-pill">Draft Response Support</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    filters_resp = requests.get(f"{API_URL}/filters", timeout=10)
    filter_data = filters_resp.json() if filters_resp.status_code == 200 else {}
except Exception:
    filter_data = {}

trades = [""] + filter_data.get("trades", [])
projects = [""] + filter_data.get("projects", [])
spec_sections = [""] + filter_data.get("spec_sections", [])

tab1, tab2, tab3 = st.tabs(["RFI Assistant", "Common Issues Dashboard", "Upload RFIs CSV"])

with tab1:
    st.markdown(
        """
        <div class="kahua-card">
            <div class="card-title">RFI Workflow Assistant</div>
            <div class="card-subtitle">
                Retrieve similar historical RFIs, flag duplicates, and generate a suggested draft response.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Filters")
        selected_trade = st.selectbox("Trade", trades)
        selected_project = st.selectbox("Project", projects)
        selected_spec = st.selectbox("Spec Section", spec_sections)
        top_k = st.slider("Number of similar RFIs", min_value=1, max_value=5, value=3)

    col_a, col_b = st.columns([1.35, 1])

    with col_a:
        st.markdown('<div class="kahua-card">', unsafe_allow_html=True)

        st.markdown('<div class="field-label">RFI Subject</div>', unsafe_allow_html=True)
        st.markdown('<div class="field-help">Enter a short title for the new RFI.</div>', unsafe_allow_html=True)
        subject = st.text_input(
            "RFI Subject",
            label_visibility="collapsed",
            placeholder="Example: Rebar spacing conflict at shear wall"
        )

        st.markdown('<div class="field-label">RFI Question</div>', unsafe_allow_html=True)
        st.markdown('<div class="field-help">Paste or type the full field question that needs a response.</div>', unsafe_allow_html=True)
        question_text = st.text_area(
            "RFI Question",
            height=240,
            label_visibility="collapsed",
            placeholder="Example: Please confirm required rebar spacing because the structural and architectural drawings appear inconsistent."
        )

        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown(
            """
            <div class="kahua-card">
                <div class="card-title">How this helps</div>
                <div class="card-subtitle">Built to reduce repetitive work and improve response consistency.</div>
                <span class="stat-chip">Hybrid retrieval</span>
                <span class="stat-chip">SVD semantic search</span>
                <span class="stat-chip">Human review required</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    payload = {
        "subject": subject,
        "question_text": question_text,
        "top_k": top_k,
        "trade": selected_trade or None,
        "project_name": selected_project or None,
        "spec_section": selected_spec or None,
    }

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Find Similar RFIs", use_container_width=True):
            try:
                response = requests.post(f"{API_URL}/search", json=payload, timeout=30)
                if response.status_code == 200:
                    data = response.json()

                    st.markdown(
                        """
                        <div class="kahua-card">
                            <div class="card-title">Retrieval Summary</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.write(f"**Overall Confidence:** {data.get('overall_confidence', 'Low')}")

                    if data.get("duplicate_warning"):
                        st.warning(data["duplicate_warning"])

                    for safeguard in data.get("safeguards", []):
                        st.info(safeguard)

                    st.markdown(
                        """
                        <div class="kahua-card">
                            <div class="card-title">Similar Historical RFIs</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if not data.get("results"):
                        st.warning("No similar RFIs found.")

                    for item in data.get("results", []):
                        with st.expander(
                            f"RFI #{item['rfi_id']} • {item['subject']} • score={item['similarity_score']:.3f} • {item['confidence']}"
                        ):
                            if item.get("project_name"):
                                st.write(f"**Project:** {item['project_name']}")
                            st.write(f"**Trade:** {item['trade']}")
                            st.write(f"**Spec Section:** {item['spec_section']}")
                            st.write(f"**Question:** {item['question_text']}")
                            st.write(f"**Response:** {item['response_text']}")
                else:
                    st.error("Search request failed.")
            except Exception as e:
                st.error(f"Search request failed: {e}")

    with col2:
        if st.button("Generate Draft Response", use_container_width=True):
            try:
                response = requests.post(f"{API_URL}/generate", json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()

                    st.markdown(
                        """
                        <div class="kahua-card">
                            <div class="card-title">Draft Summary</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.write(f"**Overall Confidence:** {data.get('overall_confidence', 'Low')}")

                    if data.get("duplicate_warning"):
                        st.warning(data["duplicate_warning"])

                    for safeguard in data.get("safeguards", []):
                        st.info(safeguard)

                    st.markdown(
                        """
                        <div class="kahua-card">
                            <div class="card-title">Suggested Draft Response</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.text_area("Draft", data["draft_response"], height=320)

                    st.markdown(
                        """
                        <div class="kahua-card">
                            <div class="card-title">Source RFIs Used</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if not data.get("similar_rfis"):
                        st.warning("No source RFIs were found.")

                    for item in data.get("similar_rfis", []):
                        st.write(
                            f"- RFI #{item['rfi_id']}: {item['subject']} "
                            f"({item['trade']}, {item['spec_section']}, "
                            f"score={item['similarity_score']:.3f}, confidence={item['confidence']})"
                        )
                else:
                    st.error("Generation request failed.")
            except Exception as e:
                st.error(f"Generation request failed: {e}")

with tab2:
    st.markdown(
        """
        <div class="kahua-card">
            <div class="card-title">Common Issues Dashboard</div>
            <div class="card-subtitle">
                Spot repeated issue themes, high-friction trades, and recurring spec sections across RFIs.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        response = requests.get(f"{API_URL}/dashboard", timeout=30)
        if response.status_code != 200:
            st.error("Failed to load dashboard data.")
        else:
            data = response.json()

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown('<div class="kahua-card"><div class="card-title">Top Trades</div>', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(data.get("top_trades", [])), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="kahua-card"><div class="card-title">Top Spec Sections</div>', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(data.get("top_spec_sections", [])), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with c3:
                st.markdown('<div class="kahua-card"><div class="card-title">Repeated Subjects</div>', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(data.get("top_subjects", [])), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="kahua-card"><div class="card-title">Issue Cluster Summary</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(data.get("cluster_summary", [])), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="kahua-card"><div class="card-title">Issue Cluster Details</div></div>', unsafe_allow_html=True)
            for cluster in data.get("cluster_details", []):
                with st.expander(f"Cluster {cluster['cluster_id']} ({cluster['count']} RFIs)"):
                    st.dataframe(pd.DataFrame(cluster["items"]), use_container_width=True)

    except Exception as e:
        st.error(f"Dashboard request failed: {e}")

with tab3:
    st.markdown(
        """
        <div class="kahua-card">
            <div class="card-title">Upload Historical RFIs</div>
            <div class="card-subtitle">
                Replace the current dataset used by retrieval, drafting, and issue analytics.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Required Columns")
    st.markdown(
        """
        <div class="kahua-card">
            <div class="card-title">CSV Schema</div>
            <div class="card-subtitle">
                rfi_id, project_name, trade, spec_section, subject, question_text, response_text
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        info_resp = requests.get(f"{API_URL}/dataset-info", timeout=10)
        if info_resp.status_code == 200:
            info = info_resp.json()
            st.info(f"Current dataset: {info['row_count']} rows")
            st.write("**Current columns:**")
            st.write(", ".join(info["columns"]))
    except Exception:
        pass

    uploaded_file = st.file_uploader("Upload RFI CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            preview_df = pd.read_csv(uploaded_file)
            st.markdown(
                """
                <div class="kahua-card">
                    <div class="card-title">Preview</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.dataframe(preview_df.head(10), use_container_width=True)

            uploaded_file.seek(0)

            if st.button("Replace Current Dataset", use_container_width=True):
                files = {
                    "file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")
                }
                response = requests.post(f"{API_URL}/upload-csv", files=files, timeout=60)

                if response.status_code == 200:
                    data = response.json()
                    st.success(data["message"])
                    st.write(f"Rows loaded: {data['row_count']}")
                    st.write("Reload the other tabs to use the new dataset.")
                else:
                    try:
                        st.error(response.json().get("detail", "Upload failed."))
                    except Exception:
                        st.error("Upload failed.")
        except Exception as e:
            st.error(f"Could not preview file: {e}")
