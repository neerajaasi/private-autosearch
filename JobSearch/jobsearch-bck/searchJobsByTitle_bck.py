import os
import yaml
import time
import requests
from datetime import datetime, timedelta

# NOTE: The SERPAPI_KEY is retrieved from the environment variable.
CONFIG_FILE = "config_bck.yaml"
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Mapping of config strings to timedelta objects for client-side filtering
TIME_WINDOW_MAP = {
    "24h": timedelta(hours=24),
    "48h": timedelta(hours=48),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

# SerpAPI 'date_posted' mapping
def get_date_posted_param(window_str):
    t = window_str.lower()
    if "24h" in t:
        return "24hr"
    if "7d" in t or "48h" in t:
        return "7days"
    if "30d" in t:
        return "30days"
    return "7days"


# -------- Load Config --------
def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Error: Config file '{CONFIG_FILE}' not found.")
        return {}


# -------- Chunk Helper (NEW) --------
def chunk_list(items, chunk_size=50):
    """Yield successive chunk_size-sized chunks from the list."""
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


# -------- Client-Side Time Filter --------
def is_posted_within_window(job, time_window_str):
    posted_at = job.get("detected_extensions", {}).get("posted_at")
    if not posted_at:
        return False

    parts = posted_at.lower().split()
    if len(parts) < 2:
        return False
    try:
        value = int(parts[0])
    except ValueError:
        return False

    unit = parts[1].rstrip("s")

    time_delta = TIME_WINDOW_MAP.get(time_window_str, timedelta(days=7))

    if unit == "hour":
        time_since_post = timedelta(hours=value)
    elif unit == "day":
        time_since_post = timedelta(days=value)
    elif unit == "month":
        time_since_post = timedelta(days=value * 30)
    else:
        return False

    return time_since_post <= time_delta


# -------- Build Query (Updated) --------
def build_query(job_title, regions, ats_domains_chunk):
    search_terms = regions + ats_domains_chunk
    search_part = " OR ".join(f'"{r}"' for r in search_terms)
    return f'"{job_title}" ({search_part})'


# -------- SerpAPI Search --------
def search_jobs(query, date_posted_param, max_pages=3):
    all_results = []
    next_page_token = None

    print(f"Attempting API pre-filter: {date_posted_param}")

    for page_num in range(1, max_pages + 1):
        print(f"  -> Fetching page {page_num}...")
        params = {
            "engine": "google_jobs",
            "q": query,
            "hl": "en",
            "api_key": SERPAPI_KEY,
            "date_posted": date_posted_param,
        }

        if next_page_token:
            params["next_page_token"] = next_page_token

        try:
            r = requests.get("https://serpapi.com/search", params=params, timeout=30)
            r.raise_for_status()

            data = r.json()
            jobs = data.get("jobs_results", [])

            if not jobs:
                print("  -> No more results.")
                break

            all_results.extend(jobs)
            print(f"  -> Added {len(jobs)} jobs. Total: {len(all_results)}")

            next_page_token = data.get("serpapi_pagination", {}).get("next_page_token")
            if not next_page_token:
                break

            time.sleep(2)

        except requests.exceptions.HTTPError as e:
            print(f"⚠️ HTTP Error {e.response.status_code}: {r.text[:150]}")
            break

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            break

    return all_results


# -------- Write Results --------
def write_results(results, job_title, output_dir):
    if not results:
        print(f"⚠️ No results for '{job_title}'. Skipping.")
        return

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{job_title.replace(' ', '_').lower()}.txt")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"JOB SEARCH RESULTS FOR: {job_title}\n")
        f.write(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        for i, job in enumerate(results, 1):
            posted = job.get("detected_extensions", {}).get("posted_at", "N/A")

            f.write(f"--- Job {i} ---\n")
            f.write(f"Title: {job.get('title', 'N/A')}\n")
            f.write(f"Company: {job.get('company_name', 'N/A')}\n")
            f.write(f"Location: {job.get('location', 'N/A')}\n")
            f.write(f"Posted: {posted}\n")

            link = job.get("apply_options", [{}])[0].get("link", job.get("link", "N/A"))
            f.write(f"URL: {link}\n")

            desc = job.get("description", "No description available.")
            processed = desc[:400].replace("\n", " ")
            if len(desc) > 400:
                processed += "..."

            f.write(f"Description:\n  {processed}\n")
            f.write("-" * 80 + "\n")

    print(f"✅ Saved {len(results)} results → {out_path}")


# -------- Main --------
def main():
    if not SERPAPI_KEY:
        print("\n❌ Missing SERPAPI_KEY env variable.")
        return

    cfg = load_config()
    if not cfg:
        return

    time_window_str = cfg.get("time_window", "7d")
    api_date_posted_param = get_date_posted_param(time_window_str)

    job_titles = cfg.get("job_titles", ["Data Analyst"])
    regions = cfg.get("regions", ["United States"])
    ats_domains = cfg.get("ats_domains", [])

    if not job_titles or (not regions and not ats_domains):
        print("❌ Config Error: job_titles must exist, and regions or ats_domains.")
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join("results", f"{date_str}-googlejobs")

    # -----------------------------
    # PROCESS EACH JOB TITLE
    # -----------------------------
    for job_title in job_titles:
        print(f"\n========== Searching '{job_title}' ==========")

        # Break into chunks of max 50 ATS domains
        domain_chunks = list(chunk_list(ats_domains, 50))
        if not domain_chunks:
            domain_chunks = [[]]

        all_filtered_results = []

        for idx, ats_chunk in enumerate(domain_chunks, start=1):
            print(f"\n--- Processing ATS chunk {idx}/{len(domain_chunks)} (size={len(ats_chunk)}) ---")

            query = build_query(job_title, regions, ats_chunk)
            print(f"🔍 Query: {query}")

            raw_results = search_jobs(query, api_date_posted_param, max_pages=3)
            print(f"Filtering {len(raw_results)} results for time-window '{time_window_str}'")

            filtered = [
                job for job in raw_results
                if is_posted_within_window(job, time_window_str)
            ]

            print(f"Chunk {idx}: {len(filtered)} results after filtering")
            all_filtered_results.extend(filtered)

        print(f"\n🔥 Total results across all chunks: {len(all_filtered_results)}")

        if not all_filtered_results:
            print(f"⚠️ No recent jobs found for '{job_title}'.")
            continue

        write_results(all_filtered_results, job_title, output_dir)

    print("\nSearch complete.")


if __name__ == "__main__":
    main()
