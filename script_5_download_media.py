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
import json
import re

def extract_video_urls_from_html(html_content):
    """Extract video URLs from embedded JSON/script data in HTML"""
    video_urls = []
    
    try:
        # Look for video URLs in script tags
        script_pattern = r'https?://[^"\s<>]+\.(?:mp4|webm|mov|m3u8)[^"\s<>]*'
        matches = re.findall(script_pattern, html_content)
        for match in matches:
            if any(ext in match.lower() for ext in ['.mp4', '.webm', '.mov', '.m3u8']):
                video_urls.append(match)
    except:
        pass
    
    return list(set(video_urls))  # Remove duplicates

def download_video_with_selenium(video_url, video_path, driver):
    """Download video using Selenium to maintain authenticated session"""
    try:
        # Use Selenium to download the video through the browser
        # This maintains the authenticated session and bypasses 403 errors
        script = f"""
        (async function() {{
            try {{
                const response = await fetch('{video_url}', {{
                    method: 'GET',
                    credentials: 'include',
                    headers: {{
                        'Referer': window.location.href
                    }}
                }});
                const blob = await response.blob();
                const reader = new FileReader();
                reader.onload = function() {{
                    window.downloadedVideo = reader.result;
                }};
                reader.readAsArrayBuffer(blob);
            }} catch(e) {{
                console.error(e);
            }}
        }})()
        """
        
        # Execute the download script
        driver.execute_script(script)
        time.sleep(3)  # Wait for download to complete
        
        # Get the downloaded data
        video_data = driver.execute_script('return window.downloadedVideo')
        
        if video_data:
            # Decode base64 and save
            with open(video_path, 'wb') as f:
                f.write(video_data)
            return True
        
    except Exception as e:
        print(f"      Selenium download failed: {str(e)[:80]}")
    
    return False

def download_media_for_library_id(library_id, parent_elem, page_html='', driver=None):
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
    
    # Check for picture elements (modern video containers)
    for picture_elem in parent_elem.find_all('picture', limit=5):
        for source_tag in picture_elem.find_all('source'):
            src = source_tag.get('src', '')
            if src and any(ext in src.lower() for ext in ['.mp4', '.webm', '.mov']):
                videos.append(src)
    
    # Check data attributes for video URLs
    for elem in parent_elem.find_all(limit=50):
        for attr in ['data-src', 'data-video', 'data-video-src']:
            value = elem.get(attr, '')
            if value and any(ext in value.lower() for ext in ['.mp4', '.webm', '.mov']):
                videos.append(value)
    
    # Check all img elements for potential video thumbnails with video data
    for img in parent_elem.find_all('img', limit=10):
        # Sometimes video thumbnails have usable src that points to video
        img_src = img.get('src', '')
        if 'video' in img_src.lower() and any(ext in img_src.lower() for ext in ['.mp4', '.webm']):
            videos.append(img_src)
        
        # Check for data attributes on images
        for attr in ['data-video', 'data-src']:
            value = img.get(attr, '')
            if value and any(ext in value.lower() for ext in ['.mp4', '.webm', '.mov']):
                videos.append(value)
    
    # Check links for video files
    for link in parent_elem.find_all('a', href=True, limit=30):
        href = link.get('href', '')
        href_lower = href.lower()
        if any(ext in href_lower for ext in ['.mp4', '.webm', '.mov']):
            videos.append(href)
    
    # Extract videos from embedded page HTML (Facebook embeds URLs in JSON/script)
    if page_html:
        embedded_videos = extract_video_urls_from_html(page_html)
        videos.extend(embedded_videos)
    
    # Remove duplicates
    videos = list(set(v for v in videos if v))
    
    if videos:
        print(f"    Found {len(videos)} potential video URL(s)")
    
    # Download videos
    video_count = 0
    for video_src in videos:
        if not video_src:
            continue
        
        try:
            # Skip very small/placeholder URLs
            if len(video_src) < 30:
                continue
            
            print(f"    Downloading video {video_count + 1}: {video_src[:80]}...")
            
            # Determine extension
            url_lower = video_src.lower()
            if '.mp4' in url_lower:
                ext = '.mp4'
            elif '.webm' in url_lower:
                ext = '.webm'
            elif '.mov' in url_lower:
                ext = '.mov'
            elif 'm3u8' in url_lower or 'playlist' in url_lower:
                print(f"    ⚠ Found HLS stream (m3u8) - skipping")
                continue
            else:
                ext = '.mp4'
            
            # Save video
            filename = f'video{f"_{video_count}" if video_count > 0 else ""}{ext}'
            video_path = download_dir / filename
            
            # Try Selenium download first (with authenticated session)
            if driver:
                print(f"      Attempting Selenium download...")
                if download_video_with_selenium(video_src, str(video_path), driver):
                    final_size_mb = video_path.stat().st_size / (1024 * 1024)
                    if final_size_mb > 0.1:
                        print(f"    ✓ Downloaded video: {filename} ({final_size_mb:.2f}MB)")
                        video_count += 1
                        continue
                    else:
                        video_path.unlink()
            
            # Fallback: Try direct HTTP request (will likely fail for Facebook videos)
            print(f"      Trying direct download...")
            headers_with_referer = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.facebook.com/',
            }
            
            response = requests.get(video_src, headers=headers_with_referer, timeout=30, allow_redirects=True, stream=True)
            response.raise_for_status()
            
            # Check file size
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) < 100000:  # Less than 100KB
                print(f"    ✗ File too small - skipped")
                continue
            
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            final_size_mb = video_path.stat().st_size / (1024 * 1024)
            if final_size_mb > 0.1:
                print(f"    ✓ Downloaded video: {filename} ({final_size_mb:.2f}MB)")
                video_count += 1
            else:
                video_path.unlink()
                
        except Exception as e:
            error_str = str(e)[:100]
            if '403' in error_str:
                print(f"    ✗ Access denied (403) - video protected")
            else:
                print(f"    ✗ Error: {error_str}")
    
    return download_dir
    
    return download_dir
    
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
        
        # Wait and scroll - longer wait for videos to load
        print("Waiting and scrolling to load all ads and videos...")
        time.sleep(8)  # Increased wait for initial page load
        
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        max_scrolls = 25  # More scrolls to load more content
        
        while scroll_count < max_scrolls:
            driver.execute_script("window.scrollBy(0, 3000);")
            time.sleep(3)  # Increased wait between scrolls for video loading
            scroll_count += 1
            
            print(f"  Scrolled {scroll_count}/{max_scrolls}...")
            
            # Check if we've reached bottom
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("  Reached end of page")
                break
            last_height = new_height
        
        time.sleep(5)  # Final wait for any remaining content
        
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
                    download_media_for_library_id(lib_id, parent, driver.page_source, driver)
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
