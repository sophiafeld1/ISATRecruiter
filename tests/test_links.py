import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrape import scraper_ISAT, URL

# Create scraper and get links
scraper = scraper_ISAT(URL)
links = scraper.get_links()

# Count total links
total_links = len(links)
print(f"Total links found: {total_links}")

# Filter and count https/http links
https_links = [link for link in links if link and re.match(r"^http", link)]
https_count = len(https_links)
print(f"Links starting with http: {https_count}")

# Write to file and count
written_count = 0
with open("links_from_course_catalog.txt", "w", encoding="utf-8") as f:
    for link in links:
        if link and re.match(r"^http", link):
            print(link)
            f.write(f"{link}\n")
            written_count += 1

print(f"Links written to file: {written_count}")

# Verification
if written_count == https_count:
    print("✓ All https/http links successfully written to file!")
else:
    print(f"⚠ Warning: {https_count - written_count} links were not written!")

# Also verify by reading the file back
with open("links_from_course_catalog.txt", "r", encoding="utf-8") as f:
    file_lines = [line.strip() for line in f.readlines() if line.strip()]
    print(f"Lines in file: {len(file_lines)}")


