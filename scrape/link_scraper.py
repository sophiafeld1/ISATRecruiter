from scrape_base import scraper_ISAT
from db_write import LinkDatabase

if __name__ == "__main__":
    urls = [
        "https://catalog.jmu.edu/preview_program.php?catoid=62&poid=27120#1",
    ]
    
    db = LinkDatabase()
    
    for url in urls:
        print(f"Scraping links from: {url}")
        scraper = scraper_ISAT(url)
        links = scraper.get_links()
        db.write_links(url, links)
        print(f"\nTotal links found: {len(links)}\n")
    
    db.close()

