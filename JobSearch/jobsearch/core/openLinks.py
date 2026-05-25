import webbrowser
import time
import os
from pathlib import Path

# File containing links
BASE_DIR = Path(__file__).resolve().parents[2]
file_path = BASE_DIR / "jobsearch" / "config" / "links.txt"

if not os.path.exists(file_path):
    print("links.txt not found!")
    exit()

# Read links
with open(file_path, "r") as f:
    links = [line.strip() for line in f if line.strip()]

if not links:
    print("No links found in file.")
    exit()

# Open each link in new tab
for link in links:
    webbrowser.open_new_tab(link)
    time.sleep(1)   # small delay to avoid opening too fast

print(f"{len(links)} links opened. Browser remains open.")