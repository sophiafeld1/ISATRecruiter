"""
Minimal chunking logic using LangChain semantic text splitter.
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from database.db_write import LinkDatabase
from psycopg2.extras import RealDictCursor
import signal
from contextlib import contextmanager


@contextmanager
def timeout(seconds):
    """Context manager for timeout handling."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def chunk_pages():
    """
    Chunk all pages from the pages table using LangChain semantic text splitter.
    Stores chunks in the chunks table.
    """
    db = LinkDatabase()
    cursor = db.conn.cursor(cursor_factory=RealDictCursor)
    
    # Get all pages
    cursor.execute("SELECT id, url, text FROM pages WHERE text IS NOT NULL ORDER BY id")
    pages = cursor.fetchall()
    
    print(f"Found {len(pages)} pages to chunk\n")
    
    if len(pages) == 0:
        print("No pages found. Run crawler first.")
        cursor.close()
        db.close()
        return
    
    # Initialize semantic chunker (requires OPENAI_API_KEY in .env)
    # Using text-embedding-3-small model for semantic chunking
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    chunker = SemanticChunker(embeddings)
    
    total_chunks = 0
    
    for page in pages:
        page_id = page['id']
        url = page['url']
        text = page['text']
        
        if not text or len(text.strip()) == 0:
            continue
        
        print(f"Chunking page {page_id}: {url[:60]}...")
        
        # Check if chunks already exist - skip if they do
        cursor.execute("SELECT COUNT(*) as count FROM chunks WHERE page_id = %s", (page_id,))
        existing_count = cursor.fetchone()['count']
        if existing_count > 0:
            print(f"  ⏭ Skipped - already has {existing_count} chunks\n")
            continue
        
        try:
            # Skip very large pages (they might timeout)
            if len(text) > 50000:
                print(f"  ⚠ Skipping page {page_id} - too large ({len(text)} chars)\n")
                continue
            
            # Split text into semantic chunks with timeout
            try:
                with timeout(120):  # 2 minute timeout
                    chunks = chunker.create_documents([text])
            except TimeoutError:
                print(f"  ⚠ Timeout chunking page {page_id}, skipping...\n")
                continue
            
            print(f"  → Created {len(chunks)} chunks")
            
            # Store each chunk
            for chunk in chunks:
                chunk_text = chunk.page_content
                token_count = len(chunk_text) // 4  # Rough estimate
                
                db.insert_chunk(
                    page_id=page_id,
                    chunk_text=chunk_text,
                    embedding=None,
                    token_count=token_count
                )
                total_chunks += 1
            
            print(f"  ✓ Stored {len(chunks)} chunks\n")
            
        except Exception as e:
            print(f"  ✗ Error chunking page {page_id}: {e}\n")
            continue
    
    cursor.close()
    db.close()
    
    print(f"Complete! Created {total_chunks} total chunks from {len(pages)} pages.")


def chunk_courses():
    """
    Chunk all courses from the courses table using LangChain semantic text splitter.
    Stores chunks in the chunks table.
    """
    db = LinkDatabase()
    cursor = db.conn.cursor(cursor_factory=RealDictCursor)
    
    # Get only ISAT courses (100-400 level only, no 500+)
    # Check both course_code and course_name since some courses have NULL course_code
    cursor.execute("""
        SELECT id, course_name, course_code, course_description, prerequisites 
        FROM courses 
        WHERE course_description IS NOT NULL 
        AND (
            (course_code LIKE 'ISAT%' AND course_code ~ '^ISAT [1-4]')
            OR (course_code IS NULL AND course_name LIKE 'ISAT%' AND course_name ~ '^ISAT [1-4]')
        )
        ORDER BY COALESCE(course_code, course_name)
    """)
    courses = cursor.fetchall()
    
    print(f"Found {len(courses)} ISAT courses (100-400 level) to chunk\n")
    
    if len(courses) == 0:
        print("No courses found. Run crawler first.")
        cursor.close()
        db.close()
        return
    
    # Initialize semantic chunker (requires OPENAI_API_KEY in .env)
    # Using text-embedding-3-small model for semantic chunking
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    chunker = SemanticChunker(embeddings)
    
    total_chunks = 0
    
    for course in courses:
        course_id = course['id']
        course_name = course['course_name']
        description = course['course_description']
        prerequisites = course.get('prerequisites', '')
        
        # Combine course name, description, and prerequisites for chunking
        text_parts = [course_name]
        if prerequisites:
            text_parts.append(f"Prerequisites: {prerequisites}")
        text_parts.append(description)
        text = "\n\n".join(text_parts)
        
        if not text or len(text.strip()) == 0:
            continue
        
        print(f"Chunking course {course_id}: {course_name[:50]}...")
        
        # Check if chunks already exist - skip if they do
        cursor.execute("SELECT COUNT(*) as count FROM chunks WHERE course_id = %s", (course_id,))
        existing_count = cursor.fetchone()['count']
        if existing_count > 0:
            print(f"  ⏭ Skipped - already has {existing_count} chunks\n")
            continue
        
        try:
            # Skip very large course descriptions (they might timeout)
            if len(text) > 10000:
                print(f"  ⚠ Skipping course {course_id} - too large ({len(text)} chars)\n")
                continue
            
            # Split text into semantic chunks with timeout
            try:
                with timeout(120):  # 2 minute timeout
                    chunks = chunker.create_documents([text])
            except TimeoutError:
                print(f"  ⚠ Timeout chunking course {course_id}, skipping...\n")
                continue
            
            print(f"  → Created {len(chunks)} chunks")
            
            # Store each chunk
            for chunk in chunks:
                chunk_text = chunk.page_content
                token_count = len(chunk_text) // 4  # Rough estimate
                
                db.insert_chunk(
                    course_id=course_id,
                    chunk_text=chunk_text,
                    embedding=None,
                    token_count=token_count
                )
                total_chunks += 1
            
            print(f"  ✓ Stored {len(chunks)} chunks\n")
            
        except Exception as e:
            print(f"  ✗ Error chunking course {course_id}: {e}\n")
            continue
    
    cursor.close()
    db.close()
    
    print(f"Complete! Created {total_chunks} total chunks from {len(courses)} courses.")


if __name__ == "__main__":
    import sys
    
    # Check for command-line argument first
    if len(sys.argv) > 1:
        if sys.argv[1] == "courses":
            chunk_courses()
        elif sys.argv[1] == "pages":
            chunk_pages()
        elif sys.argv[1] in ["-h", "--help", "help"]:
            print("Usage:")
            print("  python chunking/chunk_base.py          # Interactive menu")
            print("  python chunking/chunk_base.py pages    # Chunk pages")
            print("  python chunking/chunk_base.py courses  # Chunk courses")
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Use 'pages' or 'courses' as argument, or run without arguments for interactive menu.")
    else:
        # Interactive menu
        print("\n" + "=" * 60)
        print("CHUNKING TOOL")
        print("=" * 60)
        print("\nWhat would you like to chunk?")
        print("1. pages")
        print("2. courses")
        print("3. both")
        print("0. exit")
        
        choice = input("\nEnter your choice (0-3): ").strip()
        
        if choice == "1":
            chunk_pages()
        elif choice == "2":
            chunk_courses()
        elif choice == "3":
            print("\nChunking pages...")
            chunk_pages()
            print("\nChunking courses...")
            chunk_courses()
        elif choice == "0":
            print("Exiting...")
        else:
            print("Invalid choice. Please run again and select 0-3.")

