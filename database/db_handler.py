import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LinkDatabase:
    def __init__(self):
        """
        Initialize the database connection using environment variables.
        Expected env vars: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        """
        self.conn = None
        self.connect()
        self.create_table()
    
    def connect(self):
        """Establish connection to PostgreSQL database."""
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
    
    def create_link_table(self):
        """Create the scraped_links table if it doesn't exist."""
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
        self.conn.commit()
        cursor.close()
    
    def insert_link(self, origin_url: str, link: str):
        """
        Insert a link with its origin URL into the database.
        Ignores duplicates (same origin_url and link combination).
        
        Args:
            origin_url (str): The URL where the link was scraped from
            link (str): The link that was found
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO scraped_links (origin_url, link)
                VALUES (%s, %s)
                ON CONFLICT (origin_url, link) DO NOTHING
            """, (origin_url, link))
            self.conn.commit()
        except psycopg2.Error as e:
            print(f"Error inserting link: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def insert_links(self, origin_url: str, links: List[str]):
        """
        Insert multiple links from the same origin URL.
        Prints each link as it's inserted.
        
        Args:
            origin_url (str): The URL where the links were scraped from
            links (List[str]): List of links found on the page
        """
        print(f"\nAppending to database (origin: {origin_url}):")
        for link in links:
            self.insert_link(origin_url, link)
            print(f"  - {link}")
    
    def get_all_links(self) -> List[dict]:
        """
        Get all links from the database.
        
        Returns:
            List[dict]: List of dictionaries with link data
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, origin_url, link, created_at FROM scraped_links")
        results = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in results]
    
    def get_links_by_origin(self, origin_url: str) -> List[str]:
        """
        Get all links scraped from a specific origin URL.
        
        Args:
            origin_url (str): The origin URL to filter by
        
        Returns:
            List[str]: List of links found on that page
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT link FROM scraped_links WHERE origin_url = %s", (origin_url,))
        results = cursor.fetchall()
        cursor.close()
        return [row[0] for row in results]
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    