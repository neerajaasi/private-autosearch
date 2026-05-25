"""
sites/__init__.py — Site plugin registry.

To add a new site:
  1. Create sites/yoursite.py with a class extending BaseScraper
  2. Import and register it below
  3. Add the name to sites.txt
"""

from sites.roberthalf import RobertHalfScraper
from sites.randstad import RandstadScraper

REGISTRY: dict = {
    "roberthalf": RobertHalfScraper,
    "randstad":   RandstadScraper,
}
