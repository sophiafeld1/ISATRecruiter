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
import json

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
        print(f"Course name: {course['course_name']}\n\n")
        print(f"Course description: {course['course_description']}\n\n")
        print(f"Prerequisites: {course['prerequisites']}\n\n")
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

def main():
    db = LinkDatabase()
    cursor = db.conn.cursor(cursor_factory=RealDictCursor)
    
    print("\n" + "=" * 80 + "")
    print("DATABASE VIEWER")
    print("=" * 80 + "")
    print("\nWhich table would you like to view?")
    print("1. pages")
    print("2. chunks")
    print("3. courses")
    print("4. all")
    print("0. exit")
    
    choice = input("\nEnter your choice (0-4): ").strip()
    
    if choice == "1":
        view_pages(cursor)
    elif choice == "2":
        view_chunks(cursor)
    elif choice == "3":
        view_courses(cursor)
    elif choice == "4":
        view_pages(cursor)
        view_chunks(cursor)
        view_courses(cursor)
    elif choice == "0":
        print("Exiting...")
    else:
        print("Invalid choice. Please run again and select 0-4.")
    
    cursor.close()
    db.close()

if __name__ == "__main__":
    main()

