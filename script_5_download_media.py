"""
Script 5: Download media for matched Library IDs
For each matched Library ID:
- Download images
- Download videos (HD)
- Download description
Save to: downloads/AD_LIBRARY_ID/
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from bs4 import BeautifulSoup
import requests
import time
import os
from pathlib import Path
import sys

def download_media_for_library_id(library_id, parent_elem):
    """Download all media (images, videos, description) for a Library ID"""
    
    download_dir = Path('downloads') / f'AD_{library_id}'
    download_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n  Processing AD_{library_id}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # Extract description
    description = parent_elem.get_text(strip=True, separator=' ')[:500]
    if description:
        desc_path = download_dir / 'description.txt'
        with open(desc_path, 'w', encoding='utf-8') as f:
            f.write(description)
        print(f"    ✓ Saved description")
    
    # Download images
    images = parent_elem.find_all('img', limit=5)
    image_count = 0
    for idx, img in enumerate(images):
        img_src = img.get('src', '')
        if not img_src or len(img_src) < 20:
            continue
        if any(x in img_src.lower() for x in ['icon', 'pixel', '1x1', 'facebook.com/images']):
            continue
        
        try:
            response = requests.get(img_src, headers=headers, timeout=30, allow_redirects=True, stream=True)
            response.raise_for_status()
            
            # Determine extension
            content_type = response.headers.get('content-type', '').lower()
            if 'webp' in content_type:
                ext = '.webp'
            elif 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            else:
                ext = '.jpg'
            
            # Save image
            filename = f'image{f"_{image_count}" if image_count > 0 else ""}{ext}'
            image_path = download_dir / filename
            with open(image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            size_kb = image_path.stat().st_size / 1024
            print(f"    ✓ Downloaded image: {filename} ({size_kb:.1f}KB)")
            image_count += 1
            
        except Exception as e:
            print(f"    ✗ Error downloading image: {e}")
    
    # Download videos
    videos = []
    
    # Check standard video tags
    for video_elem in parent_elem.find_all('video', limit=3):
        source_tag = video_elem.find('source')
        if source_tag and source_tag.get('src'):
            videos.append(source_tag.get('src'))
    
    # Check links for video files
    for link in parent_elem.find_all('a', href=True, limit=20):
        href = link.get('href', '').lower()
        if any(ext in href for ext in ['.mp4', '.webm', '.mov']):
            videos.append(link.get('href'))
    
    # Download videos
    video_count = 0
    for video_src in videos:
        if not video_src:
            continue
        
        try:
            response = requests.get(video_src, headers=headers, timeout=60, allow_redirects=True, stream=True)
            response.raise_for_status()
            
            # Determine extension
            content_type = response.headers.get('content-type', '').lower()
            url_lower = video_src.lower()
            
            if 'mp4' in content_type or '.mp4' in url_lower:
                ext = '.mp4'
            elif 'webm' in content_type or '.webm' in url_lower:
                ext = '.webm'
            elif 'mov' in content_type or '.mov' in url_lower:
                ext = '.mov'
            else:
                ext = '.mp4'
            
            # Save video
            filename = f'video{f"_{video_count}" if video_count > 0 else ""}{ext}'
            video_path = download_dir / filename
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            size_mb = video_path.stat().st_size / (1024 * 1024)
            print(f"    ✓ Downloaded video: {filename} ({size_mb:.2f}MB)")
            video_count += 1
            
        except Exception as e:
            print(f"    ✗ Error downloading video: {e}")
    
    return download_dir

def download_matched_library_ids(facebook_url):
    """Download media for all matched Library IDs"""
    
    # Read matched IDs
    try:
        with open('matched_library_ids.txt', 'r') as f:
            matched_ids = [line.strip() for line in f if line.strip()]
    except:
        print("ERROR: matched_library_ids.txt not found. Run script_3 first.")
        return
    
    print(f"\nLoaded {len(matched_ids)} matched Library IDs")
    print("=" * 60)
    
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
        
        print(f"\nOpening: {facebook_url}")
        driver = webdriver.Chrome(options=options)
        driver.get(facebook_url)
        
        # Wait and scroll
        print("Waiting and scrolling to load all ads...")
        time.sleep(5)
        for scroll_num in range(15):
            driver.execute_script("window.scrollBy(0, 5000);")
            time.sleep(2)
        
        time.sleep(3)
        
        # Parse page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find all Library IDs and extract media
        all_text = soup.find_all(string=lambda text: text and 'Library ID:' in str(text))
        
        downloaded_count = 0
        for text_node in all_text:
            if downloaded_count >= len(matched_ids):
                break
            
            try:
                library_id_text = str(text_node).strip()
                if 'Library ID:' in library_id_text:
                    lib_id = library_id_text.split('Library ID:')[1].strip().split()[0]
                    
                    # Only download if matched
                    if lib_id not in matched_ids:
                        continue
                    
                    # Find parent ad card
                    parent = text_node.parent
                    for _ in range(10):
                        if not parent:
                            break
                        parent = parent.parent
                        parent_text = parent.get_text()
                        if 'Sponsored' in parent_text and len(parent_text) > 100:
                            break
                    
                    if not parent:
                        continue
                    
                    # Download media
                    download_media_for_library_id(lib_id, parent)
                    downloaded_count += 1
                    
            except Exception as e:
                print(f"  Error processing: {e}")
                continue
        
        print("\n" + "=" * 60)
        print(f"Downloaded {downloaded_count} matched ads")
        print(f"Location: downloads/")
        
    except Exception as e:
        print(f"ERROR: {e}")
        
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    facebook_url = sys.argv[1] if len(sys.argv) > 1 else 'https://www.facebook.com/ads/library?active_status=all&ad_type=all&country=US&q=rejuveen'
    download_matched_library_ids(facebook_url)
