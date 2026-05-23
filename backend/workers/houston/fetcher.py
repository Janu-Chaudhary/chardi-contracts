"""
Houston Procurement Contracts fetcher.

Source: City of Houston CKAN open data portal
Dataset: All City of Houston Procurement Contracts
Method: CKAN package_show API → XLSX download → pandas read

No Playwright required. Pure aiohttp + pandas.
"""

from __future__ import annotations

import io
from typing import Any

import aiohttp
import pandas as pd

from backend.core import settings

CKAN_API_URL = "https://data.houstontx.gov/api/3/action/package_show"
DATASET_SLUG = "all-city-of-houston-procurement-contracts"
DIRECT_DOWNLOAD_URL = (
    "https://data.houstontx.gov/dataset/fb3491ef-5aa1-4d54-97a7-c1d091a56f46"
    "/resource/0c93d5a2-4ee0-42e1-bdb6-c262718dfe0b"
    "/download/allcityofhoustoncontracts.xlsx"
)


async def _resolve_download_url(session: aiohttp.ClientSession) -> str:
    """Resolve XLSX download URL via CKAN API. Falls back to hardcoded URL."""
    try:
        async with session.get(
            CKAN_API_URL,
            params={"id": DATASET_SLUG},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
            if data.get("success"):
                resources = data.get("result", {}).get("resources") or []
                xlsx = [r for r in resources if str(r.get("format", "")).upper() == "XLSX"]
                candidates = xlsx or resources
                if candidates and candidates[0].get("url"):
                    return candidates[0]["url"]
    except Exception as exc:
        print(f"[Houston] CKAN API lookup failed ({exc}), using direct URL")
    return DIRECT_DOWNLOAD_URL


async def fetch_houston_records(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Download Houston XLSX and return list of row dicts."""
    download_url = await _resolve_download_url(session)
    print(f"[Houston] Downloading XLSX from: {download_url}")

    async with session.get(
        download_url,
        timeout=aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT_SECONDS),
        headers={"User-Agent": settings.USER_AGENT},
    ) as resp:
        resp.raise_for_status()
        content = await resp.read()

    print(f"[Houston] Downloaded {len(content):,} bytes")
    df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    print(f"[Houston] Parsed {len(df)} rows, columns: {list(df.columns)}")

    # Normalize column names
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # Replace NaN with None
    df = df.where(pd.notna(df), None)

    return df.to_dict(orient="records")
