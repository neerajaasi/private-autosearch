"""
sites/_template.py — Copy this to create a new scraper.

  1. cp sites/_template.py sites/yoursite.py
  2. Fill in SITE_NAME, BASE_URL, search_jobs()
  3. Register in sites/__init__.py
  4. Add name to sites.txt
"""

import time
import logging
from selenium.webdriver.common.by import By
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class TemplateScraper(BaseScraper):

    SITE_NAME = "yoursite"
    BASE_URL = "https://example.com/jobs"

    def search_jobs(self, keyword: str, location: str) -> list[dict]:
        # Build search URL (preferred) or navigate + fill form
        slug = keyword.strip().lower().replace(" ", "-")
        url = f"{self.BASE_URL}/{slug}"

        self.goto(url)
        self.dismiss_overlays()
        self.wait_for_page_load()

        # Scrape job cards/links and return list of dicts:
        # {"title", "url", "location", "salary", "company", "posted_date", "jd"}
        return []
