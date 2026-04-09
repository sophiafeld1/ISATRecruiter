"""
Display pages in the requested format:
- For each page: URL, scraped_at timestamp, links, and text content
"""
import sys
import os
import json

# Add project root to path so imports work
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.db_write import LinkDatabase
from psycopg2.extras import RealDictCursor

def view_pages():
    db = LinkDatabase()
    cursor = db.conn.cursor(cursor_factory=RealDictCursor)
    
    # Get all pages
    cursor.execute("""
        SELECT url, text, links, scraped_at
        FROM pages
        ORDER BY scraped_at DESC
    """)
    pages = cursor.fetchall()
    
    print("=" * 80)
    print("PAGES")
    print("=" * 80)
    print()
    
    if not pages:
        print("No pages found in database.")
    else:
        for i, page in enumerate(pages, 1):
            # Print URL
            print(f"Page {i}: {page['url']}")
            
            # Print scraped timestamp
            if page['scraped_at']:
                print(f"Scraped at: {page['scraped_at']}")
            
            # Print links if they exist
            if page['links']:
                links_list = page['links']
                if isinstance(links_list, str):
                    # If it's a JSON string, parse it
                    try:
                        links_list = json.loads(links_list)
                    except json.JSONDecodeError:
                        pass
                
                if isinstance(links_list, list) and len(links_list) > 0:
                    print(f"Links ({len(links_list)}):")
                    for link in links_list[:10]:  # Show first 10 links
                        print(f"  - {link}")
                    if len(links_list) > 10:
                        print(f"  ... and {len(links_list) - 10} more links")
            
            # Print text content (truncated if too long)
            if page['text']:
                text_preview = page['text'][:500] if len(page['text']) > 500 else page['text']
                print(f"\nText preview:")
                print(text_preview)
                if len(page['text']) > 500:
                    print(f"\n... (truncated, total length: {len(page['text'])} characters)")
            
            print("\n" + "-" * 80 + "\n")
    
    cursor.close()
    db.close()
    
    print(f"\nTotal pages: {len(pages)}")

if __name__ == "__main__":
    view_pages()

