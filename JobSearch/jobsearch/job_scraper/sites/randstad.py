"""
sites/randstad.py — Randstad USA job scraper.

URL: https://www.randstadusa.com/jobs/q-{keyword}/

Flow:
  1. Navigate to search URL
  2. Apply date filter (if available)
  3. Scrape job listings + paginate
  4. Visit each job page for full JD
"""

import time
import re
import logging
import urllib.parse

from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)

from base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class RandstadScraper(BaseScraper):

    SITE_NAME = "randstad"
    BASE_URL = "https://www.randstadusa.com/jobs"

    def search_jobs(self, keyword: str, location: str) -> list[dict]:
        kw_slug = keyword.strip().replace(" ", "+")
        url = f"{self.BASE_URL}/q-{urllib.parse.quote(kw_slug, safe='+')}/"

        self.goto(url)
        self.dismiss_overlays()
        self.wait_for_page_load(extra_wait=3)

        # Step 1: Apply date filter
        if self.date_filter.lower() != "none":
            self._apply_date_filter()

        # Step 2: Scrape all pages
        jobs = self._scrape_all_pages()
        logger.info(f"[{self.SITE_NAME}] Scraped {len(jobs)} jobs from listing pages")

        # Step 3: Visit each job for full details
        if jobs:
            self._enrich_with_full_details(jobs)

        logger.info(f"[{self.SITE_NAME}] Final count: {len(jobs)} jobs for '{keyword}'")
        return jobs

    # ── date filter ───────────────────────────────────────────
    def _apply_date_filter(self):
        logger.info(f"[{self.SITE_NAME}] Applying date filter: {self.date_filter}")

        # Randstad uses dropdown filters at the top of results
        # Look for "Date posted" or "Sort by" controls
        filter_selectors = [
            "button[class*='filter']",
            "button[class*='Filter']",
            "select[class*='sort']",
            "button[data-testid*='filter']",
            "div[class*='filter'] button",
            "button[aria-label*='date' i]",
            "button[aria-label*='filter' i]",
        ]

        filter_btns = self.find_by_selectors(filter_selectors)

        # Also try finding by text content
        if not filter_btns:
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in all_buttons:
                txt = btn.text.strip().lower()
                if any(w in txt for w in ("date", "posted", "filter", "sort")):
                    filter_btns = [btn]
                    break

        if filter_btns:
            for btn in filter_btns:
                txt = btn.text.strip().lower()
                if any(w in txt for w in ("date", "posted", "time", "sort", "filter")):
                    self.scroll_to(btn)
                    self.safe_click(btn)
                    logger.info(f"  ✓ Clicked filter: '{btn.text.strip()}'")
                    time.sleep(1.5)
                    break
        else:
            logger.info(f"  No filter buttons found")

        # Try to select the date option
        target = self.date_filter.strip().lower()
        all_options = self.driver.find_elements(By.TAG_NAME, "label") + \
                      self.driver.find_elements(By.TAG_NAME, "option") + \
                      self.driver.find_elements(By.CSS_SELECTOR, "li[role='option'], [role='menuitem']")

        for opt in all_options:
            opt_text = opt.text.strip().lower()
            if target in opt_text or ("24" in target and "24" in opt_text):
                self.safe_click(opt)
                logger.info(f"  ✓ Selected: '{opt.text.strip()}'")
                time.sleep(3)
                return

        # Try URL-based date filter as fallback
        # Randstad sometimes supports /d-1/ for past day, /d-7/ for past week
        current_url = self.driver.current_url.rstrip("/")
        if "24 hour" in target or "1 day" in target:
            date_url = current_url + "/d-1/"
        elif "week" in target:
            date_url = current_url + "/d-7/"
        elif "month" in target:
            date_url = current_url + "/d-30/"
        else:
            logger.warning(f"  ⚠ Could not apply date filter")
            return

        logger.info(f"  Trying URL-based date filter: {date_url}")
        self.driver.get(date_url)
        self.wait_for_page_load(extra_wait=3)

    # ── pagination + scraping ─────────────────────────────────
    def _scrape_all_pages(self) -> list[dict]:
        all_jobs = []
        page_num = 1
        max_pages = 20

        while page_num <= max_pages:
            logger.info(f"[{self.SITE_NAME}] Scraping page {page_num}...")
            jobs = self._scrape_current_page()
            if not jobs:
                break

            all_jobs.extend(jobs)
            logger.info(f"  Page {page_num}: {len(jobs)} jobs (total: {len(all_jobs)})")

            if not self._go_to_next_page():
                break

            page_num += 1
            self.wait_for_page_load(extra_wait=3)

        return all_jobs

    def _go_to_next_page(self) -> bool:
        next_selectors = [
            "a[aria-label='Next']", "a[aria-label='next']",
            "button[aria-label='Next']", "a[rel='next']",
            "a.next", "li.next a", "button[class*='next']",
        ]
        for sel in next_selectors:
            btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
            for btn in btns:
                if btn.is_displayed():
                    self.scroll_to(btn)
                    self.safe_click(btn)
                    time.sleep(3)
                    return True

        for el in self.driver.find_elements(
            By.XPATH, "//a[contains(text(),'Next')] | //button[contains(text(),'Next')]"
        ):
            if el.is_displayed():
                self.scroll_to(el)
                self.safe_click(el)
                time.sleep(3)
                return True

        # Try page numbers
        try:
            current = self.driver.find_element(
                By.CSS_SELECTOR, "[class*='pagination'] [class*='active'], [aria-current='page']"
            )
            next_num = int(current.text.strip()) + 1
            for a in self.driver.find_elements(By.CSS_SELECTOR, "[class*='pagination'] a"):
                if a.text.strip() == str(next_num):
                    self.safe_click(a)
                    time.sleep(3)
                    return True
        except (NoSuchElementException, ValueError):
            pass

        return False

    # ── scrape current page ───────────────────────────────────
    def _scrape_current_page(self) -> list[dict]:
        jobs = []
        seen = set()

        # Try card-based selectors
        card_selectors = [
            "article[class*='job']", "div[class*='job-card']",
            "div[data-testid='job-card']", "li[class*='job']",
            "div[class*='CardWrapper']", "div[class*='search-result']",
        ]
        cards = self.find_by_selectors(card_selectors)

        if cards:
            for card in cards:
                job = self._parse_card(card)
                if job["title"] and job["url"] not in seen:
                    seen.add(job["url"])
                    jobs.append(job)
        else:
            # Fallback: job links
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/job/']")
            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    title = link.text.strip()
                except StaleElementReferenceException:
                    continue

                if (not title or len(title) < 8 or href in seen
                    or any(skip in href for skip in [
                        "/jobs/q-", "/jobs/l-", "/jobs/t-", "/jobs/s-",
                        "/jobs/r-", "/jobs/internal", "/jobs/remote",
                        "/job-seeker", "/employers",
                    ])):
                    continue

                seen.add(href)
                if not href.startswith("http"):
                    href = "https://www.randstadusa.com" + href

                job = self.make_job_dict(title=title, url=href, company="Randstad")
                self._extract_surrounding_details(link, job)
                jobs.append(job)

        return jobs

    def _parse_card(self, card) -> dict:
        job = self.make_job_dict(company="Randstad")

        for sel in ["h2 a", "h3 a", "a[class*='title']", "a[class*='Title']", "a"]:
            try:
                el = card.find_element(By.CSS_SELECTOR, sel)
                t = el.text.strip()
                if t and len(t) > 3:
                    job["title"] = t
                    href = el.get_attribute("href") or ""
                    if href and not href.startswith("http"):
                        href = "https://www.randstadusa.com" + href
                    job["url"] = href
                    break
            except NoSuchElementException:
                pass

        for sel in ["[class*='location']", "[class*='Location']", "span.meta"]:
            try:
                job["location"] = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                break
            except NoSuchElementException:
                pass

        for sel in ["[class*='salary']", "[class*='pay']"]:
            try:
                job["salary"] = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                break
            except NoSuchElementException:
                pass

        for sel in ["[class*='description']", "[class*='Description']", "p"]:
            try:
                txt = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                if txt and len(txt) > 30:
                    job["jd"] = self.clean_html_text(txt)[:3000]
                    break
            except NoSuchElementException:
                pass

        return job

    def _extract_surrounding_details(self, link_el, job: dict):
        try:
            parent = link_el.find_element(By.XPATH, "./../..")
            text = parent.text or ""
            for line in text.split("\n"):
                line = line.strip()
                if re.match(r"^[A-Z][a-zA-Z\s\.]+,\s*[A-Z]{2}$", line) and not job["location"]:
                    job["location"] = line
                elif re.search(r"\$|per hour|per year|salary|USD", line, re.I) and not job["salary"]:
                    job["salary"] = line
        except Exception:
            pass

    # ── enrich with full details ──────────────────────────────
    def _enrich_with_full_details(self, jobs: list[dict]):
        logger.info(f"[{self.SITE_NAME}] Visiting {len(jobs)} job pages for full details...")

        for i, job in enumerate(jobs):
            try:
                logger.info(f"  [{i+1}/{len(jobs)}] {job['title'][:50]}")
                self.driver.get(job["url"])
                self.wait_for_page_load(extra_wait=2)
                self.dismiss_overlays()

                body = self.driver.find_element(By.TAG_NAME, "body").text or ""

                # Extract JD
                jd = self._extract_jd(body)
                if jd and len(jd) > len(job.get("jd", "")):
                    job["jd"] = jd

                # Fill missing fields
                if not job["location"]:
                    for line in body.split("\n"):
                        if re.match(r"^[A-Z][a-zA-Z\s\.]+,\s*[A-Z]{2}$", line.strip()):
                            job["location"] = line.strip()
                            break

                if not job["salary"]:
                    for line in body.split("\n"):
                        if re.search(r"\$[\d,]+|per hour|per year|salary range", line, re.I):
                            job["salary"] = line.strip()
                            break

                if not job["posted_date"]:
                    match = re.search(r"posted\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", body, re.I)
                    if match:
                        job["posted_date"] = match.group(1)

            except Exception as e:
                logger.debug(f"  Error: {e}")

            time.sleep(1)

    def _extract_jd(self, body_text: str) -> str:
        lines = body_text.split("\n")
        jd_lines = []
        capturing = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if any(kw in line.lower() for kw in ["job description", "about this role",
                                                    "responsibilities", "what you"]):
                capturing = True

            if capturing:
                if any(stop in line.lower() for stop in [
                    "about randstad", "equal opportunity", "apply now",
                    "similar jobs", "share this job", "randstad is",
                    "privacy policy", "cookie",
                ]):
                    break
                if len(line) > 10:
                    jd_lines.append(line)
            elif len(line) > 80:
                jd_lines.append(line)

        return self.clean_html_text(" ".join(jd_lines))[:5000]
