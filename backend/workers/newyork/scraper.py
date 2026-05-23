"""
New York State Contract Reporter scraper.

Approach:
1. Load https://www.nyscr.ny.gov/Ads/Search (sets session cookies, shows 999 results)
2. Click "Download PDF" → /Ads/GenerateSearchPdf — takes ~30-60s to generate
3. Save the PDF to a temp file
4. Parse the PDF with pypdf — each record spans multiple lines with labeled fields

PDF record format (one record per block, fields on separate lines):
  Title: <title>
  CR#: <cr_number>
  Agency: <agency>          (or Company: <company> for Contractor Ads)
  Division: <division>      (optional)
  Issue Date: <mm/dd/yyyy>
  Due date <mm/dd/yyyy>
  Location: <location>      (optional)
  Category: <category>
  Ad type: <ad_type>

Fields extracted:
  CR#        → source_record_id  (100%)
  Title      → title             (100%)
  Agency     → buyer_name        (100%, falls back to Company)
  Division   → raw_payload only
  Issue Date → posted_date       (100%)
  Due date   → deadline          (100%)
  Location   → raw_payload only
  Category   → industry          (100%)
  Ad type    → notice_type       (100%)
"""

from __future__ import annotations

import os
import re
import tempfile
import unicodedata

from pypdf import PdfReader
from playwright.async_api import async_playwright

SEARCH_URL = "https://www.nyscr.ny.gov/Ads/Search"
SOURCE_URL_BASE = "https://www.nyscr.ny.gov/Ads/Details/"

# Ligature normalization map (PDF fonts often embed ligatures as single chars)
_LIGATURES = {
    "\ufb01": "fi",  # ﬁ
    "\ufb02": "fl",  # ﬂ
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb00": "ff",
    "\ufb05": "st",
    "\ufb06": "st",
}


def _normalize(text: str) -> str:
    """Replace PDF ligature characters with ASCII equivalents."""
    for lig, repl in _LIGATURES.items():
        text = text.replace(lig, repl)
    return text


def _extract_lines_from_pdf(pdf_path: str) -> list[str]:
    """Extract all non-empty text lines from a PDF using pypdf."""
    reader = PdfReader(pdf_path)
    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        for raw in text.splitlines():
            clean = _normalize(raw).strip()
            if clean:
                lines.append(clean)
    return lines


def parse_pdf_records(pdf_path: str) -> list[dict[str, str]]:
    """
    Parse the NYSCR PDF and extract all contracting opportunity records.

    Each record is a block of labeled lines. Records are separated by a new
    'Title:' line. Fields can wrap across lines (e.g. long titles, locations).
    """
    lines = _extract_lines_from_pdf(pdf_path)

    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    current_key: str | None = None

    # Field label patterns
    FIELD_PATTERNS = [
        (re.compile(r"^Title:\s*(.*)$"),       "Title"),
        (re.compile(r"^CR#:\s*(.*)$"),          "CR#"),
        (re.compile(r"^Agency:\s*(.*)$"),        "Agency"),
        (re.compile(r"^Company:\s*(.*)$"),       "Company"),
        (re.compile(r"^Division:\s*(.*)$"),      "Division"),
        (re.compile(r"^Issue Date:\s*(.*)$"),    "Issue Date"),
        (re.compile(r"^Due date\s+(.*)$"),       "Due date"),
        (re.compile(r"^Location:\s*(.*)$"),      "Location"),
        (re.compile(r"^Category:\s*(.*)$"),      "Category"),
        (re.compile(r"^Ad type:\s*(.*)$"),       "Ad type"),
    ]

    def _save_current():
        if current.get("CR#") or current.get("Title"):
            records.append(dict(current))

    for line in lines:
        matched = False
        for pattern, key in FIELD_PATTERNS:
            m = pattern.match(line)
            if m:
                if key == "Title" and current:
                    _save_current()
                    current = {}
                current[key] = m.group(1).strip()
                current_key = key
                matched = True
                break

        if not matched and current_key:
            # Continuation line — skip header/footer noise
            if not re.match(r"^(The|New York State|Contract Reporter|NYS'|Bringing|All Open|Sorted|Total:|\d+)$", line):
                current[current_key] = (current.get(current_key, "") + " " + line).strip()

    _save_current()
    return records


async def fetch_newyork_pdf() -> str:
    """
    Load the NYSCR search page, click Download PDF, save to a temp file,
    and return the file path. PDF generation takes 30-90 seconds.
    """
    tmp_path = os.path.join(tempfile.gettempdir(), "nyscr_ads.pdf")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            user_agent=(
                "Mozilla/5.0 (compatible; Chardi.ai/1.0; +https://chardi.ai) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = await context.new_page()

        try:
            # ── 1. Load search page (sets session, loads 999 results) ─────
            resp = await page.goto(SEARCH_URL, wait_until="networkidle", timeout=90000)
            if resp and resp.status >= 400:
                raise RuntimeError(f"nyscr.ny.gov returned HTTP {resp.status}")

            # ── 2. Click Download PDF and wait for the file ───────────────
            dl_link = page.locator("a[href*='GenerateSearchPdf']").first
            await dl_link.wait_for(state="visible", timeout=15000)

            async with page.expect_download(timeout=180000) as dl_info:
                await dl_link.click()

            download = await dl_info.value
            await download.save_as(tmp_path)

        finally:
            await browser.close()

    return tmp_path


async def fetch_newyork_events() -> list[dict[str, str]]:
    """Download the NYSCR PDF and return parsed event records."""
    pdf_path = await fetch_newyork_pdf()
    return parse_pdf_records(pdf_path)
