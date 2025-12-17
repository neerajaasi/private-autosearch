import requests
import socket
import csv
import os
from datetime import datetime

# -------------------------------------------------------------
# Folder structure setup (auto-detect base)
# -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_DIR = os.path.join(BASE_DIR, "config")
CORE_DIR   = os.path.join(BASE_DIR, "core")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Ensure output folder exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


# -------------------------------------------------------------
# Load domains from config/sites.txt
# -------------------------------------------------------------
def load_domains(filename="sites.txt"):
    path = os.path.join(CONFIG_DIR, filename)

    domains = set()

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip().lower()

            if not line:
                continue

            # Remove protocol
            if line.startswith("http://"):
                line = line.replace("http://", "")
            if line.startswith("https://"):
                line = line.replace("https://", "")

            # Remove path
            line = line.split("/")[0]

            domains.add(line)

    return sorted(domains)


# -------------------------------------------------------------
# DNS Validation
# -------------------------------------------------------------
def check_dns(domain):
    try:
        socket.gethostbyname(domain)
        return "OK"
    except:
        return "DNS_FAIL"


# -------------------------------------------------------------
# HTTP/HTTPS reachability
# -------------------------------------------------------------
def check_http(domain):
    urls_to_try = [
        f"https://{domain}",
        f"http://{domain}"
    ]

    for url in urls_to_try:
        try:
            r = requests.get(url, timeout=7, allow_redirects=True)
            return (
                "UP",
                r.status_code,
                r.url
            )
        except requests.exceptions.RequestException:
            continue

    return ("DOWN", None, None)


# -------------------------------------------------------------
# MAIN PROCESS
# -------------------------------------------------------------
def main():

    domains = load_domains("sites.txt")
    results = []

    print(f"Loaded {len(domains)} unique domains from sites.txt\n")
    print("Checking...\n")

    for domain in domains:
        dns_status = check_dns(domain)

        if dns_status != "OK":
            print(f"[DNS_FAIL] {domain}")
            results.append([domain, "DNS_FAIL", "", "", ""])
            continue

        http_status, code, final_url = check_http(domain)

        note = ""
        if final_url and final_url not in (f"http://{domain}", f"https://{domain}"):
            note = "Redirected"

        print(f"[{http_status}] {domain} -> {final_url}")

        results.append([
            domain,
            http_status,
            code if code else "",
            final_url if final_url else "",
            note
        ])

    # ---------------------------------------------------------
    # Create dated output folder
    # ---------------------------------------------------------
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(OUTPUT_DIR, today)
    os.makedirs(out_dir, exist_ok=True)

    # ---------------------------------------------------------
    # Save CSV
    # ---------------------------------------------------------
    csv_filename = os.path.join(out_dir, "domain_status_report.csv")
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["domain", "reachability", "http_code", "final_url", "notes"])
        writer.writerows(results)

    print(f"\nCSV report saved: {csv_filename}")

    # ---------------------------------------------------------
    # Save TXT
    # ---------------------------------------------------------
    txt_filename = os.path.join(out_dir, "domain_status_report.txt")
    with open(txt_filename, "w", encoding="utf-8") as f:
        for row in results:
            f.write(" | ".join([str(x) for x in row]) + "\n")

    print(f"TXT report saved: {txt_filename}\n")


if __name__ == "__main__":
    main()
