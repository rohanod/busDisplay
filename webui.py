#!/usr/bin/env python3
"""
Bus Display Web Configuration UI
A modern web interface for configuring the bus display application.
"""

import os
import sys
import json
import subprocess
import logging
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
import requests

# Setup logging first thing - before any other operations
LOG_FILE = os.path.expanduser("~/busdisplay/webui.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Create log file if it doesn't exist
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as f:
        f.write(f"Web UI log started at {datetime.now()}\n")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("webui")

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration paths
CONFIG_PATH = os.path.expanduser("~/.config/busdisplay/config.json")
CONFIG_DIR = os.path.dirname(CONFIG_PATH)
BACKUP_DIR = os.path.join(CONFIG_DIR, "backups")

# CSV file for stop search
ARRETS_CSV_URL = "https://raw.githubusercontent.com/rohanod/arrets/refs/heads/main/arrets.csv"
CACHE_DIR = os.path.expanduser("~/busdisplay/cache")
ARRETS_CACHE_FILE = os.path.join(CACHE_DIR, "arrets.csv")
CACHE_DURATION = 7 * 24 * 3600  # 1 week in seconds

# Default configuration
DEFAULT_CONFIG = {
    "stops": [],
    "max_departures": 8,
    "fetch_interval": 60,
    "max_minutes": 120,
    "show_clock": True,
    "show_weather": True,
    "http_timeout": 10,
    "cols": 8,
    "rows": 2,
    "cell_w": 140,
    "bar_h": 320,
    "bar_margin": 30,
    "bar_padding": 25,
    "card_padding": 15,
    "minute_size": 48,
    "now_size": 30,
    "stop_name_size": 48,
    "line_size": 40,
    "icon_size": 60,
    "border_radius": 16,
    "shadow_offset": 6,
    "grid_shrink": 0.7,
    "widget_size": 320,
    "widget_icon_size": 48,
    "grid_widget_width": 280,
    "grid_widget_height": 100,
    "grid_scale": 1.0
}

def ensure_config_dir():
    """Ensure configuration directory exists"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)

def load_config():
    """Load configuration from file"""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged_config = DEFAULT_CONFIG.copy()
                merged_config.update(config)
                return merged_config
        else:
            return DEFAULT_CONFIG.copy()
    except Exception as e:
        log.error(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file"""
    try:
        ensure_config_dir()
        
        # Create backup
        if os.path.exists(CONFIG_PATH):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUP_DIR, f"config_{timestamp}.json")
            with open(CONFIG_PATH, 'r') as src, open(backup_path, 'w') as dst:
                dst.write(src.read())
        
        # Save new config
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        log.error(f"Error saving config: {e}")
        return False

def get_service_status():
    """Get busdisplay service status"""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'busdisplay'], 
                              capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return "unknown"

def restart_service():
    """Restart busdisplay service"""
    try:
        result = subprocess.run(['sudo', 'systemctl', 'restart', 'busdisplay'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/config')
def get_config():
    """Get current configuration"""
    config = load_config()
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        config = request.json
        if save_config(config):
            return jsonify({"success": True, "message": "Configuration saved successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to save configuration"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/status')
def get_status():
    """Get system status"""
    return jsonify({
        "service_status": get_service_status(),
        "config_exists": os.path.exists(CONFIG_PATH),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/restart', methods=['POST'])
def restart():
    """Restart the busdisplay service"""
    if restart_service():
        return jsonify({"success": True, "message": "Service restarted successfully"})
    else:
        return jsonify({"success": False, "message": "Failed to restart service"}), 500

def ensure_cache_dir():
    """Ensure cache directory exists"""
    os.makedirs(CACHE_DIR, exist_ok=True)

def is_cache_valid():
    """Check if cached CSV file exists and is less than a week old"""
    if not os.path.exists(ARRETS_CACHE_FILE):
        return False
    
    file_age = time.time() - os.path.getmtime(ARRETS_CACHE_FILE)
    return file_age < CACHE_DURATION

def download_csv_file():
    """Download CSV file and save to cache"""
    ensure_cache_dir()
    
    log.info("Downloading fresh CSV data from GitHub")
    try:
        response = requests.get(ARRETS_CSV_URL, timeout=30)
        if response.status_code == 200:
            # Save raw CSV to cache file
            with open(ARRETS_CACHE_FILE, 'w', encoding='utf-8') as f:
                f.write(response.text)
            log.info(f"CSV file cached to {ARRETS_CACHE_FILE}")
            return True
        else:
            log.error(f"Failed to download CSV: {response.status_code}")
            return False
    except Exception as e:
        log.error(f"Error downloading CSV: {e}")
        return False

def load_stops_from_cache():
    """Load and parse stops data from cached CSV file"""
    if not os.path.exists(ARRETS_CACHE_FILE):
        log.warning("No cached CSV file found")
        return []
    
    try:
        import csv
        
        stops_data = []
        with open(ARRETS_CACHE_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            for row in reader:
                stop_name = row.get('Stop', '').strip()
                stop_code = row.get('Long Code Stop', '').strip()
                didoc_code = row.get('Didoc Code', '').strip()
                municipality = row.get('Municipality', '').strip()
                country = row.get('Country', '').strip()
                active = row.get('Actif', '').strip()
                
                # Only include active stops with Didoc codes
                if active == 'Y' and didoc_code:
                    stops_data.append({
                        'stop_name': stop_name,
                        'stop_code': stop_code,
                        'didoc_code': didoc_code,
                        'municipality': municipality,
                        'country': country,
                        'search_text': f"{stop_name} {stop_code} {municipality}".lower()
                    })
        
        log.info(f"Loaded {len(stops_data)} stops from cache")
        return stops_data
        
    except Exception as e:
        log.error(f"Error loading cached CSV: {e}")
        return []

def get_stops_data():
    """Get stops data, downloading if cache is invalid"""
    # Check if cache is valid
    if not is_cache_valid():
        log.info("Cache is invalid or missing, downloading fresh data")
        if not download_csv_file():
            log.warning("Failed to download fresh data, trying to use existing cache")
    
    # Load from cache
    return load_stops_from_cache()

@app.route('/api/search/stops')
def search_stops():
    """Search for stops using cached arrets.csv file"""
    query = request.args.get('q', '').strip().lower()
    log.info(f"Stop search request for: '{query}'")
    
    if not query:
        log.info("Empty query, returning empty results")
        return jsonify([])
    
    try:
        # Get stops data from file cache
        stops_data = get_stops_data()
        
        if not stops_data:
            log.warning("No stops data available")
            return jsonify([])
        
        # Search through cached data
        stops = []
        for stop_data in stops_data:
            if query in stop_data['search_text']:
                result = {
                    'id': stop_data['didoc_code'],
                    'name': f"{stop_data['stop_name']} ({stop_data['municipality']}, {stop_data['country']})",
                    'type': 'stop'
                }
                stops.append(result)
                
                # Limit to 10 results for performance
                if len(stops) >= 10:
                    break
        
        log.info(f"Found {len(stops)} stops matching query in {len(stops_data)} total stops")
        return jsonify(stops)
        
    except Exception as e:
        log.error(f"Stop search error: {e}")
        return jsonify([])

@app.route('/api/stops/<stop_id>/info')
def get_stop_info():
    """Get detailed information about a stop from cached CSV and Search.ch stationboard"""
    stop_id = request.view_args['stop_id']
    log.info(f"Getting stop info for: {stop_id}")
    
    try:
        # Get stop details from cached CSV
        stops_data = get_stops_data()
        stop_name = "Unknown"
        municipality = ""
        country = ""
        
        # Find stop in cached data
        for stop_data in stops_data:
            if stop_data['didoc_code'] == stop_id:
                stop_name = stop_data['stop_name']
                municipality = stop_data['municipality']
                country = stop_data['country']
                break
        
        # Then get line information from Search.ch stationboard
        lines = []
        terminals = {}
        
        try:
            stationboard_url = "https://search.ch/timetable/api/stationboard.fr.json"
            sb_response = requests.get(stationboard_url, params={
                'stop': stop_id,
                'limit': 20,
                'transportation_types': 'bus,tram'
            }, timeout=10)
            
            if sb_response.status_code == 200:
                data = sb_response.json()
                lines_set = set()
                
                for conn in data.get('connections', []):
                    line = conn.get('*L') or conn.get('line')
                    terminal = conn.get('terminal', {})
                    terminal_id = terminal.get('id')
                    terminal_name = terminal.get('name', 'Unknown')
                    
                    if line:
                        lines_set.add(line)
                        if line not in terminals:
                            terminals[line] = []
                        if terminal_id and terminal_name not in [t['name'] for t in terminals[line]]:
                            terminals[line].append({
                                'id': terminal_id,
                                'name': terminal_name
                            })
                
                lines = sorted(list(lines_set))
            else:
                log.warning(f"Stationboard API returned status {sb_response.status_code}")
        except Exception as e:
            log.warning(f"Could not get line info from stationboard: {e}")
            # Provide some default lines if stationboard fails
            lines = ["1", "2", "3"]  # Generic fallback
        
        full_name = f"{stop_name} ({municipality}, {country})" if municipality else stop_name
        
        return jsonify({
            'id': stop_id,
            'name': full_name,
            'lines': lines,
            'terminals': terminals
        })
        
    except Exception as e:
        log.error(f"Stop info error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backups')
def list_backups():
    """List available configuration backups"""
    try:
        backups = []
        if os.path.exists(BACKUP_DIR):
            for filename in sorted(os.listdir(BACKUP_DIR), reverse=True):
                if filename.startswith('config_') and filename.endswith('.json'):
                    filepath = os.path.join(BACKUP_DIR, filename)
                    stat = os.stat(filepath)
                    backups.append({
                        'filename': filename,
                        'timestamp': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'size': stat.st_size
                    })
        return jsonify(backups)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/backups/<filename>')
def download_backup(filename):
    """Download a configuration backup"""
    try:
        return send_from_directory(BACKUP_DIR, filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    log.info("Starting Bus Display Web UI...")
    log.info("Access the interface at: http://localhost:5000")
    
    ensure_config_dir()
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        log.error(f"Failed to start web UI: {e}")
        sys.exit(1)