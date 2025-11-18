import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List
from dotenv import load_dotenv

load_dotenv()

class LinkDatabase:
    def __init__(self):
        self.conn = None
        self.connect()
        self.create_table()
    
    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME", "isat_recruiter"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD")
            )
        except psycopg2.Error as e:
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id SERIAL PRIMARY KEY,
                course_name TEXT NOT NULL,
                course_description TEXT NOT NULL,
                prerequisites TEXT
            )
        """)
        # Add prerequisites column if it doesn't exist (for existing tables)
        cursor.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='courses' AND column_name='prerequisites'
                ) THEN
                    ALTER TABLE courses ADD COLUMN prerequisites TEXT;
                END IF;
            END $$;
        """)
        self.conn.commit()
        cursor.close()
    
    def upsert_page(self, url: str, html: str = None, text: str = None, links: List[str] = None):
        """
        Insert or update a page in the pages table.
        On conflict (url) update html, text, links, scraped_at.
        
        Args:
            url (str): The URL of the page
            html (str, optional): The HTML content
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
                INSERT INTO pages (url, html, text, links, scraped_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (url) 
                DO UPDATE SET 
                    html = EXCLUDED.html,
                    text = EXCLUDED.text,
                    links = EXCLUDED.links,
                    scraped_at = NOW()
                RETURNING id
            """, (url, html, text, links_jsonb))
            page_id = cursor.fetchone()[0]
            self.conn.commit()
            return page_id
        except psycopg2.Error as e:
            print(f"Error upserting page: {e}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()
    
    def insert_course(self, course_name: str, course_description: str, prerequisites: str = None):
        """
        Insert a course into the courses table.
        
        Args:
            course_name (str): The name of the course (e.g., "ISAT 112")
            course_description (str): The full course description text
            prerequisites (str, optional): Comma-separated list of prerequisite courses
        
        Returns:
            int: The course id
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO courses (course_name, course_description, prerequisites)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (course_name, course_description, prerequisites))
            course_id = cursor.fetchone()[0]
            self.conn.commit()
            return course_id
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
    
    def close(self):
        if self.conn:
            self.conn.close()

