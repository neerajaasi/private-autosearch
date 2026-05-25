# Job Hunter — Single-Script End-to-End

One Python script. Discovers companies, fetches BA/QA/DA jobs from the last 24-48 hours, outputs Excel.

## Setup (one-time, ~3 minutes)

```bash
pip install playwright requests openpyxl
playwright install chromium
```

You need Python 3.9+ and Chrome (the script downloads its own Chromium for Playwright — about 150 MB on first install).

## Run

```bash
python job_hunter.py
```

That's it. Total runtime: 3-5 minutes (longer first run; faster subsequent runs since discovered companies are cached).

Output: `job_hunter_report_YYYYMMDD_HHMM.xlsx`

## What it does, in order

1. **Discovery (~90 sec)** — runs 11 Google searches across Greenhouse, Lever, and Ashby to find companies hiring for BA/QA/DA roles. Extracts company slugs from result URLs.

2. **Cache merge (~instant)** — combines newly discovered slugs with the seed list (50+ companies pre-loaded) and any from previous runs (`company_cache.json`).

3. **Parallel job fetch (~30-60 sec)** — hits every company's public ATS API in parallel (25 at a time). Filters jobs to BA/QA/DA roles, USA locations, posted within last 48 hours.

4. **Dedupe** — removes duplicate URLs.

5. **Excel output** — sorted newest-first, color-coded by role (BA = green, QA = pink, DA = blue), with clickable apply links. Plus a "Source Status" tab for debugging.

## Tweaks at the top of the file

```python
RECENCY_HOURS = 48        # 24 = today only, 48 = last 2 days, 168 = last week
DISCOVERY_ENABLED = True  # set False to skip Google searches and only use cache+seed
LOCATION_KEYWORDS = [...] # narrow to specific cities or set [] for global
ROLE_KEYWORDS = {...}     # add roles or change keywords
```

## Realistic expectations

**Companies scanned:** ~50 from seed list + ~30-80 from discovery on a good day. After a few runs, your `company_cache.json` will have 100-300 companies tracked.

**Jobs returned in 48-hour window:** typically 10-40. This isn't a bug — that's the actual rate at which BA/QA/DA jobs get posted. Companies don't post these roles every day. If you set `RECENCY_HOURS = 168` (1 week), expect 50-150 jobs.

**First run will be slowest.** Each subsequent run is faster because the cache short-circuits some discovery work.

## Failure modes (and what they mean)

| What you see | What's happening | Fix |
|---|---|---|
| `Hit Google CAPTCHA 3 times` | Google blocked your searches | Set `DISCOVERY_ENABLED = False` for a few runs, or run from a different network |
| Many sources show `HTTP 404` | Companies removed their public boards | Normal — those slugs are silently skipped |
| `0 jobs found` | Either no fresh jobs match, or all sources blocked | Increase `RECENCY_HOURS` to 168 to verify |
| `Playwright not installed` | Discovery can't run | `pip install playwright && playwright install chromium` |

## Files in this folder after running

```
job_hunter.py                       # The script
company_cache.json                  # Persistent cache of discovered companies
job_hunter_report_YYYYMMDD_HHMM.xlsx # Output (one per run)
```

## What this won't do

- **Won't scrape Workday/iCIMS/SAP SuccessFactors** — those don't have public APIs. Use the company's actual careers page in your browser if you want those.
- **Won't bypass CAPTCHAs** — Indian IT firms (TCS/Wipro/Infosys), TEKsystems, Aerotek will fail to be discovered or fetched.
- **Won't include LinkedIn/Indeed/Dice** — by design.

## What this WILL give you

✅ Real posting timestamps from each ATS's database
✅ Genuine 24-48 hour recency filter (not crawl-date approximation)
✅ Direct apply links to each company's own ATS
✅ Auto-expanding company list — discovers new companies each run
✅ Single command, single output file
