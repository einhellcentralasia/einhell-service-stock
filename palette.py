# palette.py
# Centralized theme colors. Change hex codes here only.

THEMES = {
    "Light": {
        "bg": "#ffffff",
        "card": "#f3f4f6",
        "text": "#0f172a",
        "muted": "#475569",
        "accent": "#0071e3",
        "border": "rgba(15,23,42,0.15)",
        # Explicit controls for the file-uploader button (fix unreadable text)
        "uploader_btn_bg": "#eef1f5",
        "uploader_btn_text": "#0b1220",
        "uploader_btn_bg_hover": "#e6e9ee",
        "uploader_btn_border": "rgba(15,23,42,0.25)",
    }
}

def build_css(light: dict) -> str:
    """Return CSS for the single (light) palette with strong overrides."""
    return f"""
<style>
:root, .light-theme {{
  --bg: {light['bg']};
  --card: {light['card']};
  --text: {light['text']};
  --muted: {light['muted']};
  --accent: {light['accent']};
  --border: {light['border']};
  --upl-btn-bg: {light['uploader_btn_bg']};
  --upl-btn-text: {light['uploader_btn_text']};
  --upl-btn-bg-hover: {light['uploader_btn_bg_hover']};
  --upl-btn-border: {light['uploader_btn_border']};
}}

html, body, .stApp, [data-testid="stAppViewContainer"] {{
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}}

[data-testid="stHeader"] {{
  background: var(--bg) !important;
  border-bottom: 1px solid var(--border);
}}

h1, h2, h3, .stMarkdown, .stText, .stCaption, label, p, span, div {{
  color: var(--text) !important;
}}
small, .muted {{ color: var(--muted) !important; }}

.block-container {{ padding-top: 2rem !important; }}
section.main > div {{ border-radius: 18px; }}

.stButton>button, .stDownloadButton>button {{
  border-radius: 12px;
  padding: 8px 14px;
  border: 1px solid var(--border) !important;
  background: var(--card) !important;
  color: var(--text) !important;
}}
.stButton>button:hover, .stDownloadButton>button:hover {{ border-color: var(--accent) !important; }}

.header-row {{ display:flex; align-items:center; gap:1rem; margin-bottom:.5rem; }}
.header-row .grow {{ flex:1; }}
.header-pill {{
  display:inline-flex; gap:6px; align-items:center; padding:6px 10px;
  border-radius:999px; background: var(--card);
  border:1px solid var(--border); color: var(--text);
}}

/* ---------- File uploader: HIGH-CONTRAST BUTTON ---------- */
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {{
  background: var(--card) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
}}

[data-testid="stFileUploader"] button {{
  /* Force readable button regardless of viewer shell theme */
  background-color: var(--upl-btn-bg) !important;
  color: var(--upl-btn-text) !important;
  border: 1px solid var(--upl-btn-border) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
}}
[data-testid="stFileUploader"] button * {{
  color: var(--upl-btn-text) !important;   /* text inside the button */
}}
[data-testid="stFileUploader"] button:hover {{
  background-color: var(--upl-btn-bg-hover) !important;
  border-color: var(--upl-btn-border) !important;
}}
</style>
"""
