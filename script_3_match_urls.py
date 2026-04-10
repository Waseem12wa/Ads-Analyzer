"""
Script 3: Match target URL with CTA URLs
Reads cta_map.txt and compares each CTA URL with the target URL
Saves matched Library IDs to matched_library_ids.txt
"""

from urllib.parse import urlparse
import sys

def normalize_url(url):
    """Normalize URL for comparison"""
    if not url or url == 'NOT_FOUND':
        return None
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Parse URL
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '').lower()
    path = parsed.path.rstrip('/').lower()
    
    return domain, path

def match_urls(target_url):
    """Match target URL against CTA URLs"""
    
    # Read CTA map
    try:
        with open('cta_map.txt', 'r') as f:
            cta_map = {}
            for line in f:
                line = line.strip()
                if line and '\t' in line:
                    lib_id, cta_url = line.split('\t', 1)
                    cta_map[lib_id] = cta_url
    except FileNotFoundError:
        print("ERROR: cta_map.txt not found. Run script_2 first.")
        # Create empty matched file
        with open('matched_library_ids.txt', 'w') as f:
            pass
        return []
    
    print(f"Loaded {len(cta_map)} CTA mappings")
    
    # Handle empty CTA map
    if len(cta_map) == 0:
        print("WARNING: No CTA mappings found. Creating empty matched_library_ids.txt...")
        with open('matched_library_ids.txt', 'w') as f:
            pass
        return []
    
    print(f"Target URL: {target_url}\n")
    
    # Normalize target URL
    target_domain, target_path = normalize_url(target_url)
    print(f"Target domain: {target_domain}")
    print(f"Target path: {target_path}\n")
    
    # Match all CTA URLs or search queries
    matched = []
    not_found = []
    no_match = []
    
    for lib_id, cta_url in cta_map.items():
        if cta_url == 'NOT_FOUND':
            not_found.append(lib_id)
            continue
        
        # Check if this is a URL or a search query
        is_url = cta_url.startswith(('http://', 'https://', 'www.'))
        
        if is_url:
            # Try URL matching
            result = normalize_url(cta_url)
            if not result:
                no_match.append(lib_id)
                continue
            
            cta_domain, cta_path = result
            
            # Match if domain is same
            if cta_domain == target_domain:
                matched.append(lib_id)
                print(f"[MATCH] {lib_id} -> {cta_url}")
            else:
                no_match.append(lib_id)
        else:
            # Try text matching (for search queries like "rejuveen")
            target_text = target_url.lower().replace('://', '').replace('www.', '').replace('.com', '')
            cta_text = cta_url.lower()
            
            # Check if search query appears in target URL
            if cta_text in target_text or target_text.endswith(cta_text) or target_text.startswith(cta_text):
                matched.append(lib_id)
                print(f"[MATCH] {lib_id} -> Search query '{cta_url}' matches target '{target_url}'")
            else:
                no_match.append(lib_id)
    
    # Save results (always create file)
    with open('matched_library_ids.txt', 'w') as f:
        for lib_id in matched:
            f.write(lib_id + '\n')
    
    print(f"\n=== Results ===")
    print(f"Matched: {len(matched)}")
    print(f"No match: {len(no_match)}")
    print(f"Not found: {len(not_found)}")
    print(f"\nMatched Library IDs saved to: matched_library_ids.txt")
    
    if len(matched) == 0:
        print("WARNING: No ads matched your target URL. Check that the URLs are correct.")
    
    return matched

if __name__ == '__main__':
    target_url = sys.argv[1] if len(sys.argv) > 1 else 'https://rejuveen.com/pages/sp-osteva-lumbar'
    match_urls(target_url)
