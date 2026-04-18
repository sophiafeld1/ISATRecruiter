"""
Interactive database viewer - choose which table to view.
"""
import sys
import os

# Add project root to path so imports work
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.db_write import LinkDatabase
from psycopg2.extras import RealDictCursor


def _truncate(text: str | None, max_len: int = 12000) -> str:
    if text is None:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"\n\n... [{len(text) - max_len} more chars truncated]"


def view_pages(cursor):
    """View pages table."""
    print("=" * 80)
    print("PAGES TABLE")
    print("=" * 80)
    cursor.execute("SELECT * FROM pages ORDER BY id")
    pages = cursor.fetchall()
    for page in pages:
        print(f"\nID: {page['id']}\n\n")
        print(f"URL: {page['url']}\n\n")
        print(f"Text: {page['text']}\n\n")
        print(f"Links: {page['links']}\n\n")
        print(f"Scraped at: {page['scraped_at']}\n\n")
        print("-" * 80)
    print(f"\nTotal pages: {len(pages)}\n\n")

def view_chunks(cursor):
    """View chunks table."""
    print("=" * 80)
    print("CHUNKS TABLE")
    print("=" * 80)
    cursor.execute("SELECT * FROM chunks ORDER BY id")
    chunks = cursor.fetchall()
    for chunk in chunks:
        print(f"\nID: {chunk['id']}")
        print(f"Page ID: {chunk['page_id']}\n\n")
        print(f"Chunk text: {chunk['chunk_text']}\n\n")
        print(f"Embedding: {chunk['embedding']}\n\n")
        print(f"Token count: {chunk['token_count']}\n\n")
        print("-" * 80 + "\n\n" )
    print(f"\nTotal chunks: {len(chunks)}\n")

def view_courses(cursor, show_list=True):
    """View courses table."""
    print("=" * 80)
    print("COURSES TABLE")
    print("=" * 80)
    cursor.execute("SELECT * FROM courses ORDER BY id")
    courses = cursor.fetchall()
    for course in courses:
        print(f"\nID: {course['id']}\n\n")
        print(f"Course name: {course.get('course_name', 'N/A')}\n\n")
        print(f"Course code: {course.get('course_code', 'N/A')}\n\n")
        print(f"Course description: {course.get('course_description', 'N/A')}\n\n")
        print(f"Prerequisites: {course.get('prerequisites', 'None')}\n\n")
        print(f"URL: {course.get('url', 'N/A')}\n\n")
        print("-" * 80 + "\n\n")
    print(f"\nTotal courses: {len(courses)}\n\n")
    
    # Print all course names as comma-separated list
    if show_list:
        print("=" * 80)
        print("ALL COURSE NAMES (COMMA-SEPARATED)")
        print("=" * 80)
        course_names = [course['course_name'] for course in courses]
        print(", ".join(course_names))
        print()


def view_urls(cursor):
    """View urls table."""
    print("=" * 80)
    print("URLS TABLE")
    print("=" * 80)
    cursor.execute("SELECT * FROM urls ORDER BY id")
    rows = cursor.fetchall()
    for row in rows:
        print(f"\nID: {row['id']}\n")
        print(f"Description: {row.get('description', '')}\n")
        print(f"URL: {row.get('url', '')}\n")
        print(f"Created at: {row.get('created_at')}\n")
        print("-" * 80)
    print(f"\nTotal urls: {len(rows)}\n")


def view_abet_syllabi(cursor):
    """View abet_syllabi table (parsed ABET syllabus metadata)."""
    print("=" * 80)
    print("ABET SYLLABI")
    print("=" * 80)
    cursor.execute("SELECT * FROM abet_syllabi ORDER BY id")
    rows = cursor.fetchall()
    for row in rows:
        print(f"\nID: {row['id']}\n")
        print(f"Source PDF: {row.get('source_pdf_path', '')}\n")
        print(f"Course code: {row.get('course_code', '')}\n")
        print(f"Course name: {row.get('course_name', '')}\n")
        print(f"Professor: {row.get('professor_name', '')}\n")
        print(f"Description: {row.get('course_description', '')}\n")
        print(f"Prerequisites: {row.get('prerequisites', '')}\n")
        print(f"Outcomes: {row.get('course_outcomes', '')}\n")
        print(f"Topics: {row.get('topics', '')}\n")
        print(f"Created: {row.get('created_at')}  Updated: {row.get('updated_at')}\n")
        print("-" * 80)
    print(f"\nTotal abet_syllabi rows: {len(rows)}\n")


def view_isat_supplemental_pages(cursor):
    """Pages ingested from data_isat_website (local://data_isat_website/...)."""
    print("=" * 80)
    print("ISAT EXTRA DOCS (from data_isat_website)")
    print("=" * 80)
    cursor.execute(
        """
        SELECT * FROM pages
        WHERE url LIKE 'local://data_isat_website/%'
        ORDER BY url
        """
    )
    pages = cursor.fetchall()
    for page in pages:
        print(f"\nID: {page['id']}\n")
        print(f"URL: {page['url']}\n")
        print(f"Links: {page['links']}\n")
        print(f"Scraped at: {page['scraped_at']}\n")
        print(f"Text:\n{_truncate(page.get('text'))}\n")
        print("-" * 80)
    print(f"\nTotal ISAT extra doc pages: {len(pages)}\n")


def main():
    db = LinkDatabase()
    cursor = db.conn.cursor(cursor_factory=RealDictCursor)
    
    print("\n" + "=" * 80 + "")
    print("DATABASE VIEWER")
    print("=" * 80 + "")
    print("\nWhat do you want to see?")
    print("1. Pages")
    print("2. Chunks")
    print("3. Courses")
    print("4. Urls")
    print("5. ABET syllabi")
    print("6. ISAT extra docs")
    print("7. All of the above")
    print("0. Quit")
    
    choice = input("\nPick 0–7: ").strip()
    
    if choice == "1":
        view_pages(cursor)
    elif choice == "2":
        view_chunks(cursor)
    elif choice == "3":
        view_courses(cursor)
    elif choice == "4":
        view_urls(cursor)
    elif choice == "5":
        view_abet_syllabi(cursor)
    elif choice == "6":
        view_isat_supplemental_pages(cursor)
    elif choice == "7":
        view_pages(cursor)
        view_chunks(cursor)
        view_courses(cursor)
        view_urls(cursor)
        view_abet_syllabi(cursor)
        view_isat_supplemental_pages(cursor)
    elif choice == "0":
        print("Exiting...")
    else:
        print("Invalid choice. Run again and pick 0–7.")
    
    cursor.close()
    db.close()

if __name__ == "__main__":
    main()

