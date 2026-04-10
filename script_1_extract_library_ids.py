"""
Script 1: Extract Library IDs from Facebook Ads Library
Saves all found Library IDs to library_ids.txt
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from bs4 import BeautifulSoup
import time
import sys

def extract_library_ids(facebook_url):
    """Extract all Library IDs from Facebook Ads Library page"""
    
    driver = None
    try:
        # Setup Chrome
        options = ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        print(f"Opening: {facebook_url}")
        driver = webdriver.Chrome(options=options)
        driver.get(facebook_url)
        
        # Wait for page to load
        print("Waiting for page content...")
        time.sleep(5)
        
        # Scroll to load all ads
        print("Scrolling to load all ads...")
        for scroll_num in range(15):
            driver.execute_script("window.scrollBy(0, 5000);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            print(f"  Scroll {scroll_num + 1}/15, Height: {new_height}")
        
        # Parse page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find all Library ID text
        library_ids = set()
        all_text = soup.find_all(string=lambda text: text and 'Library ID:' in str(text))
        
        print(f"\nFound {len(all_text)} Library ID texts")
        
        for text_node in all_text:
            try:
                library_id_text = str(text_node).strip()
                if 'Library ID:' in library_id_text:
                    lib_id = library_id_text.split('Library ID:')[1].strip().split()[0]
                    library_ids.add(lib_id)
            except:
                continue
        
        # Save to file
        library_ids = sorted(list(library_ids))
        with open('library_ids.txt', 'w') as f:
            for lib_id in library_ids:
                f.write(lib_id + '\n')
        
        print(f"\nExtracted {len(library_ids)} unique Library IDs")
        print(f"Saved to: library_ids.txt")
        
        if len(library_ids) == 0:
            print("WARNING: No Library IDs found. Check the Facebook URL.")
        
        return library_ids
        
    except Exception as e:
        print(f"ERROR: {e}")
        # Still create the file even on error
        with open('library_ids.txt', 'w') as f:
            pass
        return []
        
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    # Get URL from command line argument or use default
    facebook_url = sys.argv[1] if len(sys.argv) > 1 else 'https://www.facebook.com/ads/library?active_status=all&ad_type=all&country=US&q=rejuveen'
    extract_library_ids(facebook_url)
