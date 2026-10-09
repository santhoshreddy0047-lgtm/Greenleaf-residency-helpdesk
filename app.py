import os
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.answer import answer_question
from src.build_index import COLLECTION_NAME, create_client, index_documents
from src.config import UPDATES_DATA_DIR
from src.index_updates import load_update_documents

SUPPORTED_EXTENSIONS = ("pdf", "docx", "txt", "md")

# Configure page settings
st.set_page_config(
    page_title="GreenLeaf Residency Helpdesk",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom Styling adhering to GreenLeaf Residency Dark Theme & Glassmorphism Design
st.markdown(
    """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Global Dark Theme */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .stApp {
        background: radial-gradient(ellipse 90% 60% at 50% -10%, rgba(16, 185, 129, 0.14) 0%, transparent 70%),
                    radial-gradient(ellipse 70% 50% at 85% 15%, rgba(6, 182, 212, 0.08) 0%, transparent 60%),
                    linear-gradient(180deg, #070d12 0%, #0a141b 45%, #060b0f 100%);
        color: #e2e8f0;
    }

    /* Constrain main block width for responsive desktop layout */
    .block-container {
        max-width: 980px !important;
        padding-top: 1.25rem !important;
        padding-bottom: 2.5rem !important;
        margin: 0 auto !important;
    }

    /* Hide default Streamlit chrome */
    #MainMenu, footer, header {
        visibility: hidden;
    }
    [data-testid="stToolbar"] {
        display: none;
    }

    /* Top Bar Styling */
    .gl-topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.25rem 0 1.25rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 1.8rem;
    }
    .gl-brand-group {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .gl-brand-name {
        font-weight: 800;
        font-size: 1.35rem;
        color: #ffffff;
        letter-spacing: -0.02em;
        line-height: 1.1;
    }
    .gl-brand-sub {
        font-size: 0.82rem;
        color: #94a3b8;
        letter-spacing: 0.04em;
        font-weight: 500;
    }
    .gl-top-right {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .gl-datetime-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(15, 27, 36, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.82rem;
        color: #cbd5e1;
        font-weight: 500;
    }
    .gl-avatar-badge {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background: linear-gradient(135deg, #00e599 0%, #10b981 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 750;
        font-size: 0.86rem;
        color: #042f20;
        box-shadow: 0 0 14px rgba(0, 229, 153, 0.35);
    }

    /* Hero Section */
    .gl-hero-container {
        margin: 0.5rem 0 1.8rem 0;
    }
    .gl-helpdesk-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #00e599;
        font-size: 0.84rem;
        font-weight: 600;
        padding: 4px 14px;
        border-radius: 9999px;
        margin-bottom: 0.85rem;
    }
    .gl-hero-heading {
        font-size: clamp(2.1rem, 4.5vw, 2.85rem);
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.035em;
        line-height: 1.15;
        margin: 0 0 0.65rem 0;
    }
    .gl-hero-heading .accent {
        color: #00e599;
    }
    .gl-hero-subheading {
        font-size: 1.05rem;
        color: #94a3b8;
        line-height: 1.55;
        margin: 0;
        max-width: 640px;
    }

    /* Main Chat Container */
    .gl-chat-card {
        background: rgba(12, 23, 31, 0.8);
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-radius: 22px;
        padding: 26px 28px;
        box-shadow: 0 16px 44px rgba(0, 0, 0, 0.45);
        backdrop-filter: blur(20px);
        margin-bottom: 1.4rem;
    }

    /* Chat Messages */
    .gl-user-message-row {
        display: flex;
        justify-content: flex-end;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 1.4rem;
    }
    .gl-user-bubble {
        background: linear-gradient(135deg, #09634e 0%, #0d7e65 100%);
        color: #ffffff;
        padding: 13px 20px;
        border-radius: 20px 20px 4px 20px;
        font-size: 1rem;
        font-weight: 500;
        line-height: 1.45;
        max-width: 76%;
        box-shadow: 0 4px 14px rgba(6, 95, 70, 0.35);
    }
    .gl-user-avatar-icon {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.16);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        color: #94a3b8;
    }
    .gl-user-meta {
        text-align: right;
        font-size: 0.74rem;
        color: #64748b;
        margin-top: 4px;
        margin-right: 48px;
    }

    .gl-bot-message-row {
        display: flex;
        align-items: flex-start;
        gap: 14px;
        margin-bottom: 0.6rem;
    }
    .gl-bot-avatar {
        width: 44px;
        height: 44px;
        border-radius: 14px;
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.35);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        box-shadow: 0 0 16px rgba(0, 229, 153, 0.25);
    }
    .gl-bot-bubble {
        background: #13222e;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 4px 20px 20px 20px;
        padding: 20px 24px;
        color: #f1f5f9;
        font-size: 1.02rem;
        line-height: 1.65;
        flex-grow: 1;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .gl-bot-bubble strong {
        color: #ffffff;
        font-weight: 700;
    }
    .gl-bot-title {
        font-weight: 700;
        color: #00e599;
        font-size: 1.1rem;
        margin-bottom: 0.6rem;
    }
    .gl-bot-timestamp {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 8px;
    }

    /* Welcoming Empty State */
    .gl-welcome-card {
        text-align: center;
        padding: 36px 20px;
    }
    .gl-welcome-card h3 {
        color: #ffffff;
        font-size: 1.35rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .gl-welcome-card p {
        color: #94a3b8;
        font-size: 0.98rem;
        max-width: 520px;
        margin: 0 auto;
    }

    /* Quick Questions Label */
    .gl-quick-label {
        display: flex;
        align-items: center;
        gap: 6px;
        color: #cbd5e1;
        font-size: 0.92rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }
    .gl-quick-label span {
        color: #00e599;
    }

    /* Quick Questions button override */
    div[data-testid="column"] button {
        background: rgba(14, 27, 36, 0.85) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-radius: 9999px !important;
        color: #e2e8f0 !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        padding: 0.5rem 0.75rem !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="column"] button:hover {
        background: rgba(16, 185, 129, 0.16) !important;
        border-color: #00e599 !important;
        color: #ffffff !important;
        box-shadow: 0 0 14px rgba(0, 229, 153, 0.25) !important;
        transform: translateY(-1px) !important;
    }

    /* Pill-shaped Chat Input Form */
    [data-testid="stForm"] {
        background: rgba(13, 24, 33, 0.95) !important;
        border: 1px solid rgba(16, 185, 129, 0.32) !important;
        border-radius: 9999px !important;
        padding: 6px 16px !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.45) !important;
        transition: all 0.25s ease !important;
    }
    [data-testid="stForm"]:focus-within {
        border-color: #00e599 !important;
        box-shadow: 0 0 20px rgba(0, 229, 153, 0.25) !important;
    }
    [data-testid="stForm"] [data-testid="stTextInput"] input {
        background: transparent !important;
        border: none !important;
        color: #ffffff !important;
        font-size: 0.98rem !important;
        box-shadow: none !important;
    }
    [data-testid="stForm"] [data-testid="stTextInput"] input:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    [data-testid="stForm"] [data-testid="stTextInput"] > div {
        background: transparent !important;
        border: none !important;
    }

    /* Send button */
    [data-testid="stForm"] button[kind="primary"] {
        background: linear-gradient(135deg, #00e599 0%, #10b981 100%) !important;
        color: #042f20 !important;
        font-weight: 750 !important;
        border: none !important;
        border-radius: 9999px !important;
        box-shadow: 0 0 16px rgba(0, 229, 153, 0.3) !important;
        padding: 0.5rem 1.25rem !important;
    }
    [data-testid="stForm"] button[kind="primary"]:hover {
        box-shadow: 0 0 24px rgba(0, 229, 153, 0.5) !important;
        transform: translateY(-1px) !important;
    }

    /* Subtle Expander for Details */
    [data-testid="stExpander"] {
        background: rgba(15, 27, 36, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 12px !important;
        margin-top: 10px !important;
    }

    /* Sidebar Dark Styling */
    [data-testid="stSidebar"] {
        background: #09131a !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "answer_result" not in st.session_state:
    st.session_state.answer_result = None
if "timestamp" not in st.session_state:
    st.session_state.timestamp = None
if "feedback" not in st.session_state:
    st.session_state.feedback = None
if "upload_feedback" not in st.session_state:
    st.session_state.upload_feedback = None


def execute_question(question_text: str):
    """Processes a question through the RAG backend."""
    st.session_state.current_question = question_text
    try:
        with st.spinner("Checking society documents..."):
            result = answer_question(question_text)
            st.session_state.answer_result = result
            st.session_state.timestamp = datetime.now().strftime("%I:%M %p")
            st.session_state.feedback = None
    except Exception:
        st.session_state.answer_result = {
            "answer": "The helpdesk could not answer this question. Please try again.",
            "sources": [],
        }
        st.session_state.timestamp = datetime.now().strftime("%I:%M %p")


# Current formatted date and time for Top Bar (or matching the reference)
display_time = datetime.now().strftime("%b %d, %Y  %I:%M %p")

# Top Navigation Bar
st.markdown(
    f"""
    <div class="gl-topbar">
        <div class="gl-brand-group">
            <svg width="34" height="34" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M7 25C7 25 8 13 19 8C19 8 18 19 7 25Z" fill="#00e599"/>
                <path d="M14 25C14 25 18 17 26 13C26 13 24 22 14 25Z" fill="#10b981" fill-opacity="0.8"/>
            </svg>
            <div>
                <div class="gl-brand-name">GreenLeaf</div>
                <div class="gl-brand-sub">Residency</div>
            </div>
        </div>
        <div class="gl-top-right">
            <div class="gl-datetime-badge">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                    <line x1="16" y1="2" x2="16" y2="6"></line>
                    <line x1="8" y1="2" x2="8" y2="6"></line>
                    <line x1="3" y1="10" x2="21" y2="10"></line>
                </svg>
                <span>{display_time}</span>
            </div>
            <div class="gl-avatar-badge">GR</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Hero Section
st.markdown(
    """
    <div class="gl-hero-container">
        <div class="gl-helpdesk-pill">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 18v-6a9 9 0 0 1 18 0v6"></path>
                <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"></path>
            </svg>
            <span>Helpdesk</span>
        </div>
        <h1 class="gl-hero-heading">How can we <span class="accent">help you</span> today?</h1>
        <p class="gl-hero-subheading">
            Ask anything about our society rules, facilities, charges and community policies.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Main Chat / Answer Card
if st.session_state.current_question and st.session_state.answer_result:
    result = st.session_state.answer_result
    ts = st.session_state.timestamp or "07:12 PM"

    with st.container():
        # User message
        st.markdown(
            f"""
            <div class="gl-user-message-row">
                <div class="gl-user-bubble">
                    {st.session_state.current_question}
                </div>
                <div class="gl-user-avatar-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                        <circle cx="12" cy="7" r="4"></circle>
                    </svg>
                </div>
            </div>
            <div class="gl-user-meta">{ts} &#10003;&#10003;</div>
            """,
            unsafe_allow_html=True,
        )

        # Assistant response
        ans_text = result.get("answer", "")
        # Format markdown lines cleanly
        formatted_ans = ans_text.replace("\n", "<br>")

        st.markdown(
            f"""
            <div class="gl-bot-message-row">
                <div class="gl-bot-avatar">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <circle cx="9" cy="11" r="1.5" fill="#00E599"/>
                        <circle cx="15" cy="11" r="1.5" fill="#00E599"/>
                        <path d="M9 15C10 16.2 14 16.2 15 15" stroke="#00E599" stroke-width="1.6" stroke-linecap="round"/>
                        <path d="M12 4V7" stroke="#00E599" stroke-width="1.6" stroke-linecap="round"/>
                        <circle cx="12" cy="3" r="1.2" fill="#00E599"/>
                    </svg>
                </div>
                <div class="gl-bot-bubble">
                    <div class="gl-bot-title">Answer</div>
                    <div>{formatted_ans}</div>
                    <div class="gl-bot-timestamp">{ts}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Feedback actions and "Why this answer?" (unobtrusive sources)
        act_col1, act_col2, act_col3 = st.columns([0.08, 0.08, 0.84])
        with act_col1:
            if st.button("👍", key="thumb_up_btn", help="Helpful"):
                st.session_state.feedback = "positive"
                st.rerun()
        with act_col2:
            if st.button("👎", key="thumb_down_btn", help="Not helpful"):
                st.session_state.feedback = "negative"
                st.rerun()
        with act_col3:
            if st.session_state.feedback == "positive":
                st.caption("✨ Thank you for your feedback!")
            elif st.session_state.feedback == "negative":
                st.caption("Thank you, we're constantly refining our responses.")
            else:
                st.caption("Was this helpful?")

        # Discreet sources disclosure (unobtrusive, as required)
        sources = result.get("sources", [])
        if sources:
            with st.expander("📄 View details / Why this answer?", expanded=False):
                for src in sources:
                    st.markdown(
                        f"• **{src.get('source', 'Unknown')}** &nbsp;|&nbsp; "
                        f"Section: *{src.get('section', 'General')}* &nbsp;|&nbsp; "
                        f"Effective date: *{src.get('effective_date') or 'N/A'}* &nbsp;|&nbsp; "
                        f"Page {src.get('page', 1)}"
                    )

        # "Ask another question" button matching reference1.png
        st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
        reset_cols = st.columns([1, 1.4, 1])
        with reset_cols[1]:
            if st.button("🔄 Ask another question", key="btn_new_question", use_container_width=True):
                st.session_state.current_question = None
                st.session_state.answer_result = None
                st.session_state.feedback = None
                st.rerun()
else:
    # Empty welcoming placeholder
    st.markdown(
        """
        <div class="gl-chat-card">
            <div class="gl-welcome-card">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#00e599" stroke-width="1.5" style="margin-bottom: 0.75rem;">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                </svg>
                <h3>Welcome to GreenLeaf Residency Helpdesk</h3>
                <p>Have questions about amenities, maintenance, parking, or rules? Choose a quick question below or type your inquiry.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Quick Questions Section
st.markdown(
    """
    <div class="gl-quick-label">
        <span>⚡</span> Quick questions
    </div>
    """,
    unsafe_allow_html=True,
)

q_col1, q_col2, q_col3, q_col4, q_col5, q_col6 = st.columns(6)
with q_col1:
    if st.button("🏊 Pool timings", key="qq_pool", use_container_width=True):
        execute_question("What are the swimming pool timings?")
        st.rerun()
with q_col2:
    if st.button("🔧 Maintenance", key="qq_maint", use_container_width=True):
        execute_question("What is the monthly maintenance charge for a 2BHK flat?")
        st.rerun()
with q_col3:
    if st.button("🏋️ Gym rules", key="qq_gym", use_container_width=True):
        execute_question("What are the gym rules?")
        st.rerun()
with q_col4:
    if st.button("🚗 Parking rules", key="qq_parking", use_container_width=True):
        execute_question("What are the parking rules?")
        st.rerun()
with q_col5:
    if st.button("🐾 Pet policy", key="qq_pet", use_container_width=True):
        execute_question("What is the pet policy?")
        st.rerun()
with q_col6:
    if st.button("👥 Guest rules", key="qq_guest", use_container_width=True):
        execute_question("What are the guest rules?")
        st.rerun()

# Question Input Area matching reference2.png bottom bar
st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

with st.form("helpdesk_chat_form", clear_on_submit=True):
    form_cols = st.columns([0.05, 0.81, 0.14], vertical_alignment="center")
    with form_cols[0]:
        st.markdown(
            '<div style="text-align: center; color: #64748b; font-size: 1.15rem; padding-top: 2px;">📎</div>',
            unsafe_allow_html=True,
        )
    with form_cols[1]:
        typed_query = st.text_input(
            "Type your question here...",
            placeholder="Type your question here...",
            label_visibility="collapsed",
            key="chat_input_text",
        )
    with form_cols[2]:
        submit_btn = st.form_submit_button(
            "Ask Helpdesk",
            use_container_width=True,
            type="primary",
        )

    if submit_btn:
        if not typed_query or not typed_query.strip():
            st.warning("Please type a question before asking the helpdesk.")
        else:
            execute_question(typed_query.strip())
            st.rerun()

# Sidebar: Resident Management / Document Updates (Clean, Non-Technical Admin Function)
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem;">
            <span style="font-size: 1.1rem;">🏢</span>
            <span style="font-size: 1.05rem; font-weight: 700; color: #ffffff;">Admin Portal</span>
        </div>
        <p style="font-size: 0.82rem; color: #94a3b8; margin-bottom: 1.2rem;">
            Upload official notices, guidelines, and bylaws to update resident helpdesk answers.
        </p>
        """,
        unsafe_allow_html=True,
    )

    try:
        client = create_client()
        try:
            coll_names = {c.name for c in client.get_collections().collections}
            if COLLECTION_NAME in coll_names:
                pts = client.get_collection(COLLECTION_NAME).points_count
                status_label = "Knowledge base active" if pts else "Knowledge base empty"
            else:
                status_label = "Ready for indexing"
        finally:
            client.close()
    except Exception:
        status_label = "Knowledge base ready"

    st.markdown(
        f"""
        <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 8px; padding: 8px 12px; margin-bottom: 1.2rem; display: flex; align-items: center; gap: 8px;">
            <div style="width: 8px; height: 8px; border-radius: 50%; background: #00e599;"></div>
            <span style="font-size: 0.82rem; color: #00e599; font-weight: 600;">{status_label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.upload_feedback:
        st.success(st.session_state.upload_feedback)
        st.session_state.upload_feedback = None

    uploaded_files = st.file_uploader(
        "Upload society documents",
        type=list(SUPPORTED_EXTENSIONS),
        accept_multiple_files=True,
        help="Supported formats: PDF, DOCX, TXT, MD",
        key="admin_file_uploader",
    )

    if st.button("Upload and Index", use_container_width=True, type="primary", key="upload_index_btn"):
        if not uploaded_files:
            st.warning("Please choose at least one document to upload.")
        else:
            try:
                UPDATES_DATA_DIR.mkdir(parents=True, exist_ok=True)
                saved_names = []

                for uploaded_file in uploaded_files:
                    filename = Path(uploaded_file.name).name
                    extension = Path(filename).suffix.lower().lstrip(".")
                    if not filename or extension not in SUPPORTED_EXTENSIONS:
                        raise ValueError(f"Unsupported document filename: {uploaded_file.name}")

                    (UPDATES_DATA_DIR / filename).write_bytes(uploaded_file.getvalue())
                    saved_names.append(filename)

                with st.spinner("Processing documents..."):
                    documents = load_update_documents()
                    if not documents:
                        st.error("No readable documents found. Check files and try again.")
                    else:
                        index_documents(documents)
                        st.session_state.upload_feedback = f"Successfully indexed {len(saved_names)} document(s)."
                        st.rerun()
            except Exception:
                st.error("The documents could not be saved or indexed. Please try again.")
