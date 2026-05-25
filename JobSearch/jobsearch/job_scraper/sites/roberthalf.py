"""
sites/roberthalf.py — Robert Half job scraper.

URL: https://www.roberthalf.com/us/en/jobs/all/{title-slug}

Flow:
  1. Navigate to search URL
  2. Apply date filter (Past 24 hours / Past week / etc.)
  3. Scrape all jobs from listing page (has inline JD)
  4. Handle pagination (next page / load more)
  5. Visit each job page for full details
"""

import time
import re
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
)

from base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class RobertHalfScraper(BaseScraper):

    SITE_NAME = "roberthalf"
    BASE_URL = "https://www.roberthalf.com/us/en/jobs/all"

    def search_jobs(self, keyword: str, location: str) -> list[dict]:
        slug = keyword.strip().lower().replace(" ", "-")
        url = f"{self.BASE_URL}/{slug}"

        self.goto(url)
        time.sleep(2)
        self.dismiss_overlays()    # Dismiss "I understand" cookie banner
        time.sleep(1)
        self.dismiss_overlays()    # Try again in case it was slow to render
        self.wait_for_page_load(extra_wait=3)

        # Log result count
        self._log_result_count()

        # Step 1: Apply date filter
        if self.date_filter.lower() != "none":
            self.dismiss_overlays()  # Make sure cookie banner is gone before clicking filter
            self._apply_date_filter()

        # Step 2: Wait for filtered results to load, then scrape all pages
        logger.info(f"[{self.SITE_NAME}] Waiting for filtered results to load...")
        time.sleep(5)
        self.wait_for_page_load(extra_wait=3)
        self._log_result_count()

        jobs = self._scrape_all_pages()
        logger.info(f"[{self.SITE_NAME}] Scraped {len(jobs)} jobs from listing pages")

        # Step 3: Visit each job for full details
        if jobs:
            self._enrich_with_full_details(jobs)

        logger.info(f"[{self.SITE_NAME}] Final count: {len(jobs)} jobs for '{keyword}'")
        return jobs

    # ── date filter (shadow DOM) ─────────────────────────────
    def _apply_date_filter(self):
        logger.info(f"[{self.SITE_NAME}] Applying date filter: {self.date_filter}")
        target = self.date_filter.strip().lower()

        # All filter controls are inside shadow DOM.
        # Normal Selenium selectors can't reach them.
        # We must use execute_script to pierce shadow roots.

        # Step 1: Click the "Date Posted" filter button
        logger.info(f"  Step 1: Opening Date Posted filter...")
        clicked = self.driver.execute_script("""
            // Find all shadow hosts that contain filter buttons
            const allElements = document.querySelectorAll('*');
            for (const el of allElements) {
                if (el.shadowRoot) {
                    const btn = el.shadowRoot.querySelector('.rhcl-filter-item__heading-button');
                    if (btn && btn.textContent.toLowerCase().includes('date')) {
                        btn.click();
                        return btn.textContent.trim();
                    }
                }
            }
            // Also try the specific #date-posted-filter host
            const host = document.querySelector('#date-posted-filter');
            if (host && host.shadowRoot) {
                const btn = host.shadowRoot.querySelector('.rhcl-filter-item__heading-button');
                if (btn) { btn.click(); return btn.textContent.trim(); }
            }
            return null;
        """)

        if clicked:
            logger.info(f"  ✓ Clicked: '{clicked}'")
        else:
            logger.warning(f"  ⚠ Date Posted button not found in shadow DOM")
            return

        time.sleep(2)

        # Step 2: Select the radio option (e.g. "Past 24 hours")
        logger.info(f"  Step 2: Selecting '{self.date_filter}'...")
        selected = self.driver.execute_script("""
            const target = arguments[0];
            const allElements = document.querySelectorAll('*');
            for (const el of allElements) {
                if (el.shadowRoot) {
                    const labels = el.shadowRoot.querySelectorAll('.rhcl-radio-v2__info-label');
                    for (const lbl of labels) {
                        if (lbl.textContent.trim().toLowerCase().includes(target)) {
                            lbl.click();
                            return lbl.textContent.trim();
                        }
                    }
                }
            }
            return null;
        """, target)

        if selected:
            logger.info(f"  ✓ Selected: '{selected}'")
        else:
            logger.warning(f"  ⚠ '{self.date_filter}' option not found in shadow DOM")
            return

        time.sleep(1)

        # Step 3: Click "Apply Filter" button
        #         May be nested deeper in shadow DOM. Search recursively.
        logger.info(f"  Step 3: Clicking Apply Filter...")
        applied = self.driver.execute_script("""
            // Recursive function to search through nested shadow roots
            function findInShadow(root) {
                // Try aria-label first
                let btn = root.querySelector('button[aria-label="Apply Filter"]');
                if (btn) { btn.click(); return 'aria-label'; }

                // Try by text content
                const btns = root.querySelectorAll('button');
                for (const b of btns) {
                    const txt = b.textContent.trim().toLowerCase();
                    if (txt === 'apply filter' || txt === 'apply') {
                        b.click();
                        return 'text: ' + b.textContent.trim();
                    }
                }

                // Try any element with "apply" text (could be a div/span styled as button)
                const allEls = root.querySelectorAll('*');
                for (const el of allEls) {
                    const txt = el.textContent.trim().toLowerCase();
                    if (txt === 'apply filter' && el.tagName !== 'DIV') {
                        el.click();
                        return 'element: ' + el.tagName;
                    }
                }

                // Recurse into nested shadow roots
                for (const el of allEls) {
                    if (el.shadowRoot) {
                        const result = findInShadow(el.shadowRoot);
                        if (result) return result;
                    }
                }
                return null;
            }

            // Search all top-level shadow roots
            const allElements = document.querySelectorAll('*');
            for (const el of allElements) {
                if (el.shadowRoot) {
                    const result = findInShadow(el.shadowRoot);
                    if (result) return result;
                }
            }

            // Last resort: try in regular DOM too
            let btn = document.querySelector('button[aria-label="Apply Filter"]');
            if (btn) { btn.click(); return 'regular DOM'; }

            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                if (b.textContent.trim().toLowerCase().includes('apply filter')) {
                    b.click();
                    return 'regular DOM text';
                }
            }

            return null;
        """)

        if applied:
            logger.info(f"  ✓ Clicked Apply Filter (found via: {applied})")
        else:
            # Debug: dump what buttons exist in shadow roots
            debug = self.driver.execute_script("""
                const results = [];
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    if (!el.shadowRoot) continue;
                    const btns = el.shadowRoot.querySelectorAll('button');
                    for (const b of btns) {
                        results.push({
                            host: el.tagName + '#' + el.id + '.' + el.className,
                            text: b.textContent.trim().substring(0, 50),
                            ariaLabel: b.getAttribute('aria-label') || '',
                            classes: b.className
                        });
                    }
                }
                return JSON.stringify(results.slice(0, 20));
            """)
            logger.warning(f"  ⚠ Apply Filter not found. Buttons in shadow DOM: {debug}")

        time.sleep(4)
        self.wait_for_page_load(extra_wait=2)
        self._log_result_count()

    # ── pagination + scraping ─────────────────────────────────
    def _scrape_all_pages(self) -> list[dict]:
        all_jobs = []
        page_num = 1
        max_pages = 20  # safety limit

        while page_num <= max_pages:
            logger.info(f"[{self.SITE_NAME}] Scraping page {page_num}...")
            jobs = self._scrape_current_page()
            if not jobs:
                logger.info(f"  No jobs on page {page_num}, stopping pagination")
                break

            all_jobs.extend(jobs)
            logger.info(f"  Page {page_num}: {len(jobs)} jobs (total: {len(all_jobs)})")

            # Try to go to next page
            if not self._go_to_next_page():
                logger.info(f"  No more pages after page {page_num}")
                break

            page_num += 1
            self.wait_for_page_load(extra_wait=3)

        return all_jobs

    def _go_to_next_page(self) -> bool:
        """Click next page / load more. Returns True if successful."""
        # Try "Load More" button
        load_more_selectors = [
            "button[class*='load-more']",
            "button[class*='LoadMore']",
            "button[class*='show-more']",
            "a[class*='load-more']",
        ]
        for sel in load_more_selectors:
            btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
            for btn in btns:
                if btn.is_displayed():
                    self.scroll_to(btn)
                    self.safe_click(btn)
                    time.sleep(3)
                    return True

        # Try "Next" pagination link
        next_selectors = [
            "a[aria-label='Next']",
            "a[aria-label='next']",
            "button[aria-label='Next']",
            "a.next",
            "li.next a",
            "a[rel='next']",
            "button[class*='next']",
        ]
        for sel in next_selectors:
            btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
            for btn in btns:
                if btn.is_displayed():
                    self.scroll_to(btn)
                    self.safe_click(btn)
                    time.sleep(3)
                    return True

        # Try finding pagination by text "Next" or ">"
        for el in self.driver.find_elements(By.XPATH, "//a[contains(text(),'Next')] | //button[contains(text(),'Next')]"):
            if el.is_displayed():
                self.scroll_to(el)
                self.safe_click(el)
                time.sleep(3)
                return True

        # Try numbered pagination — click current+1
        try:
            current = self.driver.find_element(
                By.CSS_SELECTOR, "[class*='pagination'] [class*='active'], [class*='pagination'] [aria-current='page']"
            )
            current_num = int(current.text.strip())
            next_num = current_num + 1
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

        links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/us/en/job/']")

        for link in links:
            try:
                href = link.get_attribute("href") or ""
                title = link.text.strip()
            except StaleElementReferenceException:
                continue

            if not title or len(title) < 3 or href in seen:
                continue
            seen.add(href)

            if not href.startswith("http"):
                href = "https://www.roberthalf.com" + href

            job = self.make_job_dict(title=title, url=href, company="Robert Half")

            # Extract details from surrounding container
            try:
                container = link
                for _ in range(5):
                    try:
                        container = container.find_element(By.XPATH, "./..")
                    except NoSuchElementException:
                        break

                text = container.text or ""
                lines = [l.strip() for l in text.split("\n") if l.strip()]

                for line in lines:
                    if line == title:
                        continue

                    # Location: "City, ST" pattern
                    if re.match(r"^[A-Z][a-zA-Z\s\.]+,\s*[A-Z]{2}$", line) and not job["location"]:
                        job["location"] = line

                    # Salary
                    elif re.search(r"USD|Hourly|Yearly|\$\d", line, re.I) and not job["salary"]:
                        job["salary"] = line

                    # Date
                    elif re.match(r"^\d{4}-\d{2}-\d{2}", line) and not job["posted_date"]:
                        job["posted_date"] = line[:10]

                    # Work type
                    elif line.lower() in ("onsite", "remote", "hybrid") and not job["work_type"]:
                        job["work_type"] = line.lower()

                    # Job type
                    elif line.lower() in ("permanent", "temporary", "contract", "contract / temporary to hire",
                                           "temporary / contract") and not job["job_type"]:
                        job["job_type"] = line

                # JD: grab description-looking paragraphs
                desc_parts = []
                for line in lines:
                    if (len(line) > 60
                        and line != title
                        and "USD" not in line
                        and not re.match(r"^\d{4}-\d{2}", line)
                        and line.lower() not in ("onsite", "remote", "hybrid")):
                        desc_parts.append(line)
                if desc_parts:
                    job["jd"] = self.clean_html_text(" ".join(desc_parts))[:3000]

            except Exception as e:
                logger.debug(f"  Detail extraction error: {e}")

            jobs.append(job)

        return jobs

    # ── enrich with full details ──────────────────────────────
    def _enrich_with_full_details(self, jobs: list[dict]):
        """Visit each job page to get the complete JD + requirements."""
        logger.info(f"[{self.SITE_NAME}] Visiting {len(jobs)} job pages for full details...")

        for i, job in enumerate(jobs):
            try:
                logger.info(f"  [{i+1}/{len(jobs)}] {job['title'][:50]}")
                self.driver.get(job["url"])
                self.wait_for_page_load(extra_wait=2)
                self.dismiss_overlays()

                # Get full page text
                body = self.driver.find_element(By.TAG_NAME, "body").text or ""

                # Extract structured content
                full_jd = self._extract_jd_from_detail_page(body, job["title"])
                if full_jd and len(full_jd) > len(job.get("jd", "")):
                    job["jd"] = full_jd

                # Try to get any fields we missed
                if not job["location"]:
                    for line in body.split("\n"):
                        line = line.strip()
                        if re.match(r"^[A-Z][a-zA-Z\s\.]+,\s*[A-Z]{2}$", line):
                            job["location"] = line
                            break

                if not job["salary"]:
                    for line in body.split("\n"):
                        if re.search(r"USD|Hourly|Yearly|\$\d", line, re.I):
                            job["salary"] = line.strip()
                            break

            except Exception as e:
                logger.debug(f"  Error on job page: {e}")

            # Brief pause to be respectful
            time.sleep(1)

    def _extract_jd_from_detail_page(self, body_text: str, title: str) -> str:
        """Extract the JD section from a detail page body text."""
        lines = body_text.split("\n")
        jd_lines = []
        capturing = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Start capturing after we see the job title
            if title.lower() in line.lower() and not capturing:
                capturing = True
                continue

            if capturing:
                # Stop at footer-like content
                if any(stop in line.lower() for stop in [
                    "robert half is the world",
                    "all applicants applying",
                    "equal opportunity employer",
                    "download the robert half app",
                    "browse jobs",
                    "find your next hire",
                ]):
                    break

                # Skip short nav-like lines
                if len(line) < 15 and not line.endswith("."):
                    continue

                jd_lines.append(line)

        return self.clean_html_text(" ".join(jd_lines))[:5000]

    # ── utility ───────────────────────────────────────────────
    def _log_result_count(self):
        try:
            body = self.driver.find_element(By.TAG_NAME, "body").text
            match = re.search(r"(\d+)\s*results?\s", body)
            if match:
                logger.info(f"[{self.SITE_NAME}] Page shows: {match.group(0).strip()}")
        except Exception:
            pass
