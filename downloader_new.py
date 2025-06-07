# downloader_new.py
import os
import re
import subprocess
import logging
import time
import glob
from urllib.parse import urlparse

# Configure logging
# Corrected format string without unnecessary backslashes
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DOWNLOAD_DIR = "/tmp" # Use /tmp for cloud compatibility
DEFAULT_COOKIES_FILE = "/home/ubuntu/cookies.txt" # Default path for provided cookies

# Attempt to find yt-dlp path reliably
try:
    # Corrected command list without unnecessary backslashes
    YT_DLP_PATH = subprocess.check_output(['which', 'yt-dlp'], text=True).strip()
except subprocess.CalledProcessError:
    possible_paths = [
        '/usr/local/bin/yt-dlp',
        os.path.expanduser('~/.local/bin/yt-dlp'),
        '/opt/venv/bin/yt-dlp' # Example venv path
    ]
    for path in possible_paths:
        if os.path.exists(path):
            YT_DLP_PATH = path
            break
    else:
        logging.error("yt-dlp command not found. Please ensure it is installed and in PATH.")
        YT_DLP_PATH = 'yt-dlp' # Default

logging.info(f"Using yt-dlp path: {YT_DLP_PATH}")

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_platform(url):
    """Identifies the social media platform from the URL."""
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname.lower() if parsed_url.hostname else ''

    if 'youtube.com' in hostname or 'youtu.be' in hostname:
        return 'youtube'
    elif 'instagram.com' in hostname:
        return 'instagram'
    elif 'facebook.com' in hostname or 'fb.watch' in hostname:
        return 'facebook'
    elif 'x.com' in hostname or 'twitter.com' in hostname:
        return 'x'
    else:
        return None

def download_media(url, cookies_file=DEFAULT_COOKIES_FILE):
    """Downloads media using yt-dlp, supporting cookies."""
    platform = get_platform(url)
    if not platform:
        logging.warning(f"Unsupported URL or platform: {url}")
        platform = 'generic'
        logging.info("Attempting download with generic yt-dlp for unsupported URL...")

    logging.info(f"Detected platform: {platform} for URL: {url}")

    # Sanitize ID for filename
    # Corrected regex without unnecessary backslashes
    sanitized_id = re.sub(r'\W+', '_', url.split('/')[-1] if '/' in url else url)
    if not sanitized_id:
        sanitized_id = str(int(time.time()))
    output_template = os.path.join(DOWNLOAD_DIR, f"{platform}_{sanitized_id}_%(id)s.%(ext)s")

    # Corrected command list without unnecessary backslashes
    command = [
        YT_DLP_PATH,
        '--no-check-certificate',
        '--no-playlist',
        '--max-downloads', '1',
        '--ignore-errors',
        # '--progress', # Removed as it adds too much noise
        '--output', output_template,
        '--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        '--merge-output-format', 'mp4',
        url
    ]

    if platform in ['youtube', 'facebook'] and cookies_file and os.path.exists(cookies_file):
        logging.info(f"Using cookies file: {cookies_file}")
        # Corrected command extension without unnecessary backslashes
        command.extend(['--cookies', cookies_file])
    elif platform in ['youtube', 'facebook']:
        logging.warning(f"Cookies file not found at {cookies_file}, proceeding without cookies.")

    logging.info(f"Executing command: {' '.join(command)}")
    try:
        # Corrected encoding and errors arguments
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
        
        stdout, stderr = process.communicate(timeout=300)
        
        logging.info(f"yt-dlp stdout:\n{stdout}")
        logging.warning(f"yt-dlp stderr:\n{stderr}")

        downloaded_file = None
        # Corrected regex patterns without unnecessary backslashes
        patterns = [
            r'[Merger] Merging formats into "(.*?)"',
            r'[download] Destination: (.*?)$',
            r'[Fixing MPEG-TS in|Extracting audio from] "(.*?)"',
            r'(.*?) has already been downloaded'
        ]
        
        search_text = stderr + "\n" + stdout
        
        for line in search_text.splitlines():
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    potential_file = match.group(1).strip()
                    if potential_file.startswith(DOWNLOAD_DIR) and os.path.exists(potential_file):
                        downloaded_file = potential_file
                        logging.info(f"Found potential file via pattern '{pattern}': {downloaded_file}")
                        break
            if downloaded_file:
                break

        if downloaded_file and os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 0:
            logging.info(f"Confirmed downloaded file: {downloaded_file}")
            if os.path.getsize(downloaded_file) > 50 * 1024 * 1024:
                logging.warning(f"Downloaded file {downloaded_file} exceeds 50MB Telegram limit.")
            return downloaded_file
        else:
            if downloaded_file and os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) == 0:
                 logging.error("Download resulted in an empty file.")
                 try: os.remove(downloaded_file) 
                 except OSError: pass
                 return "Error: Download failed (empty file). Platform might restrict access or resource limits hit."
            
            logging.warning("Could not reliably determine downloaded file from yt-dlp output or file is missing/empty.")
            base_pattern = os.path.join(DOWNLOAD_DIR, f"{platform}_{sanitized_id}_*")
            list_of_files = glob.glob(base_pattern + ".mp4") + glob.glob(base_pattern + ".jpg") + glob.glob(base_pattern + ".jpeg") + glob.glob(base_pattern + ".png") + glob.glob(base_pattern + ".mkv") + glob.glob(base_pattern + ".webm")
            
            if not list_of_files:
                logging.error("yt-dlp fallback search: No files found matching pattern.")
                # Corrected regex without unnecessary backslashes
                error_match = re.search(r"ERROR: (.*?)$", stderr, re.MULTILINE)
                if error_match:
                    err_msg = error_match.group(1).strip()
                    return f"Error: yt-dlp failed - {err_msg}"
                elif process.returncode != 0:
                     return f"Error: yt-dlp failed with return code {process.returncode}. Check logs."
                else:
                     return "Error: Download failed, could not find output file."
            
            latest_file = None
            latest_mtime = 0
            for f in list_of_files:
                try:
                    mtime = os.path.getmtime(f)
                    fsize = os.path.getsize(f)
                    if mtime > latest_mtime and fsize > 0:
                        latest_mtime = mtime
                        latest_file = f
                except OSError:
                    continue

            if latest_file and time.time() - latest_mtime < 300:
                logging.warning(f"yt-dlp fallback: Using latest non-empty file found: {latest_file}")
                if os.path.getsize(latest_file) > 50 * 1024 * 1024:
                    logging.warning(f"Downloaded file {latest_file} exceeds 50MB Telegram limit.")
                return latest_file
            else:
                logging.error("yt-dlp fallback search: No recently modified, non-empty file found matching pattern.")
                return "Error: Download failed, could not find recent, valid output file."

    except subprocess.TimeoutExpired:
        logging.error(f"yt-dlp timed out for {url}.")
        try:
            process.kill()
            stdout, stderr = process.communicate()
            logging.info(f"yt-dlp stdout after timeout kill:\n{stdout}")
            logging.warning(f"yt-dlp stderr after timeout kill:\n{stderr}")
        except Exception as kill_err:
            logging.error(f"Error killing timed out process: {kill_err}")
        return "Error: Download timed out."
    except Exception as e:
        logging.error(f"An unexpected error occurred during yt-dlp download for {url}: {e}")
        return f"Error: An unexpected error occurred: {e}"

if __name__ == "__main__":
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.instagram.com/p/C7qahywRg44/",
        "https://x.com/SpaceX/status/1793719178710683863",
    ]
    
    print("--- Starting New Downloader Tests (yt-dlp only, cookies enabled) ---")
    if not os.path.exists(DEFAULT_COOKIES_FILE):
        print(f"Creating dummy {DEFAULT_COOKIES_FILE} for testing.")
        # Corrected file write without unnecessary backslashes
        with open(DEFAULT_COOKIES_FILE, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            
    for test_url in test_urls:
        print(f"\nTesting URL: {test_url}")
        file_path_or_error = download_media(test_url)
        if isinstance(file_path_or_error, str) and file_path_or_error.startswith("Error:"):
            print(f"Download Failed: {file_path_or_error}")
        elif file_path_or_error and os.path.exists(file_path_or_error):
            print(f"Success! Downloaded file: {file_path_or_error}")
            print(f"File size: {os.path.getsize(file_path_or_error) / (1024*1024):.2f} MB")
            try:
                os.remove(file_path_or_error)
                print(f"Cleaned up: {file_path_or_error}")
            except OSError as e:
                print(f"Error cleaning up {file_path_or_error}: {e}")
        else:
            print(f"Download Failed: Unknown reason or file path was None ({file_path_or_error})")
    print("--- Finished New Downloader Tests ---")

