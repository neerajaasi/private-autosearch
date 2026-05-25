"""
base_scraper.py — Abstract base class for all job site scrapers.
Includes helpers for date filtering, pagination, and detail extraction.
"""

import time
import logging
import re
from abc import ABC, abstractmethod

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)

logger = logging.getLogger(__name__)

# Standard job dict keys
JOB_KEYS = ["title", "url", "location", "salary", "company", "posted_date", "jd", "job_type", "work_type"]


class BaseScraper(ABC):
    SITE_NAME: str = ""
    BASE_URL: str = ""
    WAIT_TIMEOUT: int = 15

    def __init__(self, driver: webdriver.Chrome, date_filter: str = "Past 24 hours"):
        self.driver = driver
        self.wait = WebDriverWait(driver, self.WAIT_TIMEOUT)
        self.date_filter = date_filter  # e.g. "Past 24 hours", "Past week", "none"

    @abstractmethod
    def search_jobs(self, keyword: str, location: str) -> list[dict]:
        ...

    # ── navigation ────────────────────────────────────────────
    def goto(self, url: str | None = None):
        url = url or self.BASE_URL
        logger.info(f"[{self.SITE_NAME}] → {url}")
        self.driver.get(url)
        time.sleep(3)

    def wait_for_page_load(self, extra_wait: float = 2):
        try:
            self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        except TimeoutException:
            pass
        time.sleep(extra_wait)

    # ── overlays ──────────────────────────────────────────────
    def dismiss_overlays(self):
        # Regular DOM cookie banners
        for sel in ["#onetrust-accept-btn-handler", "button[aria-label='Close']",
                     ".cookie-accept", "#cookie-accept", "button[id*='cookie']"]:
            try:
                self.driver.find_element(By.CSS_SELECTOR, sel).click()
                time.sleep(1)
                logger.debug(f"  Dismissed overlay: {sel}")
            except (NoSuchElementException, ElementClickInterceptedException):
                pass

        # "I understand" button (Robert Half cookie banner)
        try:
            for btn in self.driver.find_elements(By.TAG_NAME, "button"):
                if btn.text.strip().lower() in ("i understand", "accept", "accept all", "got it", "agree"):
                    btn.click()
                    time.sleep(1)
                    logger.debug(f"  Dismissed: '{btn.text.strip()}'")
                    break
        except Exception:
            pass

        # Also try shadow DOM overlays
        try:
            self.driver.execute_script("""
                // Search regular DOM for common cookie buttons
                const texts = ['i understand', 'accept', 'accept all', 'got it', 'agree'];
                const btns = document.querySelectorAll('button, a.button, [role="button"]');
                for (const btn of btns) {
                    const txt = btn.textContent.trim().toLowerCase();
                    if (texts.includes(txt)) { btn.click(); return; }
                }
                // Search shadow roots
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    if (!el.shadowRoot) continue;
                    const shadowBtns = el.shadowRoot.querySelectorAll('button, a.button, [role="button"]');
                    for (const btn of shadowBtns) {
                        const txt = btn.textContent.trim().toLowerCase();
                        if (texts.includes(txt)) { btn.click(); return; }
                    }
                }
            """)
        except Exception:
            pass

    # ── interaction helpers ───────────────────────────────────
    def safe_click(self, element):
        try:
            element.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", element)

    def scroll_to(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        time.sleep(0.3)

    def clear_and_type(self, element, text: str):
        element.click()
        time.sleep(0.2)
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.DELETE)
        time.sleep(0.2)
        element.send_keys(text)
        time.sleep(0.4)

    def find_by_selectors(self, selectors: list[str], parent=None):
        root = parent or self.driver
        for sel in selectors:
            els = root.find_elements(By.CSS_SELECTOR, sel)
            if els:
                return els
        return []

    def shadow_click(self, host_selector: str, inner_selector: str, match_text: str = "") -> bool:
        """Click an element inside a shadow DOM root.
        
        Args:
            host_selector: CSS selector for the shadow host element
            inner_selector: CSS selector inside the shadow root
            match_text: Optional text to match (case-insensitive)
        Returns:
            True if clicked successfully
        """
        script = """
            const hosts = document.querySelectorAll(arguments[0]);
            const innerSel = arguments[1];
            const matchText = arguments[2].toLowerCase();
            for (const host of hosts) {
                if (!host.shadowRoot) continue;
                const els = host.shadowRoot.querySelectorAll(innerSel);
                for (const el of els) {
                    if (!matchText || el.textContent.trim().toLowerCase().includes(matchText)) {
                        el.click();
                        return el.textContent.trim();
                    }
                }
            }
            // Also scan ALL shadow roots on page
            const allEls = document.querySelectorAll('*');
            for (const el of allEls) {
                if (!el.shadowRoot) continue;
                const matches = el.shadowRoot.querySelectorAll(innerSel);
                for (const m of matches) {
                    if (!matchText || m.textContent.trim().toLowerCase().includes(matchText)) {
                        m.click();
                        return m.textContent.trim();
                    }
                }
            }
            return null;
        """
        result = self.driver.execute_script(script, host_selector, inner_selector, match_text)
        return result is not None

    def screenshot(self, name: str = "debug"):
        path = f"{name}_{self.SITE_NAME}.png"
        self.driver.save_screenshot(path)
        return path

    # ── job detail extraction ─────────────────────────────────
    def visit_job_page(self, url: str) -> dict:
        """Navigate to a single job page and extract full details."""
        details = {"jd": "", "requirements": ""}
        try:
            self.driver.get(url)
            self.wait_for_page_load(extra_wait=2)
            self.dismiss_overlays()

            body_text = self.driver.find_element(By.TAG_NAME, "body").text or ""
            details["jd"] = body_text[:5000]
        except Exception as e:
            logger.debug(f"  Error visiting {url}: {e}")
        return details

    # ── text parsing helpers ──────────────────────────────────
    @staticmethod
    def clean_html_text(text: str) -> str:
        """Strip HTML tags from text."""
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    @staticmethod
    def make_job_dict(**kwargs) -> dict:
        """Create a standardized job dict."""
        job = {k: "" for k in JOB_KEYS}
        job.update(kwargs)
        return job
