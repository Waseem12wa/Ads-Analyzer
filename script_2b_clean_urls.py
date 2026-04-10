"""
Script 2b: Clean up garbage characters from extracted CTA URLs
Removes URL encoding, trailing parameters, and normalizes URLs
Saves cleaned URLs to cta_map.txt
"""

import sys
from urllib.parse import unquote, urlparse
import re

def clean_urls():
    """Clean garbage characters from raw CTA URLs"""
    
    try:
        # Read raw CTA URLs
        try:
            with open('cta_map_raw.txt', 'r') as f:
                raw_urls = {}
                for line in f:
                    if line.strip() and '\t' in line:
                        lib_id, url = line.strip().split('\t', 1)
                        raw_urls[lib_id] = url
        except FileNotFoundError:
            print("WARNING: cta_map_raw.txt not found. Run script_2 first.")
            with open('cta_map.txt', 'w') as f:
                pass
            return
        
        if not raw_urls:
            print("WARNING: No raw URLs found. Creating empty cta_map.txt...")
            with open('cta_map.txt', 'w') as f:
                pass
            return
        
        print(f"Cleaning {len(raw_urls)} URLs...\n")
        
        cleaned_urls = {}
        error_count = 0
        
        for idx, (lib_id, raw_url) in enumerate(raw_urls.items(), 1):
            try:
                # Skip error URLs
                if raw_url.startswith('ERROR') or raw_url == 'AD_NOT_FOUND' or raw_url == 'NO_CTA_LINK':
                    cleaned_urls[lib_id] = raw_url
                    continue
                
                # Decode URL encoding (%2F → /, %3D → =, etc.)
                decoded = unquote(raw_url)
                
                # Remove common garbage characters and artifacts
                # Remove tracking parameters (fbclid, utm_*, etc.)
                decoded = re.sub(r'[?&](fbclid|utm_\w+|redirect_uri|state|nonce)=[^&]*', '', decoded)
                
                # Remove multiple ? or & in a row
                decoded = re.sub(r'([?&])\1+', r'\1', decoded)
                
                # Remove trailing & or ?
                decoded = re.sub(r'[?&]$', '', decoded)
                
                # Clean up spaces and special chars
                decoded = decoded.strip()
                
                # Only keep URLs that start with http
                if decoded.startswith('http'):
                    cleaned_urls[lib_id] = decoded
                    if idx <= 20:  # Show first 20
                        print(f"[OK] {idx}. Clean: {decoded[:80]}")
                else:
                    cleaned_urls[lib_id] = f'INVALID: {raw_url[:50]}'
                    error_count += 1
                    
            except Exception as e:
                cleaned_urls[lib_id] = 'CLEAN_ERROR'
                error_count += 1
        
        # Save cleaned URLs
        print(f"\nSaving {len(cleaned_urls)} cleaned URLs to cta_map.txt...")
        with open('cta_map.txt', 'w') as f:
            for lib_id, clean_url in cleaned_urls.items():
                f.write(f"{lib_id}\t{clean_url}\n")
        
        # Count results
        valid = len([v for v in cleaned_urls.values() if v.startswith('http')])
        invalid = len(cleaned_urls) - valid
        
        print(f"\n=== URL Cleanup Results ===")
        print(f"Total URLs processed: {len(cleaned_urls)}")
        print(f"Valid URLs: {valid}")
        print(f"Invalid/Errors: {invalid}")
        print(f"\n[OK] Cleaned URLs saved to: cta_map.txt")
        print(f"[NEXT] Run script_3_match_urls.py to match against your target website")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        with open('cta_map.txt', 'w') as f:
            pass

if __name__ == '__main__':
    clean_urls()
