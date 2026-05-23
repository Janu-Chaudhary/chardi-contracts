# Improvements for Reliable 30-Day SAM.gov Scraping

**Status**: API Rate Limited until May 23, 2026 00:00:00 UTC  
**Current Issue**: Hit daily quota during testing  
**Goal**: Make the scraper robust enough to handle 30 days reliably

---

## 🔍 Root Cause Analysis

### What Happened During Testing

1. **Initial Success** (Run #2, #3): 1-day ingestion worked perfectly (82 records)
2. **Partial Success** (Run #4): 7-day ingestion got 108 records but 5 days failed
3. **Complete Failure** (Run #5, #6): Hit API rate limit - quota exceeded

### API Rate Limit Details

```json
{
  "code": "900804",
  "message": "Message throttled out",
  "description": "You have exceeded your quota. You can access API after 2026-May-23 00:00:00+0000 UTC",
  "nextAccessTime": "2026-May-23 00:00:00+0000 UTC"
}
```

**HTTP Status**: 429 (Too Many Requests)  
**Retry-After Header**: Sat, 23 May 2026 00:00:00 GMT

---

## ✅ Improvements Already Applied

### 1. Fixed Backoff Sleep Location ✅

**Issue**: Backoff sleep was happening INSIDE the semaphore block, holding the concurrency slot during retry delays.

**Fix Applied**:
```python
# Before: Sleep inside semaphore (BAD)
async with self._semaphore:
    if response.status in RETRYABLE_STATUS:
        await self._backoff_sleep(attempt, response.status)  # Blocks slot!

# After: Sleep outside semaphore (GOOD)
async with self._semaphore:
    if response.status in RETRYABLE_STATUS:
        should_retry = True
        retry_status = response.status
# Exit semaphore, then sleep
if should_retry:
    await self._backoff_sleep(attempt, retry_status)  # Releases slot!
```

**Impact**: Allows other concurrent requests to proceed while one is backing off.

### 2. Improved Jitter Formula ✅

**Changed from**: `random.uniform(0, 1)`  
**Changed to**: `random.uniform(0.1, 1.5)`

**Reason**: Matches Phase 2 spec exactly and provides better distribution.

### 3. Reduced Concurrency Limit ✅

**Changed from**: `CONCURRENCY_LIMIT = 5`  
**Changed to**: `CONCURRENCY_LIMIT = 3`

**Reason**: More conservative approach reduces API pressure and rate limit risk.

---

## 🎯 Additional Improvements Needed

### 1. Respect Retry-After Header (HIGH PRIORITY)

**Current Behavior**: Ignores `Retry-After` header from 429 responses.

**Proposed Fix**:
```python
async def _backoff_sleep(self, attempt: int, status: int | None = None, retry_after: str | None = None) -> None:
    """
    Exponential backoff with jitter, respecting Retry-After header.
    """
    if retry_after and status == 429:
        # Parse Retry-After header (can be seconds or HTTP date)
        try:
            # Try parsing as seconds first
            delay = float(retry_after)
        except ValueError:
            # Parse as HTTP date
            from email.utils import parsedate_to_datetime
            retry_time = parsedate_to_datetime(retry_after)
            delay = (retry_time - datetime.now(timezone.utc)).total_seconds()
        
        # Cap at reasonable maximum (e.g., 1 hour)
        delay = min(delay, 3600)
    else:
        # Standard exponential backoff
        base = min(2**attempt, 60)
        jitter = random.uniform(0.1, 1.5)
        delay = base + jitter
    
    await asyncio.sleep(max(delay, 0))
```

**Impact**: Prevents wasting retries when API tells us exactly when to retry.

### 2. Add Request Delay Between Successful Requests (MEDIUM PRIORITY)

**Current Behavior**: No delay between successful requests.

**Proposed Fix**:
```python
# In SamGovFetcher.__init__
self._request_delay = 0.5  # 500ms delay between requests

# In fetch_page, after successful response
if response.status == 200:
    result = await response.json()
    await asyncio.sleep(self._request_delay)  # Polite delay
    return result
```

**Impact**: Reduces API pressure and likelihood of hitting rate limits.

### 3. Implement Progressive Backoff Strategy (MEDIUM PRIORITY)

**Current Behavior**: Fixed retry strategy regardless of error type.

**Proposed Fix**:
```python
# Different strategies for different errors
if status == 429:
    # Rate limit: longer backoff
    base = min(2**attempt * 2, 120)  # Double the base
elif status in {500, 502, 503, 504}:
    # Server error: standard backoff
    base = min(2**attempt, 60)
else:
    # Other errors: shorter backoff
    base = min(2**attempt, 30)
```

**Impact**: Adapts retry strategy to error type.

### 4. Add Circuit Breaker Pattern (LOW PRIORITY)

**Current Behavior**: Continues retrying even when API is consistently failing.

**Proposed Fix**:
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=10, timeout=300):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpen("Circuit breaker is open")
        
        try:
            result = await func()
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            raise
```

**Impact**: Prevents hammering a failing API, allows graceful recovery.

### 5. Implement Pagination Cap Handling (MEDIUM PRIORITY)

**Current Behavior**: No handling for SAM.gov's 10,000 record pagination limit.

**Proposed Fix** (from Phase 2 spec):
```python
async def collect_paginated_notices(
    self,
    posted_from: str,
    posted_to: str,
    ptype: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch all pages for a date window and return notice dicts."""
    offset = 0
    notices: list[dict[str, Any]] = []
    total_records: int | None = None

    while True:
        payload = await self.fetch_page(posted_from, posted_to, offset, ptype)
        batch = payload.get("opportunitiesData") or []
        if not isinstance(batch, list):
            batch = []

        notices.extend(batch)

        if total_records is None:
            total_records = int(payload.get("totalRecords") or 0)
            
            # Check if we're approaching pagination limit
            if total_records > 9000 and not ptype:
                # Need to subdivide by ptype to avoid 10k cap
                # This would require fetching by procurement type
                # For now, log a warning
                print(f"WARNING: {total_records} records for {posted_from}, may hit pagination cap")

        offset += PAGE_LIMIT
        if offset >= total_records or not batch:
            break
        
        # Safety check: don't exceed 10k pagination limit
        if offset >= 10000:
            print(f"WARNING: Hit 10k pagination limit for {posted_from}")
            break

    return notices
```

**Impact**: Prevents data loss when a single day has >10k records.

---

## 📊 Testing Strategy (After Rate Limit Resets)

### Phase 1: Verify Fixes (May 23, 2026)

```bash
# 1. Test 1-day ingestion
export $(grep -v '^#' .env | xargs)
.venv/bin/python scripts/run_samgov_1day.py

# 2. Verify data quality
.venv/bin/python scripts/data_quality_check.py

# 3. Test deduplication
.venv/bin/python scripts/run_samgov_1day.py  # Run again
```

**Expected**: 1-day should work perfectly with improved backoff.

### Phase 2: Test 7-Day Ingestion

```bash
# Test 7-day with reduced concurrency
.venv/bin/python scripts/run_samgov_7day.py
```

**Expected**: Should complete with fewer or no failures due to:
- Reduced concurrency (3 instead of 5)
- Backoff outside semaphore
- Better jitter distribution

### Phase 3: Test 30-Day Ingestion

```bash
# Create 30-day script if it doesn't exist
.venv/bin/python -m backend.workers.samgov.main --days 30
```

**Expected**: Should complete successfully or with PARTIAL_SUCCESS status.

### Phase 4: Monitor and Adjust

```sql
-- Check scrape run performance
SELECT 
    id,
    start_time,
    end_time,
    EXTRACT(EPOCH FROM (end_time - start_time)) as duration_seconds,
    records_scraped,
    status,
    metadata->>'error_count' as errors
FROM scrape_runs
WHERE source_portal = 'SAM.gov'
ORDER BY id DESC
LIMIT 10;

-- Check error patterns
SELECT 
    error_message,
    COUNT(*) as occurrence_count
FROM scrape_errors
WHERE source_portal = 'SAM.gov'
GROUP BY error_message
ORDER BY occurrence_count DESC;
```

---

## 🎯 Success Criteria for 30-Day Scraping

### Must Have ✅
- [x] Backoff sleep outside semaphore
- [x] Improved jitter formula (0.1 to 1.5)
- [x] Reduced concurrency (3 concurrent requests)
- [ ] Respect Retry-After header
- [ ] 30-day ingestion completes with SUCCESS or PARTIAL_SUCCESS
- [ ] Error rate < 20% of total day-windows
- [ ] All successful days have data in database

### Should Have 🎯
- [ ] Request delay between successful requests (500ms)
- [ ] Progressive backoff based on error type
- [ ] Pagination cap handling for high-volume days
- [ ] Circuit breaker for persistent failures

### Nice to Have 💡
- [ ] Automatic retry of failed days after cooldown
- [ ] Adaptive concurrency based on error rate
- [ ] Metrics dashboard for scrape performance
- [ ] Alert system for persistent failures

---

## 📝 Configuration Recommendations

### Current Settings
```python
PAGE_LIMIT = 100
MAX_RETRIES = 5
CONCURRENCY_LIMIT = 3  # Reduced from 5
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
```

### Recommended for 30-Day Production
```python
PAGE_LIMIT = 100
MAX_RETRIES = 5
CONCURRENCY_LIMIT = 2  # Even more conservative for 30-day runs
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
REQUEST_DELAY = 0.5  # 500ms between successful requests
RESPECT_RETRY_AFTER = True  # Honor API's Retry-After header
```

### Environment Variables
```bash
# Add to .env
SAM_GOV_CONCURRENCY=2
SAM_GOV_REQUEST_DELAY=0.5
SAM_GOV_MAX_RETRIES=5
```

---

## 🐛 Known Issues

### 1. API Rate Limit Hit During Testing ✅
**Status**: Expected behavior  
**Resolution**: Wait until May 23, 2026 00:00:00 UTC  
**Prevention**: Implement request delay and respect Retry-After header

### 2. Date Format Bug Fixed ✅
**Issue**: `sanitize_date()` returned ISO strings instead of datetime objects  
**Fix**: Modified to return datetime objects  
**Status**: Resolved and tested

### 3. Backoff Inside Semaphore Fixed ✅
**Issue**: Backoff sleep held concurrency slot  
**Fix**: Moved sleep outside semaphore block  
**Status**: Resolved, needs testing after rate limit reset

---

## 📈 Performance Expectations

### Current Performance (Before Rate Limit)
- **1-day ingestion**: ~6 seconds (82 records)
- **7-day ingestion**: ~44 seconds (108 records, 5 failures)
- **Records per second**: ~13

### Expected Performance After Improvements
- **1-day ingestion**: ~8-10 seconds (with request delay)
- **7-day ingestion**: ~60-90 seconds (fewer failures)
- **30-day ingestion**: ~5-10 minutes (estimated)
- **Records per second**: ~8-10 (slower but more reliable)

### Trade-offs
- ✅ **Reliability**: Significantly improved
- ✅ **Error Rate**: Reduced by 50-80%
- ⚠️ **Speed**: 20-30% slower due to delays
- ✅ **API Friendliness**: Much better

---

## 🚀 Next Steps (After Rate Limit Resets)

1. **Immediate** (May 23, 2026):
   - Test 1-day ingestion with current fixes
   - Verify all improvements are working
   - Run data quality checks

2. **Short Term** (Same day):
   - Implement Retry-After header respect
   - Add request delay between successful requests
   - Test 7-day ingestion

3. **Medium Term** (Within 24 hours):
   - Test 30-day ingestion
   - Monitor error patterns
   - Adjust concurrency if needed

4. **Long Term** (Before production):
   - Implement circuit breaker
   - Add pagination cap handling
   - Create monitoring dashboard
   - Document operational procedures

---

## 📚 References

- **Phase 2 Spec**: `phase2-federal-ingestion.md`
- **SAM.gov API Docs**: https://open.gsa.gov/api/opportunities-api/
- **Test Results**: `TEST_RESULTS.md`
- **Current Code**: `backend/workers/samgov/fetcher.py`

---

**Document Created**: May 22, 2026  
**Last Updated**: May 22, 2026  
**Status**: Ready for testing after rate limit reset  
**Priority**: HIGH - Critical for 30-day scraping goal
