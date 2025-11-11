from scrape_base import scraper_ISAT
from database.db_write import LinkDatabase

if __name__ == "__main__":
    urls = [
        "https://catalog.jmu.edu/preview_program.php?catoid=62&poid=27120#1",
    ]
    
    db = LinkDatabase()
    
    for url in urls:
        print(f"Scraping text from: {url}")
        scraper = scraper_ISAT(url)
        cleaned = scraper.clean_text()
        db.write_text(url, cleaned)
        print(f"\nTotal text length: {len(cleaned)} characters\n")
    
    db.close()

