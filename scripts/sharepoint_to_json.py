#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pull a Microsoft Excel Table from SharePoint via Microsoft Graph and write JSON for the frontend.

Required env:
  TENANT_ID, CLIENT_ID, CLIENT_SECRET
  SP_SITE_HOSTNAME, SP_SITE_PATH, SP_XLSX_PATH, SP_TABLE_NAME

Optional env (column overrides):
  SP_COL_SKU, SP_COL_MODEL, SP_COL_QTY

Output:
  public/data/service_stock.json  (array of {SKU, Model, Qty})
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

# -------------------- POKA-YOKE / SAFETY BOOTSTRAP --------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("sharepoint_to_json")

def die(msg: str, code: int = 2) -> None:
    log.error(msg)
    raise SystemExit(code)

def require_env(*names: str) -> Dict[str, str]:
    out = {}
    missing = []
    for n in names:
        v = os.getenv(n, "").strip()
        if not v:
            missing.append(n)
        else:
            out[n] = v
    if missing:
        die(
            "Missing required env vars: "
            + ", ".join(missing)
            + "\n➡️ Check GitHub Secrets / workflow env mapping."
        )
    return out

def to_int(x: Any) -> int:
    if x is None:
        return 0
    if isinstance(x, (int, float)):
        return int(x)
    s = str(x).strip()
    if not s:
        return 0
    s = s.replace(" ", "").replace("\u00a0", "")
    # keep digits and minus
    cleaned = "".join(ch for ch in s if ch.isdigit() or ch == "-")
    try:
        return int(cleaned) if cleaned else 0
    except Exception:
        return 0

def safe_str(x: Any) -> str:
    return "" if x is None else str(x).strip()

def normalize_site_path(raw: str) -> str:
    s = raw.strip()
    if not s.startswith("/"):
        s = "/" + s
    # Ensure /sites/ prefix (common Graph pattern)
    if not s.startswith("/sites/"):
        # If user provided something like "/Einhell_common"
        if s.startswith("/"):
            s = "/sites" + s
        else:
            s = "/sites/" + s
    return s

def normalize_drive_path(raw: str) -> str:
    # Graph expects "root:/path/to/file.xlsx"
    s = raw.strip().lstrip("/")
    return s

# -------------------- GRAPH CLIENT --------------------

GRAPH = "https://graph.microsoft.com/v1.0"

@dataclass
class GraphAuth:
    tenant_id: str
    client_id: str
    client_secret: str

def get_token(auth: GraphAuth) -> str:
    url = f"https://login.microsoftonline.com/{auth.tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": auth.client_id,
        "client_secret": auth.client_secret,
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default",
    }
    r = requests.post(url, data=data, timeout=40)
    if r.status_code != 200:
        die(f"Token request failed: HTTP {r.status_code} — {r.text[:400]}")
    token = r.json().get("access_token")
    if not token:
        die("Token response missing access_token.")
    return token

def graph_get(url: str, token: str, params: Optional[dict] = None, max_retries: int = 6) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    backoff = 2.0
    for attempt in range(1, max_retries + 1):
        r = requests.get(url, headers=headers, params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504):
            retry_after = r.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else backoff
            log.warning(f"Transient HTTP {r.status_code} on GET. attempt={attempt}/{max_retries} waiting={wait}s")
            time.sleep(wait)
            backoff = min(backoff * 1.8, 30)
            continue
        die(f"Graph GET failed: {url}\nHTTP {r.status_code} — {r.text[:600]}")
    die(f"Graph GET failed after retries: {url}")
    return {}  # unreachable

def pick_col(row: Dict[str, Any], candidates: List[str]) -> Any:
    # case-insensitive / whitespace-tolerant lookup
    norm = {k.strip().lower(): k for k in row.keys()}
    for c in candidates:
        k = norm.get(c.strip().lower())
        if k is not None:
            return row.get(k)
    return None

# -------------------- MAIN LOGIC --------------------

def main() -> None:
    env = require_env(
        "TENANT_ID", "CLIENT_ID", "CLIENT_SECRET",
        "SP_SITE_HOSTNAME", "SP_SITE_PATH", "SP_XLSX_PATH", "SP_TABLE_NAME",
    )

    auth = GraphAuth(env["TENANT_ID"], env["CLIENT_ID"], env["CLIENT_SECRET"])
    hostname = env["SP_SITE_HOSTNAME"].strip()
    site_path = normalize_site_path(env["SP_SITE_PATH"])
    xlsx_path = normalize_drive_path(env["SP_XLSX_PATH"])
    table_name = env["SP_TABLE_NAME"].strip()

    # Optional overrides
    col_sku_override = os.getenv("SP_COL_SKU", "").strip()
    col_model_override = os.getenv("SP_COL_MODEL", "").strip()
    col_qty_override = os.getenv("SP_COL_QTY", "").strip()

    log.info("🔐 Getting Graph token...")
    token = get_token(auth)

    log.info(f"🌐 Resolving site: {hostname}:{site_path}")
    site = graph_get(f"{GRAPH}/sites/{hostname}:{site_path}", token)
    site_id = site.get("id")
    if not site_id:
        die(f"Could not resolve site id from response: {site}")

    log.info(f"📄 Resolving file in site drive: /{xlsx_path}")
    item = graph_get(f"{GRAPH}/sites/{site_id}/drive/root:/{quote(xlsx_path)}", token)
    item_id = item.get("id")
    if not item_id:
        die(f"Could not resolve drive item id from response: {item}")

    # Get columns (names + index)
    log.info(f"📊 Loading table columns: {table_name}")
    cols_json = graph_get(
        f"{GRAPH}/sites/{site_id}/drive/items/{item_id}/workbook/tables/{quote(table_name)}/columns?$select=name,index",
        token,
    )
    cols = cols_json.get("value", [])
    if not cols:
        die("No columns returned. Check SP_TABLE_NAME (exact Excel table name).")
    cols_sorted = sorted(cols, key=lambda c: int(c.get("index", 0)))
    col_names = [c.get("name", "") for c in cols_sorted]

    log.info("✅ Table columns found: " + " | ".join(col_names))

    # Pull rows with pagination (rows endpoint supports @odata.nextLink)
    log.info("⬇️ Loading table rows...")
    rows_out: List[Dict[str, Any]] = []
    url = f"{GRAPH}/sites/{site_id}/drive/items/{item_id}/workbook/tables/{quote(table_name)}/rows?$top=500"
    while url:
        rows_json = graph_get(url, token)
        for r in rows_json.get("value", []):
            values = (r.get("values") or [[]])[0]
            row = {col_names[i]: (values[i] if i < len(values) else None) for i in range(len(col_names))}
            rows_out.append(row)
        url = rows_json.get("@odata.nextLink")

    if not rows_out:
        die("Parsed 0 rows from table. Possibly empty table or permission issue.")

    # Column candidates (your table shows: SKU, Qty, pcs, Model; and you said qty == 'Бронь для сервиса')
    sku_candidates = [col_sku_override] if col_sku_override else ["SKU", "Артикул", "Sku"]
    model_candidates = [col_model_override] if col_model_override else ["Model", "Модель", "Наименование", "Название"]
    qty_candidates = ([col_qty_override] if col_qty_override else [
        "Бронь для сервиса", "Бронь_для_сервиса", "Service reserve", "Service Reserve",
        "Qty, pcs", "Qty", "Количество", "Кол-во"
    ])

    items: List[Dict[str, Any]] = []
    for row in rows_out:
        sku = safe_str(pick_col(row, sku_candidates))
        if not sku:
            continue
        model = safe_str(pick_col(row, model_candidates))
        qty = to_int(pick_col(row, qty_candidates))
        items.append({"SKU": sku, "Model": model, "Qty": qty})

    # Stable order
    items.sort(key=lambda x: x["SKU"])

    out_path = Path("public/data/service_stock.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    out_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info(f"✅ DONE: wrote {len(items)} items → {out_path.as_posix()}")

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        log.exception("💥 Fatal error")
        die(str(e), code=1)
