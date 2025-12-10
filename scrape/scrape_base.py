from bs4 import BeautifulSoup
import requests
import re
from urllib.parse import urljoin


class scraper_ISAT:
    def __init__(self, URL):
        self.URL = URL
        clean_url = URL.split('#')[0] if '#' in URL else URL
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            page = requests.get(clean_url, headers=headers, timeout=10)
            if page.status_code == 404:
                raise Exception(f"404 Not Found: {clean_url}")
            page.raise_for_status()
            self.soup = BeautifulSoup(page.text, "html.parser")
            
            # Check for error pages
            text_content = self.soup.get_text(separator=" ", strip=True)
            if "Resource Not Found" in text_content:
                raise Exception(f"Error page detected: {clean_url}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch {clean_url}: {e}")

    def _remove_bottom_bar(self):
        '''Remove bottom bar and JavaScript error messages.'''
        try:
            # Remove elements containing JavaScript error
            js_error = "Javascript is currently not supported"
            for text_node in self.soup.find_all(text=lambda t: t and js_error in str(t)):
                parent = text_node.find_parent()
                if parent:
                    parent.decompose()
            
            # Remove table rows starting from tr[4]
            body = self.soup.find('body')
            if body:
                table = body.find('table')
                if table:
                    tbody = table.find('tbody')
                    if tbody:
                        tr_elements = tbody.find_all('tr', recursive=False)
                        if len(tr_elements) >= 4:
                            for tr in tr_elements[3:]:
                                tr.decompose()
            
            # Remove footer elements
            for selector in ['footer', '#footer', '.footer']:
                for elem in self.soup.select(selector):
                    elem.decompose()
        except Exception:
            pass

    def _remove_js_error_from_text(self, text):
        '''Remove JavaScript error messages from text.'''
        patterns = [
            "Javascript is currently not supported",
            "or is disabled by this browser",
            "Please enable Javascript for full functionality"
        ]
        for pattern in patterns:
            if pattern in text:
                pos = text.find(pattern)
                text = text[:pos].strip()
                break
        return text

    def clean_text(self):
        '''Clean text by removing bottom bar and JS errors.'''
        self._remove_bottom_bar()
        text = self.soup.get_text(separator=" ", strip=True)
        return self._remove_js_error_from_text(text)

    def get_links(self):
        '''Get all valid links from the page.'''
        links = []
        for a_tag in self.soup.find_all("a", href=True):
            href = a_tag.get("href", "").strip()
            if href and not href.startswith(('javascript:', 'mailto:', 'tel:')):
                if '#' in href and not href.startswith('#'):
                    href = href.split('#')[0]
                if href:
                    links.append(href)
        return links

    def _extract_course_description(self):
        '''Extract course description from course description page.'''
        # Remove unwanted elements first
        for tag in self.soup(['script', 'style', 'nav', 'header', 'footer', 'noscript']):
            tag.decompose()
        
        self._remove_bottom_bar()
        
        # The course description is usually in a specific table row
        # Look for table rows containing course code and "Credits"
        tables = self.soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                text = row.get_text(separator=" ", strip=True)
                # Check if this row contains course code and "Credits" (indicating course description)
                if re.search(r'[A-Z]{2,4}\s+\d{3}[A-Z]?\.', text) and 'Credits' in text:
                    # Extract just the course description part
                    # Pattern: course code ... Credits ... description text
                    match = re.search(r'([A-Z]{2,4}\s+\d{3}[A-Z]?\.\s+[^.]+\.)\s+(Credits.*?)(?=Print-Friendly|Skip to Content|Info For|$)', text, re.DOTALL)
                    if match:
                        # Get everything from course code to end (before navigation)
                        desc_text = match.group(0)
                    else:
                        # Try simpler: from course code to end of row
                        course_match = re.search(r'([A-Z]{2,4}\s+\d{3}[A-Z]?\.\s+.*)', text)
                        if course_match:
                            desc_text = course_match.group(1)
                            # Remove navigation patterns
                            desc_text = re.sub(r'(Print-Friendly Page|Skip to Content|Info For).*', '', desc_text, flags=re.DOTALL)
                        else:
                            desc_text = text
                    
                    desc_text = self._remove_js_error_from_text(desc_text)
                    # Remove "Back to Top" and similar navigation
                    desc_text = re.sub(r'Back to Top.*', '', desc_text, flags=re.IGNORECASE)
                    desc_text = re.sub(r'\s+', ' ', desc_text).strip()
                    if len(desc_text) > 100:
                        return desc_text
        
        # Fallback: try to extract from all text
        all_text = self.soup.get_text(separator=" ", strip=True)
        # Look for pattern: course code ... Credits ... description ... (end before navigation)
        match = re.search(r'([A-Z]{2,4}\s+\d{3}[A-Z]?\.\s+.*?Credits.*?)(?=Print-Friendly|Skip to Content|Info For|James Madison)', all_text, re.DOTALL)
        if match:
            text = match.group(1)
            text = self._remove_js_error_from_text(text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text if len(text) > 50 else ''
        
        return ''

    def _extract_course_name(self):
        '''Extract descriptive course name from course description page.'''
        # Try h1 first
        h1 = self.soup.find('h1')
        if h1:
            text = h1.get_text().strip()
            match = re.match(r'[A-Z]{2,4}\s+\d{3}[A-Z]?\.\s+(.+)', text)
            if match:
                return match.group(1).strip()
            return text
        
        # Try h2
        h2 = self.soup.find('h2')
        if h2:
            text = h2.get_text().strip()
            match = re.match(r'[A-Z]{2,4}\s+\d{3}[A-Z]?\.\s+(.+)', text)
            if match:
                return match.group(1).strip()
            return text
        
        return None

    def _extract_prerequisites(self):
        '''Extract prerequisites from course description page.'''
        all_text = self.soup.get_text(separator=" ", strip=True)
        
        # Look for prerequisite patterns
        patterns = [
            r'Prerequisite\(s\):\s*(.+?)(?=Corequisite|Prerequisite|Credits|PeopleSoft|Grading|Back to Top|Print-Friendly|$)',
            r'Prerequisites?:\s*(.+?)(?=Corequisite|Prerequisite|Credits|PeopleSoft|Grading|Back to Top|Print-Friendly|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, all_text, re.IGNORECASE | re.DOTALL)
            if match:
                prereq_text = match.group(1).strip()
                # Clean up - remove extra whitespace
                prereq_text = re.sub(r'\s+', ' ', prereq_text)
                # Remove trailing punctuation/whitespace
                prereq_text = prereq_text.rstrip('. ')
                if len(prereq_text) > 5:  # Only return if substantial
                    return prereq_text
        
        return None

    def get_courses_from_program_page(self):
        '''
        Extract courses from program page.
        Returns: list of dicts with course_name, course_code, course_description, prerequisites, url
        '''
        courses_metadata = []
        
        # Step 1: Extract metadata from program page
        for link in self.soup.find_all('a', href=True):
            course_code_text = link.get_text().strip()
            if not re.match(r'[A-Z]{2,4}\s+\d{3}[A-Z]?\.', course_code_text):
                continue
            
            course_code = course_code_text.rstrip('.')
            
            # Extract course ID from onclick
            onclick = link.get('onclick', '')
            course_id = None
            catoid = None
            if 'showCourse' in onclick:
                match = re.search(r"showCourse\('(\d+)',\s*'(\d+)'", onclick)
                if match:
                    catoid = match.group(1)
                    course_id = match.group(2)
            
            # Extract prerequisites
            li = link.find_parent('li', class_='acalog-course')
            prerequisites = []
            if li:
                for prereq_link in li.find_all('a', href=lambda x: x and x.startswith('#tt')):
                    prereq_name = prereq_link.get_text().strip()
                    if prereq_name and prereq_name not in course_code_text:
                        if re.match(r'[A-Z]{2,4}\s+\d{3}', prereq_name):
                            prerequisites.append(prereq_name)
            
            # Build course URL
            course_url = None
            if course_id and catoid:
                desc_url = f"preview_course_nopop.php?catoid={catoid}&coid={course_id}"
                course_url = urljoin(self.URL, desc_url)
            
            courses_metadata.append({
                'course_code': course_code,
                'prerequisites': ', '.join(prerequisites) if prerequisites else None,
                'url': course_url
            })
        
        # Step 2: Fetch course descriptions
        courses = []
        for metadata in courses_metadata:
            description = None
            course_name = None
            prerequisites = metadata['prerequisites']  # Start with prerequisites from program page
            
            if metadata['url']:
                try:
                    desc_scraper = scraper_ISAT(metadata['url'])
                    course_name = desc_scraper._extract_course_name()
                    description = desc_scraper._extract_course_description()
                    # Extract prerequisites from description page (overrides program page if found)
                    desc_prereqs = desc_scraper._extract_prerequisites()
                    if desc_prereqs:
                        prerequisites = desc_prereqs
                except Exception:
                    pass
            
            if not course_name:
                course_name = metadata['course_code']
            
            courses.append({
                'course_name': course_name,
                'course_code': metadata['course_code'],
                'course_description': description or '',
                'prerequisites': prerequisites,
                'url': metadata['url']
            })
        
        return courses
