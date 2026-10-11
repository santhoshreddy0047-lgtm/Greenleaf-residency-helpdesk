import html
import os
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    kolkata_tz = ZoneInfo("Asia/Kolkata")
except Exception:
    from datetime import timezone, timedelta
    kolkata_tz = timezone(timedelta(hours=5, minutes=30))

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

# Custom Styling adhering to GreenLeaf Residency Dark Theme & Design Specification
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
        background: radial-gradient(ellipse 90% 60% at 50% -10%, rgba(16, 185, 129, 0.12) 0%, transparent 70%),
                    radial-gradient(ellipse 70% 50% at 85% 15%, rgba(6, 182, 212, 0.08) 0%, transparent 60%),
                    linear-gradient(180deg, #040e14 0%, #06151c 45%, #030a0f 100%);
        color: #e2e8f0;
    }

    /* Constrain main block width for responsive desktop layout */
    .block-container {
        max-width: 1040px !important;
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
        border-bottom: 1px solid rgba(20, 184, 166, 0.18);
        margin-bottom: 1.8rem;
    }
    .gl-brand-group {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .gl-brand-name {
        font-weight: 800;
        font-size: 1.4rem;
        color: #ffffff;
        letter-spacing: -0.025em;
        line-height: 1.1;
    }
    .gl-brand-sub {
        font-size: 0.85rem;
        color: #94a3b8;
        letter-spacing: 0.02em;
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
        background: rgba(9, 26, 36, 0.85);
        border: 1px solid rgba(20, 184, 166, 0.25);
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
        background: #00e599;
        color: #022c1e;
        font-weight: 800;
        font-size: 0.88rem;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 14px rgba(0, 229, 153, 0.4);
        letter-spacing: 0.02em;
    }

    /* Hero Section */
    .gl-hero-text-block {
        padding-right: 10px;
    }
    .gl-helpdesk-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.35);
        color: #00e599;
        font-size: 0.82rem;
        font-weight: 600;
        padding: 4px 14px;
        border-radius: 9999px;
        margin-bottom: 0.85rem;
    }
    .gl-hero-heading {
        font-size: clamp(2.2rem, 4.2vw, 3rem);
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.035em;
        line-height: 1.15;
        margin: 0 0 0.85rem 0;
    }
    .gl-accent-text {
        color: #00e599;
    }
    .gl-hero-desc {
        font-size: 0.98rem;
        color: #94a3b8;
        line-height: 1.6;
        margin: 0;
        max-width: 540px;
    }
    .gl-hero-illustration {
        display: flex;
        align-items: center;
        justify-content: center;
        max-width: 440px;
        margin: 0 auto;
    }

    /* Trusted Information Card */
    .gl-trusted-card {
        background: rgba(7, 24, 34, 0.75);
        border: 1px solid rgba(20, 184, 166, 0.22);
        border-radius: 20px;
        padding: 26px 30px;
        margin-top: 1.2rem;
        margin-bottom: 1.8rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
        backdrop-filter: blur(16px);
    }
    .gl-trusted-header {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        margin-bottom: 24px;
    }
    .gl-trusted-line {
        height: 1px;
        width: 60px;
        background: linear-gradient(90deg, transparent, #14b8a6);
    }
    .gl-trusted-header .gl-trusted-line:last-child {
        background: linear-gradient(90deg, #14b8a6, transparent);
    }
    .gl-trusted-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.01em;
        text-align: center;
    }
    .gl-trusted-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
    }
    .gl-feature-col {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 0 12px;
        border-right: 1px solid rgba(255, 255, 255, 0.07);
    }
    .gl-feature-col-last {
        border-right: none;
    }
    .gl-feature-icon-circle {
        width: 52px;
        height: 52px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 14px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
    }
    .gl-icon-rules {
        background: rgba(16, 185, 129, 0.12);
        border: 1.5px solid rgba(16, 185, 129, 0.45);
    }
    .gl-icon-maint {
        background: rgba(14, 165, 233, 0.12);
        border: 1.5px solid rgba(14, 165, 233, 0.45);
    }
    .gl-icon-fac {
        background: rgba(168, 85, 247, 0.12);
        border: 1.5px solid rgba(168, 85, 247, 0.45);
    }
    .gl-icon-pol {
        background: rgba(20, 184, 166, 0.12);
        border: 1.5px solid rgba(20, 184, 166, 0.45);
    }
    .gl-feature-title {
        font-weight: 700;
        font-size: 0.98rem;
        color: #ffffff;
        margin-bottom: 6px;
    }
    .gl-feature-desc {
        font-size: 0.82rem;
        color: #94a3b8;
        line-height: 1.45;
    }

    /* Quick Questions Label */
    .gl-quick-label {
        display: flex;
        align-items: center;
        gap: 6px;
        color: #cbd5e1;
        font-size: 0.94rem;
        font-weight: 600;
        margin-bottom: 0.85rem;
    }
    .gl-quick-bolt {
        color: #f59e0b;
        font-size: 1.05rem;
    }

    /* Quick Questions button override */
    div[data-testid="column"] button {
        background: rgba(9, 29, 39, 0.75) !important;
        border: 1px solid rgba(20, 184, 166, 0.28) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        padding: 0.52rem 0.65rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25) !important;
    }
    div[data-testid="column"] button:hover {
        background: rgba(16, 185, 129, 0.16) !important;
        border-color: #00e599 !important;
        color: #ffffff !important;
        box-shadow: 0 0 16px rgba(0, 229, 153, 0.3) !important;
        transform: translateY(-1px) !important;
    }

    /* Pill-shaped Chat Input Form */
    [data-testid="stForm"] {
        background: rgba(7, 24, 34, 0.95) !important;
        border: 1px solid rgba(20, 184, 166, 0.3) !important;
        border-radius: 9999px !important;
        padding: 6px 14px 6px 18px !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.45) !important;
        transition: all 0.25s ease !important;
        margin-top: 1.2rem !important;
    }
    [data-testid="stForm"]:focus-within {
        border-color: #00e599 !important;
        box-shadow: 0 0 20px rgba(0, 229, 153, 0.3) !important;
    }
    [data-testid="stForm"] [data-testid="stTextInput"] input {
        background: transparent !important;
        border: none !important;
        color: #ffffff !important;
        font-size: 0.96rem !important;
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
        color: #022c1e !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 9999px !important;
        box-shadow: 0 0 18px rgba(0, 229, 153, 0.35) !important;
        width: 44px !important;
        min-width: 44px !important;
        height: 44px !important;
        padding: 0 !important;
        font-size: 1.15rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stForm"] button[kind="primary"]:hover {
        box-shadow: 0 0 26px rgba(0, 229, 153, 0.6) !important;
        transform: translateY(-1px) !important;
    }

    /* Input Attachment Clip */
    .gl-input-clip {
        display: flex;
        align-items: center;
        justify-content: center;
        color: #64748b;
        cursor: pointer;
    }

    /* Answer Card Styling */
    .gl-answer-card {
        background: rgba(7, 24, 34, 0.85);
        border: 1px solid rgba(0, 229, 153, 0.25);
        border-radius: 20px;
        padding: 26px 28px;
        box-shadow: 0 12px 36px rgba(0, 0, 0, 0.45);
        margin-top: 1.2rem;
        margin-bottom: 1.4rem;
        backdrop-filter: blur(16px);
    }
    .gl-user-message-row {
        display: flex;
        justify-content: flex-end;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 1.2rem;
    }
    .gl-user-bubble {
        background: linear-gradient(135deg, #094b3c 0%, #0d6954 100%);
        color: #ffffff;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        font-size: 0.98rem;
        font-weight: 500;
        line-height: 1.45;
        max-width: 75%;
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
        margin-bottom: 0.8rem;
    }

    .gl-bot-message-row {
        display: flex;
        align-items: flex-start;
        gap: 14px;
        margin-bottom: 1rem;
    }
    .gl-bot-avatar {
        width: 44px;
        height: 44px;
        border-radius: 14px;
        background: rgba(0, 229, 153, 0.14);
        border: 1px solid rgba(0, 229, 153, 0.35);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        box-shadow: 0 0 16px rgba(0, 229, 153, 0.25);
    }
    .gl-bot-bubble {
        background: #0b1e2a;
        border: 1px solid rgba(20, 184, 166, 0.18);
        border-radius: 4px 20px 20px 20px;
        padding: 20px 24px;
        color: #f1f5f9;
        font-size: 1.01rem;
        line-height: 1.65;
        flex-grow: 1;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .gl-bot-title {
        font-weight: 700;
        color: #00e599;
        font-size: 1.12rem;
        margin-bottom: 0.5rem;
    }
    .gl-bot-timestamp {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 8px;
    }

    /* Sources box styling */
    .gl-sources-box {
        background: rgba(4, 15, 22, 0.7);
        border: 1px solid rgba(20, 184, 166, 0.18);
        border-radius: 12px;
        padding: 14px 18px;
        margin-top: 14px;
    }
    .gl-sources-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.88rem;
        font-weight: 600;
        color: #00e599;
        margin-bottom: 10px;
    }
    .gl-source-item {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px;
        font-size: 0.83rem;
        color: #cbd5e1;
        padding: 6px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .gl-source-item:last-child {
        border-bottom: none;
    }
    .gl-source-badge {
        background: rgba(20, 184, 166, 0.14);
        border: 1px solid rgba(20, 184, 166, 0.25);
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.75rem;
        color: #00e599;
    }

    /* Sidebar Dark Styling */
    [data-testid="stSidebar"] {
        background: #061118 !important;
        border-right: 1px solid rgba(20, 184, 166, 0.18) !important;
    }

    /* Responsive Adjustments */
    @media (max-width: 900px) {
        .gl-trusted-grid {
            grid-template-columns: repeat(2, 1fr) !important;
            row-gap: 20px !important;
        }
        .gl-feature-col {
            border-right: none !important;
        }
    }
    @media (max-width: 640px) {
        .gl-trusted-grid {
            grid-template-columns: 1fr !important;
        }
        .gl-hero-heading {
            font-size: 2.1rem !important;
        }
        .gl-topbar {
            flex-direction: column !important;
            gap: 12px !important;
            align-items: flex-start !important;
        }
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
            now = datetime.now(kolkata_tz)
            st.session_state.timestamp = now.strftime("%I:%M %p")
            st.session_state.feedback = None
    except Exception:
        now = datetime.now(kolkata_tz)
        st.session_state.answer_result = {
            "answer": "The helpdesk could not answer this question. Please try again.",
            "sources": [],
        }
        st.session_state.timestamp = now.strftime("%I:%M %p")


# Current formatted date and time for Header in Asia/Kolkata
now_kolkata = datetime.now(kolkata_tz)
display_time = now_kolkata.strftime("%b %d, %Y %I:%M %p")

# Top Navigation Bar matching reference UI
st.markdown(
    f"""
    <div class="gl-topbar">
        <div class="gl-brand-group">
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 28C8 28 9.5 14 22 8.5C22 8.5 21 21 8 28Z" fill="#00e599"/>
                <path d="M16 28C16 28 20.5 19 29.5 14.5C29.5 14.5 27.5 24.5 16 28Z" fill="#10b981" fill-opacity="0.85"/>
            </svg>
            <div>
                <div class="gl-brand-name">GreenLeaf</div>
                <div class="gl-brand-sub">Residency</div>
            </div>
        </div>
        <div class="gl-top-right">
            <div class="gl-datetime-badge">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2">
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

# Hero Section (Two-column layout matching reference UI)
hero_col1, hero_col2 = st.columns([1.18, 0.82], vertical_alignment="center")

with hero_col1:
    st.markdown(
        """
        <div class="gl-hero-text-block">
            <div class="gl-helpdesk-pill">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 18v-6a9 9 0 0 1 18 0v6"></path>
                    <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"></path>
                </svg>
                <span>Helpdesk</span>
            </div>
            <h1 class="gl-hero-heading">How can we<br><span class="gl-accent-text">help you</span> today?</h1>
            <p class="gl-hero-desc">
                Our GreenLeaf Residency Helpdesk is a RAG-based AI chatbot that answers residents' questions about society rules, maintenance charges, facilities, and policies using uploaded documents, with supporting sources and privacy protection.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with hero_col2:
    st.markdown(
        """
        <div class="gl-hero-illustration">
            <svg viewBox="0 0 460 300" width="100%" height="auto" fill="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <radialGradient id="gl-glow" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stop-color="#00e599" stop-opacity="0.22" />
                        <stop offset="100%" stop-color="#00e599" stop-opacity="0" />
                    </radialGradient>
                    <linearGradient id="gl-bubble-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#00e599" />
                        <stop offset="100%" stop-color="#059669" />
                    </linearGradient>
                    <linearGradient id="gl-mini-bubble-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#14b8a6" />
                        <stop offset="100%" stop-color="#0d9488" />
                    </linearGradient>
                    <linearGradient id="gl-shield-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#00e599" />
                        <stop offset="100%" stop-color="#0f766e" />
                    </linearGradient>
                </defs>
                <!-- Soft Glow -->
                <circle cx="210" cy="140" r="130" fill="url(#gl-glow)" />
                <!-- Orbit Track -->
                <ellipse cx="230" cy="140" rx="160" ry="95" stroke="rgba(20, 184, 166, 0.3)" stroke-width="1.5" stroke-dasharray="5 7" />
                <!-- Orbit Leaf Accents -->
                <path d="M 320 60 C 320 60 326 48 338 46 C 338 46 336 56 320 60 Z" fill="#00e599" />
                <path d="M 105 210 C 105 210 98 220 86 220 C 86 220 90 210 105 210 Z" fill="#10b981" />
                <!-- Stacked Documents Behind -->
                <rect x="255" y="65" width="112" height="152" rx="10" transform="rotate(7 255 65)" fill="rgba(255, 255, 255, 0.15)" stroke="rgba(255, 255, 255, 0.25)" stroke-width="1.5" />
                <g transform="rotate(7 255 65)">
                    <rect x="268" y="80" width="50" height="4" rx="2" fill="rgba(255, 255, 255, 0.4)" />
                    <rect x="268" y="90" width="80" height="3" rx="1.5" fill="rgba(255, 255, 255, 0.25)" />
                    <rect x="268" y="98" width="75" height="3" rx="1.5" fill="rgba(255, 255, 255, 0.25)" />
                </g>
                <rect x="245" y="70" width="108" height="148" rx="8" fill="#e2e8f0" fill-opacity="0.95" stroke="rgba(255, 255, 255, 0.4)" stroke-width="1" />
                <rect x="260" y="86" width="55" height="5" rx="2.5" fill="#94a3b8" />
                <rect x="260" y="98" width="78" height="4" rx="2" fill="#cbd5e1" />
                <rect x="260" y="108" width="72" height="4" rx="2" fill="#cbd5e1" />
                <rect x="260" y="118" width="76" height="4" rx="2" fill="#cbd5e1" />
                <rect x="260" y="128" width="66" height="4" rx="2" fill="#cbd5e1" />
                <rect x="260" y="138" width="74" height="4" rx="2" fill="#cbd5e1" />
                <rect x="260" y="148" width="58" height="4" rx="2" fill="#cbd5e1" />
                <!-- Main Green Chat Bubble -->
                <path d="M 125 60 H 265 A 24 24 0 0 1 289 84 V 162 A 24 24 0 0 1 265 186 H 165 L 135 210 L 142 186 H 125 A 24 24 0 0 1 101 162 V 84 A 24 24 0 0 1 125 60 Z" fill="url(#gl-bubble-grad)" />
                <!-- Connected Turquoise Bubble -->
                <path d="M 235 92 H 285 A 12 12 0 0 1 297 104 V 132 A 12 12 0 0 1 285 144 H 255 L 244 154 L 247 144 H 235 A 12 12 0 0 1 223 132 V 104 A 12 12 0 0 1 235 92 Z" fill="url(#gl-mini-bubble-grad)" />
                <rect x="236" y="104" width="48" height="4" rx="2" fill="#ffffff" />
                <rect x="236" y="114" width="38" height="4" rx="2" fill="#ffffff" />
                <rect x="236" y="124" width="44" height="4" rx="2" fill="#ffffff" />
                <!-- Robot Character Inside Green Bubble -->
                <!-- Antenna -->
                <path d="M 165 88 V 97" stroke="#ffffff" stroke-width="3" stroke-linecap="round" />
                <circle cx="165" cy="85" r="4.5" fill="#00e599" stroke="#ffffff" stroke-width="2" />
                <!-- Ears / Headsets -->
                <rect x="132" y="110" width="6" height="16" rx="3" fill="#ffffff" />
                <rect x="192" y="110" width="6" height="16" rx="3" fill="#ffffff" />
                <!-- Head Body -->
                <rect x="136" y="97" width="58" height="44" rx="14" fill="#ffffff" />
                <!-- Dark Screen Face -->
                <rect x="144" y="103" width="42" height="30" rx="8" fill="#093d30" />
                <!-- Eyes -->
                <circle cx="154" cy="117" r="4.2" fill="#00e599" />
                <circle cx="176" cy="117" r="4.2" fill="#00e599" />
                <circle cx="155.5" cy="115.5" r="1.3" fill="#ffffff" />
                <circle cx="177.5" cy="115.5" r="1.3" fill="#ffffff" />
                <!-- Smile -->
                <path d="M 159 125 Q 165 129 171 125" stroke="#00e599" stroke-width="2.2" stroke-linecap="round" fill="none" />
                <!-- Security Shield with Padlock in Front-Right -->
                <path d="M 335 155 Q 365 155 365 175 C 365 208 335 226 335 226 C 335 226 305 208 305 175 Q 305 155 335 155 Z" fill="url(#gl-shield-grad)" stroke="#00e599" stroke-width="2" />
                <path d="M 330 184 V 177 A 5 5 0 0 1 340 177 V 184" stroke="#ffffff" stroke-width="2.2" fill="none" stroke-linecap="round" />
                <rect x="326" y="184" width="18" height="14" rx="3" fill="#ffffff" />
                <circle cx="335" cy="190" r="1.8" fill="#0f766e" />
                <path d="M 335 191 V 194" stroke="#0f766e" stroke-width="1.8" stroke-linecap="round" />
            </svg>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Main Content Area: Answer Card (when query active) or Trusted Information Card (when idle)
if st.session_state.current_question and st.session_state.answer_result:
    result = st.session_state.answer_result
    ts = st.session_state.timestamp or now_kolkata.strftime("%I:%M %p")

    ans_text = result.get("answer", "")
    formatted_ans = ans_text.replace("\n", "<br>")

    sources = result.get("sources", [])
    sources_html = ""
    if sources:
        sources_items = []
        for src in sources:
            source_file = html.escape(str(src.get("source", "Unknown")))
            sec = html.escape(str(src.get("section", "General")))
            page_num = html.escape(str(src.get("page", 1)))
            eff_date = src.get("effective_date")
            eff_badge = (
                f'<span class="gl-source-badge">Effective: {html.escape(str(eff_date))}</span>'
                if eff_date
                else ""
            )

            sources_items.append(
                f'<div class="gl-source-item">'
                f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00e599" stroke-width="2">'
                f'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>'
                f'<polyline points="14 2 14 8 20 8"></polyline>'
                f'</svg>'
                f'<strong style="color: #ffffff;">{source_file}</strong>'
                f'<span class="gl-source-badge">Page {page_num}</span>'
                f'<span class="gl-source-badge">Section: {sec}</span>'
                f'{eff_badge}'
                f'</div>'
            )
        sources_html = (
            f'<div class="gl-sources-box">'
            f'<div class="gl-sources-header">'
            f'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00e599" stroke-width="2">'
            f'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>'
            f'<polyline points="14 2 14 8 20 8"></polyline>'
            f'</svg>'
            f'<span>Verified Supporting Sources</span>'
            f'</div>'
            f'{"".join(sources_items)}'
            f'</div>'
        )

    st.markdown(
        f"""
        <div class="gl-answer-card">
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
            <div class="gl-bot-message-row">
                <div class="gl-bot-avatar">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <rect x="3" y="6" width="18" height="14" rx="4" fill="rgba(0, 229, 153, 0.2)" stroke="#00e599" stroke-width="1.8"/>
                        <circle cx="8.5" cy="12" r="1.5" fill="#00e599"/>
                        <circle cx="15.5" cy="12" r="1.5" fill="#00e599"/>
                        <path d="M9.5 15.5C10.5 16.5 13.5 16.5 14.5 15.5" stroke="#00e599" stroke-width="1.6" stroke-linecap="round"/>
                        <path d="M12 2V6" stroke="#00e599" stroke-width="1.8" stroke-linecap="round"/>
                        <circle cx="12" cy="2" r="1" fill="#00e599"/>
                    </svg>
                </div>
                <div class="gl-bot-bubble">
                    <div class="gl-bot-title">Answer</div>
                    <div>{formatted_ans}</div>
                    <div class="gl-bot-timestamp">{ts}</div>{sources_html}
                </div>
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

    # "Ask another question" button matching reference design
    st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
    reset_cols = st.columns([1, 1.4, 1])
    with reset_cols[1]:
        if st.button("🔄 Ask another question", key="btn_new_question", use_container_width=True):
            st.session_state.current_question = None
            st.session_state.answer_result = None
            st.session_state.feedback = None
            st.rerun()
else:
    # Trusted Information Card matching reference UI
    st.markdown(
        """
        <div class="gl-trusted-card">
            <div class="gl-trusted-header">
                <span class="gl-trusted-line"></span>
                <span class="gl-trusted-title">Get accurate answers with trusted sources</span>
                <span class="gl-trusted-line"></span>
            </div>
            <div class="gl-trusted-grid">
                <div class="gl-feature-col">
                    <div class="gl-feature-icon-circle gl-icon-rules">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#00e599" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                            <line x1="16" y1="13" x2="8" y2="13"></line>
                            <line x1="16" y1="17" x2="8" y2="17"></line>
                            <line x1="10" y1="9" x2="8" y2="9"></line>
                        </svg>
                    </div>
                    <div class="gl-feature-title">Society Rules</div>
                    <div class="gl-feature-desc">Know the rules and regulations of our community.</div>
                </div>
                <div class="gl-feature-col">
                    <div class="gl-feature-icon-circle gl-icon-maint">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2">
                            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
                        </svg>
                    </div>
                    <div class="gl-feature-title">Maintenance Charges</div>
                    <div class="gl-feature-desc">Get details about charges, payments and dues.</div>
                </div>
                <div class="gl-feature-col">
                    <div class="gl-feature-icon-circle gl-icon-fac">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#c084fc" stroke-width="2">
                            <rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect>
                            <line x1="9" y1="22" x2="9" y2="18"></line>
                            <line x1="15" y1="22" x2="15" y2="18"></line>
                            <line x1="9" y1="18" x2="15" y2="18"></line>
                            <line x1="8" y1="6" x2="10" y2="6"></line>
                            <line x1="14" y1="6" x2="16" y2="6"></line>
                            <line x1="8" y1="10" x2="10" y2="10"></line>
                            <line x1="14" y1="10" x2="16" y2="10"></line>
                        </svg>
                    </div>
                    <div class="gl-feature-title">Facilities</div>
                    <div class="gl-feature-desc">Explore amenities and common area services.</div>
                </div>
                <div class="gl-feature-col gl-feature-col-last">
                    <div class="gl-feature-icon-circle gl-icon-pol">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#14b8a6" stroke-width="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                            <polyline points="9 12 11 14 15 10"></polyline>
                        </svg>
                    </div>
                    <div class="gl-feature-title">Policies</div>
                    <div class="gl-feature-desc">Understand society policies, processes and guidelines.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Quick Questions Section matching reference UI
st.markdown(
    """
    <div class="gl-quick-label">
        <span class="gl-quick-bolt">⚡</span>
        <span>Quick questions</span>
    </div>
    """,
    unsafe_allow_html=True,
)

q_col1, q_col2, q_col3, q_col4, q_col5, q_col6 = st.columns(6)
with q_col1:
    if st.button("📄 Society rules", key="qq_guest", use_container_width=True):
        execute_question("What are the society rules and regulations?")
        st.rerun()
with q_col2:
    if st.button("🔧 Maintenance charges", key="qq_maint", use_container_width=True):
        execute_question("What is the monthly maintenance charge for a 2BHK flat?")
        st.rerun()
with q_col3:
    if st.button("🏢 Facilities", key="qq_pool", use_container_width=True):
        execute_question("What are the swimming pool timings?")
        st.rerun()
with q_col4:
    if st.button("🛡️ Policies", key="qq_pet", use_container_width=True):
        execute_question("What is the pet policy?")
        st.rerun()
with q_col5:
    if st.button("❓ Visitor entry", key="qq_parking", use_container_width=True):
        execute_question("What are the visitor entry and parking rules?")
        st.rerun()
with q_col6:
    if st.button("👥 Committee details", key="qq_gym", use_container_width=True):
        execute_question("Who are the managing committee members?")
        st.rerun()

# Question Input Area matching reference UI bottom bar
st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

with st.form("helpdesk_chat_form", clear_on_submit=True):
    form_cols = st.columns([0.05, 0.83, 0.12], vertical_alignment="center")
    with form_cols[0]:
        st.markdown(
            """
            <div class="gl-input-clip" title="Attach document (Admin managed)">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                </svg>
            </div>
            """,
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
            "➤",
            type="primary",
            help="Submit question",
        )

    if submit_btn:
        if not typed_query or not typed_query.strip():
            st.warning("Please type a question before asking the helpdesk.")
        else:
            execute_question(typed_query.strip())
            st.rerun()

# Sidebar: Resident Management / Document Updates (Admin Function)
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.6rem;">
            <div style="width: 32px; height: 32px; border-radius: 8px; background: rgba(0, 229, 153, 0.15); border: 1px solid rgba(0, 229, 153, 0.3); display: flex; align-items: center; justify-content: center;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00e599" stroke-width="2">
                    <rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect>
                    <line x1="9" y1="22" x2="9" y2="18"></line>
                    <line x1="15" y1="22" x2="15" y2="18"></line>
                    <line x1="9" y1="18" x2="15" y2="18"></line>
                </svg>
            </div>
            <span style="font-size: 1.1rem; font-weight: 700; color: #ffffff;">Admin Portal</span>
        </div>
        <p style="font-size: 0.82rem; color: #94a3b8; line-height: 1.5; margin-bottom: 1.2rem;">
            Upload official notices, bylaws, and circulars to update resident helpdesk retrieval and answers.
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
            <div style="width: 8px; height: 8px; border-radius: 50%; background: #00e599; box-shadow: 0 0 8px #00e599;"></div>
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
