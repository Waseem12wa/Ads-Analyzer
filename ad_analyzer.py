import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from bs4 import BeautifulSoup
import json
import os
import re
import base64
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path
import time

class FacebookAdAnalyzer:
    def __init__(self, download_dir="downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.options = ChromeOptions()
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option('useAutomationExtension', False)
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--disable-web-resources')

    def extract_ad_data(self, facebook_ads_url, target_url):
        """
        Extract ad data from Facebook Ads Library URL
        Returns: dict with ad_media_url, cta_url, description, match_result
        """
        driver = None
        try:
            driver = webdriver.Chrome(options=self.options)
            driver.set_page_load_timeout(45)
            
            print(f"Loading URL: {facebook_ads_url}")
            driver.get(facebook_ads_url)
            
            # Wait for ads to load - try multiple selectors
            print("Waiting for page content...")
            time.sleep(3)
            
            # Try to wait for ad content to appear
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "img"))
                )
            except:
                pass
            
            # Scroll down multiple times to load all ads dynamically
            print("Scrolling to load more ads...")
            for scroll_num in range(5):  # Scroll 5 times
                driver.execute_script("window.scrollBy(0, 3000);")  # Scroll 3000px down
                time.sleep(2)  # Wait 2 seconds for new content to load
                print(f"  Scroll {scroll_num + 1}/5 complete")
            
            # Scroll back to top
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Get page source and extract data
            ads_data = self._scrape_ad_library(driver, target_url)
            
            return ads_data
            
        except Exception as e:
            print(f"Error extracting ad data: {str(e)}")
            return {"error": f"Failed to load page: {str(e)}"}
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def _scrape_ad_library(self, driver, target_url):
        """Scrape Facebook Ads Library page with multiple strategies"""
        try:
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            print("Searching for ads in page...")
            
            all_ads = []
            processed_urls = set()  # Track processed URLs to avoid duplicates
            
            # REVISED: Find divs containing BOTH images and links
            print("\nSearching for ad containers (divs with images + links)...")
            divs = soup.find_all('div', recursive=True, limit=5000)  # Limit divs to avoid excessive parsing
            print(f"Found {len(divs)} divs, analyzing for ads...")
            
            for div in divs:
                # Look for images in this div
                img = div.find('img', recursive=True)
                if not img:
                    continue
                
                img_src = img.get('src', '')
                if not img_src or len(img_src) < 20:
                    continue
                
                # Skip meaningless images
                if any(x in img_src.lower() for x in ['icon', 'pixel', 'spacer', 'placeholder', '1x1', 'data:', 
                                                       'facebook.com/images', 'static.xx.fbcdn.net/rsrc.php',
                                                       '//fb','fbcdn.net/rsrc', 'scontent']):
                    continue
                
                # Look for links in this SAME div
                links = div.find_all('a', href=True, recursive=True, limit=10)
                
                for link in links:
                    href = link.get('href', '')
                    
                    # Skip bad links
                    if not href or href.startswith('#') or len(href) < 10:
                        continue
                    if 'javascript:' in href.lower():
                        continue
                    if any(x in href.lower() for x in ['facebook.com/ads', 'facebook.com/help', 'facebook.com/policies']):
                        continue
                    
                    if href in processed_urls:
                        continue
                    
                    processed_urls.add(href)
                    
                    # Get text from this ad container for description
                    text_content = div.get_text(strip=True)[:300]
                    
                    ad_info = {
                        'media_url': img_src,
                        'media_type': 'image',
                        'cta_url': best_link_href,
                        'cta_text': best_link_text,
                        'description': text_content if len(text_content) > 20 else '',
                        'source': 'div_container'
                    }
                    all_ads.append(ad_info)
                    
                    if len(all_ads) <= 10:
                        print(f"  Found ad #{len(all_ads)}: {href[:60]}...")
                    break  # Only use first valid link per image
            
            print(f"\nExtracted {len(all_ads)} ads from containers")
            
            # Strategy 2: Find ALL videos with associated links
            print("\nStrategy 2: Extracting videos with associated links...")
            videos = soup.find_all('video')  # No limit - get ALL videos
            print(f"Found {len(videos)} videos total")
            
            for video in videos:
                source_tag = video.find('source')
                if not source_tag or not source_tag.get('src'):
                    continue
                
                video_src = source_tag.get('src')
                
                # Look for nearby links
                parent = video.parent
                best_link_href = None
                best_link_text = ''
                description = ''
                
                for level in range(10):
                    if not parent:
                        break
                    
                    links = parent.find_all('a', href=True, recursive=False)
                    for link in links:
                        href = link.get('href', '')
                        
                        if not href or href.startswith('#') or 'javascript:' in href.lower():
                            continue
                        if any(x in href.lower() for x in ['facebook.com/ads', 'facebook.com/help']):
                            continue
                        
                        if len(href) > 10:
                            best_link_href = href
                            best_link_text = link.get_text(strip=True)[:100] or 'Ad'
                            nearby_text = parent.get_text(strip=True)[:300]
                            if nearby_text and len(nearby_text) > 20:
                                description = nearby_text
                            break
                    
                    if best_link_href:
                        break
                    
                    parent = parent.parent
                
                if best_link_href and best_link_href not in processed_urls:
                    processed_urls.add(best_link_href)
                    
                    ad_info = {
                        'media_url': video_src,
                        'media_type': 'video',
                        'cta_url': best_link_href,
                        'cta_text': best_link_text,
                        'description': description if description else '',
                        'source': 'video_link'
                    }
                    all_ads.append(ad_info)
                    print(f"  Found video ad: {best_link_href[:60]}...")
            
            # Strategy 3: Collect ALL external links as potential ads
            print("\nStrategy 3: Extracting ALL external links as potential ads...")
            all_links = soup.find_all('a', href=True)  # No limit - get ALL links
            print(f"Found {len(all_links)} links total")
            
            link_count = 0
            for link in all_links:
                
                href = link.get('href', '')
                link_text = link.get_text(strip=True)
                
                if not href or href.startswith('#') or 'javascript:' in href.lower():
                    continue
                
                if any(x in href.lower() for x in ['facebook.com/ads', 'facebook.com/help', 'facebook.com/policies']):
                    continue
                
                if len(href) < 10 or href in processed_urls:
                    continue
                
                # Check if this link has media nearby
                parent = link.parent
                media_url = None
                media_type = 'none'
                
                for _ in range(3):
                    if not parent:
                        break
                    
                    img = parent.find('img')
                    if img and img.get('src'):
                        media_url = img.get('src')
                        media_type = 'image'
                        break
                    
                    video = parent.find('video')
                    if video:
                        source = video.find('source')
                        if source and source.get('src'):
                            media_url = source.get('src')
                            media_type = 'video'
                            break
                    
                    parent = parent.parent
                
                processed_urls.add(href)
                link_count += 1
                
                ad_info = {
                    'cta_url': href,
                    'cta_text': link_text[:100] if link_text else 'Ad',
                    'media_type': media_type,
                    'source': 'link_fallback'
                }
                
                if media_url:
                    ad_info['media_url'] = media_url
                
                all_ads.append(ad_info)
            
            print(f"\nTotal extracted: {len(all_ads)} ads from all strategies")
            
            if not all_ads:
                print("No ads found on page. The page might not have loaded properly.")
                return []
            
            # Look for matching URLs
            matched_ads = []
            for ad in all_ads:
                if ad.get('cta_url'):
                    if self._urls_match(ad.get('cta_url'), target_url):
                        ad['match'] = True
                        matched_ads.append(ad)
            
            print(f"\nFound {len(matched_ads)} matching ads (out of {len(all_ads)} total)")
            
            # Return ALL matched ads
            if matched_ads:
                return matched_ads
            
            # If no match, return best ones with media
            if all_ads:
                ads_with_media = [ad for ad in all_ads if ad.get('media_url')]
                if ads_with_media:
                    print(f"No matching URLs found, returning {min(10, len(ads_with_media))} best ads with media")
                    return ads_with_media[:10]
                print(f"No ads with media found, returning {min(10, len(all_ads))} best ads")
                return all_ads[:10]
            
            return []
            
        except Exception as e:
            print(f"Scraping error: {str(e)}")
            import traceback
            traceback.print_exc()
            return []



    def _urls_match(self, cta_url, target_url):
        """Compare two URLs for matching with multiple strategies"""
        try:
            # Normalize the URLs first
            cta_url = unquote(str(cta_url)).strip()
            target_url = unquote(str(target_url)).strip()
            
            print(f"Comparing URLs:")
            print(f"  CTA URL: {cta_url}")
            print(f"  Target URL: {target_url}")
            
            # Remove common redirect prefixes
            if 'facebook.com/flite_redirect.php' in cta_url or 'l.facebook.com' in cta_url:
                if 'u=' in cta_url:
                    cta_url = cta_url.split('u=')[1].split('&')[0]
                elif 'redirect_uri=' in cta_url:
                    cta_url = cta_url.split('redirect_uri=')[1].split('&')[0]
            
            # Ensure URLs have protocol
            if not cta_url.startswith(('http://', 'https://')):
                cta_url = 'https://' + cta_url
            
            if not target_url.startswith(('http://', 'https://')):
                target_url = 'https://' + target_url
            
            # Parse URLs
            try:
                cta_parsed = urlparse(cta_url)
                target_parsed = urlparse(target_url)
            except:
                return False
            
            # Get normalized domain
            cta_domain = cta_parsed.netloc.replace('www.', '').lower()
            target_domain = target_parsed.netloc.replace('www.', '').lower()
            
            # Get paths (remove trailing slashes)
            cta_path = cta_parsed.path.rstrip('/').lower()
            target_path = target_parsed.path.rstrip('/').lower()
            
            print(f"  Parsed CTA domain: {cta_domain}, path: {cta_path}")
            print(f"  Parsed Target domain: {target_domain}, path: {target_path}")
            
            # Match 1: Exact URL match
            if cta_url.rstrip('/') == target_url.rstrip('/'):
                print("Result: EXACT MATCH")
                return True
            
            # Match 2: Domain and path match
            if cta_domain == target_domain:
                print("Result: DOMAIN MATCH (same website)")
                return True  # Match if same domain, regardless of path
            
            # Match 3: Subdomain variations
            if cta_domain.endswith(target_domain) or target_domain.endswith(cta_domain):
                # If one starts with the other, it might be a subdomain
                cta_parts = cta_domain.split('.')
                target_parts = target_domain.split('.')
                
                if len(cta_parts) > 1 and len(target_parts) > 1:
                    if cta_parts[-2:] == target_parts[-2:]:  # Same base domain
                        print("Result: SUBDOMAIN MATCH")
                        return True
            
            print("Result: NO MATCH")
            return False
            
        except Exception as e:
            print(f"URL matching error: {e}")
            return False

    def download_media(self, media_url, media_type, ad_name):
        """Download media from URL"""
        try:
            if not media_url:
                return None
            
            # Skip data URLs 
            if media_url.startswith('data:'):
                return None
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.facebook.com/'
            }
            
            print(f"Downloading {media_type} from: {media_url}")
            response = requests.get(media_url, headers=headers, timeout=15, allow_redirects=True, stream=True)
            response.raise_for_status()
            
            # Determine file extension from content-type or URL
            content_type = response.headers.get('content-type', '')
            
            if media_type == 'image':
                if 'webp' in content_type:
                    extension = '.webp'
                elif 'png' in content_type:
                    extension = '.png'
                elif 'gif' in content_type:
                    extension = '.gif'
                else:
                    extension = '.jpg'
            else:  # video
                if 'mp4' in content_type or '.mp4' in media_url:
                    extension = '.mp4'
                elif 'webm' in content_type:
                    extension = '.webm'
                elif 'mov' in content_type:
                    extension = '.mov'
                else:
                    extension = '.mp4'
            
            filename = f"{ad_name}_{media_type}{extension}"
            filepath = self.download_dir / filename
            
            # Download file in chunks to handle large files
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = filepath.stat().st_size
            if file_size == 0:
                filepath.unlink()
                return None
            
            print(f"Downloaded: {filename} ({file_size} bytes)")
            return str(filepath)
            
        except Exception as e:
            print(f"Error downloading media: {str(e)}")
            return None

    def save_description(self, description, ad_name):
        """Save description to text file"""
        try:
            if not description:
                return None
            
            filename = f"{ad_name}_description.txt"
            filepath = self.download_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(description)
            
            return str(filepath)
            
        except Exception as e:
            print(f"Error saving description: {str(e)}")
            return None

    def process_ad(self, facebook_ads_url, target_url):
        """Main processing function - Download all matching ads"""
        print("\n=== Processing All Matching Ads ===")
        
        # Extract ad data
        ads_data = self.extract_ad_data(facebook_ads_url, target_url)
        
        # Handle error response
        if isinstance(ads_data, dict) and ads_data.get('error'):
            print(f"Error: {ads_data.get('error')}")
            return ads_data
        
        # Handle non-list response (backward compatibility)
        if not isinstance(ads_data, list):
            ads_data = [ads_data]
        
        print(f"\nProcessing {len(ads_data)} ads...")
        
        # Separate matched and unmatched ads
        matched_ads = [ad for ad in ads_data if ad.get('match')]
        unmatched_ads = [ad for ad in ads_data if not ad.get('match')]
        
        print(f"Matched ads: {len(matched_ads)}")
        print(f"Unmatched ads: {len(unmatched_ads)}")
        
        # Process all matched ads
        results = {
            "success": len(matched_ads) > 0,
            "total_matched": len(matched_ads),
            "total_checked": len(ads_data),
            "message": f"Found {len(matched_ads)} matching ads",
            "downloads": []
        }
        
        if len(matched_ads) == 0:
            results["message"] = "No matching ads found"
            return results
        
        # Process each matched ad
        for idx, ad in enumerate(matched_ads, 1):
            print(f"\n--- Processing Matched Ad {idx}/{len(matched_ads)} ---")
            ad_result = self._process_single_ad(ad, idx)
            results["downloads"].append(ad_result)
        
        print(f"\n=== Processing Complete ===")
        print(f"Total matched ads downloaded: {len(matched_ads)}")
        
        return results
    
    def _process_single_ad(self, ad, index):
        """Process a single ad and create folder structure"""
        try:
            import hashlib
            
            # Generate Library ID from ad data
            cta_url = ad.get('cta_url', '')
            library_id = hashlib.md5(f"{cta_url}{index}".encode()).hexdigest()[:8].upper()
            
            # Create folder for this ad
            ad_folder = self.download_dir / f"AD_{library_id}"
            ad_folder.mkdir(exist_ok=True)
            
            print(f"Created folder: AD_{library_id}")
            
            ad_result = {
                "library_id": library_id,
                "folder": str(ad_folder),
                "cta_url": ad.get('cta_url'),
                "cta_text": ad.get('cta_text'),
                "media_files": [],
                "description_file": None
            }
            
            # Download media
            if ad.get('media_url'):
                media_path = self._download_media_to_folder(
                    ad.get('media_url'),
                    ad.get('media_type'),
                    ad_folder
                )
                if media_path:
                    ad_result["media_files"].append({
                        "type": ad.get('media_type'),
                        "path": str(media_path)
                    })
            
            # Save description
            if ad.get('description'):
                desc_path = self._save_description_to_folder(
                    ad.get('description'),
                    ad_folder
                )
                if desc_path:
                    ad_result["description_file"] = str(desc_path)
            
            # Save metadata
            meta_path = self._save_metadata_to_folder(ad, ad_folder)
            if meta_path:
                ad_result["metadata_file"] = str(meta_path)
            
            print(f"✓ Completed AD_{library_id}")
            return ad_result
            
        except Exception as e:
            print(f"Error processing ad: {str(e)}")
            return {"error": str(e)}
    
    def _download_media_to_folder(self, media_url, media_type, folder_path):
        """Download media to specific folder"""
        try:
            if not media_url or media_url.startswith('data:'):
                return None
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.facebook.com/'
            }
            
            print(f"  Downloading {media_type}...")
            response = requests.get(media_url, headers=headers, timeout=15, allow_redirects=True, stream=True)
            response.raise_for_status()
            
            # Determine file extension
            content_type = response.headers.get('content-type', '').lower()
            
            if media_type == 'image':
                if 'webp' in content_type:
                    extension = '.webp'
                elif 'png' in content_type:
                    extension = '.png'
                elif 'gif' in content_type:
                    extension = '.gif'
                else:
                    extension = '.jpg'
            else:  # video
                if 'mp4' in content_type or '.mp4' in media_url.lower():
                    extension = '.mp4'
                elif 'webm' in content_type:
                    extension = '.webm'
                elif 'mov' in content_type:
                    extension = '.mov'
                else:
                    extension = '.mp4'
            
            filename = f"{media_type}{extension}"
            filepath = folder_path / filename
            
            # Download file in chunks
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = filepath.stat().st_size
            if file_size == 0:
                filepath.unlink()
                return None
            
            print(f"  ✓ Downloaded {filename} ({file_size} bytes)")
            return filepath
            
        except Exception as e:
            print(f"  ✗ Error downloading media: {str(e)}")
            return None
    
    def _save_description_to_folder(self, description, folder_path):
        """Save description to specific folder"""
        try:
            if not description:
                return None
            
            filepath = folder_path / "description.txt"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(description)
            
            print(f"  ✓ Saved description.txt")
            return filepath
            
        except Exception as e:
            print(f"  ✗ Error saving description: {str(e)}")
            return None
    
    def _save_metadata_to_folder(self, ad, folder_path):
        """Save ad metadata to JSON file"""
        try:
            filepath = folder_path / "metadata.json"
            
            metadata = {
                "cta_url": ad.get('cta_url'),
                "cta_text": ad.get('cta_text'),
                "media_type": ad.get('media_type'),
                "has_media": bool(ad.get('media_url')),
                "has_description": bool(ad.get('description')),
                "source": ad.get('source', 'unknown')
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            return filepath
            
        except Exception as e:
            print(f"  ✗ Error saving metadata: {str(e)}")
            return None
