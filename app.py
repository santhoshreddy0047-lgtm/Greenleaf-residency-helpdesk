import base64
import html
import logging
import os
from datetime import datetime
from pathlib import Path
from textwrap import dedent

try:
    from zoneinfo import ZoneInfo
    kolkata_tz = ZoneInfo("Asia/Kolkata")
except Exception:
    from datetime import timezone, timedelta
    kolkata_tz = timezone(timedelta(hours=5, minutes=30))

import streamlit as st
import streamlit.components.v1 as components

from src.answer import answer_question
from src.build_index import COLLECTION_NAME, create_client, index_documents
from src.config import UPDATES_DATA_DIR
from src.index_updates import load_update_documents

SUPPORTED_EXTENSIONS = ("pdf", "docx", "txt", "md")
BACKGROUND_IMAGE_PATH = (
    Path(__file__).resolve().parent
    / "assets"
    / "greenleaf_background.png"
)

try:
    BACKGROUND_IMAGE_DATA = base64.b64encode(
        BACKGROUND_IMAGE_PATH.read_bytes()
    ).decode("ascii")
except OSError as error:
    logging.getLogger(__name__).warning(
        "Helpdesk background image unavailable; using the default background: %s",
        error,
    )
    BACKGROUND_IMAGE_DATA = None

# Configure page settings
st.set_page_config(
    page_title="GreenLeaf Residency Helpdesk",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
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
    html,
    body,
    .stApp,
    [data-testid="stAppViewContainer"] {
        height: 100dvh;
        overflow: hidden;
    }

    .stApp {
        background:
                    radial-gradient(ellipse 34rem 26rem at 0% 0%, rgba(16, 185, 129, 0.16) 0%, transparent 76%),
                    radial-gradient(ellipse 30rem 34rem at 100% 8%, rgba(20, 184, 166, 0.12) 0%, transparent 76%),
                    radial-gradient(ellipse 32rem 24rem at 100% 100%, rgba(6, 182, 212, 0.1) 0%, transparent 78%),
                    radial-gradient(ellipse 90% 55% at 50% -10%, rgba(16, 185, 129, 0.08) 0%, transparent 70%),
                    linear-gradient(180deg, #040e14 0%, #06151c 45%, #030a0f 100%);
        color: #e2e8f0;
    }

    /* Main workspace */
    .block-container {
        box-sizing: border-box;
        max-width: 1600px;
        height: 100dvh;
        max-height: 100dvh;
        min-height: 0;
        overflow: hidden;
        padding: 0.65rem 1.15rem 0.65rem;
        margin: 0 auto;
    }
    .stMainBlockContainer > [data-testid="stVerticalBlock"] {
        height: 100%;
        min-height: 0;
        display: flex;
        flex-direction: column;
        gap: 0.5rem !important;
    }
    [data-testid="stMain"] {
        height: 100dvh;
        max-height: 100dvh;
        overflow: hidden;
    }
    .stMainBlockContainer > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has(.st-key-helpdesk-chat-experience) {
        display: flex;
        flex: 1 1 0;
        min-height: 0;
        overflow: hidden;
    }

    /* Hide default Streamlit chrome */
    #MainMenu, footer {
        visibility: hidden;
    }
    header[data-testid="stHeader"] {
        background: transparent;
    }
    [data-testid="stToolbar"] {
        background: transparent;
    }
    [data-testid="stAppDeployButton"] {
        display: none;
    }

    section[data-testid="stSidebar"] {
        width: clamp(250px, 20vw, 270px) !important;
        min-width: clamp(250px, 20vw, 270px) !important;
        max-width: clamp(250px, 20vw, 270px) !important;
        height: 100dvh;
        background: linear-gradient(180deg, #031116 0%, #041b20 55%, #021014 100%);
        border-right: 1px solid rgba(20, 184, 166, 0.18);
    }
    section[data-testid="stSidebar"] > div {
        width: inherit !important;
        height: 100dvh;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        display: flex;
        flex-direction: column;
        height: 100dvh;
        max-height: 100dvh;
        overflow: hidden;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        flex: 1 1 auto;
        height: calc(100dvh - 60px);
        max-height: calc(100dvh - 60px);
        min-height: 0;
        overflow: hidden;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div {
        height: 100%;
        min-height: 0;
        display: flex;
        flex-direction: column;
    }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.3rem;
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
        margin: 0.45rem 0 0.4rem;
    }
    .gl-quick-bolt {
        color: #f59e0b;
        font-size: 1.05rem;
    }

    /* Quick question chips */
    .st-key-helpdesk-quick-questions [data-testid="stColumn"] button {
        background: rgba(9, 29, 39, 0.75) !important;
        border: 1px solid rgba(20, 184, 166, 0.28) !important;
        border-radius: 999px !important;
        color: #e2e8f0 !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        padding: 0.35rem 0.45rem !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
    }
    .st-key-helpdesk-quick-questions [data-testid="stColumn"] button:hover {
        background: rgba(16, 185, 129, 0.16) !important;
        border-color: #00e599 !important;
        color: #ffffff !important;
        box-shadow: 0 0 16px rgba(0, 229, 153, 0.3) !important;
    }
    .st-key-helpdesk-quick-questions [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
        gap: 0.45rem;
    }
    .st-key-helpdesk-quick-questions [data-testid="stColumn"] {
        flex: 1 1 130px !important;
        min-width: 130px;
        width: auto !important;
    }

    /* Screenshot-inspired header with a local gradient fallback. */
    .gl-page-header {
        position: relative;
        display: flex;
        align-items: center;
        min-height: 132px;
        margin: -0.2rem -0.1rem 0.45rem;
        padding: 0.85rem 1.4rem;
        overflow: hidden;
        border: 1px solid rgba(20, 184, 166, 0.14);
        border-radius: 20px;
        background:
            radial-gradient(ellipse at 100% 12%, rgba(16, 185, 129, 0.2), transparent 34%),
            radial-gradient(ellipse at 0% 100%, rgba(20, 184, 166, 0.1), transparent 38%),
            linear-gradient(105deg, rgba(3, 16, 21, 0.97) 0%, rgba(5, 33, 40, 0.91) 58%, rgba(3, 20, 26, 0.84) 100%);
        box-shadow: inset 0 -50px 90px rgba(2, 13, 18, 0.25);
    }
    div[data-testid="stElementContainer"]:has(.gl-hero-text-block),
    div[data-testid="stElementContainer"]:has(.gl-hero-illustration),
    div[data-testid="stElementContainer"]:has(.gl-trusted-card) {
        display: none;
    }
    .gl-header-content {
        display: flex;
        align-items: center;
        gap: 1rem;
        max-width: 690px;
        position: relative;
        z-index: 1;
    }
    .gl-header-icon {
        width: 62px;
        height: 62px;
        flex: 0 0 62px;
        display: grid;
        place-items: center;
        border: 1px solid rgba(0, 229, 153, 0.38);
        border-radius: 16px;
        color: #69f0c1;
        background: rgba(0, 229, 153, 0.13);
        box-shadow: 0 0 28px rgba(0, 229, 153, 0.12);
    }
    .gl-header-eyebrow {
        margin: 0 0 0.2rem;
        color: #a8c2c9;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.09em;
        line-height: 1.2;
    }
    .gl-page-header .gl-header-title {
        margin: 0 0 0.35rem;
        padding: 0;
        color: #f8fafc;
        font-size: clamp(1.65rem, 2.5vw, 2.1rem);
        font-weight: 750;
        letter-spacing: -0.035em;
        line-height: 1.1;
    }
    .gl-header-description {
        max-width: 470px;
        margin: 0;
        color: #c1d2d8;
        font-size: 0.88rem;
        line-height: 1.4;
    }
    .gl-header-profile {
        position: absolute;
        top: 1rem;
        right: 1.2rem;
        display: flex;
        align-items: center;
        gap: 0.65rem;
    }
    .gl-header-time {
        padding: 0.4rem 0.7rem;
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 999px;
        color: #dbe7eb;
        background: rgba(3, 15, 20, 0.7);
        font-size: 0.68rem;
    }

    .st-key-helpdesk-chat-experience {
        box-sizing: border-box;
        display: flex;
        flex: 1 1 0;
        flex-direction: column;
        min-height: 0;
        gap: 0.45rem;
        overflow: hidden;
        padding: 1rem;
        border: 1px solid rgba(20, 184, 166, 0.58);
        border-radius: 22px;
        background:
            radial-gradient(ellipse at 95% 0%, rgba(16, 185, 129, 0.12), transparent 38%),
            linear-gradient(145deg, rgba(2, 29, 38, 0.94), rgba(3, 18, 27, 0.97));
        box-shadow: 0 14px 42px rgba(0, 0, 0, 0.3), inset 0 1px rgba(255, 255, 255, 0.025);
        backdrop-filter: blur(14px);
    }
    .st-key-helpdesk-chat-experience {
        align-items: stretch;
    }
    .st-key-helpdesk-chat-experience > [data-testid="stElementContainer"] {
        width: 100%;
    }
    .st-key-helpdesk-chat-experience [data-testid="stElementContainer"]:has(.gl-conversation-history) {
        display: flex;
        flex: 1 1 0;
        min-height: 0;
        overflow: hidden;
    }
    .st-key-helpdesk-chat-experience [data-testid="stMarkdown"]:has(.gl-conversation-history),
    .st-key-helpdesk-chat-experience [data-testid="stMarkdownContainer"]:has(.gl-conversation-history) {
        display: flex;
        flex: 1 1 auto;
        width: 100%;
        height: 100%;
        min-height: 0;
        overflow: hidden;
    }
    .gl-conversation-history {
        box-sizing: border-box;
        width: 100%;
        height: 100%;
        min-height: 0;
        overflow-y: auto;
        overscroll-behavior: contain;
        scrollbar-gutter: stable;
        scroll-behavior: smooth;
    }
    .st-key-helpdesk-chat-experience [data-testid="stLayoutWrapper"]:has(.st-key-helpdesk-chat-footer) {
        flex: 0 0 auto;
        margin-top: 0;
    }
    .st-key-helpdesk-chat-experience .gl-answer-card {
        padding: 0.6rem 0.25rem;
        border: 0;
        background: transparent;
        box-shadow: none;
        backdrop-filter: none;
    }
    .gl-chat-welcome {
        min-height: 0;
        width: 100%;
        box-sizing: border-box;
        flex: 1 1 auto;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 1.5rem 0.75rem;
        color: #a9c0c8;
        background: radial-gradient(ellipse at center, rgba(10, 67, 68, 0.12), transparent 70%);
        text-align: center;
    }
    .gl-chat-welcome strong {
        color: #f1f8f7;
        font-size: clamp(1.25rem, 2vw, 1.7rem);
    }
    .gl-chat-welcome span {
        margin-top: 0.55rem;
        color: #9eb4bc;
        font-size: 0.9rem;
    }
    .st-key-helpdesk-quick-questions {
        padding: 0.35rem 0.5rem;
        border: 1px solid rgba(20, 184, 166, 0.18);
        border-radius: 16px;
        background: rgba(5, 26, 33, 0.72);
        margin-bottom: 0.15rem;
    }
    .st-key-helpdesk-quick-questions [data-testid="stHorizontalBlock"] {
        gap: 0.35rem;
    }
    .st-key-qq_pool button {
        border-color: rgba(56, 189, 248, 0.45) !important;
        background: rgba(14, 116, 144, 0.16) !important;
    }
    .st-key-qq_maint button {
        border-color: rgba(52, 211, 153, 0.42) !important;
        background: rgba(5, 150, 105, 0.15) !important;
    }
    .st-key-qq_gym button {
        border-color: rgba(167, 139, 250, 0.45) !important;
        background: rgba(109, 40, 217, 0.14) !important;
    }
    .st-key-qq_parking button {
        border-color: rgba(251, 146, 60, 0.45) !important;
        background: rgba(194, 65, 12, 0.14) !important;
    }
    .st-key-qq_pet button {
        border-color: rgba(244, 114, 182, 0.45) !important;
        background: rgba(190, 24, 93, 0.13) !important;
    }
    .st-key-qq_guest button {
        border-color: rgba(34, 211, 238, 0.45) !important;
        background: rgba(8, 145, 178, 0.14) !important;
    }
    /* Compact, scoped chat composer */
    .st-key-helpdesk-chat-composer [data-testid="stForm"] {
        box-sizing: border-box;
        width: 100%;
        background: rgba(7, 24, 34, 0.95) !important;
        border: 1px solid rgba(20, 184, 166, 0.3) !important;
        border-radius: 9999px !important;
        padding: 3px 8px 3px 10px !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.45) !important;
        transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
        margin: 0.2rem 0 0 !important;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"]:focus-within {
        border-color: #00e599 !important;
        box-shadow: 0 0 20px rgba(0, 229, 153, 0.3) !important;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stTextInput"] input {
        background: transparent !important;
        border: none !important;
        color: #ffffff !important;
        font-size: 0.96rem !important;
        box-shadow: none !important;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stTextInput"] input:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stTextInput"] > div {
        background: transparent !important;
        border: none !important;
    }
    .st-key-helpdesk-chat-composer [data-testid="stTextInputRootElement"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stHorizontalBlock"] {
        width: 100%;
        flex-wrap: nowrap;
        align-items: center;
        gap: 0.4rem;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        min-width: 0;
        display: flex;
        align-items: center;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) {
        flex: 0 0 2.5rem !important;
        width: 2.5rem !important;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
        flex: 1 1 auto !important;
        width: auto !important;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) {
        flex: 0 0 2.75rem !important;
        width: 2.75rem !important;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {
        width: 100%;
        min-height: 44px;
        justify-content: center;
        gap: 0;
    }
    .st-key-helpdesk-chat-composer [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stElementContainer"] {
        display: flex;
        align-items: center;
        min-height: 44px;
        margin: 0;
    }
    .st-key-helpdesk-chat-composer [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stMarkdownContainer"] {
        display: flex;
        align-items: center;
        min-height: 44px;
        margin: 0;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stTextInput"] input {
        min-width: 0;
        box-sizing: border-box;
        width: 100%;
        padding-top: 0.55rem;
        padding-bottom: 0.55rem;
    }

    /* Send button */
    .st-key-helpdesk-chat-composer [data-testid="stForm"] button[kind="primaryFormSubmit"] {
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
    .st-key-helpdesk-chat-composer [data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {
        box-shadow: 0 0 26px rgba(0, 229, 153, 0.6) !important;
        transform: translateY(-1px) !important;
    }

    /* Input Attachment Clip */
    .st-key-helpdesk-chat-composer .gl-input-clip {
        width: 40px;
        height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #64748b;
        cursor: default;
    }
    .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) button {
        flex: 0 0 44px;
    }

    /* Keep the question-processing spinner and label compact and inline. */
    .st-key-helpdesk-question-loading [data-testid="stSpinner"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.5rem !important;
        margin: 0.35rem 0 !important;
        padding: 0 !important;
    }
    .st-key-helpdesk-question-loading [data-testid="stSpinner"] > div {
        display: flex !important;
        align-items: center !important;
        gap: 0.5rem !important;
        white-space: nowrap !important;
    }

    /* Answer Card Styling */
    .gl-answer-card {
        background: linear-gradient(145deg, rgba(2, 38, 45, 0.9), rgba(4, 27, 37, 0.92));
        border: 1px solid rgba(20, 184, 166, 0.52);
        border-radius: 18px;
        padding: 1rem 1.2rem;
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.22);
        margin: 0;
        backdrop-filter: blur(12px);
    }
    .gl-user-message-row {
        display: flex;
        justify-content: flex-end;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 0.8rem;
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
        padding: 16px 20px;
        color: #f1f5f9;
        font-size: 1.01rem;
        line-height: 1.65;
        flex-grow: 1;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        overflow-wrap: anywhere;
    }
    .gl-empty-chat {
        min-height: 70px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 0.75rem 1rem;
        border: 1px solid rgba(20, 184, 166, 0.2);
        border-radius: 18px;
        background:
            radial-gradient(ellipse at 75% 0%, rgba(13, 63, 72, 0.2), transparent 48%),
            linear-gradient(145deg, rgba(7, 32, 40, 0.78), rgba(5, 24, 32, 0.84));
        color: #dce8eb;
    }
    .gl-empty-chat strong {
        color: #f8fafc;
        font-size: 1.05rem;
    }
    .gl-empty-chat span {
        margin-top: 0.45rem;
        color: #9eb4bc;
        font-size: 0.87rem;
    }
    .gl-trusted-card {
        display: none;
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

    /* Sidebar navigation */
    .gl-sidebar-brand {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        margin: 0.1rem 0 0.65rem;
        color: #f8fafc;
    }
    .gl-sidebar-brand svg {
        flex: 0 0 40px;
    }
    .gl-sidebar-brand-name {
        font-weight: 750;
        font-size: 1.05rem;
        line-height: 1.15;
    }
    .gl-sidebar-brand-sub {
        color: #a8bbc2;
        font-size: 0.75rem;
    }
    .st-key-sidebar-navigation {
        width: 100%;
    }
    .st-key-sidebar-navigation > [data-testid="stVerticalBlock"] {
        gap: 0.4rem !important;
    }
    .st-key-sidebar-navigation [data-testid="stMarkdownContainer"] {
        margin: 0;
    }
    .st-key-sidebar-navigation .st-key-sidebar_home,
    .st-key-sidebar-navigation .st-key-sidebar_helpdesk,
    .st-key-sidebar-navigation .st-key-sidebar_facilities,
    .st-key-sidebar-navigation .st-key-sidebar_notices {
        width: 100%;
    }
    .st-key-sidebar-navigation .st-key-sidebar_home button,
    .st-key-sidebar-navigation .st-key-sidebar_facilities button,
    .st-key-sidebar-navigation .st-key-sidebar_notices button,
    .st-key-sidebar-navigation .gl-sidebar-active {
        box-sizing: border-box;
        display: flex;
        align-items: center;
        width: 100%;
        min-height: 48px;
        padding: 0 0.9rem;
        justify-content: flex-start;
        border-radius: 12px;
        color: #c6d5da;
        background: rgba(5, 31, 36, 0.72);
        border: 1px solid rgba(20, 184, 166, 0.18);
        font: inherit;
        font-size: 0.97rem;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
    }
    .st-key-sidebar-navigation .st-key-sidebar_home button p,
    .st-key-sidebar-navigation .st-key-sidebar_facilities button p,
    .st-key-sidebar-navigation .st-key-sidebar_notices button p {
        margin: 0;
        text-align: left;
        white-space: nowrap;
    }
    .st-key-sidebar-navigation .st-key-sidebar_home button > div,
    .st-key-sidebar-navigation .st-key-sidebar_facilities button > div,
    .st-key-sidebar-navigation .st-key-sidebar_notices button > div {
        justify-content: flex-start;
        gap: 0.75rem;
        width: 100%;
    }
    .st-key-sidebar-navigation .st-key-sidebar_home button [data-testid="stIconMaterial"],
    .st-key-sidebar-navigation .st-key-sidebar_facilities button [data-testid="stIconMaterial"],
    .st-key-sidebar-navigation .st-key-sidebar_notices button [data-testid="stIconMaterial"] {
        font-size: 1.25rem;
        flex: 0 0 1.25rem;
    }
    .st-key-sidebar-navigation .gl-sidebar-active svg {
        width: 20px;
        height: 20px;
        flex: 0 0 20px;
    }
    .st-key-sidebar-navigation .gl-sidebar-active span {
        margin-left: 0.25rem;
    }
    .st-key-sidebar-navigation .st-key-sidebar_home button:hover,
    .st-key-sidebar-navigation .st-key-sidebar_facilities button:hover,
    .st-key-sidebar-navigation .st-key-sidebar_notices button:hover {
        color: #f1f8f7;
        background: rgba(20, 184, 166, 0.14);
        border-color: rgba(20, 184, 166, 0.4);
    }
    .gl-sidebar-active {
        color: #72f2c4 !important;
        background: rgba(0, 229, 153, 0.12) !important;
        border-color: rgba(0, 229, 153, 0.32) !important;
        box-shadow: inset 3px 0 #39e6b0;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] .st-key-sidebar_logout {
        width: 100%;
        margin-top: 0.2rem;
    }
    section[data-testid="stSidebar"] .st-key-sidebar_logout button {
        box-sizing: border-box;
        width: 100%;
        min-height: 44px;
        justify-content: flex-start;
        border-radius: 12px;
        color: #8ea2a9;
        background: transparent;
        border: 1px solid rgba(20, 184, 166, 0.18);
    }
    section[data-testid="stSidebar"] .st-key-sidebar_logout button p {
        margin: 0;
        text-align: left;
        white-space: nowrap;
    }
    .st-key-sidebar_helpdesk {
        width: 100%;
    }
    .st-key-sidebar_helpdesk .gl-sidebar-active {
        display: flex;
        align-items: center;
        gap: 0;
        width: 100%;
        min-height: 48px;
        padding: 0 0.9rem;
    }
    .gl-sidebar-note {
        margin: -0.35rem 0 0.6rem;
        color: #81969e;
        font-size: 0.7rem;
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
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div {
            width: min(260px, 84vw) !important;
            min-width: min(260px, 84vw) !important;
            max-width: min(260px, 84vw) !important;
        }
        .st-key-helpdesk-chat-experience {
            padding: 0.65rem;
            border-radius: 16px;
        }
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
        .block-container {
            padding: 0.65rem 0.75rem 0.85rem;
        }
        .gl-page-header {
            min-height: 88px;
            padding: 0.55rem 0.65rem;
        }
        .gl-header-profile {
            top: 0.6rem;
            right: 0.6rem;
        }
        .gl-header-time {
            display: none;
        }
        .gl-header-content {
            gap: 0.55rem;
            margin-top: 0;
        }
        .gl-header-icon {
            width: 40px;
            height: 40px;
            flex-basis: 40px;
        }
        .gl-page-header .gl-header-title {
            margin-bottom: 0.15rem;
            font-size: 1.35rem;
        }
        .gl-header-description {
            max-width: 245px;
            font-size: 0.72rem;
            line-height: 1.25;
        }
        .st-key-helpdesk-quick-questions [data-testid="stHorizontalBlock"] {
            display: flex;
            flex-wrap: wrap;
            gap: 0.3rem;
        }
        .st-key-helpdesk-quick-questions [data-testid="stColumn"] {
            flex: 1 1 calc(50% - 0.3rem) !important;
            min-width: 0;
            width: calc(50% - 0.3rem) !important;
        }
        .st-key-helpdesk-chat-composer [data-testid="stForm"] {
            padding-right: 6px !important;
            padding-left: 6px !important;
        }
        .st-key-helpdesk-chat-composer [data-testid="stForm"] [data-testid="stHorizontalBlock"] {
            gap: 0.25rem;
        }
        .st-key-helpdesk-quick-questions button {
            min-height: 36px;
            padding: 0.25rem 0.2rem;
            font-size: 0.68rem;
            white-space: nowrap;
        }
        .gl-answer-card {
            padding: 0.6rem 0;
        }
        .gl-user-bubble {
            max-width: 88%;
        }
        .gl-bot-message-row {
            gap: 0.5rem;
        }
        .gl-bot-avatar {
            width: 34px;
            height: 34px;
        }
        .gl-bot-bubble {
            padding: 0.85rem;
            font-size: 0.92rem;
        }
    }
    @media (max-height: 820px) {
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.2rem;
        }
        .gl-sidebar-brand {
            margin-bottom: 0.35rem;
        }
        .st-key-sidebar-navigation > [data-testid="stVerticalBlock"] {
            gap: 0.2rem !important;
        }
        .st-key-sidebar-navigation .st-key-sidebar_home button,
        .st-key-sidebar-navigation .st-key-sidebar_facilities button,
        .st-key-sidebar-navigation .st-key-sidebar_notices button,
        .st-key-sidebar-navigation .gl-sidebar-active {
            min-height: 44px;
        }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            line-height: 1.25;
        }
        section[data-testid="stSidebar"] hr {
            margin: 0.35rem 0;
        }
        .gl-sidebar-note {
            margin-top: -0.45rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if BACKGROUND_IMAGE_DATA:
    st.markdown(
        f"""
        <style>
        .stApp {{
            isolation: isolate;
        }}
        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            z-index: -1;
            pointer-events: none;
            opacity: 0.3;
            background-image:
                linear-gradient(rgba(3, 14, 20, 0.58), rgba(3, 14, 20, 0.58)),
                url("data:image/png;base64,{BACKGROUND_IMAGE_DATA}");
            background-position: center;
            background-size: cover;
            background-repeat: no-repeat;
            mask-image: radial-gradient(
                ellipse 72% 70% at center,
                transparent 25%,
                rgba(0, 0, 0, 0.35) 65%,
                #000 100%
            );
            -webkit-mask-image: radial-gradient(
                ellipse 72% 70% at center,
                transparent 25%,
                rgba(0, 0, 0, 0.35) 65%,
                #000 100%
            );
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# Initialize Session State
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "answer_result" not in st.session_state:
    st.session_state.answer_result = None
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
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
        with st.container(key="helpdesk-question-loading"):
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
    st.session_state.conversation_history.append({
        "question": question_text,
        "answer_result": st.session_state.answer_result,
        "timestamp": st.session_state.timestamp,
    })


# Current formatted date and time for Header in Asia/Kolkata
now_kolkata = datetime.now(kolkata_tz)
display_time = now_kolkata.strftime("%b %d, %Y %I:%M %p")

# Top Navigation Bar matching reference UI
st.markdown(
    f"""
    <div class="gl-page-header">
        <div class="gl-header-profile">
            <span class="gl-header-time">{display_time}</span>
            <span class="gl-avatar-badge">GR</span>
        </div>
        <div class="gl-header-content">
            <div class="gl-header-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 18v-6a9 9 0 0 1 18 0v6"></path>
                    <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"></path>
                </svg>
            </div>
            <div>
                <p class="gl-header-eyebrow">GREENLEAF RESIDENCY</p>
                <h1 class="gl-header-title">Helpdesk</h1>
                <p class="gl-header-description">Ask anything about our society rules, facilities, charges and community policies.</p>
            </div>
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
            <svg viewBox="0 0 460 300" width="100%" height="300" fill="none" xmlns="http://www.w3.org/2000/svg">
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


def render_history_card(turn):
    question = html.escape(str(turn.get("question", "")))
    result = turn.get("answer_result") or {}
    answer = html.escape(str(result.get("answer", ""))).replace("\n", "<br>")
    timestamp = html.escape(str(turn.get("timestamp") or ""))

    sources = []
    for source in result.get("sources", []):
        source_name = html.escape(str(source.get("source", "Unknown")))
        page = html.escape(str(source.get("page", 1)))
        section = html.escape(str(source.get("section", "General")))
        effective_date = source.get("effective_date")
        effective_badge = (
            f'<span class="gl-source-badge">Effective: '
            f'{html.escape(str(effective_date))}</span>'
            if effective_date
            else ""
        )
        sources.append(
            f'<div class="gl-source-item">'
            f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00e599" stroke-width="2">'
            f'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>'
            f'<polyline points="14 2 14 8 20 8"></polyline>'
            f'</svg>'
            f'<strong style="color: #ffffff;">{source_name}</strong>'
            f'<span class="gl-source-badge">Page {page}</span>'
            f'<span class="gl-source-badge">Section: {section}</span>'
            f'{effective_badge}</div>'
        )
    sources_html = ""
    if sources:
        sources_html = (
            '<div class="gl-sources-box">'
            '<div class="gl-sources-header">'
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00e599" stroke-width="2">'
            '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>'
            '<polyline points="14 2 14 8 20 8"></polyline>'
            '</svg>'
            '<span>Verified Supporting Sources</span>'
            '</div>'
            f'{"".join(sources)}</div>'
        )

    return dedent(
        f"""
        <div class="gl-answer-card">
            <div class="gl-user-message-row">
                <div class="gl-user-bubble">{question}</div>
                <div class="gl-user-avatar-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                        <circle cx="12" cy="7" r="4"></circle>
                    </svg>
                </div>
            </div>
            <div class="gl-user-meta">{timestamp} &#10003;&#10003;</div>
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
                    <div>{answer}</div>
                    <div class="gl-bot-timestamp">{timestamp}</div>
                    {sources_html}
                </div>
            </div>
        </div>
        """
    ).strip()


# Unified conversation, quick-question, and composer card.
with st.container(key="helpdesk-chat-experience"):
    history_to_render = list(st.session_state.conversation_history)
    current_question = st.session_state.current_question
    current_result = st.session_state.answer_result
    if current_question and current_result:
        current_turn = {
            "question": current_question,
            "answer_result": current_result,
            "timestamp": st.session_state.timestamp or now_kolkata.strftime("%I:%M %p"),
        }
        current_turn_is_stored = (
            bool(history_to_render)
            and history_to_render[-1].get("question") == current_turn["question"]
            and history_to_render[-1].get("answer_result") == current_turn["answer_result"]
        )
        if not current_turn_is_stored:
            history_to_render.append(current_turn)

    history_markup = "".join(
        render_history_card(turn)
        for turn in history_to_render
    )
    if not history_to_render:
        history_markup = dedent(
            """
            <div class="gl-chat-welcome">
                <strong>Welcome to GreenLeaf Helpdesk</strong>
                <span>Ask about society rules, facilities, charges, notices or policies. Answers are grounded in GreenLeaf documents.</span>
            </div>
            """
        ).strip()
    elif not current_question or not current_result:
        history_markup += (
            '<div class="gl-chat-welcome">'
            '<strong>Your conversation history is above.</strong>'
            '<span>Ask another question below.</span>'
            '</div>'
        )

    st.markdown(
        f'<div class="gl-conversation-history">{history_markup}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.current_question and st.session_state.answer_result:
        components.html(
            """
            <script>
              const conversation = window.parent.document.querySelector(
                ".gl-conversation-history"
              );
              if (conversation) {
                conversation.scrollTop = conversation.scrollHeight;
              }
            </script>
            """,
            height=0,
        )

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

        reset_cols = st.columns([1, 1.4, 1])
        with reset_cols[1]:
            if st.button("🔄 Ask another question", key="btn_new_question", use_container_width=True):
                st.session_state.current_question = None
                st.session_state.answer_result = None
                st.session_state.feedback = None
                st.rerun()

    # Quick questions grounded in the current knowledge base
    with st.container(key="helpdesk-chat-footer"):
        st.markdown(
            """
            <div class="gl-quick-label">
                <span class="gl-quick-bolt">✦</span>
                <span>Quick questions</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(key="helpdesk-quick-questions"):
            quick_questions = [
                ("🌊  Pool timings", "What are the swimming pool timings?", "qq_pool"),
                ("💳  Maintenance charges", "What is the monthly maintenance charge for a 2BHK flat?", "qq_maint"),
                ("🏋️  Gym rules", "What are the gym rules and opening hours?", "qq_gym"),
                ("🚘  Parking rules", "What are the parking rules for residents and visitors?", "qq_parking"),
                ("🐾  Pet policy", "What is the GreenLeaf Residency pet policy?", "qq_pet"),
                ("👥  Guest rules", "What rules apply to guests and visitors at GreenLeaf Residency?", "qq_guest"),
            ]
            quick_columns = st.columns(6)
            for column, (label, question, key) in zip(quick_columns, quick_questions):
                with column:
                    if st.button(label, key=key, use_container_width=True):
                        execute_question(question)
                        st.rerun()

        # Question Input Area matching reference UI bottom bar
        with st.container(key="helpdesk-chat-composer"):
            with st.form("helpdesk_chat_form", clear_on_submit=True):
                form_cols = st.columns([0.08, 0.80, 0.12], vertical_alignment="center")
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
        <div class="gl-sidebar-brand">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true">
                <path d="M5 25C5 25 7 10 21 5C21 5 20 20 5 25Z" fill="#00e599"/>
                <path d="M16 31C16 31 21 18 35 12C35 12 32 27 16 31Z" fill="#10b981"/>
            </svg>
            <div><div class="gl-sidebar-brand-name">GreenLeaf</div><div class="gl-sidebar-brand-sub">Residency</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="sidebar-navigation"):
        if st.button("Home", icon=":material/home:", key="sidebar_home", use_container_width=True):
            st.session_state.current_question = None
            st.session_state.answer_result = None
            st.session_state.conversation_history.clear()
            st.session_state.feedback = None
            st.rerun()
        with st.container(key="sidebar_helpdesk"):
            st.markdown(
                """
                <div class="gl-sidebar-active" aria-current="page">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <path d="M3 13v-1a9 9 0 0 1 18 0v1"></path>
                        <path d="M5 12h2a2 2 0 0 1 2 2v4H7a4 4 0 0 1-4-4v-1a1 1 0 0 1 1-1Z"></path>
                        <path d="M19 12h-2a2 2 0 0 0-2 2v4h2a4 4 0 0 0 4-4v-1a1 1 0 0 0-1-1Z"></path>
                        <path d="M17 18a5 5 0 0 1-5 3h-2"></path>
                    </svg>
                    <span>Helpdesk</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if st.button("Facilities", icon=":material/apartment:", key="sidebar_facilities", use_container_width=True):
            execute_question("What facilities and amenities are available at GreenLeaf Residency?")
            st.rerun()
        if st.button("Notices", icon=":material/campaign:", key="sidebar_notices", use_container_width=True):
            execute_question("What are the latest society notices and their effective dates?")
            st.rerun()

    st.divider()
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
        <p style="font-size: 0.76rem; color: #94a3b8; line-height: 1.35; margin-bottom: 0.55rem;">
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
    except Exception as error:
        status_label = (
            f"Knowledge base status unavailable ({type(error).__name__})"
        )

    st.markdown(
        f"""
        <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 8px; padding: 7px 10px; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 8px;">
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
    st.divider()
    st.button(
        "Logout",
        icon=":material/logout:",
        key="sidebar_logout",
        disabled=True,
        help="Sign-in and logout are not configured for this application.",
        use_container_width=True,
    )
    st.markdown(
        '<p class="gl-sidebar-note">Sign-in is not enabled</p>',
        unsafe_allow_html=True,
    )
