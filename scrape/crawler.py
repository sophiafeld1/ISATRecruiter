import sys
import os

# Add project root to path so imports work
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scrape.scrape_base import scraper_ISAT
from database.db_write import LinkDatabase
from urllib.parse import urljoin, urlparse
import time


class Crawler:
    def __init__(self, seed_url: str):
        self.seed_url = seed_url
        self.visited = set[str]()
        self.queue = [seed_url]
        self.db = LinkDatabase()

    def should_follow(self, url: str, base_domain: str) -> bool:
        """Decide if we should follow this link."""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ['http', 'https'] or parsed.netloc.lower() != base_domain.lower():
                return False
            # Allow preview_program.php pages (you want to scrape the seed page)
            return True
        except:
            return False

    def crawl(self, max_pages: int = 100):
        """Crawl starting from seed_url."""
        base_domain = urlparse(self.seed_url).netloc
        pages_crawled = 0
        
        print(f"Starting crawl: {self.seed_url} (max {max_pages} pages)\n")
        
        while self.queue and pages_crawled < max_pages:
            url = self.queue.pop(0)
            
            if url in self.visited:
                continue
            
            self.visited.add(url)
            pages_crawled += 1
            
            try:
                scraper = scraper_ISAT(url)
                text = scraper.clean_text()
                links = scraper.get_links()
                
                # Store main page text (without course descriptions)
                page_id = self.db.upsert_page(url, text=text, links=links)
                print(f"[{pages_crawled}] {url}")
                print(f"  ✓ Stored page (ID: {page_id}, {len(text)} chars, {len(links)} links)")
                
                # Extract courses from program page
                courses = scraper.get_courses_from_program_page()
                courses_stored = 0
                courses_with_desc = 0
                if courses:
                    print(f"  Found {len(courses)} courses on page")
                    for course in courses:
                        # Only store if we have a description (non-empty)
                        if course['course_description']:
                            self.db.insert_course(
                                course['course_name'],
                                course['course_description'],
                                course.get('prerequisites')
                            )
                            courses_stored += 1
                            courses_with_desc += 1
                        time.sleep(0.2)  # Be nice to server when fetching descriptions
                    
                    if courses_stored > 0:
                        print(f"  ✓ Stored {courses_stored} courses ({courses_with_desc} with descriptions)")
                
                # Add new links to queue
                new_links = 0
                for link in links:
                    # Skip fragment-only links (they're anchors on the same page)
                    if link.startswith('#'):
                        continue
                    
                    absolute_link = urljoin(url, link)
                    
                    # Skip if URL is same page with just different fragment
                    parsed_current = urlparse(url)
                    parsed_link = urlparse(absolute_link)
                    base_current = parsed_current.path + ('?' + parsed_current.query if parsed_current.query else '')
                    base_link = parsed_link.path + ('?' + parsed_link.query if parsed_link.query else '')
                    
                    if base_current == base_link:
                        continue  # Same page, different fragment - don't follow
                    
                    if self.should_follow(absolute_link, base_domain):
                        if absolute_link not in self.visited and absolute_link not in self.queue:
                            self.queue.append(absolute_link)
                            new_links += 1
                
                if new_links > 0:
                    print(f"  → Added {new_links} URLs to queue ({len(self.queue)} total)\n")
                else:
                    print()
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ✗ Error: {e}\n")
                continue
        
        print(f"\nComplete! Visited {pages_crawled} pages.")
        self.db.close()


if __name__ == "__main__":
    seed_url = "https://catalog.jmu.edu/preview_program.php?catoid=62&poid=27120#1"
    crawler = Crawler(seed_url)
    crawler.crawl(max_pages=50)  # Start with 50 pages as a test
