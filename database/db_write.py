import os
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraped_links (
                id SERIAL PRIMARY KEY,
                origin_url TEXT NOT NULL,
                link TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(origin_url, link)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraped_text (
                id SERIAL PRIMARY KEY,
                origin_url TEXT NOT NULL,
                text_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(origin_url)
            )
        """)
        self.conn.commit()
        cursor.close()
    
    def write_links(self, origin_url: str, links: List[str]):
        print(f"\nAppending to database (origin: {origin_url}):")
        for link in links:
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO scraped_links (origin_url, link)
                    VALUES (%s, %s)
                    ON CONFLICT (origin_url, link) DO NOTHING
                """, (origin_url, link))
                self.conn.commit()
                print(f"  - {link}")
            except psycopg2.Error as e:
                print(f"Error inserting link: {e}")
                self.conn.rollback()
            finally:
                cursor.close()
    
    def write_text(self, origin_url: str, text: str):
        print(f"\nAppending text to database (origin: {origin_url}):")
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO scraped_text (origin_url, text_content)
                VALUES (%s, %s)
                ON CONFLICT (origin_url) DO UPDATE SET text_content = EXCLUDED.text_content
            """, (origin_url, text))
            self.conn.commit()
            print(f"  - Text stored ({len(text)} characters)")
        except psycopg2.Error as e:
            print(f"Error inserting text: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def get_all_links(self) -> List[dict]:
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, origin_url, link, created_at FROM scraped_links")
        results = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in results]
    
    def get_all_text(self) -> List[dict]:
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, origin_url, text_content, created_at FROM scraped_text")
        results = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in results]
    
    def close(self):
        if self.conn:
            self.conn.close()

