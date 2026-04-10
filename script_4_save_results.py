"""
Script 4: Save matched results to a summary file
Reads matched_library_ids.txt and creates a summary with CTA URLs
Saves to matched_results.txt in format: LIBRARY_ID	CTA_URL
"""

def save_matched_results():
    """Create summary of matched results"""
    
    # Check if matched_library_ids.txt exists
    try:
        with open('matched_library_ids.txt', 'r') as f:
            matched_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("WARNING: matched_library_ids.txt not found. No ads to process.")
        # Create empty results file
        with open('matched_results.txt', 'w') as f:
            f.write("LIBRARY_ID\tCTA_URL\n")
            f.write("=" * 100 + "\n")
        print("Created empty matched_results.txt")
        return
    
    if not matched_ids:
        print("WARNING: No matched IDs found. No ads were matched to your target URL.")
        # Create empty results file
        with open('matched_results.txt', 'w') as f:
            f.write("LIBRARY_ID\tCTA_URL\n")
            f.write("=" * 100 + "\n")
        print("Created empty matched_results.txt")
        return
    
    print(f"Loaded {len(matched_ids)} matched Library IDs")
    
    # Read CTA map
    cta_map = {}
    with open('cta_map.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line and '\t' in line:
                lib_id, cta_url = line.split('\t', 1)
                cta_map[lib_id] = cta_url
    
    # Create summary
    with open('matched_results.txt', 'w') as f:
        f.write("LIBRARY_ID\tCTA_URL\n")
        f.write("=" * 100 + "\n")
        
        for lib_id in matched_ids:
            cta_url = cta_map.get(lib_id, 'NOT_FOUND')
            f.write(f"{lib_id}\t{cta_url}\n")
    
    print(f"\nMatched results saved to: matched_results.txt")
    print(f"Total matched: {len(matched_ids)}")

if __name__ == '__main__':
    save_matched_results()
