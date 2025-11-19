import os
import json
from datetime import datetime

from .constants import HISTORY_FILE, PSVMP_DIR
from .helpers import logger

def log_to_history(url, media_type, status="completed", error_message=None):
    try:
        os.makedirs(PSVMP_DIR, exist_ok=True)
        
        # Convert exception objects to strings for JSON serialization
        if error_message and isinstance(error_message, Exception):
            error_message = str(error_message)
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'url': url,
            'media_type': media_type,
            'status': status,
            'error': error_message
        }
        
        with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        logger.info(f"Logged to history: {url} ({media_type}) - {status}")
        
    except Exception as e:
        logger.error(f"Failed to write to history file: {e}")

def read_history(limit=None):
    try:
        if not os.path.exists(HISTORY_FILE):
            return []
        
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        entries = []
        for line in lines:
            try:
                entries.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
        
        entries.reverse()
        
        if limit:
            entries = entries[:limit]
        
        return entries
        
    except Exception as e:
        logger.error(f"Failed to read history file: {e}")
        return []

def clear_history():
    try:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
            logger.info("History file cleared")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to clear history file: {e}")
        return False

def show_history(limit=10):
    entries = read_history(limit)
    
    if not entries:
        print("No history entries found.")
        return
    
    print(f"\nRecent History (last {len(entries)} entries):")
    print("=" * 80)
    
    for i, entry in enumerate(entries, 1):
        timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        status_icon = "✓" if entry['status'] == 'completed' else "✗"
        
        print(f"{i}. [{timestamp}] {status_icon} {entry['media_type'].upper()}")
        print(f"   URL: {entry['url']}")
        if entry['status'] != 'completed' and entry.get('error'):
            print(f"   Error: {entry['error']}")
        print()