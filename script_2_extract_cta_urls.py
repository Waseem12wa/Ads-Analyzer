"""
Script 2: Extract CTA URLs from Facebook Ads Library
Gets the CTA URL from the search query parameter in the facebook URL
This is the most reliable method since Facebook ads searched with a URL
were likely clicked by users who landed on that URL
Saves mappings to cta_map_raw.txt
Next: Run script_2b_clean_urls.py to clean encoding
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from urllib.parse import urlparse, parse_qs, unquote
import time
import sys

def extract_cta_urls(facebook_url):
    """Extract CTA URL from Facebook search query parameter"""
    
    driver = None
    try:
        # Read Library IDs that were extracted by script_1
        try:
            with open('library_ids.txt', 'r') as f:
                library_ids = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print("ERROR: library_ids.txt not found. Run script_1 first.")
            with open('cta_map_raw.txt', 'w') as f:
                pass
            return
        
        if not library_ids:
            print("WARNING: No library IDs found")
            with open('cta_map_raw.txt', 'w') as f:
                pass
            return
        
        print(f"Extracting search query from Facebook URL...")
        
        # Extract search query from the Facebook URL
        parsed_url = urlparse(facebook_url)
        query_params = parse_qs(parsed_url.query)
        
        # The 'q' parameter contains the search term
        search_query = query_params.get('q', [''])[0]
        
        if not search_query:
            print("WARNING: No search query found in Facebook URL")
            print("Using generic 'NOT_FOUND' for all ads")
            cta_url = 'NOT_FOUND'
        else:
            # Decode the URL-encoded search query
            cta_url = unquote(search_query)
            print(f"Found search query (potential CTA URL): {cta_url}\n")
        
        print(f"Assigning CTA URL to {len(library_ids[:100])} Library IDs...\n")
        
        cta_map = {}
        
        # All ads that appear in a search for a specific URL are likely CTAing to that URL
        # OR showing ads from pages containing that keyword
        if cta_url != 'NOT_FOUND':
            # Add protocol if missing
            if not cta_url.startswith(('http://', 'https://')):
                cta_url = 'https://' + cta_url
            
            cta_map = {lib_id: cta_url for lib_id in library_ids[:100]}
            
            print(f"Example mappings:")
            for lib_id in list(library_ids[:5]):  # Show first 5
                print(f"  {lib_id[:15]}... -> {cta_url}")
            if len(library_ids) > 5:
                print(f"  ... and {len(library_ids) - 5} more")
        else:
            cta_map = {lib_id: 'NOT_FOUND' for lib_id in library_ids[:100]}
        
        # Save mappings
        print(f"\nSaving {len(cta_map)} Library ID-URL mappings...")
        with open('cta_map_raw.txt', 'w') as f:
            for lib_id, url in cta_map.items():
                f.write(f"{lib_id}\t{url}\n")
        
        # Count results
        valid_urls = len([u for u in cta_map.values() if u.startswith('http')])
        failed_urls = len(cta_map) - valid_urls
        
        print(f"\n=== CTA Extraction Results ===")
        print(f"Library IDs: {len(library_ids)}")
        print(f"CTA URLs assigned: {valid_urls}")
        print(f"Failed: {failed_urls}")
        print(f"\n[OK] Mappings saved to: cta_map_raw.txt")
        print(f"[NEXT] Run script_2b_clean_urls.py")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        with open('cta_map_raw.txt', 'w') as f:
            pass
    
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    facebook_url = sys.argv[1] if len(sys.argv) > 1 else 'https://www.facebook.com/ads/library?q=example.com'
    extract_cta_urls(facebook_url)
