import os
import subprocess
import json
import re
from .helpers import logger, verify_media_file
from .constants import CONVERTED_FOLDER 

def run_ffmpeg_conversion(cmd, input_file, output_file, media_type):
    try:
        logger.info(f"Running FFmpeg conversion: {os.path.basename(input_file)} -> {os.path.basename(output_file)}")
        print("Running FFmpeg conversion...")
        print("Please wait, this may take a few minutes...")
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        last_time = ""
        for line in process.stdout:
            if 'time=' in line:
                try:
                    # Extract just the time part
                    time_match = re.search(r'time=(\S+)', line)
                    if time_match:
                        current_time = time_match.group(1)
                        if current_time != last_time:
                            print(f"Converting... time={current_time}", flush=True)
                            last_time = current_time
                except:
                    print("Converting...", flush=True)
            elif 'error' in line.lower() or 'failed' in line.lower():
                logger.warning(f"FFmpeg warning: {line.strip()}")
                print(f"Warning: {line.strip()}", flush=True)
        
        process.wait()
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
        
        if not verify_media_file(output_file, media_type):
            raise Exception("Conversion failed - output file is invalid")
        
        logger.info(f"Conversion completed: {os.path.basename(output_file)}")
        print("=" * 50, flush=True)
        print("CONVERSION COMPLETED SUCCESSFULLY!", flush=True)
        print(f"Output file: {os.path.basename(output_file)}", flush=True)
        print(f"File size: {os.path.getsize(output_file) / (1024*1024):.1f} MB", flush=True)
        print("=" * 50, flush=True)
        
        return output_file
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Conversion failed with error code {e.returncode}")
        raise Exception(f"Conversion failed with error code {e.returncode}")

def convert_for_vita_video(input_file, output_file):
    logger.info(f"Converting video for PS Vita: {os.path.basename(input_file)}")
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
    if not metadata:
        return input_file
    
    logger.info("Embedding metadata into audio file...")
    print("Embedding metadata into audio file...")
    
    base_name = os.path.splitext(input_file)[0]
    output_file = f"{base_name}_tagged.mp3"
    
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-c', 'copy',
        '-y'
    ]
    
    # Add metadata fields
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
            os.remove(input_file)
            os.rename(output_file, input_file)
            logger.info("Metadata embedded successfully")
            print("Metadata embedded successfully")
        else:
            logger.warning(f"Could not embed metadata: {result.stderr}")
            print(f"Warning: Could not embed metadata: {result.stderr}")
            if os.path.exists(output_file):
                os.remove(output_file)
    except Exception as e:
        logger.warning(f"Metadata embedding failed: {e}")
        print(f"Warning: Metadata embedding failed: {e}")
        # Clean up failed output file
        if os.path.exists(output_file):
            os.remove(output_file)
    
    return input_file

def convert_for_vita_music(input_file, output_file):
    logger.info(f"Converting audio to MP3 for PS Vita: {os.path.basename(input_file)}")
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
        logger.warning(f"Could not extract metadata from file: {e}")
        print(f"Could not extract metadata from file: {e}")
    
    return None