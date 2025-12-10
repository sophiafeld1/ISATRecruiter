import sys
import os

# Add project root to path so imports work
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scrape.scrape_base import scraper_ISAT
from database.db_write import LinkDatabase
import time


class Crawler:
    def __init__(self, seed_url: str):
        self.seed_url = seed_url
        self.db = LinkDatabase()
        # Open log files for appending
        self.courses_log = open(os.path.join(project_root, "all_db_output.txt"), "a", encoding="utf-8")
        self.pages_log = open(os.path.join(project_root, "pages_output.txt"), "a", encoding="utf-8")

    def crawl(self):
        """Crawl the ISAT program page and extract all courses."""
        print(f"Starting crawl: {self.seed_url}\n")
        
        try:
            # Scrape the ISAT program page
            scraper = scraper_ISAT(self.seed_url)
            text = scraper.clean_text()
            links = scraper.get_links()
            
            # Store program page
            page_id = self.db.upsert_page(self.seed_url, text=text, links=links)
            print(f"✓ Stored program page (ID: {page_id}, {len(text)} chars, {len(links)} links)")
            
            # Log page to file
            self.pages_log.write("=" * 80 + "\n")
            self.pages_log.write(f"ID: {page_id}\n")
            self.pages_log.write(f"URL: {self.seed_url}\n")
            self.pages_log.write(f"Text length: {len(text)} characters\n")
            self.pages_log.write(f"Links: {len(links)} links\n")
            self.pages_log.write(f"Text preview: {text[:500]}...\n")
            self.pages_log.write("-" * 80 + "\n\n")
            self.pages_log.flush()
            
            # Extract courses from program page
            courses = scraper.get_courses_from_program_page()
            print(f"\nFound {len(courses)} courses on page\n")
            
            courses_stored = 0
            for course in courses:
                # Only store if we have a description (non-empty)
                if course.get('course_description') and len(course['course_description'].strip()) > 50:
                    course_id = self.db.insert_course(
                        course['course_name'],
                        course['course_code'],
                        course['course_description'],
                        course.get('prerequisites'),
                        course.get('url')
                    )
                    courses_stored += 1
                    
                    # Log course to file
                    self.courses_log.write("=" * 80 + "\n")
                    self.courses_log.write(f"Course ID: {course_id}\n")
                    self.courses_log.write(f"Course Name: {course['course_name']}\n")
                    self.courses_log.write(f"Course Code: {course['course_code']}\n")
                    self.courses_log.write(f"Prerequisites: {course.get('prerequisites', 'None')}\n")
                    self.courses_log.write(f"URL: {course.get('url', 'N/A')}\n")
                    self.courses_log.write(f"Description length: {len(course['course_description'])} characters\n")
                    self.courses_log.write(f"Description preview: {course['course_description'][:500]}...\n")
                    self.courses_log.write("-" * 80 + "\n\n")
                    self.courses_log.flush()
                    
                    print(f"  ✓ Stored: {course['course_code']} - {course['course_name']}")
                else:
                    print(f"  ✗ Skipped: {course['course_code']} - No description")
                
                time.sleep(0.2)  # Be nice to server
            
            print(f"\n✓ Complete! Stored {courses_stored} courses out of {len(courses)} total.")
            
        except Exception as e:
            print(f"✗ Error: {e}")
        finally:
            self.db.close()
            self.courses_log.close()
            self.pages_log.close()


if __name__ == "__main__":
    seed_url = "https://catalog.jmu.edu/preview_program.php?catoid=62&poid=27120#1"
    crawler = Crawler(seed_url)
    crawler.crawl()
