import os
import json
import re
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List
from dotenv import load_dotenv

# Load .env file from project root (two levels up from database/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(project_root, '.env'))


def is_trustworthy_abet_course_title(name: str | None) -> bool:
    """
    True when ABET `course_name` looks like a real title, not syllabus boilerplate
    or formatting instructions accidentally scraped into the name field.
    """
    if not name:
        return False
    s = str(name).strip()
    if len(s) < 3:
        return False
    low = s.lower()
    if "please use" in low:
        return False
    if "times new roman" in low:
        return False
    if ("following format" in low or "format for" in low) and (
        "syllabus" in low or "syllabi" in low
    ):
        return False
    if "page" in low and "maximum" in low and ("font" in low or "point" in low):
        return False
    if len(s) > 180:
        return False
    return True


class LinkDatabase:
    def __init__(self):
        self.conn = None
        self.connect()
        self.create_table()
    
    def connect(self):
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        database = os.getenv("DB_NAME", "isat_recruiter")
        user = os.getenv("DB_USER", "postgres")  # Default for shared/local setup
        password = os.getenv("DB_PASSWORD", "")    # Default for shared/local setup
        
        try:
            # Try to connect to the target database
            self.conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
        except psycopg2.Error as e:
            # If database doesn't exist, create it
            error_msg = str(e).lower()
            if "does not exist" in error_msg or "database" in error_msg:
                try:
                    # Connect to default 'postgres' database to create the target database
                    admin_conn = psycopg2.connect(
                        host=host,
                        port=port,
                        database="postgres",  # Connect to default database
                        user=user,
                        password=password
                    )
                    admin_conn.autocommit = True  # Required for CREATE DATABASE
                    cursor = admin_conn.cursor()
                    
                    # Check if database exists, create if it doesn't
                    # Use parameterized query for safety (though database name is from env var)
                    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
                    if not cursor.fetchone():
                        # CREATE DATABASE doesn't support parameters, but we validate the name
                        # Only allow alphanumeric, underscore, and hyphen for safety
                        if not all(c.isalnum() or c in ('_', '-') for c in database):
                            raise ValueError(f"Invalid database name: {database}")
                        cursor.execute(f'CREATE DATABASE "{database}"')
                        print(f"Created database '{database}'")
                    
                    cursor.close()
                    admin_conn.close()
                    
                    # Now connect to the newly created database
                    self.conn = psycopg2.connect(
                        host=host,
                        port=port,
                        database=database,
                        user=user,
                        password=password
                    )
                except psycopg2.Error as create_error:
                    print(f"Error creating database: {create_error}")
                    raise
            else:
                print(f"Error connecting to database: {e}")
                raise
    
    def create_table(self):
        cursor = self.conn.cursor()
        # Enable pgvector extension if not already enabled
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id SERIAL PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                text TEXT,
                links JSONB,
                scraped_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id SERIAL PRIMARY KEY,
                description TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id SERIAL PRIMARY KEY,
                course_name TEXT NOT NULL,
                course_code TEXT NOT NULL,
                course_description TEXT NOT NULL,
                prerequisites TEXT,
                url TEXT
            )
        """)
        # ABET syllabi metadata (hyphenated SQL names are awkward, so use abet_syllabi)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS abet_syllabi (
                id SERIAL PRIMARY KEY,
                source_pdf_path TEXT UNIQUE NOT NULL,
                course_code TEXT,
                course_name TEXT,
                professor_name TEXT,
                course_description TEXT,
                prerequisites TEXT,
                course_outcomes TEXT,
                topics TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id SERIAL PRIMARY KEY,
                page_id INTEGER REFERENCES pages(id) ON DELETE CASCADE,
                course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
                chunk_text TEXT NOT NULL,
                embedding VECTOR(1536),
                token_count INTEGER
            )
        """)
        # Add course_id column if it doesn't exist (migration)
        cursor.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='chunks' AND column_name='course_id'
                ) THEN
                    ALTER TABLE chunks ADD COLUMN course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE;
                END IF;
            END $$;
        """)
        # Migration: Handle existing tables with old schema
        cursor.execute("""
            DO $$ 
            BEGIN
                -- Add course_code if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='courses' AND column_name='course_code'
                ) THEN
                    ALTER TABLE courses ADD COLUMN course_code TEXT;
                    -- If course_id exists, copy it to course_code, then drop course_id
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='courses' AND column_name='course_id'
                    ) THEN
                        UPDATE courses SET course_code = course_id WHERE course_code IS NULL;
                        ALTER TABLE courses DROP COLUMN IF EXISTS course_id;
                    END IF;
                END IF;
                
                -- Add prerequisites if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='courses' AND column_name='prerequisites'
                ) THEN
                    ALTER TABLE courses ADD COLUMN prerequisites TEXT;
                END IF;
                
                -- Add url if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='courses' AND column_name='url'
                ) THEN
                    ALTER TABLE courses ADD COLUMN url TEXT;
                END IF;
            END $$;
        """)
        self.conn.commit()
        cursor.close()
    
    def upsert_page(self, url: str, html: str = None, text: str = None, links: List[str] = None):
        """
        Insert or update a page in the pages table.
        On conflict (url) update text, links, scraped_at.
        
        Args:
            url (str): The URL of the page
            html (str, optional): The HTML content (not stored, kept for API compatibility)
            text (str, optional): The text content
            links (List[str], optional): List of links found on the page
        
        Returns:
            int: The page id
        """
        cursor = self.conn.cursor()
        try:
            # Convert links list to JSONB if provided
            links_jsonb = json.dumps(links) if links else None
            
            cursor.execute("""
                INSERT INTO pages (url, text, links, scraped_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (url) 
                DO UPDATE SET 
                    text = EXCLUDED.text,
                    links = EXCLUDED.links,
                    scraped_at = NOW()
                RETURNING id
            """, (url, text, links_jsonb))
            page_id = cursor.fetchone()[0]
            self.conn.commit()
            return page_id
        except psycopg2.Error as e:
            print(f"Error upserting page: {e}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def upsert_url(self, description: str, url: str):
        """
        Insert or update a URL row in the urls table.

        Args:
            description (str): Human-readable label for the URL
            url (str): URL string

        Returns:
            int: URL row id
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO urls (description, url, created_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (url)
                DO UPDATE SET description = EXCLUDED.description
                RETURNING id
                """,
                (description, url),
            )
            row_id = cursor.fetchone()[0]
            self.conn.commit()
            return row_id
        except psycopg2.Error as e:
            print(f"Error upserting url: {e}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()
    
    def insert_course(self, course_name: str, course_code: str, course_description: str, prerequisites: str = None, url: str = None):
        """
        Insert a course into the courses table.
        
        Args:
            course_name (str): The descriptive name of the course (e.g., "Sustainability and Environment")
            course_code (str): The course code (e.g., "ISAT 400", "ISAT 330")
            course_description (str): The full course description text
            prerequisites (str, optional): Comma-separated list of prerequisite courses (e.g., "ISAT 100, ISAT 212")
            url (str, optional): The direct URL to the course description page
        
        Returns:
            int: The course id
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO courses (course_name, course_code, course_description, prerequisites, url)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (course_name, course_code, course_description, prerequisites, url))
            course_id_db = cursor.fetchone()[0]
            self.conn.commit()
            return course_id_db
        except psycopg2.Error as e:
            print(f"Error inserting course: {e}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()
    
    def insert_chunk(self, page_id: int = None, course_id: int = None, chunk_text: str = None, embedding: List[float] = None, token_count: int = None):
        """
        Insert a chunk into the chunks table.
        
        Args:
            page_id (int, optional): The id of the page this chunk belongs to
            course_id (int, optional): The id of the course this chunk belongs to
            chunk_text (str): The text content of the chunk
            embedding (List[float], optional): The embedding vector (1536 dimensions)
            token_count (int, optional): The number of tokens in the chunk
        """
        if not page_id and not course_id:
            raise ValueError("Either page_id or course_id must be provided")
        
        cursor = self.conn.cursor()
        try:
            # Convert embedding list to string format for pgvector if provided
            embedding_str = None
            if embedding:
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
            
            cursor.execute("""
                INSERT INTO chunks (page_id, course_id, chunk_text, embedding, token_count)
                VALUES (%s, %s, %s, %s::vector, %s)
            """, (page_id, course_id, chunk_text, embedding_str, token_count))
            self.conn.commit()
        except psycopg2.Error as e:
            print(f"Error inserting chunk: {e}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()
    
    def find_chunks_for_course_code(self, course_code: str, limit: int = 8) -> List[dict]:
        """
        Chunks for a course row (e.g. ISAT 449). Vector search alone often misses a specific course.
        """
        normalized = "".join(course_code.upper().split())
        if not normalized:
            return []
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(
                """
                SELECT
                    c.id AS chunk_id,
                    c.chunk_text,
                    c.page_id,
                    c.course_id,
                    c.token_count,
                    co.course_name,
                    co.course_code,
                    co.course_description,
                    co.prerequisites,
                    co.url AS course_url,
                    0.99 AS similarity
                FROM chunks c
                INNER JOIN courses co ON c.course_id = co.id
                WHERE REPLACE(UPPER(TRIM(co.course_code)), ' ', '') = %s
                ORDER BY c.id
                LIMIT %s
                """,
                (normalized, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        except psycopg2.Error as e:
            print(f"Error finding chunks by course code: {e}", file=sys.stderr)
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def find_chunks_mentioning_course_code(self, course_code: str, limit: int = 8) -> List[dict]:
        """
        Chunks whose text references a course (e.g. prerequisites) when there is no
        course_id row or no chunks linked to that course.
        """
        mm = re.search(r"(?:ISAT\s*)?(\d{3}[A-Z]?)", (course_code or "").upper())
        if not mm:
            return []
        token = mm.group(1).upper()
        like_space = f"%ISAT {token}%"
        like_compact = f"%ISAT{token}%"
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(
                """
                SELECT
                    c.id AS chunk_id,
                    c.chunk_text,
                    c.page_id,
                    c.course_id,
                    c.token_count,
                    co.course_name,
                    co.course_code,
                    co.course_description,
                    co.prerequisites,
                    co.url AS course_url,
                    0.95 AS similarity
                FROM chunks c
                LEFT JOIN courses co ON c.course_id = co.id
                WHERE (c.chunk_text ILIKE %s OR c.chunk_text ILIKE %s)
                ORDER BY c.id
                LIMIT %s
                """,
                (like_space, like_compact, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        except psycopg2.Error as e:
            print(f"Error finding chunks mentioning course code: {e}", file=sys.stderr)
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def find_similar_chunks(self, query_embedding: List[float], top_k: int = 8) -> List[dict]:
        """
        Find the most similar chunks to a query embedding using cosine similarity.
        Includes course information when chunks are from courses.
        
        Args:
            query_embedding (List[float]): The embedding vector of the query (1536 dimensions)
            top_k (int): Number of top similar chunks to return (default: 8)
        
        Returns:
            List[dict]: List of dictionaries containing chunk_id, chunk_text, page_id, course_id, 
                       course_name, course_description, and similarity score
        """
        if not query_embedding:
            return []
        
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Convert embedding list to string format for pgvector
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Query chunks with LEFT JOIN to get course info
            # Get balanced mix: top_k/2 from courses, top_k/2 from pages
            cursor.execute("""
                WITH course_chunks AS (
                    SELECT 
                        c.id as chunk_id,
                        c.chunk_text,
                        c.page_id,
                        c.course_id,
                        c.token_count,
                        co.course_name,
                        co.course_code,
                        co.course_description,
                        co.prerequisites,
                        co.url as course_url,
                        1 - (c.embedding <=> %s::vector) as similarity
                    FROM chunks c
                    LEFT JOIN courses co ON c.course_id = co.id
                    WHERE c.embedding IS NOT NULL 
                    AND c.course_id IS NOT NULL
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                ),
                page_chunks AS (
                    SELECT 
                        c.id as chunk_id,
                        c.chunk_text,
                        c.page_id,
                        c.course_id,
                        c.token_count,
                        co.course_name,
                        co.course_code,
                        co.course_description,
                        co.prerequisites,
                        co.url as course_url,
                        1 - (c.embedding <=> %s::vector) as similarity
                    FROM chunks c
                    LEFT JOIN courses co ON c.course_id = co.id
                    WHERE c.embedding IS NOT NULL 
                    AND c.page_id IS NOT NULL
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                ),
                combined AS (
                    SELECT * FROM course_chunks
                    UNION ALL
                    SELECT * FROM page_chunks
                )
                SELECT * FROM combined
                ORDER BY similarity DESC
                LIMIT %s
            """, (embedding_str, embedding_str, top_k // 2, embedding_str, embedding_str, top_k // 2, top_k))
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except psycopg2.Error as e:
            print(f"Error finding similar chunks: {e}", file=sys.stderr)
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def fetch_all_courses(self) -> List[dict]:
        """
        Fetch all courses from the courses table.
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(
                """
                SELECT
                    id,
                    course_name,
                    course_code,
                    course_description,
                    prerequisites,
                    url
                FROM courses
                ORDER BY course_code
                """
            )
            return [dict(row) for row in cursor.fetchall()]
        except psycopg2.Error as e:
            print(f"Error fetching all courses: {e}", file=sys.stderr)
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def fetch_all_abet_syllabi(self) -> List[dict]:
        """
        Fetch ABET syllabi rows with usable course codes.
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(
                """
                SELECT
                    id,
                    source_pdf_path,
                    course_code,
                    course_name,
                    professor_name,
                    course_description,
                    prerequisites,
                    course_outcomes,
                    topics,
                    updated_at
                FROM abet_syllabi
                WHERE course_code IS NOT NULL
                ORDER BY updated_at DESC, id DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]
        except psycopg2.Error as e:
            print(f"Error fetching ABET syllabi: {e}", file=sys.stderr)
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def fetch_course_catalog_abet_first(self) -> List[dict]:
        """
        Return course catalog rows keyed by course_code with ABET precedence.
        If a course exists in abet_syllabi, ABET fields override courses table fields.
        """
        courses = self.fetch_all_courses()
        abet_rows = self.fetch_all_abet_syllabi()

        def _norm(code: str | None) -> str:
            raw = (code or "").upper().strip()
            if not raw:
                return ""
            compact = "".join(ch for ch in raw if ch.isalnum())
            if compact.startswith("ISAT") and len(compact) >= 7:
                return f"ISAT {compact[4:]}"
            if compact[:3].isdigit():
                return f"ISAT {compact}"
            return raw

        merged: dict[str, dict] = {}

        for row in courses:
            code = _norm(row.get("course_code"))
            if not code:
                continue
            merged[code] = {
                "course_code": code,
                "course_name": row.get("course_name"),
                "course_description": row.get("course_description"),
                "prerequisites": row.get("prerequisites"),
                "source": "courses",
            }

        # ABET is source of truth when fields are trustworthy; fall back to catalog for bad extractions.
        for row in abet_rows:
            code = _norm(row.get("course_code"))
            if not code:
                continue
            base = merged.get(
                code,
                {
                    "course_code": code,
                    "course_name": None,
                    "course_description": None,
                    "prerequisites": None,
                    "source": "courses",
                },
            )
            abet_name = row.get("course_name")
            base_name = base.get("course_name")
            if abet_name and is_trustworthy_abet_course_title(str(abet_name).strip()):
                merged_name = str(abet_name).strip()
            elif base_name:
                merged_name = base_name
            else:
                merged_name = str(abet_name).strip() if abet_name else None
            merged[code] = {
                "course_code": code,
                "course_name": merged_name,
                "course_description": row.get("course_description") or base.get("course_description"),
                "prerequisites": row.get("prerequisites") or base.get("prerequisites"),
                "source": "abet_syllabi",
            }

        return [merged[k] for k in sorted(merged.keys())]
    
    def close(self):
        if self.conn:
            self.conn.close()

__main__ = __name__ == "__main__"
if __main__:
    db = LinkDatabase()
    db.close()
