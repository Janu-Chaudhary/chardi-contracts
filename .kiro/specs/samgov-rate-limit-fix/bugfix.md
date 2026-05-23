# Bugfix Requirements Document

## Introduction

The SAM.gov fetcher (`backend/workers/samgov/fetcher.py`) currently does not distinguish between temporary rate limits (429 errors that should be retried) and daily quota exhaustion (429 errors with `nextAccessTime` that indicate the API is locked until the next day). This causes the system to waste retry attempts on unrecoverable quota exhaustion errors instead of failing fast. Additionally, the `PAGE_LIMIT` is set too low at 100, causing excessive API requests that burn through the daily quota unnecessarily.

**Impact**: Workers waste time retrying unrecoverable errors, and the low page limit causes faster quota exhaustion, reducing the amount of data that can be collected per day.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN SAM.gov returns a 429 status code with `nextAccessTime` in the response body (indicating daily quota exhaustion) THEN the system retries up to 5 times with exponential backoff before failing

1.2 WHEN SAM.gov returns a 429 status code without `nextAccessTime` (indicating temporary rate limiting) THEN the system retries up to 5 times with exponential backoff

1.3 WHEN `PAGE_LIMIT` is set to 100 THEN the system makes 10x more API requests than necessary for the same amount of data (e.g., 10 requests for 1000 records instead of 1 request)

### Expected Behavior (Correct)

2.1 WHEN SAM.gov returns a 429 status code with `nextAccessTime` in the response body (indicating daily quota exhaustion) THEN the system SHALL immediately raise a fatal error with the quota reset time and abort the worker without retrying

2.2 WHEN SAM.gov returns a 429 status code without `nextAccessTime` in the response body (indicating temporary rate limiting) THEN the system SHALL continue with exponential backoff retry logic up to MAX_RETRIES attempts

2.3 WHEN `PAGE_LIMIT` is set to 1000 THEN the system SHALL make 10x fewer API requests for the same amount of data, preserving daily quota

### Unchanged Behavior (Regression Prevention)

3.1 WHEN SAM.gov returns 500, 502, 503, or 504 status codes THEN the system SHALL CONTINUE TO retry up to MAX_RETRIES times with exponential backoff

3.2 WHEN SAM.gov returns a 200 status code with valid data THEN the system SHALL CONTINUE TO parse and return the response without modification

3.3 WHEN exponential backoff sleep occurs during retry THEN the system SHALL CONTINUE TO sleep outside the semaphore to release the concurrency slot

3.4 WHEN pagination is required (totalRecords > PAGE_LIMIT) THEN the system SHALL CONTINUE TO fetch subsequent pages until all records are retrieved

3.5 WHEN the backoff sleep calculation is performed THEN the system SHALL CONTINUE TO use the formula `min(2**attempt, 60) + random.uniform(0.1, 1.5)`
