import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import urllib.parse

class FiverrGigScraper:
    def __init__(self, headless=True):
        """
        Initialize the scraper with Chrome driver
        """
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Initialize driver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=self.chrome_options
        )
        
        # Add stealth
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.wait = WebDriverWait(self.driver, 10)
        
    def search_gigs(self, category, max_pages=3):
        """
        Search for gigs in a specific category
        """
        # Encode category for URL
        encoded_category = urllib.parse.quote(category)
        
        gigs_data = []
        page = 1
        
        while page <= max_pages:
            try:
                # Construct URL (Fiverr search structure)
                if page == 1:
                    url = f"https://www.fiverr.com/search/gigs?query={encoded_category}&source=pagination"
                else:
                    url = f"https://www.fiverr.com/search/gigs?query={encoded_category}&page={page}&source=pagination"
                
                print(f"Scraping page {page}: {url}")
                
                self.driver.get(url)
                time.sleep(3)  # Wait for page load
                
                # Scroll to load all content
                self._scroll_page()
                
                # Parse page content
                page_gigs = self._parse_page()
                gigs_data.extend(page_gigs)
                
                print(f"Found {len(page_gigs)} gigs on page {page}")
                
                # Check if there are more pages
                if not self._has_next_page():
                    break
                    
                page += 1
                time.sleep(2)  # Delay between pages
                
            except Exception as e:
                print(f"Error on page {page}: {str(e)}")
                break
        
        return gigs_data
    
    def _scroll_page(self):
        """Scroll page to load all content"""
        scroll_pause_time = 1
        screen_height = self.driver.execute_script("return window.screen.height;")
        i = 1
        
        while True:
            # Scroll one screen height each time
            self.driver.execute_script(f"window.scrollTo(0, {screen_height * i});")
            i += 1
            time.sleep(scroll_pause_time)
            
            # Check if we've reached the bottom
            scroll_height = self.driver.execute_script("return document.body.scrollHeight;")
            if (screen_height * i) > scroll_height:
                break
    
    def _parse_page(self):
        """Parse gig information from current page"""
        gigs = []
        
        try:
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find gig cards - Fiverr's structure may vary
            # These selectors might need adjustment if Fiverr changes their layout
            gig_cards = soup.find_all('article', {'data-test': 'gig-card'})
            
            if not gig_cards:
                # Alternative selector
                gig_cards = soup.find_all('div', class_=lambda x: x and 'gig-card' in x.lower())
            
            for card in gig_cards:
                try:
                    # Extract gig title
                    title_elem = card.find(['h3', 'a'], class_=lambda x: x and ('title' in str(x).lower() or 'gig-card' in str(x).lower()))
                    title = title_elem.text.strip() if title_elem else "N/A"
                    
                    # Extract gig URL
                    link_elem = card.find('a', href=True)
                    if link_elem:
                        url = link_elem['href']
                        if not url.startswith('http'):
                            url = f"https://www.fiverr.com{url}"
                    else:
                        url = "N/A"
                    
                    # Extract freelancer name
                    seller_elem = card.find(['span', 'div'], class_=lambda x: x and ('seller' in str(x).lower() or 'user' in str(x).lower()))
                    seller = seller_elem.text.strip() if seller_elem else "N/A"
                    
                    # If seller not found, try alternative selectors
                    if seller == "N/A":
                        seller_elem = card.find('a', class_=lambda x: x and 'seller' in str(x).lower())
                        seller = seller_elem.text.strip() if seller_elem else "N/A"
                    
                    gig_data = {
                        'title': title,
                        'url': url,
                        'freelancer': seller,
                        'category': self.current_category
                    }
                    
                    gigs.append(gig_data)
                    
                except Exception as e:
                    print(f"Error parsing gig card: {str(e)}")
                    continue
            
        except Exception as e:
            print(f"Error parsing page: {str(e)}")
        
        return gigs
    
    def _has_next_page(self):
        """Check if there's a next page available"""
        try:
            next_button = self.driver.find_element(By.CSS_SELECTOR, '[aria-label="Next"]')
            return next_button.is_enabled()
        except:
            return False
    
    def save_to_csv(self, gigs_data, filename='fiverr_gigs.csv'):
        """Save scraped data to CSV file"""
        if not gigs_data:
            print("No data to save!")
            return
        
        df = pd.DataFrame(gigs_data)
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"Data saved to {filename}")
        print(f"Total gigs scraped: {len(gigs_data)}")
        
        # Display sample
        print("\nSample of scraped data:")
        print(df.head())
    
    def close(self):
        """Close the browser"""
        self.driver.quit()

# Alternative using requests and BeautifulSoup (simpler but may not work with JavaScript)
def simple_fiverr_scraper(category):
    """
    Simple scraper using requests (may not work if page requires JavaScript)
    """
    import requests
    from bs4 import BeautifulSoup
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    encoded_category = urllib.parse.quote(category)
    url = f"https://www.fiverr.com/search/gigs?query={encoded_category}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        gigs = []
        # Note: Fiverr loads content dynamically, so this might not capture all data
        for card in soup.find_all('article', limit=10):
            try:
                title = card.find('h3').text.strip() if card.find('h3') else "N/A"
                link = card.find('a', href=True)
                url = f"https://www.fiverr.com{link['href']}" if link else "N/A"
                
                gigs.append({
                    'title': title,
                    'url': url,
                    'category': category
                })
            except:
                continue
        
        return gigs
        
    except Exception as e:
        print(f"Error with simple scraper: {e}")
        return []

# Main execution
if __name__ == "__main__":
    # Configuration
    CATEGORY = "Custom Websites"  # Change this to your desired category
    MAX_PAGES = 2  # Number of pages to scrape
    OUTPUT_FILE = 'fiverr_gigs.csv'
    
    print(f"Starting Fiverr scraper for category: {CATEGORY}")
    
    # Method 1: Using Selenium (more reliable for JavaScript sites)
    scraper = FiverrGigScraper(headless=False)  # Set headless=True for background running
    
    try:
        gigs_data = scraper.search_gigs(CATEGORY, max_pages=MAX_PAGES)
        scraper.save_to_csv(gigs_data, OUTPUT_FILE)
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        scraper.close()
    
    # Method 2: Simple scraper (uncomment to try)
    print("\nTrying simple scraper...")
    simple_gigs = simple_fiverr_scraper(CATEGORY)
    if simple_gigs:
        df = pd.DataFrame(simple_gigs)
        df.to_csv('simple_fiverr_gigs.csv', index=False)
        print(f"Simple scraper saved {len(simple_gigs)} gigs")