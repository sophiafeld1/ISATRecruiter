from bs4 import BeautifulSoup
import requests

URL = "https://catalog.jmu.edu/preview_program.php?catoid=62&poid=27120#1"

class scraper_ISAT:
    def __init__(self, URL):
        self.URL = URL
        page = requests.get(URL)
        self.soup = BeautifulSoup(page.text, "html.parser")

    def get_text(self):
        ''' get the text of the page '''
        return self.soup.get_text()

    def clean_text(self):
        ''' clean the text of the page '''
        return self.soup.get_text(separator=" ", strip=True)

    def get_links(self):
        ''' get the links of the page (only absolute URLs starting with www. or http) '''
        all_links = [a.get("href") for a in self.soup.find_all("a")]
        return [link for link in all_links if link and (link.startswith("www.") or link.startswith("http"))]



