"""
Minimal test script for the crawler.
"""
import sys
import os

# Add project root to path so imports work
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scrape.crawler import Crawler
from database.db_write import LinkDatabase
from psycopg2.extras import RealDictCursor

if __name__ == "__main__":
    seed_url = "https://catalog.jmu.edu/preview_program.php?catoid=62&poid=27120#1"
    crawler = Crawler(seed_url)
    
    try:
        crawler.crawl(max_pages=5)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\nVisited: {len(crawler.visited)} pages")
    print(f"Queue: {len(crawler.queue)} URLs remaining")
    
    # Write all parsed text to file
    print("\nWriting all parsed text to parsed_text.txt...")
    db = LinkDatabase()
    cursor = db.conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT url, text FROM pages ORDER BY id")
    pages = cursor.fetchall()
    cursor.close()
    db.close()
    
    # Use absolute path to project root
    output_file = os.path.join(project_root, "parsed_text.txt")
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            for i, page in enumerate(pages, 1):
                f.write(f"{'='*80}\n")
                f.write(f"Page {i}: {page['url']}\n")
                f.write(f"{'='*80}\n\n")
                if page['text']:
                    f.write(page['text'])
                    f.write("\n\n")
                else:
                    f.write("[No text content]\n\n")
        
        print(f"✓ Wrote {len(pages)} pages to {output_file}")
    except Exception as e:
        print(f"✗ Error writing file: {e}")
        import traceback
        traceback.print_exc()

