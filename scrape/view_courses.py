"""
Display courses in the requested format:
- Origin link (course catalogue page) displayed ONCE
- Then "=====courses========="
- For each course: course title, description, prerequisites
"""
import sys
import os

# Add project root to path so imports work
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.db_write import LinkDatabase
from psycopg2.extras import RealDictCursor

def view_courses():
    db = LinkDatabase()
    cursor = db.conn.cursor(cursor_factory=RealDictCursor)
    
    # Get the program page URL (assuming it's the most recent page with courses)
    cursor.execute("""
        SELECT p.url 
        FROM pages p
        WHERE p.url LIKE '%preview_program%'
        ORDER BY p.scraped_at DESC
        LIMIT 1
    """)
    program_page = cursor.fetchone()
    
    if program_page:
        origin_url = program_page['url']
        print(f"{origin_url}\n")
        print("=" * 80)
        print("COURSES")
        print("=" * 80)
        print()
    else:
        print("No program page found in database\n")
        print("=" * 80)
        print("COURSES")
        print("=" * 80)
        print()
    
    # Get all courses
    cursor.execute("""
        SELECT course_name, course_description, prerequisites
        FROM courses
        ORDER BY course_name
    """)
    courses = cursor.fetchall()
    
    if not courses:
        print("No courses found in database.")
    else:
        for i, course in enumerate(courses, 1):
            # Print full course name (no truncation)
            print(f"{course['course_name']}")
            
            # Print prerequisites if they exist (full text, no truncation)
            if course['prerequisites']:
                print(f"Prerequisites: {course['prerequisites']}")
            
            # Print full course description (no truncation)
            print(f"\n{course['course_description']}")
            print("\n" + "-" * 80 + "\n")
    
    cursor.close()
    db.close()
    
    print(f"\nTotal courses: {len(courses)}")

if __name__ == "__main__":
    view_courses()

