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
        text = self.soup.get_text()
        return text

    def clean_text(self):
        ''' clean the text of the page '''
        cleaned_text = self.soup.get_text(separator=" ", strip=True) 
        return cleaned_text


    def get_links(self):
        ''' get the links of the page and write to a file '''
        links = [a.get("href") for a in self.soup.find_all("a")]
        with open("links_from_course_catalog.txt", "w", encoding="utf-8") as f:
            for link in links:
                if link:
                    f.write(f"{link}\n")
        return links


if __name__ == "__main__":
    scraper = scraper_ISAT(URL)
    print(scraper.get_text())
    print(scraper.clean_text())
    print(scraper.get_links())