#!/usr/bin/env python3
# https://github.com/v7upSln

import sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding="utf-8", errors="replace")

logo = """
 ######   #####  #     # #     # ######  
 #     # #     # #     # ##   ## #     # 
 #     # #       #     # # # # # #     # 
 ######   #####  #     # #  #  # ######  
 #             #  #   #  #     # #       
 #       #     #   # #   #     # #       
 #        #####     #    #     # #       
"""

# Change this import
from modules.VERSION import VERSION

import time
import os
import sys
import argparse
import logging
from datetime import datetime

#==============================================================
# Change all module imports to relative
from modules.constants import (
    DEFAULT_VITA_IP, DEFAULT_VITA_PORT, 
    VITA_VIDEO_PATH, VITA_MUSIC_PATH,
    TEMP_FOLDER, CONVERTED_FOLDER
)
from modules.config import (
    load_config, save_config, show_config, 
    update_config_from_args, handle_config_command
)
from modules.download import download_media
from modules.conversion import convert_for_vita_video, convert_for_vita_music
from modules.transfer import VitaFTP
from modules.helpers import (
    setup_logging, logger, check_dependencies,
    sanitize_filename, cleanup_temp_files
)

from modules.history import log_to_history, show_history, clear_history

from modules.updater import check_for_update

def process_media(url, vita_ip, vita_port, media_type='video'):
    try:
        # Check dependencies first
        if not check_dependencies():
            log_to_history(url, media_type, "failed", "Missing dependencies")
            return False
        
        # 1. Download media
        logger.info(f"Starting media processing: {media_type} from {url}")
        print("=" * 50)
        print("STEP 1: DOWNLOADING MEDIA")
        print("=" * 50)
        downloaded_file = download_media(url, media_type)
        logger.info("Download completed successfully!")
        print("Download completed successfully!")
        
        # 2. Convert media
        print("\n" + "=" * 50)
        print("STEP 2: CONVERTING FOR PS VITA")
        print("=" * 50)
        
        if media_type == 'music':
            output_extension = ".mp3"
            vita_path = VITA_MUSIC_PATH
            conversion_func = convert_for_vita_music
        else:
            output_extension = "_psvita.mp4"
            vita_path = VITA_VIDEO_PATH
            conversion_func = convert_for_vita_video
        
        base_name = sanitize_filename(os.path.splitext(os.path.basename(downloaded_file))[0])
        output_filename = base_name + output_extension
        output_path = os.path.join(CONVERTED_FOLDER, output_filename)
        
        converted_file = conversion_func(downloaded_file, output_path)
        
        # 3. Transfer to Vita
        print("\n" + "=" * 50)
        print("STEP 3: TRANSFERRING TO PS VITA")
        print("=" * 50)
        print(f"Target: {vita_path}")
        print("Make sure VitaShell FTP is running (Press SELECT in VitaShell)")
        print("Waiting 3 seconds for you to confirm...")
        time.sleep(3)
        
        ftp = VitaFTP(vita_ip, vita_port)
        remote_path = f"{vita_path}{os.path.basename(converted_file)}"
        
        def progress_callback(message):
            print(f"  {message}" , flush=True)
        
        if ftp.transfer(converted_file, remote_path, progress_callback):
            logger.info(f"Media processing completed successfully: {os.path.basename(converted_file)}")
            print("\n" + "=" * 50)
            print(f"SUCCESS! {media_type.upper()} TRANSFERRED TO PS VITA")
            print("=" * 50)
            
            log_to_history(url, media_type, "completed")
            
            # Clean up
            print("\nCleaning up temporary files...")
            os.remove(downloaded_file)
            logger.info(f"Deleted temporary download: {os.path.basename(downloaded_file)}")
            print(f"Deleted temporary download: {os.path.basename(downloaded_file)}")
            
            keep_converted = input("Keep converted file for backup? (y/n): ").strip().lower()
            if keep_converted != 'y':
                os.remove(converted_file)
                logger.info(f"Deleted converted file: {os.path.basename(converted_file)}")
                print(f"Deleted converted file: {os.path.basename(converted_file)}")
            else:
                logger.info(f"Converted file kept at: {converted_file}")
                print(f"Converted file kept at: {converted_file}")
            
            return True
        
    except Exception as e:
        logger.error(f"Media processing failed: {str(e)}")
        print(f"\nERROR: {str(e)}", file=sys.stderr)
        
        log_to_history(url, media_type, "failed", str(e))
        
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
                        logger.info(f"Cleaned up on error: {os.path.basename(file)}")
                        print(f"Deleted: {os.path.basename(file)}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to clean up {file}: {cleanup_error}")
        
        return False

def check_and_display_update_info():
    print(f"PS Vita Media Processor Version {VERSION}")
    
    update_result = check_for_update()
    
    if update_result[0] is True:
        # Update available
        print(f"Update available: Version {update_result[1]} is available!")
        print(f"Current version: {VERSION}")
        print("To update, run: pip install --upgrade psvmp")
    elif update_result[0] is False:
        # Up to date
        print(f"You have the latest version ({VERSION})")
    else:
        # Error
        print(f"Could not check for updates: {update_result[1]}")

def main():
    parser = argparse.ArgumentParser(description='PS Vita Media Processor')
    parser.add_argument('url', nargs='?', help='URL of the media file (Mega.nz, YouTube, SoundCloud, etc.)')
    parser.add_argument('--type', choices=['video', 'music'], default='video', help='Type of media to process (default: video)')
    parser.add_argument('--ip', default=DEFAULT_VITA_IP,  help=f'PS Vita IP address (default: {DEFAULT_VITA_IP})')
    parser.add_argument('--port', type=int, default=DEFAULT_VITA_PORT,  help=f'PS Vita FTP port (default: {DEFAULT_VITA_PORT})')
    parser.add_argument('--check-deps', action='store_true', help='Check if required dependencies are installed')
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit')
    parser.add_argument('-u', '--update', action='store_true', help='Check for updates and exit')
    parser.add_argument('--history', action='store_true', help='Show download history')
    parser.add_argument('--history-clear', action='store_true', help='Clear download history')
    parser.add_argument('--history-limit', type=int, default=10, help='Number of history entries to show (default: 10)')
    
    config_group = parser.add_argument_group('configuration options')
    config_group.add_argument('--config', '-c', action='store_true', help='Show configuration file location and current settings')
    config_group.add_argument('--config-set', dest='set_config', action='append', metavar='KEY=VALUE', help='Set configuration value (can be used multiple times)')
    config_group.add_argument('--config-show', dest='show_config', action='store_true', help='Show current configuration')
    
    args = parser.parse_args()
    
    if args.update:
        check_and_display_update_info()
        sys.exit(0)
    
    if args.config or args.set_config or args.show_config:
        if handle_config_command(args):
            sys.exit(0)
        else:
            sys.exit(1)
    
    load_config(silent=True)
    
    if args.history:
        show_history(args.history_limit)
        sys.exit(0)
    
    if args.history_clear:
        if clear_history():
            print("History cleared successfully.")
        else:
            print("Failed to clear history or history was already empty.")
        sys.exit(0)
    
    if args.check_deps:
        if check_dependencies():
            print("All required dependencies are installed!")
        sys.exit(0)
    
    if args.version:
        check_and_display_update_info()
        sys.exit(0)

    if not args.url:
        parser.error("URL is required unless using --check-deps or --config")
    
    config, config_changed = update_config_from_args(args)
    if config_changed:
        logger.info("Using command-line overrides for this session")
    
    print(logo)
    print(f"    PS Vita Media Processor")
    print(f"        Version {VERSION}")
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