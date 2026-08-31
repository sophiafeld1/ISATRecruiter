"""
Scrape module for ISAT RAG project.
"""

from .scrape_base import scraper_ISAT

# Default program preview URL (same seed as crawler); tests and scripts may import this.
URL = "https://catalog.jmu.edu/preview_program.php?catoid=62&poid=27120#1"

__all__ = ["scraper_ISAT", "URL"]

