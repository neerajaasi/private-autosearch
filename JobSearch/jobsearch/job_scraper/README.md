# Job Scraper Framework

Multi-site job search automation using Python + Selenium. Searches multiple job titles across multiple staffing sites and outputs a single Excel report organized by title.

## Features

- **Date filtering** — Configurable via `config.yaml` (Past 24 hours, Past week, Past month)
- **Full job details** — Clicks into each job listing to extract complete JD, requirements, salary, and posted date
- **Pagination** — Automatically traverses all result pages (Load More, Next, numbered pages)
- **Multi-title search** — Search 5+ job titles in one run, each gets its own Excel sheet
- **Multi-site** — Plugin architecture — add new sites without touching existing code
- **Excel output** — Professional formatted `.xlsx` with Summary, All Jobs, and per-title sheets

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run (uses defaults from config.yaml)
python main.py

# 3. Find your results
open output/job_results.xlsx
```

---

## Project Structure

```
job_scraper/
├── main.py              ← Entry point
├── config.yaml          ← Job titles, location, output settings
├── sites.txt            ← Which sites to scrape (one per line)
├── base_scraper.py      ← Shared base class for all scrapers
├── driver_factory.py    ← Chrome browser setup + anti-detection
├── requirements.txt     ← Python dependencies
├── README.md            ← This file
├── sites/
│   ├── __init__.py      ← Registry mapping names → classes
│   ├── _template.py     ← Copy this to add a new site
│   ├── roberthalf.py    ← Robert Half  (URL: /jobs/all/{slug})
│   └── randstad.py      ← Randstad USA (URL: /jobs/q-{slug}/)
└── output/
    └── job_results.xlsx ← Generated Excel report
```

---

## Configuration

### config.yaml — What to search

```yaml
# Job titles (searched on ALL enabled sites)
titles:
  - Business Analyst
  - Data Analyst
  - Quality Assurance Engineer
  - QA Engineer
  - Business Data Analyst

# Default location
location: "united states"

# Date filter — applied after each search
# Options: "Past 24 hours", "Past week", "Past month", or "none" to skip
date_filter: "Past 24 hours"

# Output settings
output:
  filename: "job_results.xlsx"
  directory: "output"
```

Add or remove titles by editing this file. No code changes needed.

### sites.txt — Where to search

```
# Comment out a site with # to skip it
roberthalf
randstad
```

---

## CLI Options

| Flag | Example | Description |
|------|---------|-------------|
| *(none)* | `python main.py` | Run with config.yaml defaults |
| `--no-headless` | `python main.py --no-headless` | Show browser window (for debugging) |
| `--sites` | `python main.py --sites roberthalf` | Override sites.txt |
| `--titles` | `python main.py --titles "Data Analyst,QA Engineer"` | Override config.yaml titles |
| `--date-filter` | `python main.py --date-filter "Past week"` | Override config.yaml date filter |
| `-v` | `python main.py -v` | Verbose/debug logging |

### Common Recipes

```bash
# Test a single site first
python main.py --sites roberthalf --no-headless

# Search only one title
python main.py --titles "Business Analyst"

# Multiple sites, one title, visible browser
python main.py --sites roberthalf,randstad --titles "Data Analyst" --no-headless

# Full run, all titles, all sites, headless
python main.py

# Debug mode with verbose logging
python main.py --sites roberthalf --no-headless -v
```

---

## Excel Output

The script generates `output/job_results.xlsx` with these sheets:

| Sheet | Contents |
|-------|----------|
| **Summary** | Job count per title, which sites returned results |
| **All Jobs** | Every job from every site and title combined |
| **Business Analyst** | Jobs matching "Business Analyst" across all sites |
| **Data Analyst** | Jobs matching "Data Analyst" across all sites |
| *(one sheet per title)* | ... |

### Columns in each sheet

| Column | Description |
|--------|-------------|
| Company | Source site (Robert Half, Randstad, etc.) |
| Title | Job title as listed on the site |
| Location | City, State |
| Salary | Pay range if available |
| Job Type | Permanent, Temporary, Contract, etc. |
| Work Type | onsite, remote, hybrid |
| Posted Date | When the job was posted |
| JD | Full job description (from detail page) |
| URL | Direct link to the job posting |

---

## How the Scraping Pipeline Works

For each job title × each site, the scraper runs this pipeline:

```
1. NAVIGATE     → Build search URL (e.g. /jobs/all/business-analyst)
2. DATE FILTER  → Click filter button → select "Past 24 hours" → Apply
3. SCRAPE PAGE  → Extract all job cards/links on current page
4. PAGINATE     → Click "Next" / "Load More" → repeat step 3
5. GET DETAILS  → Visit each job URL → extract full JD + requirements
6. OUTPUT       → Write all results to Excel
```

### Date Filter
Set in `config.yaml` or override with `--date-filter`:
- `"Past 24 hours"` — jobs posted today
- `"Past week"` — last 7 days
- `"Past month"` — last 30 days
- `"none"` — skip filtering, get all results

### Pagination
Each scraper handles pagination automatically:
- Tries: Load More buttons, Next links, numbered page links
- Safety limit: 20 pages max per search
- Stops when no more jobs or no next page found

### Full Detail Extraction
After collecting all job links from listing pages, the scraper visits each job URL individually to extract:
- Complete job description (not truncated)
- Requirements / qualifications
- Any missing fields (salary, location, date)

---

## How to Add a New Site

### Step 1 — Create the scraper (copy the template)

```bash
cp sites/_template.py sites/indeed.py
```

Edit `sites/indeed.py`:

```python
import time
import logging
from selenium.webdriver.common.by import By
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class IndeedScraper(BaseScraper):

    SITE_NAME = "indeed"
    BASE_URL = "https://www.indeed.com/jobs"

    def search_jobs(self, keyword: str, location: str) -> list[dict]:
        # Build the search URL
        url = f"{self.BASE_URL}?q={keyword.replace(' ', '+')}&l={location.replace(' ', '+')}"
        self.goto(url)
        self.dismiss_overlays()
        self.wait_for_page_load()

        # Scrape job cards
        jobs = []
        cards = self.find_by_selectors(["div.job_seen_beacon"])

        for card in cards:
            job = {
                "title": "",
                "url": "",
                "location": "",
                "salary": "",
                "company": "Indeed",
                "posted_date": "",
                "jd": "",
            }
            # Parse title
            try:
                el = card.find_element(By.CSS_SELECTOR, "h2 a")
                job["title"] = el.text.strip()
                job["url"] = el.get_attribute("href") or ""
            except Exception:
                pass
            # Parse location
            try:
                job["location"] = card.find_element(
                    By.CSS_SELECTOR, "[class*='location']"
                ).text.strip()
            except Exception:
                pass

            if job["title"]:
                jobs.append(job)

        return jobs
```

### Step 2 — Register it

Edit `sites/__init__.py`:

```python
from sites.roberthalf import RobertHalfScraper
from sites.randstad import RandstadScraper
from sites.indeed import IndeedScraper          # ← add

REGISTRY = {
    "roberthalf": RobertHalfScraper,
    "randstad":   RandstadScraper,
    "indeed":     IndeedScraper,                 # ← add
}
```

### Step 3 — Enable it

Add to `sites.txt`:

```
roberthalf
randstad
indeed
```

### Step 4 — Run

```bash
python main.py --sites indeed --no-headless
```

---

## Finding CSS Selectors for a New Site

1. Open the job site in Chrome
2. Right-click on an element (search box, job card, title link) → **Inspect**
3. Note the HTML tag, class, id, name, or data-* attributes

**Examples:**

| Element | HTML you see | CSS Selector |
|---------|-------------|--------------|
| Search box | `<input class="search-input" name="q">` | `input.search-input` or `input[name='q']` |
| Job card | `<div class="job-card-wrapper">` | `div.job-card-wrapper` |
| Title link | `<h2><a href="/job/123">Analyst</a></h2>` | `h2 a` |
| Location | `<span class="job-location">NYC</span>` | `span.job-location` |

**Pro tip:** Many sites use URL-based search (no form filling needed):
- Robert Half: `/us/en/jobs/all/business-analyst`
- Randstad: `/jobs/q-business+analyst/`
- Indeed: `/jobs?q=business+analyst&l=new+york`

URL-based search is more reliable than form filling. Check if the site encodes search terms in the URL first.

---

## Troubleshooting

### "No jobs found"

1. Run with `--no-headless` to watch the browser
2. Check if the site loads correctly (some sites block headless browsers)
3. Check if the URL pattern is correct by opening it manually in Chrome
4. Run with `-v` for detailed logs
5. Check `output/error_*.png` for screenshots captured on failure

### "chromedriver not found"

```bash
pip install --upgrade webdriver-manager
```

webdriver-manager auto-downloads the correct chromedriver for your Chrome version.

### "ModuleNotFoundError"

Make sure you're in the `job_scraper/` directory or running from the correct path:

```bash
cd path/to/job_scraper
python main.py
```

The script resolves all paths relative to `main.py`'s location, so it should work from anywhere, but `cd`-ing in is simplest.

### Site changed its layout

Websites update their HTML regularly. If a scraper breaks:

1. Open the site in Chrome with DevTools (F12)
2. Find the new selectors for job cards, titles, locations
3. Update the corresponding `sites/yoursite.py`
4. Test with `python main.py --sites yoursite --no-headless`

---

## Available Helper Methods (BaseScraper)

Every site scraper inherits these — no need to rewrite common logic:

| Method | What it does |
|--------|-------------|
| `self.goto(url)` | Navigate (defaults to BASE_URL) |
| `self.dismiss_overlays()` | Close cookie banners, modals |
| `self.wait_for_page_load(extra_wait)` | Wait for JS to finish rendering |
| `self.clear_and_type(element, text)` | Clear an input field and type |
| `self.safe_click(element)` | Click with JavaScript fallback |
| `self.scroll_to(element)` | Scroll element into viewport |
| `self.find_by_selectors([...])` | Try multiple CSS selectors, return first match |
| `self.screenshot(name)` | Save a debug screenshot |

---

## Requirements

- Python 3.10+
- Google Chrome browser installed
- Internet connection

Dependencies (installed via `pip install -r requirements.txt`):

| Package | Purpose |
|---------|---------|
| selenium | Browser automation |
| webdriver-manager | Auto-downloads matching chromedriver |
| pyyaml | Reads config.yaml |
| openpyxl | Writes Excel output |
