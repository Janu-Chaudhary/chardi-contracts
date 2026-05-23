#!/usr/bin/env python3
"""Direct API test to diagnose connection issues."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import aiohttp
from backend.core import settings


async def test_api() -> None:
    """Test SAM.gov API directly."""
    print("=" * 80)
    print("SAM.GOV API DIRECT TEST")
    print("=" * 80)
    
    print(f"\nAPI Key: {settings.SAM_GOV_API_KEY[:20]}...")
    print(f"Base URL: {settings.SAM_GOV_BASE_URL}")
    
    params = {
        "api_key": settings.SAM_GOV_API_KEY,
        "postedFrom": "05/22/2026",
        "postedTo": "05/22/2026",
        "limit": 10,
        "offset": 0,
    }
    
    print(f"\nTest Parameters:")
    print(f"  postedFrom: {params['postedFrom']}")
    print(f"  postedTo: {params['postedTo']}")
    print(f"  limit: {params['limit']}")
    
    async with aiohttp.ClientSession() as session:
        try:
            print(f"\nMaking request...")
            async with session.get(
                settings.SAM_GOV_BASE_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "User-Agent": settings.USER_AGENT,
                    "Accept": "application/json",
                },
            ) as response:
                print(f"Status Code: {response.status}")
                print(f"Headers: {dict(response.headers)}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"\n✓ SUCCESS!")
                    print(f"Total Records: {data.get('totalRecords', 0)}")
                    print(f"Opportunities Returned: {len(data.get('opportunitiesData', []))}")
                    
                    if data.get('opportunitiesData'):
                        first = data['opportunitiesData'][0]
                        print(f"\nFirst Opportunity:")
                        print(f"  Title: {first.get('title', 'N/A')[:60]}...")
                        print(f"  Notice ID: {first.get('noticeId', 'N/A')}")
                        print(f"  Posted: {first.get('postedDate', 'N/A')}")
                else:
                    text = await response.text()
                    print(f"\n✗ FAILED!")
                    print(f"Response Body: {text[:500]}")
                    
        except Exception as e:
            print(f"\n✗ EXCEPTION!")
            print(f"Error: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_api())
