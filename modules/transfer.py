import os
import ftplib
import time
import sys
from tqdm import tqdm
from .helpers import logger
from .constants import MAX_RETRIES, RETRY_DELAY

class VitaFTP:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.timeout = 10
        logger.info(f"Initialized FTP connection to {ip}:{port}")

    def transfer(self, local_path, remote_path, progress_callback=None):
        file_size = os.path.getsize(local_path)
        filename = os.path.basename(local_path)
        logger.info(f"Starting FTP transfer: {filename} ({file_size} bytes)")
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if progress_callback:
                    progress_callback(f"Attempt {attempt}/{MAX_RETRIES}: Connecting to {self.ip}:{self.port}...")
                    sys.stdout.flush()  # Force immediate output
                
                with ftplib.FTP(timeout=self.timeout) as ftp:
                    ftp.connect(self.ip, self.port)
                    
                    if '/music/' in remote_path:
                        # Music path
                        try:
                            ftp.cwd('ux0:')
                            ftp.cwd('music')
                        except ftplib.error_perm:
                            if progress_callback:
                                progress_callback("Music directory not found, creating it...")
                                sys.stdout.flush()
                            try:
                                ftp.cwd('ux0:')
                                ftp.mkd('music')
                                ftp.cwd('music')
                            except ftplib.error_perm as e:
                                if progress_callback:
                                    progress_callback(f"Directory creation error: {str(e)}")
                                    sys.stdout.flush()
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
                                sys.stdout.flush()
                            try:
                                ftp.cwd('ux0:')
                                ftp.cwd('video')
                                ftp.mkd('shows')
                                ftp.cwd('shows')
                            except ftplib.error_perm as e:
                                if progress_callback:
                                    progress_callback(f"Directory creation error: {str(e)}")
                                    sys.stdout.flush()
                                pass
                    
                    if progress_callback:
                        progress_callback(f"Connected! Transferring {filename}...")
                        sys.stdout.flush()
                    
                    with open(local_path, 'rb') as f:
                        with tqdm(total=file_size, unit='B', unit_scale=True, 
                                 desc="Transfer Progress", leave=False) as pbar:
                            def callback(data):
                                pbar.update(len(data))
                            
                            remote_filename = os.path.basename(remote_path)
                            ftp.storbinary(f"STOR {remote_filename}", f, callback=callback)
                            print()  # Add newline after progress bar
                    
                    logger.info(f"FTP transfer completed: {filename}")
                    if progress_callback:
                        progress_callback("Transfer completed successfully")
                        sys.stdout.flush()
                    return True
                    
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"FTP transfer attempt {attempt} failed: {error_msg}")
                
                if progress_callback:
                    # Show specific error message
                    if "10060" in error_msg or "timeout" in error_msg.lower():
                        progress_callback(f"[!] Connection timeout - Vita not responding")
                    elif "10061" in error_msg:
                        progress_callback(f"[!] Connection refused - FTP server not running")
                    else:
                        progress_callback(f"[!] Connection failed: {error_msg}")
                    sys.stdout.flush()
                
                if attempt < MAX_RETRIES:
                    if progress_callback:
                        progress_callback(f"[*] Retrying in {RETRY_DELAY}s... (Attempt {attempt + 1}/{MAX_RETRIES})")
                        sys.stdout.flush()
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"FTP transfer failed after {MAX_RETRIES} attempts: {error_msg}")
                    if progress_callback:
                        progress_callback(f"[!] Failed after {MAX_RETRIES} attempts: {error_msg}")
                        sys.stdout.flush()
                    raise Exception(f"Failed after {MAX_RETRIES} attempts: {error_msg}")
        return False