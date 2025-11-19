import os
import sys
import shutil
import subprocess
import re
import glob
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

from .constants import LOG_FOLDER, TEMP_FOLDER, CONVERTED_FOLDER

# Setup logging
def setup_logging():
    log_filename = "psvmp.log"
    log_filepath = os.path.join(LOG_FOLDER, log_filename)
    
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    file_handler = RotatingFileHandler(
        log_filepath,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,          # keep 3 backup files
        encoding='utf-8'
    )
    
    # Config logging format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Config root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler],
        force=True
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info(f"PS Vita Media Processor started")
    logger.info(f"Log file: {log_filepath}")
    logger.info("=" * 50)
    
    return logger

logger = setup_logging()

def sanitize_filename(filename):
    if not filename:
        return "unknown"
    
    # Replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # Limit length to avoid filesystem issues
    if len(filename) > 100:
        # Try to preserve the extension
        name, ext = os.path.splitext(filename)
        filename = name[:100-len(ext)] + ext
    
    return filename.strip()

def create_folders():
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    os.makedirs(CONVERTED_FOLDER, exist_ok=True)

def cleanup_temp_files(folder_path):
    patterns = ['*.part', '*.ytdl', '*.part-*', '*.temp']
    for pattern in patterns:
        files = glob.glob(os.path.join(folder_path, pattern))
        for file in files:
            try:
                os.remove(file)
                logger.info(f"Cleaned up: {os.path.basename(file)}")
            except Exception as e:
                logger.warning(f"Failed to clean up {file}: {e}")

def check_dependencies():
    missing_tools = []
    
    # Check for megatools (either megatools-dl or megatools)
    if not shutil.which('megatools-dl') and not shutil.which('megatools'):
        missing_tools.append('megatools')
    
    # Check for yt-dlp
    if not shutil.which('yt-dlp'):
        missing_tools.append('yt-dlp')
    
    # Check for ffmpeg and ffprobe
    for tool in ['ffmpeg', 'ffprobe']:
        if not shutil.which(tool):
            missing_tools.append(tool)
    
    if missing_tools:
        logger.error(f"Missing required tools: {', '.join(missing_tools)}")
        print(f"Error: Missing required tools: {', '.join(missing_tools)}")
        print("\nInstall instructions:")
        print("- megatools: https://megatools.megous.com/ or package manager")
        print("- yt-dlp: pip install yt-dlp")
        print("- ffmpeg: https://ffmpeg.org/ or package manager")
        return False
    return True

def detect_url_type(url):
    url_lower = url.lower()
    
    if 'mega.nz' in url_lower or 'mega.co.nz' in url_lower:
        return 'mega'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'soundcloud.com' in url_lower:
        return 'soundcloud'
    else:
        return 'other'

def verify_media_file(file_path, media_type='video'):
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_format', '-show_streams', file_path]
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Verified {media_type} file: {os.path.basename(file_path)}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"File verification failed for {file_path}: {e}")
        return False
    
def check_logs_exist():
    if os.path.exists(LOG_FOLDER):
        log_files = [f for f in os.listdir(LOG_FOLDER) if f.endswith('.log')]
        if log_files:
            print(f"Log files found in {LOG_FOLDER}:")
            for log_file in sorted(log_files):
                file_path = os.path.join(LOG_FOLDER, log_file)
                file_size = os.path.getsize(file_path)
                print(f"  - {log_file} ({file_size} bytes)")
            return True
        else:
            print(f"No log files found in {LOG_FOLDER}")
            return False
    else:
        print(f"Log folder does not exist: {LOG_FOLDER}")
        return False