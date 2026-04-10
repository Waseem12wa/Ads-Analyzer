from flask import Flask, render_template, request, jsonify, send_file
from ad_analyzer import FacebookAdAnalyzer
import os
from pathlib import Path

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

analyzer = FacebookAdAnalyzer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/process-ad', methods=['POST'])
def process_ad():
    """Process Facebook ad and compare URLs"""
    try:
        data = request.get_json()
        facebook_url = data.get('facebook_url', '').strip()
        target_url = data.get('target_url', '').strip()
        
        print(f"\n=== Processing Request ===")
        print(f"Facebook URL: {facebook_url}")
        print(f"Target URL: {target_url}")
        
        if not facebook_url or not target_url:
            return jsonify({
                "success": False,
                "error": "Both URLs are required"
            }), 400
        
        # Validate URLs
        if 'facebook.com' not in facebook_url:
            return jsonify({
                "success": False,
                "error": "Please provide a valid Facebook Ads Library URL"
            }), 400
        
        if not target_url.startswith(('http://', 'https://')):
            target_url = 'https://' + target_url
        
        # Process the ad
        print("\nStarting ad extraction...")
        result = analyzer.process_ad(facebook_url, target_url)
        
        print(f"\nResult: {result}")
        return jsonify(result)
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Error processing ad: {str(e)}"
        }), 500

@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """Download processed media or description from any nested folder"""
    try:
        # Security: prevent directory traversal attacks - normalize path
        # Remove any .. or suspicious patterns
        filepath = Path(app.config['UPLOAD_FOLDER']) / filename
        
        # Additional safety check - ensure the resolved path is within uploads folder
        try:
            filepath = filepath.resolve()
            uploads_dir = Path(app.config['UPLOAD_FOLDER']).resolve()
            
            # Check if file is within the uploads directory
            if not str(filepath).startswith(str(uploads_dir)):
                return jsonify({"error": "Invalid file path"}), 403
        except Exception:
            return jsonify({"error": "Invalid file path"}), 403
        
        if not filepath.exists() or not filepath.is_file():
            return jsonify({"error": "File not found"}), 404
        
        return send_file(filepath, as_attachment=True)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/downloads', methods=['GET'])
def list_downloads():
    """List all downloads with folder structure"""
    try:
        downloads_dir = Path(app.config['UPLOAD_FOLDER'])
        if not downloads_dir.exists():
            return jsonify({"structure": {}, "files": []})
        
        # Build folder structure
        structure = _build_folder_structure(downloads_dir)
        
        # List all files recursively
        all_files = []
        for root, dirs, files in os.walk(downloads_dir):
            for file in files:
                filepath = Path(root) / file
                relative_path = filepath.relative_to(downloads_dir)
                all_files.append(str(relative_path))
        
        return jsonify({
            "structure": structure,
            "files": all_files,
            "total_files": len(all_files)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _build_folder_structure(path, max_depth=3, current_depth=0):
    """Recursively build folder structure for display"""
    if current_depth >= max_depth:
        return {}
    
    structure = {}
    try:
        for item in Path(path).iterdir():
            if item.is_dir():
                file_count = len(list(item.glob('**/*')))
                structure[item.name] = {
                    "type": "folder",
                    "files": file_count,
                    "contents": _build_folder_structure(item, max_depth, current_depth + 1)
                }
            else:
                size = item.stat().st_size
                structure[item.name] = {
                    "type": "file",
                    "size": size,
                    "size_kb": f"{size / 1024:.2f} KB"
                }
    except Exception as e:
        pass
    
    return structure

@app.route('/api/clear-downloads', methods=['POST'])
def clear_downloads():
    """Clear all downloaded files"""
    try:
        import shutil
        downloads_dir = Path(app.config['UPLOAD_FOLDER'])
        
        if downloads_dir.exists():
            shutil.rmtree(downloads_dir)
            downloads_dir.mkdir()
        
        return jsonify({"success": True, "message": "Downloads cleared"})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Ensure downloads directory exists
    Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
    
    # Run app
    app.run(debug=True, host='127.0.0.1', port=5000)
