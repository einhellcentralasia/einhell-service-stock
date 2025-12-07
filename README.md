# Einhell — Service Reserve Stock

Frontend: `public/index.html`  
Data source: SharePoint Excel table (Graph API)  
Deploy: Cloudflare Pages (Direct Upload from GitHub Actions)

## GitHub Secrets required

Microsoft Graph:
- TENANT_ID
- CLIENT_ID
- CLIENT_SECRET
- SP_SITE_HOSTNAME
- SP_SITE_PATH
- SP_XLSX_PATH
- SP_TABLE_NAME

Cloudflare Pages:
- CF_API_TOKEN
- CF_ACCOUNT_ID
- CF_PROJECT_NAME

Optional (only if your Excel columns are non-standard):
- SP_COL_SKU
- SP_COL_MODEL
- SP_COL_QTY

## What happens
- Every 3 hours workflow `Update service stock JSON` pulls the Excel Table and writes:
  - `public/data/service_stock.json`
- Also generates `public/styles.css` from `palette.py`
- Any push to `main` triggers Cloudflare Pages deploy.

## Cloudflare setup (one-time)
Create a Pages project named exactly like `CF_PROJECT_NAME` (Direct Upload is fine).
