import os
import yaml
import time
import requests
from datetime import datetime

--DontRun--

CONFIG_FILE = "config_bck.yaml"
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# ---------------- Load Config ----------------
def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ---------------- Time Filter ----------------
def parse_time_window(window):
    mapping = {"24h": 24, "48h": 48, "7d": 168}  # hours
    return mapping.get(window, 24)

def within_time_window(posted_text, max_hours):
    if not posted_text:
        return False
    t = posted_text.lower()
    try:
        if "hour" in t:
            n = int(t.split()[0])
            return n <= max_hours
        if "day" in t:
            n = int(t.split()[0])
            return n * 24 <= max_hours
        if "week" in t:
            n = int(t.split()[0])
            return n * 7 * 24 <= max_hours
    except Exception:
        pass
    if any(k in t for k in ["today", "just posted", "few hours"]):
        return True
    return False

# ---------------- SerpAPI Search ----------------
def search_jobs(job_title, location, max_pages=3, max_hours=24):
    all_results = []
    next_page_token = None
    for _ in range(max_pages):
        params = {
            "engine": "google_jobs",
            "q": f"{job_title} {location}",
            "hl": "en",
            "api_key": SERPAPI_KEY,
        }
        if next_page_token:
            params["next_page_token"] = next_page_token
        r = requests.get("https://serpapi.com/search", params=params, timeout=30)
        if r.status_code != 200:
            print(f"⚠️ HTTP {r.status_code}: {r.text[:200]}")
            break
        data = r.json()
        jobs = data.get("jobs_results", [])
        if not jobs:
            break
        # Apply time filter
        jobs = [
            j for j in jobs
            if within_time_window(j.get("detected_extensions", {}).get("posted_at", ""), max_hours)
        ]
        all_results.extend(jobs)
        next_page_token = data.get("serpapi_pagination", {}).get("next_page_token")
        if not next_page_token:
            break
        time.sleep(2)
    return all_results

# ---------------- Write Output ----------------
def write_results(results, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for job in results:
            posted = job.get("detected_extensions", {}).get("posted_at", "")
            f.write(f"Title: {job.get('title', '')}\n")
            f.write(f"Company: {job.get('company_name', '')}\n")
            f.write(f"Location: {job.get('location', '')}\n")
            f.write(f"Posted: {posted}\n")
            f.write(f"URL: {job.get('apply_options', [{}])[0].get('link', job.get('link', ''))}\n")
            desc = job.get("description", "")
            f.write(f"Description: {desc[:500]}{'...' if len(desc)>500 else ''}\n")
            f.write("-" * 80 + "\n")

# ---------------- Main ----------------
def main():
    if not SERPAPI_KEY:
        print("❌ Missing SERPAPI_KEY. Run: export SERPAPI_KEY='your_key'")
        return

    cfg = load_config()
    hours_limit = parse_time_window(cfg.get("time_window", "24h"))
    job_titles = cfg.get("job_titles", ["Data Analyst"])
    regions = cfg.get("regions", ["United States"])

    date_str = datetime.now().strftime("%Y-%m-%d")
    results_dir = os.path.join("results", f"{date_str}-googlejobs")

    for job_title in job_titles:
        cumulative = []
        print(f"\n===== {job_title.upper()} =====")
        for region in regions:
            print(f"🔍 {job_title} → {region} (≤{hours_limit}h)")
            results = search_jobs(job_title, region, max_pages=3, max_hours=hours_limit)
            if not results:
                print(f"⚠️ No results for {job_title} in {region}. Skipping file creation.")
                continue

            region_file = os.path.join(results_dir, f"{job_title.replace(' ', '_')}_{region.replace(' ', '_')}.txt")
            write_results(results, region_file)
            print(f"✅ {len(results)} results saved → {region_file}")
            cumulative.extend(results)
            time.sleep(2)

        # Only create cumulative file if results exist
        if cumulative:
            cumulative_file = os.path.join(results_dir, f"{job_title.replace(' ', '_')}_ALL.txt")
            write_results(cumulative, cumulative_file)
            print(f"📦 Total {len(cumulative)} results → {cumulative_file}")
        else:
            print(f"⚠️ No results found for any region for {job_title}. Skipping cumulative file.")

if __name__ == "__main__":
    main()