#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate public/styles.css from palette.py.

poka-yoke: works with multiple palette.py formats:
- PALETTE dict
- LIGHT/DARK dicts
- uppercase vars like BRAND, BG, etc.

Writes:
  public/styles.css
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("generate_css")

DEFAULT_LIGHT = {
    "brand": "#E2001A",
    "bg": "#ffffff",
    "bg2": "#f5f5f7",
    "ink": "#1c1c1e",
    "muted": "#6b7280",
    "card": "#f8f9fb",
    "border": "#e5e7eb",
    "accent": "#111111",
}
DEFAULT_DARK = {
    "bg": "#1c1c1e",
    "bg2": "#161618",
    "ink": "#f2f2f7",
    "muted": "#a1a1a6",
    "card": "#2c2c2e",
    "border": "#3a3a3c",
    "accent": "#f2f2f7",
}

def load_palette_module(path: Path):
    spec = importlib.util.spec_from_file_location("palette", str(path))
    if not spec or not spec.loader:
        raise RuntimeError("Could not import palette.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def safe_dict(obj: Any) -> Dict[str, Any]:
    return obj if isinstance(obj, dict) else {}

def extract_palettes(mod) -> tuple[Dict[str, str], Dict[str, str]]:
    # Try PALETTE = {"light": {...}, "dark": {...}}
    p = safe_dict(getattr(mod, "PALETTE", None))
    light = safe_dict(p.get("light"))
    dark = safe_dict(p.get("dark"))

    # Try LIGHT / DARK dicts
    if not light:
        light = safe_dict(getattr(mod, "LIGHT", None))
    if not dark:
        dark = safe_dict(getattr(mod, "DARK", None))

    # Try uppercase vars
    # (only fills missing keys; doesn’t override dicts you already have)
    for key, var in [
        ("brand", "BRAND"),
        ("bg", "BG"),
        ("bg2", "BG2"),
        ("ink", "INK"),
        ("muted", "MUTED"),
        ("card", "CARD"),
        ("border", "BORDER"),
        ("accent", "ACCENT"),
    ]:
        if key not in light and hasattr(mod, var):
            light[key] = str(getattr(mod, var))

    # merge with defaults
    out_light = {**DEFAULT_LIGHT, **{k: str(v) for k, v in light.items() if v}}
    out_dark = {**DEFAULT_DARK, **{k: str(v) for k, v in dark.items() if v}}

    # ensure brand exists in dark too
    if "brand" not in out_dark:
        out_dark["brand"] = out_light["brand"]

    return out_light, out_dark

def css_vars(d: Dict[str, str]) -> str:
    return "\n".join([f"  --{k}:{v};" for k, v in d.items()])

def main() -> None:
    palette_path = Path("palette.py")
    light, dark = DEFAULT_LIGHT, DEFAULT_DARK

    try:
        if palette_path.exists():
            mod = load_palette_module(palette_path)
            light, dark = extract_palettes(mod)
            log.info("✅ Loaded palette.py")
        else:
            log.warning("palette.py not found; using defaults")
    except Exception:
        log.exception("Failed to load palette.py; using defaults")

    out = f""":root{{
{css_vars(light)}
}}
html[data-theme="dark"]{{
{css_vars(dark)}
}}
"""
    out_path = Path("public/styles.css")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")
    log.info(f"✅ DONE: wrote {out_path.as_posix()}")

if __name__ == "__main__":
    main()
