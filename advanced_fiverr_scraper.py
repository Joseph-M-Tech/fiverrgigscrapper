import time
import csv
import json
import pandas as pd
import numpy as np
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import urllib.parse
import re
import requests
from fake_useragent import UserAgent
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import threading
import queue
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fiverr_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class GigData:
    title: str
    url: str
    freelancer: str
    rating: float
    reviews: int
    price: str
    delivery_time: str
    completed_jobs: int
    category: str
    keywords: List[str]
    description: str
    tags: List[str]
    level: str
    online_status: bool
    response_time: str
    last_delivery: str
    gig_created: str
    scraped_at: datetime
    
    def to_dict(self):
        data = asdict(self)
        data['scraped_at'] = self.scraped_at.isoformat()
        return data

class AdvancedFiverrScraper:
    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.driver = None
        self.wait = None
        self.session = None
        self.user_agent = UserAgent()
        self.categories_cache = {}
        self.initialize_driver()
        self.initialize_session()
        
    def initialize_driver(self):
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        chrome_options.add_argument(f"user-agent={self.user_agent.random}")
        
        if self.proxy:
            chrome_options.add_argument(f'--proxy-server={self.proxy}')
        
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 15)
            logger.info("Chrome driver initialized")
        except Exception as e:
            logger.error(f"Failed to initialize driver: {e}")
            raise
    
    def initialize_session(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent.random,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        })
    
    def search_gigs_advanced(
        self,
        keywords: List[str],
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        max_pages: int = 3,
        sort_by: str = "relevant",
        delivery_time: Optional[str] = None,
        online_only: bool = False,
        top_rated_seller: bool = False
    ) -> List[GigData]:
        
        all_gigs = []
        
        try:
            base_url = "https://www.fiverr.com/search/gigs"
            
            query_parts = []
            if keywords:
                query_parts.append(" ".join(keywords))
            if category:
                query_parts.append(category)
            
            search_query = " ".join(query_parts)
            encoded_query = urllib.parse.quote(search_query)
            
            url = f"{base_url}?query={encoded_query}"
            
            sort_map = {
                "relevant": "relevant",
                "best_selling": "best_selling",
                "newest": "newest",
                "rating": "seller_rating"
            }
            url += f"&order={sort_map.get(sort_by, 'relevant')}"
            
            if delivery_time:
                url += f"&delivery={delivery_time}"
            if online_only:
                url += "&online=true"
            
            logger.info(f"Searching with URL: {url}")
            
            for page in range(1, max_pages + 1):
                try:
                    page_url = f"{url}&page={page}" if page > 1 else url
                    logger.info(f"Scraping page {page}")
                    
                    self.driver.get(page_url)
                    time.sleep(np.random.uniform(2, 4))
                    
                    self._scroll_page_gradually()
                    page_gigs = self._parse_advanced_page()
                    
                    if min_rating:
                        page_gigs = [gig for gig in page_gigs if gig.rating >= min_rating]
                    
                    all_gigs.extend(page_gigs)
                    logger.info(f"Found {len(page_gigs)} gigs on page {page}")
                    
                    if not self._has_next_page():
                        break
                    
                    time.sleep(np.random.uniform(3, 6))
                    
                except Exception as e:
                    logger.error(f"Error scraping page {page}: {e}")
                    break
            
            logger.info(f"Total gigs scraped: {len(all_gigs)}")
            return all_gigs
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _scroll_page_gradually(self):
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        current_position = 0
        scroll_step = viewport_height // 2
        
        while current_position < total_height:
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            current_position += scroll_step
            time.sleep(np.random.uniform(0.5, 1.5))
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height > total_height:
                total_height = new_height
    
    def _parse_advanced_page(self) -> List[GigData]:
        gigs = []
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            selectors = [
                'article[data-test="gig-card"]',
                'div[class*="gig-card"]',
                'div[class*="gig-wrapper"]',
            ]
            
            gig_cards = []
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    gig_cards = elements
                    break
            
            if not gig_cards:
                potential_cards = soup.find_all(['article', 'div'], {
                    'class': re.compile(r'card|gig|listing', re.I)
                })
                gig_cards = [card for card in potential_cards if len(card.text.strip()) > 50]
            
            for card in gig_cards:
                try:
                    gig_data = self._extract_gig_details(card)
                    if gig_data:
                        gigs.append(gig_data)
                except:
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing page: {e}")
        
        return gigs
    
    def _extract_gig_details(self, card) -> Optional[GigData]:
        try:
            title_elem = card.find(['h3', 'a'], {
                'class': re.compile(r'title|gig-title', re.I)
            })
            title = title_elem.get_text(strip=True) if title_elem else "N/A"
            
            url = "N/A"
            link_elem = card.find('a', href=True)
            if link_elem:
                href = link_elem.get('href', '')
                if href and not href.startswith('http'):
                    url = f"https://www.fiverr.com{href}"
                else:
                    url = href
            
            seller_elem = card.find(['a', 'span'], {
                'class': re.compile(r'seller|user|username', re.I)
            })
            seller = seller_elem.get_text(strip=True) if seller_elem else "N/A"
            
            rating = 0.0
            rating_elem = card.find(['span', 'div'], {
                'class': re.compile(r'rating|stars', re.I)
            })
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            reviews = 0
            reviews_elem = card.find(['span', 'div'], {
                'class': re.compile(r'review|rating-count', re.I)
            })
            if reviews_elem:
                reviews_text = reviews_elem.get_text(strip=True)
                reviews_match = re.search(r'\(?(\d+)\)?', reviews_text)
                if reviews_match:
                    reviews = int(reviews_match.group(1))
            
            price = "N/A"
            price_elem = card.find(['span', 'div'], {
                'class': re.compile(r'price|amount', re.I)
            })
            if price_elem:
                price = price_elem.get_text(strip=True)
            
            description = self._extract_description(card)
            tags = self._extract_tags(card)
            
            level = "Level 1"
            level_indicators = card.find_all(['span', 'div'], {
                'class': re.compile(r'level|badge|seller-level', re.I)
            })
            for indicator in level_indicators:
                level_text = indicator.get_text(strip=True)
                if any(word in level_text.lower() for word in ['top', 'pro', 'level']):
                    level = level_text
            
            online_status = bool(card.find(['span', 'div'], {
                'class': re.compile(r'online|status', re.I)
            }))
            
            gig_data = GigData(
                title=title,
                url=url,
                freelancer=seller,
                rating=rating,
                reviews=reviews,
                price=price,
                delivery_time=self._extract_delivery_time(card),
                completed_jobs=self._extract_completed_jobs(card),
                category="",
                keywords=[],
                description=description,
                tags=tags,
                level=level,
                online_status=online_status,
                response_time=self._extract_response_time(card),
                last_delivery="",
                gig_created="",
                scraped_at=datetime.now()
            )
            
            return gig_data
            
        except Exception as e:
            return None
    
    def _extract_description(self, card) -> str:
        desc_elem = card.find(['p', 'div'], {
            'class': re.compile(r'description|text|content', re.I)
        })
        return desc_elem.get_text(strip=True)[:200] if desc_elem else ""
    
    def _extract_tags(self, card) -> List[str]:
        tags = []
        tag_elements = card.find_all(['span', 'a'], {
            'class': re.compile(r'tag|skill|category', re.I)
        })
        for tag_elem in tag_elements:
            tag_text = tag_elem.get_text(strip=True)
            if tag_text and len(tag_text) < 30:
                tags.append(tag_text)
        return list(set(tags))[:5]
    
    def _extract_delivery_time(self, card) -> str:
        time_elem = card.find(['span', 'div'], {
            'class': re.compile(r'delivery|time|days', re.I)
        })
        return time_elem.get_text(strip=True) if time_elem else "N/A"
    
    def _extract_completed_jobs(self, card) -> int:
        jobs_elem = card.find(['span', 'div'], {
            'class': re.compile(r'orders|completed|delivered', re.I)
        })
        if jobs_elem:
            jobs_text = jobs_elem.get_text(strip=True)
            match = re.search(r'(\d+[\d,]*)\s*(orders|completed|delivered)', jobs_text, re.I)
            if match:
                try:
                    return int(match.group(1).replace(',', ''))
                except:
                    pass
        return 0
    
    def _extract_response_time(self, card) -> str:
        response_elem = card.find(['span', 'div'], {
            'class': re.compile(r'response|reply', re.I)
        })
        return response_elem.get_text(strip=True) if response_elem else "N/A"
    
    def _has_next_page(self) -> bool:
        try:
            next_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                '[aria-label*="Next"], button[class*="next"], a[class*="next"]'
            )
            for button in next_buttons:
                if button.is_displayed() and button.is_enabled():
                    return True
            return False
        except:
            return False
    
    def export_to_csv(self, gigs_data: List[GigData], filename: str):
        if not gigs_data:
            logger.warning("No data to export")
            return
        
        data = []
        for gig in gigs_data:
            data.append({
                'Title': gig.title,
                'URL': gig.url,
                'Freelancer': gig.freelancer,
                'Rating': gig.rating,
                'Reviews': gig.reviews,
                'Price': gig.price,
                'Delivery Time': gig.delivery_time,
                'Completed Jobs': gig.completed_jobs,
                'Category': gig.category,
                'Keywords': ', '.join(gig.keywords),
                'Description': gig.description,
                'Tags': ', '.join(gig.tags),
                'Seller Level': gig.level,
                'Online Status': 'Online' if gig.online_status else 'Offline',
                'Response Time': gig.response_time,
                'Scraped At': gig.scraped_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values(['Rating', 'Completed Jobs'], ascending=[False, False])
        df.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"Data exported to {filename}")
        
        try:
            excel_filename = filename.replace('.csv', '.xlsx')
            df.to_excel(excel_filename, index=False)
            logger.info(f"Data also exported to {excel_filename}")
        except:
            pass
        
        return df
    
    def export_to_json(self, gigs_data: List[GigData], filename: str):
        if not gigs_data:
            return
        
        data = []
        for gig in gigs_data:
            data.append(gig.to_dict())
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data exported to {filename}")
    
    def close(self):
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")
        if self.session:
            self.session.close()