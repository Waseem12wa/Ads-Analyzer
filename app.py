"""
Flask backend for Facebook Ads Library Download Tool
Takes user input and runs all 5 scripts
"""

from flask import Flask, render_template, request, jsonify
import subprocess
import sys
import os
import logging
from pathlib import Path

# Configure logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.before_request
def log_request():
    logger.info(f"[REQUEST] {request.method} {request.path}")
    logger.info(f"  Content-Type: {request.content_type}")
    logger.info(f"  Remote Addr: {request.remote_addr}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/run', methods=['POST'])
def run_extraction():
    """Run the extraction process with user-provided URLs"""
    try:
        data = request.get_json()
        facebook_url = data.get('facebook_url', '').strip()
        target_url = data.get('target_url', '').strip()
        
        # Validate URLs
        if not facebook_url:
            return jsonify({'success': False, 'error': 'Facebook URL is required'}), 400
        if not target_url:
            return jsonify({'success': False, 'error': 'Target URL is required'}), 400
        
        if 'facebook.com/ads/library' not in facebook_url:
            return jsonify({'success': False, 'error': 'Invalid Facebook Ads Library URL'}), 400
        
        logger.info(f"=== Processing Request ===")
        logger.info(f"Facebook URL: {facebook_url}")
        logger.info(f"Target URL: {target_url}")
        
        results = {
            'facebook_url': facebook_url,
            'target_url': target_url,
            'steps': {}
        }
        
        # Step 1: Extract Library IDs
        logger.info("[1/5] Extracting Library IDs...")
        result = subprocess.run(
            [sys.executable, 'script_1_extract_library_ids.py', facebook_url],
            capture_output=True, text=True, timeout=600
        )
        results['steps']['step1'] = {
            'name': 'Extract Library IDs',
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else ''
        }
        
        if result.returncode != 0:
            logger.error(f"ERROR in Step 1: {result.stderr}")
            return jsonify(results), 200
        
        # Step 2: Extract raw CTA URLs
        logger.info("[2/6] Extracting raw CTA URLs...")
        result = subprocess.run(
            [sys.executable, 'script_2_extract_cta_urls.py', facebook_url],
            capture_output=True, text=True, timeout=600
        )
        results['steps']['step2'] = {
            'name': 'Extract CTA URLs',
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else ''
        }
        
        if result.returncode != 0:
            logger.error(f"ERROR in Step 2: {result.stderr}")
            return jsonify(results), 200
        
        # Step 2b: Clean up garbage characters from URLs
        logger.info("[3/6] Cleaning up URL characters...")
        result = subprocess.run(
            [sys.executable, 'script_2b_clean_urls.py'],
            capture_output=True, text=True, timeout=60
        )
        results['steps']['step2b'] = {
            'name': 'Clean CTA URLs',
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else ''
        }
        
        if result.returncode != 0:
            logger.error(f"ERROR in Step 2b: {result.stderr}")
            return jsonify(results), 200
        
        # Step 3: Match URLs
        logger.info("[4/6] Matching URLs...")
        result = subprocess.run(
            [sys.executable, 'script_3_match_urls.py', target_url],
            capture_output=True, text=True, timeout=300
        )
        results['steps']['step3'] = {
            'name': 'Match URLs',
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else ''
        }
        
        if result.returncode != 0:
            logger.error(f"ERROR in Step 3: {result.stderr}")
            return jsonify(results), 200
        
        # Step 4: Save Results
        logger.info("[5/6] Saving Results...")
        result = subprocess.run(
            [sys.executable, 'script_4_save_results.py'],
            capture_output=True, text=True, timeout=60
        )
        results['steps']['step4'] = {
            'name': 'Save Results',
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else ''
        }
        
        if result.returncode != 0:
            logger.error(f"ERROR in Step 4: {result.stderr}")
            return jsonify(results), 200
        
        # Step 5: Download Media
        logger.info("[6/6] Downloading Media...")
        result = subprocess.run(
            [sys.executable, 'script_5_download_media.py', facebook_url],
            capture_output=True, text=True, timeout=1800
        )
        results['steps']['step5'] = {
            'name': 'Download Media',
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else ''
        }
        
        # Count downloaded files
        download_count = 0
        if Path('downloads').exists():
            download_count = len(list(Path('downloads').glob('AD_*')))
        
        results['success'] = all(step['success'] for step in results['steps'].values())
        results['downloaded_ads'] = download_count
        
        logger.info(f"=== Process Complete ===")
        logger.info(f"Success: {results['success']}")
        logger.info(f"Downloaded: {download_count} ads")
        
        return jsonify(results), 200
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Process timed out. Please try again.'
        }), 500
    except Exception as e:
        logger.exception(f"ERROR: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/downloads', methods=['GET'])
def list_downloads():
    """List downloaded ads"""
    downloads = []
    download_dir = Path('downloads')
    
    if download_dir.exists():
        for folder in sorted(download_dir.glob('AD_*')):
            if folder.is_dir():
                files = {
                    'images': list(folder.glob('image*')),
                    'videos': list(folder.glob('video*')),
                    'description': folder / 'description.txt'
                }
                
                downloads.append({
                    'library_id': folder.name.replace('AD_', ''),
                    'folder': str(folder),
                    'files': {
                        'images': [f.name for f in files['images']],
                        'videos': [f.name for f in files['videos']],
                        'description': 'description.txt' if files['description'].exists() else None
                    }
                })
    
    return jsonify({
        'count': len(downloads),
        'downloads': downloads
    }), 200

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)
