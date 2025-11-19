import os
import json
import platform
import logging
from .constants import (
    DEFAULT_CONFIG, TEMP_FOLDER, CONVERTED_FOLDER, LOG_FOLDER,
    DEFAULT_VITA_IP, DEFAULT_VITA_PORT, VITA_VIDEO_PATH, VITA_MUSIC_PATH,
    MAX_RETRIES, RETRY_DELAY, PSVMP_DIR
)
from .helpers import logger

def get_config_path():
    return os.path.join(PSVMP_DIR, 'configuration.json')

def load_config(silent=False):
    config_path = get_config_path()
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            # global variables
            global DEFAULT_VITA_IP, DEFAULT_VITA_PORT, VITA_VIDEO_PATH, VITA_MUSIC_PATH, MAX_RETRIES, RETRY_DELAY
            
            DEFAULT_VITA_IP = loaded_config.get('vita_ip', DEFAULT_CONFIG['vita_ip'])
            DEFAULT_VITA_PORT = loaded_config.get('vita_port', DEFAULT_CONFIG['vita_port'])
            VITA_VIDEO_PATH = loaded_config.get('video_path', DEFAULT_CONFIG['video_path'])
            VITA_MUSIC_PATH = loaded_config.get('music_path', DEFAULT_CONFIG['music_path'])
            MAX_RETRIES = loaded_config.get('max_retries', DEFAULT_CONFIG['max_retries'])
            RETRY_DELAY = loaded_config.get('retry_delay', DEFAULT_CONFIG['retry_delay'])
            
            if not silent:
                logger.info(f"Configuration loaded from: {config_path}")
            return loaded_config
        except Exception as e:
            if not silent:
                logger.warning(f"Failed to load configuration: {e}. Using defaults.")
    else:
        if not silent:
            logger.info("No configuration file found. Using defaults.")
    
    return DEFAULT_CONFIG.copy()

def save_config(config=None):
    if config is None:
        config = {
            'vita_ip': DEFAULT_VITA_IP,
            'vita_port': DEFAULT_VITA_PORT,
            'video_path': VITA_VIDEO_PATH,
            'music_path': VITA_MUSIC_PATH,
            'max_retries': MAX_RETRIES,
            'retry_delay': RETRY_DELAY
        }
    
    config_path = get_config_path()
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Configuration saved to: {config_path}")
        return config_path
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        return None

def show_config():
    config = {
        'vita_ip': DEFAULT_VITA_IP,
        'vita_port': DEFAULT_VITA_PORT,
        'video_path': VITA_VIDEO_PATH,
        'music_path': VITA_MUSIC_PATH,
        'max_retries': MAX_RETRIES,
        'retry_delay': RETRY_DELAY
    }
    
    print("\nCurrent Configuration:")
    print("-" * 40)
    for key, value in config.items():
        print(f"  {key}: {value}")
    print("-" * 40)
    print(f"Config file: {get_config_path()}")

def update_config_from_args(args):
    config_changed = False
    config = {
        'vita_ip': DEFAULT_VITA_IP,
        'vita_port': DEFAULT_VITA_PORT,
        'video_path': VITA_VIDEO_PATH,
        'music_path': VITA_MUSIC_PATH,
        'max_retries': MAX_RETRIES,
        'retry_delay': RETRY_DELAY
    }
    
    # Update config with command line values
    if hasattr(args, 'ip') and args.ip != DEFAULT_VITA_IP:
        config['vita_ip'] = args.ip
        config_changed = True
    
    if hasattr(args, 'port') and args.port != DEFAULT_VITA_PORT:
        config['vita_port'] = args.port
        config_changed = True
    
    return config, config_changed

def handle_config_command(args):
    config = load_config(silent=True)
    config_path = get_config_path()
    
    if args.set_config:
        
        for setting in args.set_config:
            try:
                key, value = setting.split('=', 1)
                key = key.strip()
                
                # Convert value to appropriate type
                if key in ['vita_port', 'max_retries']:
                    value = int(value)
                elif key in ['retry_delay']:
                    value = float(value)
                elif key in ['vita_ip', 'video_path', 'music_path']:
                    value = str(value)
                
                if key in config:
                    old_value = config[key]
                    config[key] = value
                    print(f"Updated {key}: {old_value} -> {value}")
                    logger.info(f"Config updated: {key} = {value}")
                else:
                    print(f"Warning: Unknown configuration key '{key}'")
            except ValueError:
                print(f"Error: Invalid format for '{setting}'. Use key=value format.")
                return False
        
        saved_path = save_config(config)
        if saved_path:
            print(f"\nConfiguration saved to: {saved_path}")
            return True
        else:
            print("Error: Failed to save configuration")
            return False
    
    elif args.show_config:
        show_config()
        return True
    
    else:
        print(f"\nConfiguration file location: {config_path}")
        show_config()
        print("\nUse --config set key=value to change settings")
        print("Example: --config set vita_ip=192.168.1.10 --config set vita_port=1338")
        return True