#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# https://github.com/R0salman

# Set UTF-8 encoding for Windows
import sys
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logo = """
 ######   #####  #     # #     # ######  
 #     # #     # #     # ##   ## #     # 
 #     # #       #     # # # # # #     # 
 ######   #####  #     # #  #  # ######  
 #             #  #   #  #     # #       
 #       #     #   # #   #     # #       
 #        #####     #    #     # #       
"""

import os
import sys
import argparse
import subprocess
import ftplib
from tqdm import tqdm
import time
import re
import hashlib
import shutil
from urllib.parse import urlparse
import glob
import json
import unicodedata

# Configuration
DEFAULT_VITA_IP = "192.168.1.7"
DEFAULT_VITA_PORT = 1337
VITA_VIDEO_PATH = "ux0:/video/shows/"
VITA_MUSIC_PATH = "ux0:/music/"
MAX_RETRIES = 5
RETRY_DELAY = 3  # seconds
TEMP_FOLDER = "psvita_temp"
CONVERTED_FOLDER = "psvita_converted"

def sanitize_filename(filename):
    """Sanitize filename for filesystem compatibility while preserving Unicode"""
    if not filename:
        return "unknown"
    
    # Replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)  # Remove control characters
    
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
    """Clean up incomplete download files"""
    patterns = ['*.part', '*.ytdl', '*.part-*', '*.temp']
    for pattern in patterns:
        files = glob.glob(os.path.join(folder_path, pattern))
        for file in files:
            try:
                os.remove(file)
                print(f"Cleaned up: {os.path.basename(file)}")
            except:
                pass

def check_dependencies():
    """Check if required tools are installed"""
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
        print(f"Error: Missing required tools: {', '.join(missing_tools)}")
        print("\nInstall instructions:")
        print("- megatools: https://megatools.megous.com/ or package manager")
        print("- yt-dlp: pip install yt-dlp")
        print("- ffmpeg: https://ffmpeg.org/ or package manager")
        return False
    return True

def detect_url_type(url):
    """Detect if URL is from Mega, YouTube, SoundCloud, or other"""
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
    """Verify the media file is valid before conversion"""
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_format', '-show_streams', file_path]
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

def download_from_mega(url):
    """Download from Mega.nz using megatools"""
    create_folders()
    print(f"Downloading from Mega: {url}")
    
    try:
        # Try megatools-dl first, then fall back to megatools
        megatool_cmd = 'megatools-dl' if shutil.which('megatools-dl') else 'megatools'
        
        cmd = [
            megatool_cmd,
            '--path', TEMP_FOLDER,
            url
        ]
        
        print("Running megatools download...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Find downloaded file
        downloaded_files = [f for f in os.listdir(TEMP_FOLDER) 
                           if os.path.isfile(os.path.join(TEMP_FOLDER, f)) and not f.endswith(('.part', '.ytdl', '.temp'))]
        if not downloaded_files:
            raise Exception("Download completed but no file found")
        
        file_path = os.path.join(TEMP_FOLDER, max(
            downloaded_files,
            key=lambda x: os.path.getmtime(os.path.join(TEMP_FOLDER, x))
        ))
        
        print(f"Downloaded: {file_path}")
        return file_path
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Mega download failed: {e.stderr}")
    except Exception as e:
        raise Exception(f"Mega download error: {str(e)}")

def get_metadata_from_url(url):
    """Extract metadata from URL using yt-dlp without downloading"""
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
            
            # Sanitize metadata for filesystem compatibility
            title = sanitize_filename(metadata.get('title', 'Unknown Title'))
            artist = sanitize_filename(metadata.get('uploader', metadata.get('channel', 'Unknown Artist')))
            album = sanitize_filename(metadata.get('album', metadata.get('playlist_title', 'Unknown Album')))
            
            return {
                'title': title,
                'artist': artist,
                'album': album,
                'year': str(metadata.get('upload_date', '')[:4]) if metadata.get('upload_date') else '',
                'genre': metadata.get('genre', ''),
                'duration': metadata.get('duration', 0)
            }
    except Exception as e:
        print(f"Could not extract metadata: {e}")
    
    return None

def download_with_ytdlp(url, media_type='video'):
    """Download from YouTube, SoundCloud, or other sites using yt-dlp"""
    create_folders()
    cleanup_temp_files(TEMP_FOLDER)  # Clean up any previous incomplete downloads
    
    print(f"Downloading with yt-dlp: {url}")
    
    # First, get metadata for music files
    metadata = None
    if media_type == 'music':
        print("Extracting metadata...")
        metadata = get_metadata_from_url(url)
        if metadata:
            print(f"Found: {metadata['title']} by {metadata['artist']}")
    
    try:
        # Generate a safe filename template with ASCII fallback
        safe_template = os.path.join(TEMP_FOLDER, '%(title).80s.%(ext)s')
        
        if media_type == 'music':
            # For music, use a more robust approach for SoundCloud
            url_type = detect_url_type(url)
            
            if url_type == 'soundcloud':
                # Special handling for SoundCloud
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
            # For video, download best quality
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
        
        print("Running yt-dlp download...")
        print(f"Command: {' '.join(cmd[:3])}...")  # Show partial command for debugging
        
        # Run the download with proper error handling
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode != 0:
            print(f"yt-dlp stderr: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd)
        
        # Wait a moment for file system to sync
        time.sleep(1)
        
        # Clean up any partial files first
        cleanup_temp_files(TEMP_FOLDER)
        
        # Find downloaded file (exclude temporary files)
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
        
        # Verify the file is not corrupted
        if not verify_media_file(file_path, media_type if media_type == 'video' else 'audio'):
            raise Exception("Downloaded file appears to be corrupted")
        
        # For music files, ensure metadata is properly embedded
        if media_type == 'music' and metadata:
            file_path = embed_metadata_with_ffmpeg(file_path, metadata)
        
        print(f"Downloaded: {file_path}")
        return file_path
        
    except subprocess.TimeoutExpired:
        cleanup_temp_files(TEMP_FOLDER)
        raise Exception("Download timed out (5 minutes)")
    except subprocess.CalledProcessError as e:
        cleanup_temp_files(TEMP_FOLDER)
        raise Exception(f"yt-dlp download failed with code {e.returncode}: {e.stderr}")
    except Exception as e:
        cleanup_temp_files(TEMP_FOLDER)
        raise Exception(f"yt-dlp download error: {str(e)}")

def download_media(url, media_type='video'):
    """Main download function that chooses the appropriate method"""
    url_type = detect_url_type(url)
    
    if url_type == 'mega':
        return download_from_mega(url)
    else:
        # Use yt-dlp for YouTube, SoundCloud, and other sites
        return download_with_ytdlp(url, media_type)

class VitaFTP:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.timeout = 30

    def transfer(self, local_path, remote_path, progress_callback=None):
        file_size = os.path.getsize(local_path)
        filename = os.path.basename(local_path)
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if progress_callback:
                    progress_callback(f"Attempt {attempt}/{MAX_RETRIES}: Connecting to {self.ip}:{self.port}...")
                
                with ftplib.FTP(timeout=self.timeout) as ftp:
                    ftp.connect(self.ip, self.port)
                    
                    # Navigate to the appropriate directory based on media type
                    if '/music/' in remote_path:
                        # Music path
                        try:
                            ftp.cwd('ux0:')
                            ftp.cwd('music')
                        except ftplib.error_perm:
                            if progress_callback:
                                progress_callback("Music directory not found, creating it...")
                            try:
                                ftp.cwd('ux0:')
                                ftp.mkd('music')
                                ftp.cwd('music')
                            except ftplib.error_perm as e:
                                if progress_callback:
                                    progress_callback(f"Directory creation error: {str(e)}")
                                pass
                    else:
                        # Video path
                        try:
                            ftp.cwd('ux0:')
                            ftp.cwd('video')
                            ftp.cwd('shows')
                        except ftplib.error_perm:
                            if progress_callback:
                                progress_callback("Shows directory not found, creating it...")
                            try:
                                ftp.cwd('ux0:')
                                ftp.cwd('video')
                                ftp.mkd('shows')
                                ftp.cwd('shows')
                            except ftplib.error_perm as e:
                                if progress_callback:
                                    progress_callback(f"Directory creation error: {str(e)}")
                                pass
                    
                    if progress_callback:
                        progress_callback(f"Transferring {filename}...")
                    
                    with open(local_path, 'rb') as f:
                        with tqdm(total=file_size, unit='B', unit_scale=True, 
                                 desc="Transfer Progress", leave=False) as pbar:
                            def callback(data):
                                pbar.update(len(data))
                            
                            remote_filename = os.path.basename(remote_path)
                            ftp.storbinary(f"STOR {remote_filename}", f, callback=callback)
                    
                    if progress_callback:
                        progress_callback("Transfer completed successfully")
                    return True
                    
            except Exception as e:
                if attempt < MAX_RETRIES:
                    if progress_callback:
                        progress_callback(f"Connection failed: {str(e)}. Retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                else:
                    raise Exception(f"Failed after {MAX_RETRIES} attempts: {str(e)}")
        return False

def convert_for_vita_video(input_file, output_file):
    """Convert video for PS Vita compatibility"""
    print("Converting video for PS Vita...")
    
    if not verify_media_file(input_file, 'video'):
        raise Exception("Input video file is corrupted and cannot be converted")
    
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-c:v', 'libx264',
        '-profile:v', 'baseline',
        '-level:v', '3.1',
        '-vf', 'scale=960:544:force_original_aspect_ratio=decrease,pad=960:544:-1:-1:black',
        '-pix_fmt', 'yuv420p',
        '-b:v', '1500k',
        '-maxrate', '2000k',
        '-bufsize', '4000k',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-ar', '44100',
        '-movflags', '+faststart',
        '-y',
        output_file
    ]
    
    return run_ffmpeg_conversion(cmd, input_file, output_file, 'video')

def embed_metadata_with_ffmpeg(input_file, metadata):
    """Embed metadata into audio file using FFmpeg"""
    if not metadata:
        return input_file
    
    print("Embedding metadata into audio file...")
    
    # Create output file with _tagged suffix
    base_name = os.path.splitext(input_file)[0]
    output_file = f"{base_name}_tagged.mp3"
    
    # Build FFmpeg command with metadata
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-c', 'copy',  # Copy streams without re-encoding
        '-y'  # Overwrite output file
    ]
    
    # Add metadata tags
    if metadata.get('title'):
        cmd.extend(['-metadata', f'title={metadata["title"]}'])
    if metadata.get('artist'):
        cmd.extend(['-metadata', f'artist={metadata["artist"]}'])
    if metadata.get('album'):
        cmd.extend(['-metadata', f'album={metadata["album"]}'])
    if metadata.get('year'):
        cmd.extend(['-metadata', f'date={metadata["year"]}'])
    if metadata.get('genre'):
        cmd.extend(['-metadata', f'genre={metadata["genre"]}'])
    
    cmd.append(output_file)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode == 0:
            # Remove original file and rename tagged file
            os.remove(input_file)
            os.rename(output_file, input_file)
            print("Metadata embedded successfully")
        else:
            print(f"Warning: Could not embed metadata: {result.stderr}")
            # Clean up failed output file
            if os.path.exists(output_file):
                os.remove(output_file)
    except Exception as e:
        print(f"Warning: Metadata embedding failed: {e}")
        # Clean up failed output file
        if os.path.exists(output_file):
            os.remove(output_file)
    
    return input_file

def convert_for_vita_music(input_file, output_file):
    """Convert audio to MP3 for PS Vita with proper metadata preservation"""
    print("Converting audio to MP3 for PS Vita...")
    
    if not verify_media_file(input_file, 'audio'):
        raise Exception("Input audio file is corrupted and cannot be converted")
    
    # First, extract existing metadata from the file
    existing_metadata = extract_metadata_from_file(input_file)
    
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-c:a', 'mp3',
        '-b:a', '320k',  # High quality MP3
        '-ar', '44100',
        '-map_metadata', '0',  # Copy all metadata from input
        '-id3v2_version', '3',  # Use ID3v2.3 for better compatibility
        '-y',
        output_file
    ]
    
    # Add any additional metadata if we have it
    if existing_metadata:
        if existing_metadata.get('title'):
            cmd.extend(['-metadata', f'title={existing_metadata["title"]}'])
        if existing_metadata.get('artist'):
            cmd.extend(['-metadata', f'artist={existing_metadata["artist"]}'])
        if existing_metadata.get('album'):
            cmd.extend(['-metadata', f'album={existing_metadata["album"]}'])
        if existing_metadata.get('date'):
            cmd.extend(['-metadata', f'date={existing_metadata["date"]}'])
        if existing_metadata.get('genre'):
            cmd.extend(['-metadata', f'genre={existing_metadata["genre"]}'])
    
    return run_ffmpeg_conversion(cmd, input_file, output_file, 'audio')

def extract_metadata_from_file(file_path):
    """Extract metadata from an audio file using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            format_info = data.get('format', {})
            tags = format_info.get('tags', {})
            
            # Normalize tag keys (they can be in different cases)
            normalized_tags = {}
            for key, value in tags.items():
                normalized_tags[key.lower()] = value
            
            return {
                'title': normalized_tags.get('title', ''),
                'artist': normalized_tags.get('artist', ''),
                'album': normalized_tags.get('album', ''),
                'date': normalized_tags.get('date', ''),
                'genre': normalized_tags.get('genre', '')
            }
    except Exception as e:
        print(f"Could not extract metadata from file: {e}")
    
    return None

def run_ffmpeg_conversion(cmd, input_file, output_file, media_type):
    """Run FFmpeg conversion with progress display and proper encoding"""
    try:
        print("Running FFmpeg conversion...")
        
        # Use proper encoding for subprocess
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        for line in process.stdout:
            if 'time=' in line:
                # Safely handle Unicode in progress output
                try:
                    print(f"\rConverting... {line.strip()}", end='', flush=True)
                except UnicodeEncodeError:
                    print(f"\rConverting...", end='', flush=True)
        
        process.wait()
        print()  # New line after progress
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
        
        # Verify the output file
        if not verify_media_file(output_file, media_type):
            raise Exception("Conversion failed - output file is invalid")
            
        print(f"Conversion completed: {os.path.basename(output_file)}")
        return output_file
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Conversion failed with error code {e.returncode}")

def process_media(url, vita_ip, vita_port, media_type='video'):
    """Main processing function for both video and music"""
    try:
        # Check dependencies first
        if not check_dependencies():
            return False
        
        # 1. Download media
        downloaded_file = download_media(url, media_type)
        print(f"Verified download: {downloaded_file}")
        
        # 2. Convert media
        if media_type == 'music':
            output_extension = ".mp3"
            vita_path = VITA_MUSIC_PATH
            conversion_func = convert_for_vita_music
        else:
            output_extension = "_psvita.mp4"
            vita_path = VITA_VIDEO_PATH
            conversion_func = convert_for_vita_video
        
        # Create a safe filename for output
        base_name = sanitize_filename(os.path.splitext(os.path.basename(downloaded_file))[0])
        output_filename = base_name + output_extension
        output_path = os.path.join(CONVERTED_FOLDER, output_filename)
        
        converted_file = conversion_func(downloaded_file, output_path)
        print(f"Successfully converted: {converted_file}")
        
        # 3. Transfer to Vita
        print(f"\nInitiating Vita transfer to {vita_path}...")
        print(f"Make sure VitaShell FTP is running (Press SELECT in VitaShell)")
        print("Waiting 3 seconds for you to confirm...")
        time.sleep(3)
        
        ftp = VitaFTP(vita_ip, vita_port)
        remote_path = f"{vita_path}{os.path.basename(converted_file)}"
        
        def progress_callback(message):
            print(f"  {message}")
        
        if ftp.transfer(converted_file, remote_path, progress_callback):
            print(f"\nSuccess! {media_type.capitalize()} transferred to your PS Vita")
            print(f"File location: {vita_path}{os.path.basename(converted_file)}")
            
            # Clean up
            print("\nCleaning up temporary files...")
            os.remove(downloaded_file)
            print(f"Deleted temporary download: {downloaded_file}")
            
            keep_converted = input("Keep converted file for backup? (y/n): ").strip().lower()
            if keep_converted != 'y':
                os.remove(converted_file)
                print(f"Deleted converted file: {converted_file}")
            else:
                print(f"Converted file kept at: {converted_file}")
            
            return True
        
    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        
        # Clean up on error
        cleanup_temp_files(TEMP_FOLDER)
        temp_files = []
        if 'downloaded_file' in locals() and os.path.exists(downloaded_file):
            temp_files.append(downloaded_file)
        if 'converted_file' in locals() and os.path.exists(converted_file):
            temp_files.append(converted_file)
        
        if temp_files:
            cleanup = input("Clean up temporary files? (y/n): ").strip().lower()
            if cleanup == 'y':
                for file in temp_files:
                    try:
                        os.remove(file)
                        print(f"Deleted: {file}")
                    except:
                        pass
        
        return False

def main():
    parser = argparse.ArgumentParser(description='PS Vita Media Processor')
    parser.add_argument('url', nargs='?', help='URL of the media file (Mega.nz, YouTube, SoundCloud, etc.)')
    parser.add_argument('--type', choices=['video', 'music'], default='video', help='Type of media to process (default: video)')
    parser.add_argument('--ip', default=DEFAULT_VITA_IP,  help=f'PS Vita IP address (default: {DEFAULT_VITA_IP})')
    parser.add_argument('--port', type=int, default=DEFAULT_VITA_PORT,  help=f'PS Vita FTP port (default: {DEFAULT_VITA_PORT})')
    parser.add_argument('--check-deps', action='store_true', help='Check if required dependencies are installed')
    
    args = parser.parse_args()
    
    if args.check_deps:
        if check_dependencies():
            print("All required dependencies are installed!")
        sys.exit(0)
    
    # Check if URL is provided when not just checking dependencies
    if not args.url:
        parser.error("URL is required unless using --check-deps")
    
    print(logo)
    print(f"    PS Vita Media Processor")
    print("-" * 50)
    print(f"Media Type: {args.type.upper()}")
    print(f"Vita IP: {args.ip}:{args.port}")
    print(f"URL: {args.url}")
    if args.type == 'video':
        print(f"Destination: {VITA_VIDEO_PATH}")
    else:
        print(f"Destination: {VITA_MUSIC_PATH}")
    print("-" * 50)
    
    if not process_media(args.url, args.ip, args.port, args.type):
        sys.exit(1)

if __name__ == "__main__":
    main()