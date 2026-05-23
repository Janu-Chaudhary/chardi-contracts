# Action Plan for May 23, 2026

**Goal**: Test and perfect the SAM.gov scraper for reliable 30-day data collection  
**Status**: API rate limit resets at 00:00:00 UTC  
**Priority**: HIGH - Critical for project completion

---

## 🚀 Quick Start (First Thing Tomorrow)

### Step 1: Verify API Access (5 minutes)

```bash
# Load environment variables
export $(grep -v '^#' .env | xargs)

# Test API directly
.venv/bin/python scripts/test_api_direct.py
```

**Expected**: Status 200, should see opportunities data  
**If Failed**: API still rate limited, wait longer

---

### Step 2: Test 1-Day Ingestion (5 minutes)

```bash
# Run 1-day ingestion
.venv/bin/python scripts/run_samgov_1day.py
```

**Expected Output**:
```json
{
  "run_id": X,
  "status": "SUCCESS",
  "records_scraped": 80-100,
  "errors": []
}
```

**If Failed**: Check error message, may need to adjust retry logic

---

### Step 3: Verify Data Quality (2 minutes)

```bash
# Run data quality check
.venv/bin/python scripts/data_quality_check.py
```

**Expected**: All quality checks pass, no duplicates

---

### Step 4: Test 7-Day Ingestion (10 minutes)

```bash
# Run 7-day ingestion
.venv/bin/python scripts/run_samgov_7day.py
```

**Expected**: SUCCESS or PARTIAL_SUCCESS with < 20% errors

**Success Criteria**:
- At least 5 out of 7 days succeed
- Total records > 200
- No complete failures

---

### Step 5: Test 30-Day Ingestion (15-20 minutes)

```bash
# Run 30-day ingestion
.venv/bin/python -m backend.workers.samgov.main --days 30
```

**Expected**: SUCCESS or PARTIAL_SUCCESS

**Success Criteria**:
- At least 24 out of 30 days succeed (80%)
- Total records > 1000
- Completes in < 15 minutes
- Error rate < 20%

---

### Step 6: Analyze Results (5 minutes)

```bash
# Check final state
.venv/bin/python scripts/smoke_test.py

# Run data quality check
.venv/bin/python scripts/data_quality_check.py
```

**Check**:
- Total opportunities count
- No duplicates
- All scrape runs logged
- Error patterns in scrape_errors

---

## 📊 Decision Tree

### If 30-Day Test Succeeds ✅

**Action**: Mark as production-ready and move to next phase

**Next Steps**:
1. Document final configuration
2. Create operational procedures
3. Move to state portal workers OR dashboard development

---

### If 30-Day Test Has < 20% Errors ⚠️

**Action**: Implement additional improvements

**Priority Improvements**:
1. **Implement Retry-After Header Respect** (30 minutes)
2. **Add Request Delay** (15 minutes)
3. **Test Again** (20 minutes)

---

### If 30-Day Test Has > 20% Errors ❌

**Action**: Deeper investigation needed

**Investigation Steps**:
1. Check error patterns in scrape_errors table
2. Identify if errors are:
   - Rate limiting (429)
   - Server errors (5xx)
   - Network timeouts
   - Data issues

**Possible Solutions**:
- Further reduce concurrency (to 2 or 1)
- Increase retry delays
- Implement circuit breaker
- Add longer delays between requests

---

## 🔧 Quick Fixes to Implement (If Needed)

### Fix 1: Respect Retry-After Header (30 minutes)

**File**: `backend/workers/samgov/fetcher.py`

**Add to fetch_page method**:
```python
if response.status in RETRYABLE_STATUS:
    retry_after = response.headers.get('Retry-After')
    should_retry = True
    retry_status = response.status
    last_error = aiohttp.ClientResponseError(...)
    
# Outside semaphore
if should_retry:
    await self._backoff_sleep(attempt, retry_status, retry_after)
```

**Update _backoff_sleep**:
```python
async def _backoff_sleep(self, attempt: int, status: int | None = None, retry_after: str | None = None) -> None:
    if retry_after and status == 429:
        try:
            delay = float(retry_after)
        except ValueError:
            from email.utils import parsedate_to_datetime
            from datetime import datetime, timezone
            retry_time = parsedate_to_datetime(retry_after)
            delay = (retry_time - datetime.now(timezone.utc)).total_seconds()
        delay = min(max(delay, 0), 3600)  # Cap at 1 hour
    else:
        base = min(2**attempt, 60)
        jitter = random.uniform(0.1, 1.5)
        delay = base + jitter
    
    await asyncio.sleep(delay)
```

---

### Fix 2: Add Request Delay (15 minutes)

**File**: `backend/workers/samgov/fetcher.py`

**Add to __init__**:
```python
def __init__(self, session: aiohttp.ClientSession) -> None:
    self._session = session
    self._semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    self._timeout = aiohttp.ClientTimeout(...)
    self._request_delay = 0.5  # 500ms delay
```

**Add to fetch_page after successful response**:
```python
response.raise_for_status()
result = await response.json()
await asyncio.sleep(self._request_delay)  # Polite delay
return result
```

---

### Fix 3: Reduce Concurrency Further (5 minutes)

**File**: `backend/workers/samgov/fetcher.py`

**Change**:
```python
CONCURRENCY_LIMIT = 2  # Reduced from 3 to 2
```

---

## 📝 Testing Checklist

### Before Starting
- [ ] API rate limit has reset (check with test_api_direct.py)
- [ ] Virtual environment activated
- [ ] Environment variables loaded
- [ ] Database accessible

### During Testing
- [ ] 1-day ingestion works
- [ ] Data quality checks pass
- [ ] 7-day ingestion succeeds
- [ ] Error rate acceptable
- [ ] 30-day ingestion completes

### After Testing
- [ ] Total opportunities > 1000
- [ ] No duplicates
- [ ] Error rate < 20%
- [ ] All scrape runs logged
- [ ] Performance acceptable (< 15 min for 30 days)

---

## 🎯 Success Metrics

### Minimum Acceptable
- ✅ 30-day ingestion completes
- ✅ At least 24/30 days succeed (80%)
- ✅ Total records > 1000
- ✅ No duplicates
- ✅ Error rate < 20%

### Target
- 🎯 30-day ingestion SUCCESS status
- 🎯 At least 28/30 days succeed (93%)
- 🎯 Total records > 2000
- 🎯 Error rate < 10%
- 🎯 Completes in < 10 minutes

### Stretch
- 🌟 30-day ingestion SUCCESS status
- 🌟 All 30 days succeed (100%)
- 🌟 Total records > 3000
- 🌟 Error rate < 5%
- 🌟 Completes in < 8 minutes

---

## 📊 Monitoring Queries

### Check Scrape Run Status
```sql
SELECT 
    id,
    start_time,
    end_time,
    EXTRACT(EPOCH FROM (end_time - start_time)) as duration_seconds,
    records_scraped,
    status,
    metadata->>'error_count' as errors,
    metadata->>'task_count' as total_tasks
FROM scrape_runs
WHERE source_portal = 'SAM.gov'
ORDER BY id DESC
LIMIT 5;
```

### Check Error Patterns
```sql
SELECT 
    LEFT(error_message, 100) as error_type,
    COUNT(*) as count
FROM scrape_errors
WHERE source_portal = 'SAM.gov'
  AND created_at > NOW() - INTERVAL '1 day'
GROUP BY LEFT(error_message, 100)
ORDER BY count DESC;
```

### Check Data Completeness
```sql
SELECT 
    DATE(posted_date) as date,
    COUNT(*) as opportunities
FROM opportunities
WHERE source_portal = 'SAM.gov'
  AND posted_date > NOW() - INTERVAL '30 days'
GROUP BY DATE(posted_date)
ORDER BY date DESC;
```

---

## 🚨 Troubleshooting

### Issue: Still Getting 429 Errors

**Possible Causes**:
1. Rate limit hasn't fully reset
2. Concurrency too high
3. Not respecting Retry-After header

**Solutions**:
1. Wait 1 more hour
2. Reduce CONCURRENCY_LIMIT to 2 or 1
3. Implement Retry-After header respect

---

### Issue: Many 5xx Errors

**Possible Causes**:
1. SAM.gov API having issues
2. Timeout too short
3. Network problems

**Solutions**:
1. Increase REQUEST_TIMEOUT_SECONDS to 90
2. Add longer delays between retries
3. Check SAM.gov status page

---

### Issue: Slow Performance

**Possible Causes**:
1. Too many retries
2. Long backoff delays
3. Network latency

**Solutions**:
1. This is expected with conservative settings
2. Trade-off: reliability > speed
3. Can optimize after confirming reliability

---

## 📋 Final Checklist Before Moving On

### SAM.gov Scraper Complete
- [ ] 30-day ingestion tested successfully
- [ ] Error rate acceptable (< 20%)
- [ ] Data quality verified
- [ ] Performance acceptable
- [ ] All improvements implemented
- [ ] Documentation updated

### Ready for Next Phase
- [ ] SAM.gov scraper production-ready
- [ ] Operational procedures documented
- [ ] Monitoring queries saved
- [ ] Known issues documented
- [ ] Configuration finalized

---

## 🎯 Timeline

| Time | Task | Duration |
|------|------|----------|
| 00:00 UTC | API rate limit resets | - |
| 00:05 | Test API access | 5 min |
| 00:10 | Test 1-day ingestion | 5 min |
| 00:15 | Verify data quality | 2 min |
| 00:20 | Test 7-day ingestion | 10 min |
| 00:35 | Test 30-day ingestion | 20 min |
| 01:00 | Analyze results | 5 min |
| 01:10 | Implement fixes (if needed) | 30-60 min |
| 02:00 | Retest (if needed) | 20 min |
| 02:30 | **DONE** | - |

**Total Time**: 1.5 - 2.5 hours

---

## 💡 Pro Tips

1. **Start Early**: Begin testing as soon as rate limit resets
2. **Be Patient**: Don't rush to 30-day test immediately
3. **Monitor Closely**: Watch for error patterns
4. **Document Everything**: Note any issues for future reference
5. **Celebrate Success**: You've built a robust scraper!

---

**Created**: May 22, 2026  
**Execute**: May 23, 2026 00:00:00 UTC  
**Priority**: HIGH  
**Estimated Time**: 1.5 - 2.5 hours
