import os
import subprocess
import time
import json
import shutil
from .helpers import (
    logger, create_folders, cleanup_temp_files,
    sanitize_filename, verify_media_file, detect_url_type
)
from .conversion import embed_metadata_with_ffmpeg
from .constants import TEMP_FOLDER

def get_metadata_from_url(url):
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-warnings',
            '--no-playlist',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
        if result.returncode == 0:
            metadata = json.loads(result.stdout)
            
            title = sanitize_filename(metadata.get('title', 'Unknown Title'))
            artist = sanitize_filename(metadata.get('uploader', metadata.get('channel', 'Unknown Artist')))
            album = sanitize_filename(metadata.get('album', metadata.get('playlist_title', 'Unknown Album')))
            
            logger.info(f"Extracted metadata: {title} by {artist}")
            
            return {
                'title': title,
                'artist': artist,
                'album': album,
                'year': str(metadata.get('upload_date', '')[:4]) if metadata.get('upload_date') else '',
                'genre': metadata.get('genre', ''),
                'duration': metadata.get('duration', 0)
            }
    except Exception as e:
        logger.warning(f"Could not extract metadata: {e}")
        print(f"Could not extract metadata: {e}")
    
    return None

def download_from_mega(url):
    create_folders()
    logger.info(f"Downloading from Mega: {url}")
    print(f"Downloading from Mega: {url}")
    
    try:
        # Try megatools-dl first, then fall back to megatools
        megatool_cmd = 'megatools-dl' if shutil.which('megatools-dl') else 'megatools'
        
        cmd = [
            megatool_cmd,
            '--path', TEMP_FOLDER,
            url
        ]
        
        logger.info("Running megatools download...")
        print("Running megatools download...")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        for line in process.stdout:
            if line.strip():
                print(line.strip(), flush=True)
        
        process.wait()
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
        
        # Find downloaded file
        downloaded_files = [f for f in os.listdir(TEMP_FOLDER) 
                           if os.path.isfile(os.path.join(TEMP_FOLDER, f)) and not f.endswith(('.part', '.ytdl', '.temp'))]
        if not downloaded_files:
            raise Exception("Download completed but no file found")
        
        file_path = os.path.join(TEMP_FOLDER, max(
            downloaded_files,
            key=lambda x: os.path.getmtime(os.path.join(TEMP_FOLDER, x))
        ))
        
        logger.info(f"Download completed: {file_path}")
        print(f"Download completed: {file_path}")
        return file_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Mega download failed: {e}")
        raise Exception(f"Mega download failed")
    except Exception as e:
        logger.error(f"Mega download error: {str(e)}")
        raise Exception(f"Mega download error: {str(e)}")

def download_with_ytdlp(url, media_type='video'):
    create_folders()
    cleanup_temp_files(TEMP_FOLDER)
    
    logger.info(f"Downloading with yt-dlp: {url}")
    print(f"Downloading with yt-dlp: {url}")
    
    metadata = None
    if media_type == 'music':
        logger.info("Extracting metadata...")
        print("Extracting metadata...")
        metadata = get_metadata_from_url(url)
        if metadata:
            logger.info(f"Found: {metadata['title']} by {metadata['artist']}")
            print(f"Found: {metadata['title']} by {metadata['artist']}")
    
    try:
        # Generate a safe filename template with ASCII fallback
        safe_template = os.path.join(TEMP_FOLDER, '%(title).80s.%(ext)s')
        
        if media_type == 'music':
            url_type = detect_url_type(url)
            
            if url_type == 'soundcloud':
                cmd = [
                    'yt-dlp',
                    '--extract-audio',
                    '--audio-format', 'mp3',
                    '--audio-quality', '0',  # Best quality
                    '--no-warnings',
                    '--no-playlist',
                    '--ignore-errors',
                    '--retries', '3',
                    '--fragment-retries', '3',
                    '--embed-metadata',  # Embed metadata in the file
                    '--add-metadata',    # Add metadata
                    '--restrict-filenames',  # Use ASCII-safe filenames
                    '-o', safe_template,
                    url
                ]
            else:
                # For other audio sources
                cmd = [
                    'yt-dlp',
                    '-f', 'bestaudio/best',
                    '--extract-audio',
                    '--audio-format', 'mp3',
                    '--audio-quality', '0',
                    '--no-warnings',
                    '--no-playlist',
                    '--ignore-errors',
                    '--retries', '3',
                    '--embed-metadata',  # Embed metadata in the file
                    '--add-metadata',    # Add metadata
                    '--restrict-filenames',  # Use ASCII-safe filenames
                    '-o', safe_template,
                    url
                ]
        else:
            # For video
            cmd = [
                'yt-dlp',
                '-f', 'best[height<=720]/best',  # Limit to 720p for Vita compatibility
                '--no-warnings',
                '--no-playlist',
                '--ignore-errors',
                '--retries', '3',
                '--restrict-filenames',  # Use ASCII-safe filenames
                '-o', safe_template,
                url
            ]
        
        logger.info("Running yt-dlp download...")
        print("Running yt-dlp download...")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Show real-time download progress
        for line in process.stdout:
            if line.strip():  # Only print non-empty lines
                if '[download]' in line or 'ERROR:' in line or 'WARNING:' in line:
                    print(line.strip(), flush=True)
        
        process.wait()
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
        
        # Wait a moment for file system to sync
        time.sleep(2)
        
        # Clean up any partial files first
        cleanup_temp_files(TEMP_FOLDER)
        
        # Find downloaded file
        downloaded_files = []
        for f in os.listdir(TEMP_FOLDER):
            full_path = os.path.join(TEMP_FOLDER, f)
            if (os.path.isfile(full_path) and 
                not f.endswith(('.part', '.ytdl', '.temp')) and
                not f.startswith('.') and
                os.path.getsize(full_path) > 1024):  # File must be at least 1KB
                downloaded_files.append(f)
        
        if not downloaded_files:
            raise Exception("Download completed but no valid file found")
        
        # Get the most recently created file
        file_path = os.path.join(TEMP_FOLDER, max(
            downloaded_files,
            key=lambda x: os.path.getmtime(os.path.join(TEMP_FOLDER, x))
        ))
        
        if not verify_media_file(file_path, media_type if media_type == 'video' else 'audio'):
            raise Exception("Downloaded file appears to be corrupted")
        
        if media_type == 'music' and metadata:
            file_path = embed_metadata_with_ffmpeg(file_path, metadata)
        
        logger.info(f"Download completed: {file_path}")
        print(f"Download completed: {file_path}")
        return file_path
        
    except subprocess.TimeoutExpired:
        cleanup_temp_files(TEMP_FOLDER)
        logger.error("Download timed out (5 minutes)")
        raise Exception("Download timed out (5 minutes)")
    except subprocess.CalledProcessError as e:
        cleanup_temp_files(TEMP_FOLDER)
        logger.error(f"yt-dlp download failed with code {e.returncode}")
        raise Exception(f"yt-dlp download failed with code {e.returncode}")
    except Exception as e:
        cleanup_temp_files(TEMP_FOLDER)
        logger.error(f"yt-dlp download error: {str(e)}")
        raise Exception(f"yt-dlp download error: {str(e)}")

def download_media(url, media_type='video'):
    url_type = detect_url_type(url)
    logger.info(f"Downloading {media_type} from {url_type}: {url}")
    
    if url_type == 'mega':
        return download_from_mega(url)
    else:
        return download_with_ytdlp(url, media_type)