from bs4 import BeautifulSoup
import requests
import re
from urllib.parse import urljoin, urlparse


class scraper_ISAT:
    def __init__(self, URL):
        self.URL = URL
        # Remove fragment identifier (#) from URL before requesting
        clean_url = URL.split('#')[0] if '#' in URL else URL
        
        # Add headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            page = requests.get(clean_url, headers=headers, timeout=10)
            page.raise_for_status()  # Raise exception for bad status codes
            self.soup = BeautifulSoup(page.text, "html.parser")
            self.status_code = page.status_code
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch {clean_url}: {e}")

    def get_text(self):
        ''' get the text of the page '''
        return self.soup.get_text()

    def clean_text(self):
        ''' clean the text of the page '''
        return self.soup.get_text(separator=" ", strip=True)

    def get_links(self):
        ''' get all links from the page (absolute and relative URLs) '''
        all_links = []
        for a_tag in self.soup.find_all("a", href=True):
            href = a_tag.get("href")
            if href:
                all_links.append(href.strip())
        
        valid_links = []
        for link in all_links:
            if not link:
                continue
            if link.startswith('javascript:') or link.startswith('mailto:') or link.startswith('tel:'):
                continue
            if not link.startswith('#') and '#' in link:
                link = link.split('#')[0]
            if link:
                valid_links.append(link)
        
        return valid_links
    
    def get_courses_from_program_page(self):
        '''
        Extract courses from a program page.
        Returns list of dicts with: course_name, course_description, prerequisites
        '''
        courses = []
        
        # Find all course title links (they have onclick="showCourse(...)")
        all_links = self.soup.find_all('a', href=True)
        
        for link in all_links:
            course_title = link.get_text().strip()
            # Only process if it matches course pattern (e.g., "ISAT 330." or "BIO 140.")
            if not re.match(r'[A-Z]{2,4}\s+\d{3}[A-Z]?\.', course_title):
                continue
            
            # Extract course ID from onclick handler
            # onclick="showCourse('62', '369747', ...)"
            onclick = link.get('onclick', '')
            course_id = None
            catoid = None
            
            if 'showCourse' in onclick:
                # Extract catoid and coid from onclick
                match = re.search(r"showCourse\('(\d+)',\s*'(\d+)'", onclick)
                if match:
                    catoid = match.group(1)
                    course_id = match.group(2)
            
            # If we found course ID, build description URL
            description = None
            if course_id and catoid:
                desc_url = f"preview_course_nopop.php?catoid={catoid}&coid={course_id}"
                full_desc_url = urljoin(self.URL, desc_url)
                try:
                    desc_scraper = scraper_ISAT(full_desc_url)
                    description = desc_scraper.clean_text()
                except Exception as e:
                    # If we can't get description, continue anyway
                    pass
            
            # Find the parent li to extract prerequisites
            li = link.find_parent('li', class_='acalog-course')
            prerequisites = []
            if li:
                # Extract prerequisites - links with #tt IDs that are NOT the course itself
                prereq_links = li.find_all('a', href=lambda x: x and x.startswith('#tt'))
                for prereq_link in prereq_links:
                    prereq_name = prereq_link.get_text().strip()
                    # Skip if it's the course title itself or empty
                    if prereq_name and prereq_name not in course_title and prereq_name not in prerequisites:
                        # Only add if it looks like a course code
                        if re.match(r'[A-Z]{2,4}\s+\d{3}', prereq_name):
                            prerequisites.append(prereq_name)
            
            # Add course even if description is None (we'll try to get it later)
            courses.append({
                'course_name': course_title,
                'course_description': description or '',  # Empty string if not found
                'prerequisites': ', '.join(prerequisites) if prerequisites else None
            })
        
        return courses
