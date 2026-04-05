import streamlit as st


LIGHT_THEME = {
    "bg": "#f5f7fb",
    "panel": "#ffffff",
    "panel_alt": "#eef2ff",
    "text": "#101828",
    "muted": "#475467",
    "line": "#d0d5dd",
    "accent": "#0f62fe",
    "accent_soft": "#dbe7ff",
    "glow": "rgba(15, 98, 254, 0.16)",
}


DARK_THEME = {
    "bg": "#0b1020",
    "panel": "#11172a",
    "panel_alt": "#162038",
    "text": "#f5f7fb",
    "muted": "#b7c0d4",
    "line": "#26324b",
    "accent": "#7cb3ff",
    "accent_soft": "#18294d",
    "glow": "rgba(124, 179, 255, 0.18)",
}


def get_theme(mode: str):
    if mode == "dark":
        return DARK_THEME
    return LIGHT_THEME


def init_shell_state():
    if "ui_theme_mode" not in st.session_state:
        st.session_state.ui_theme_mode = "light"
    if "ui_active_module" not in st.session_state:
        st.session_state.ui_active_module = "render"
    if "render_focus" not in st.session_state:
        st.session_state.render_focus = "engine"


def inject_global_styles(mode: str):
    theme = get_theme(mode)
    st.markdown(
        f"""
<style>
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    [data-testid="collapsedControl"],
    header[data-testid="stHeader"],
    #MainMenu,
    footer {{
        display: none !important;
    }}

    .stApp {{
        background: {theme["bg"]};
        color: {theme["text"]};
    }}

    .block-container {{
        max-width: 100%;
        padding-top: 1rem;
        padding-left: 2rem;
        padding-right: 2rem;
        padding-bottom: 2rem;
    }}

    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stMarkdownContainer"] span,
    label,
    .stCaption,
    .stText,
    .stSelectbox label,
    .stTextInput label,
    .stNumberInput label,
    .stCheckbox label,
    .stRadio label {{
        color: {theme["text"]};
    }}

    .shell-card,
    .shell-panel,
    .shell-hero,
    .shell-nav {{
        border: 1px solid {theme["line"]};
        background: linear-gradient(180deg, color-mix(in srgb, {theme["panel"]} 94%, #ffffff 6%) 0%, {theme["panel"]} 100%);
        border-radius: 24px;
        box-shadow: 0 18px 55px rgba(15, 23, 42, 0.08);
    }}

    .shell-hero {{
        padding: 1.6rem 1.8rem;
        margin-bottom: 1.25rem;
    }}

    .shell-hero h1 {{
        margin: 0;
        font-size: 2.1rem;
        line-height: 1.08;
        letter-spacing: -0.04em;
        color: {theme["text"]};
    }}

    .shell-hero p {{
        margin: 0.7rem 0 0 0;
        color: {theme["muted"]};
        font-size: 1rem;
        line-height: 1.6;
        max-width: 58rem;
    }}

    .shell-nav {{
        padding: 1rem;
        margin-top: 0.25rem;
    }}

    .shell-kicker {{
        display: inline-block;
        padding: 0.32rem 0.72rem;
        border-radius: 999px;
        background: {theme["accent_soft"]};
        color: {theme["accent"]};
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.8rem;
    }}

    .shell-section-title {{
        margin: 0 0 0.35rem 0;
        font-size: 1.35rem;
        line-height: 1.2;
        letter-spacing: -0.03em;
        color: {theme["text"]};
    }}

    .shell-section-copy {{
        margin: 0;
        color: {theme["muted"]};
        font-size: 0.96rem;
        line-height: 1.6;
    }}

    .shell-status-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 0.9rem;
        margin: 1rem 0 1.4rem 0;
    }}

    .shell-status-item {{
        padding: 1rem 1.05rem;
        border-radius: 18px;
        background: color-mix(in srgb, {theme["panel_alt"]} 55%, {theme["panel"]} 45%);
        border: 1px solid {theme["line"]};
    }}

    .shell-status-label {{
        display: block;
        font-size: 0.74rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {theme["muted"]};
        margin-bottom: 0.4rem;
    }}

    .shell-status-value {{
        display: block;
        font-size: 0.98rem;
        line-height: 1.45;
        color: {theme["text"]};
        word-break: break-word;
    }}

    .stButton > button {{
        width: 100%;
        border-radius: 18px;
        border: 1px solid {theme["line"]};
        background: linear-gradient(180deg, color-mix(in srgb, {theme["panel"]} 92%, #ffffff 8%) 0%, color-mix(in srgb, {theme["panel"]} 97%, #000000 3%) 100%);
        color: {theme["text"]};
        min-height: 3rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
    }}

    .stButton > button:hover {{
        border-color: {theme["accent"]};
        color: {theme["accent"]};
        box-shadow: 0 14px 34px rgba(15, 23, 42, 0.12);
    }}

    .stButton > button[kind="primary"] {{
        background: linear-gradient(180deg, {theme["accent"]} 0%, color-mix(in srgb, {theme["accent"]} 72%, #000000 28%) 100%);
        border-color: transparent;
        color: white;
        box-shadow: 0 16px 36px {theme["glow"]};
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 1.5rem;
        background: transparent;
        border-bottom: 1px solid {theme["line"]};
        margin-bottom: 1.5rem;
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 0;
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        padding: 0.5rem 0;
        color: {theme["muted"]};
        font-weight: 500;
        height: auto;
    }}

    .stTabs [aria-selected="true"] {{
        background: transparent;
        color: {theme["text"]};
        border-color: {theme["text"]};
    }}

    .stTextInput > div > div > input,
    .stNumberInput input,
    .stSelectbox [data-baseweb="select"] > div,
    .stTextArea textarea {{
        border-radius: 6px !important;
        border: 1px solid {theme["line"]} !important;
        background: transparent !important;
        color: {theme["text"]} !important;
    }}

    .stRadio > div,
    .stCheckbox {{
        color: {theme["text"]};
    }}

    .stAlert {{
        border-radius: 6px;
    }}

    div[data-testid="stExpander"] {{
        border: 1px solid {theme["line"]};
        border-radius: 6px;
        background: transparent;
        overflow: hidden;
    }}

    div[data-testid="stExpander"] details summary {{
        background: transparent;
        border-radius: 6px;
    }}

    .stProgress > div > div > div > div {{
        background: {theme["text"]};
    }}

    .shell-inline-note {{
        display: none;
    }}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_shell_hero(title: str, body: str = ""):
    body_html = f"<p>{body}</p>" if body else ""
    st.markdown(
        f"""
<section class="shell-hero">
    <h1>{title}</h1>
    {body_html}
</section>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(kicker: str, title: str, body: str = ""):
    st.markdown(
        f"""
<div style="margin-bottom: 1rem;">
    <h2 class="shell-section-title">{title}</h2>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_status_grid(items):
    blocks = []
    for label, value in items:
        blocks.append(
            f"""
<div class="shell-status-item">
    <span class="shell-status-label">{label}</span>
    <span class="shell-status-value">{value}</span>
</div>
            """
        )
    st.markdown(
        f'<div class="shell-status-grid">{"".join(blocks)}</div>',
        unsafe_allow_html=True,
    )
