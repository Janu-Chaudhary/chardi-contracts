#!/usr/bin/env python3
"""Data quality verification script."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core import db


async def main() -> None:
    pool = await db.create_pool()
    try:
        print("=" * 80)
        print("DATA QUALITY VERIFICATION")
        print("=" * 80)
        
        # 1. Check total opportunities
        total = await pool.fetchval("SELECT COUNT(*) FROM opportunities")
        print(f"\n✓ Total opportunities: {total}")
        
        # 2. Verify deterministic IDs (should be 64 characters)
        id_check = await pool.fetchrow("""
            SELECT 
                MIN(LENGTH(id)) as min_len,
                MAX(LENGTH(id)) as max_len,
                COUNT(DISTINCT id) as unique_ids,
                COUNT(*) as total_rows
            FROM opportunities
        """)
        print(f"\n✓ ID lengths: min={id_check['min_len']}, max={id_check['max_len']}")
        print(f"✓ Unique IDs: {id_check['unique_ids']} (total rows: {id_check['total_rows']})")
        if id_check['unique_ids'] == id_check['total_rows']:
            print("  ✓ No duplicates found!")
        
        # 3. Check status values
        statuses = await pool.fetch("""
            SELECT status, COUNT(*) as count
            FROM opportunities
            GROUP BY status
            ORDER BY count DESC
        """)
        print(f"\n✓ Status distribution:")
        for row in statuses:
            print(f"  - {row['status']}: {row['count']}")
        
        # 4. Check date formats
        date_check = await pool.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE posted_date IS NOT NULL) as has_posted,
                COUNT(*) FILTER (WHERE deadline IS NOT NULL) as has_deadline
            FROM opportunities
        """)
        print(f"\n✓ Date fields:")
        print(f"  - posted_date populated: {date_check['has_posted']}/{total}")
        print(f"  - deadline populated: {date_check['has_deadline']}/{total}")
        
        # 5. Check buyer metadata
        buyer_check = await pool.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE buyer_name IS NOT NULL) as has_buyer_name,
                COUNT(*) FILTER (WHERE buyer_type IS NOT NULL) as has_buyer_type
            FROM opportunities
        """)
        print(f"\n✓ Buyer metadata:")
        print(f"  - buyer_name populated: {buyer_check['has_buyer_name']}/{total}")
        print(f"  - buyer_type populated: {buyer_check['has_buyer_type']}/{total}")
        
        # 6. Check NAICS codes
        naics_count = await pool.fetchval("""
            SELECT COUNT(*) 
            FROM opportunities 
            WHERE naics_code IS NOT NULL
        """)
        print(f"\n✓ NAICS codes populated: {naics_count}/{total}")
        
        # 7. Check state regions
        states = await pool.fetch("""
            SELECT state_region, COUNT(*) as count
            FROM opportunities
            WHERE state_region IS NOT NULL
            GROUP BY state_region
            ORDER BY count DESC
            LIMIT 10
        """)
        print(f"\n✓ Top 10 state regions:")
        for row in states:
            print(f"  - {row['state_region']}: {row['count']}")
        
        # 8. Check JSONB fields
        jsonb_check = await pool.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE documents IS NOT NULL) as has_documents,
                COUNT(*) FILTER (WHERE raw_payload IS NOT NULL) as has_raw_payload
            FROM opportunities
        """)
        print(f"\n✓ JSONB fields:")
        print(f"  - documents populated: {jsonb_check['has_documents']}/{total}")
        print(f"  - raw_payload populated: {jsonb_check['has_raw_payload']}/{total}")
        
        # 9. Sample records
        samples = await pool.fetch("""
            SELECT 
                id,
                title,
                buyer_name,
                status,
                posted_date,
                deadline
            FROM opportunities
            ORDER BY posted_date DESC
            LIMIT 3
        """)
        print(f"\n✓ Sample records:")
        for i, row in enumerate(samples, 1):
            print(f"\n  {i}. {row['title'][:60]}...")
            print(f"     Buyer: {row['buyer_name']}")
            print(f"     Status: {row['status']}")
            print(f"     Posted: {row['posted_date']}")
            print(f"     Deadline: {row['deadline']}")
        
        print("\n" + "=" * 80)
        print("DATA QUALITY CHECK COMPLETE")
        print("=" * 80)
        
    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
