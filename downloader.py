# downloader.py
import os
import re
import subprocess
import logging
from urllib.parse import urlparse
# import instaloader # Removed instaloader

# Configure logging
logging.basicConfig(level=logging.INFO, format=\'%(asctime)s - %(levelname)s - %(message)s\')

DOWNLOAD_DIR = "/tmp" # Use /tmp for cloud compatibility
# Attempt to find yt-dlp path reliably
try:
    YT_DLP_PATH = subprocess.check_output([\'which\', \'yt-dlp\'], text=True).strip()
except subprocess.CalledProcessError:
    # Fallback if \'which\' fails or yt-dlp is not in PATH (might happen in some envs)
    # Check common pip install locations
    possible_paths = [
        \'/usr/local/bin/yt-dlp\',
        os.path.expanduser(\'~/.local/bin/yt-dlp\'),
        \'/opt/venv/bin/yt-dlp\' # Example venv path
    ]
    for path in possible_paths:
        if os.path.exists(path):
            YT_DLP_PATH = path
            break
    else:
        logging.error("yt-dlp command not found. Please ensure it is installed and in PATH.")
        YT_DLP_PATH = \'yt-dlp\' # Default to just the command name, hoping it\'s in PATH

logging.info(f"Using yt-dlp path: {YT_DLP_PATH}")

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_platform(url):
    """Identifies the social media platform from the URL."""
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname.lower() if parsed_url.hostname else \'\'

    if \'youtube.com\' in hostname or \'youtu.be\' in hostname:
        return \'youtube\'
    elif \'instagram.com\' in hostname:
        return \'instagram\'
    elif \'facebook.com\' in hostname or \'fb.watch\' in hostname:
        return \'facebook\'
    elif \'x.com\' in hostname or \'twitter.com\' in hostname:
        return \'x\'
    else:
        return None

def download_with_yt_dlp(url, platform):
    """Downloads media using yt-dlp."""
    # Sanitize ID for filename (replace non-alphanumeric) - basic example
    sanitized_id = re.sub(r\'[\\W]+\', \'_\', url.split(\'/\')[-1] if \'/\' in url else url)
    if not sanitized_id:
        sanitized_id = \'media\'
    # Use a simpler output template, especially for /tmp
    output_template = os.path.join(DOWNLOAD_DIR, f"{platform}_{sanitized_id}_%(id)s.%(ext)s")
    
    command = [
        YT_DLP_PATH,
        \'--no-check-certificate\',
        \'-o\', output_template,
        \'-f\', \'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best\', # Prefer mp4
        \'--merge-output-format\', \'mp4\',
        # \'--max-filesize\', \'49m\', # Add Telegram\'s 50MB limit approx
        url
    ]
    logging.info(f"Attempting download from {platform} using yt-dlp: {url}")
    logging.info(f"Executing command: {\' \'.join(command)}")
    try:
        # Run yt-dlp and capture output
        process = subprocess.run(command, capture_output=True, text=True, check=False, timeout=300) # 5 min timeout, check=False to parse output even on error
        logging.info(f"yt-dlp stdout:\\n{process.stdout}")
        logging.warning(f"yt-dlp stderr:\\n{process.stderr}") # Use warning for stderr as it often contains non-fatal messages

        # Find the downloaded file path from yt-dlp output
        output_lines = process.stdout.splitlines()
        downloaded_file = None
        
        # More robust search for filename patterns
        patterns = [
            r\'Merging formats into "(.*?)\"\',
            r\'Destination: (.*?)$\',
            r\'Fixing MPEG-TS in "(.*?)\"\',
            r\'(.*?) has already been downloaded\'
        ]
        
        for line in output_lines + process.stderr.splitlines(): # Check both stdout and stderr
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    potential_file = match.group(1).strip()
                    # Ensure it\'s likely a file path within our download dir
                    if potential_file.startswith(DOWNLOAD_DIR) and os.path.exists(potential_file):
                        downloaded_file = potential_file
                        logging.info(f"Found potential file via pattern \'{pattern}\': {downloaded_file}")
                        break # Found a likely candidate
            if downloaded_file: # Stop searching lines if found
                 break
        
        # Verify the found file exists
        if downloaded_file and os.path.exists(downloaded_file):
            logging.info(f"Confirmed downloaded file: {downloaded_file}")
            # Check file size (Telegram limit is 50MB for bots)
            if os.path.getsize(downloaded_file) > 50 * 1024 * 1024:
                logging.warning(f"Downloaded file {downloaded_file} exceeds 50MB Telegram limit.")
                # Optionally remove the large file
                # os.remove(downloaded_file)
                # return "Error: File size exceeds 50MB limit."
            return downloaded_file
        else:
             logging.warning("Could not reliably determine downloaded file from yt-dlp output.")
             # Fallback: search the download directory for the most recent file matching the pattern
             import glob
             import time
             # Be more specific with glob pattern if possible
             base_pattern = os.path.join(DOWNLOAD_DIR, f"{platform}_{sanitized_id}_*")
             list_of_files = glob.glob(base_pattern + ".mp4") + glob.glob(base_pattern + ".jpg") + glob.glob(base_pattern + ".jpeg") + glob.glob(base_pattern + ".png") + glob.glob(base_pattern + ".mkv") + glob.glob(base_pattern + ".webm")
             
             if not list_of_files:
                 logging.error("yt-dlp fallback search: No files found matching pattern.")
                 # Check if the process indicated an error explicitly
                 if "ERROR:" in process.stderr or process.returncode != 0:
                     # Try to extract a meaningful error message
                     error_match = re.search(r"ERROR: (.*?)$\", process.stderr, re.MULTILINE)
                     if error_match:
                         # Sanitize common non-informative errors
                         err_msg = error_match.group(1).strip()
                         if "The downloaded file is empty" in err_msg:
                             return "Error: Download failed (empty file). Platform might restrict access."
                         return f"Error: yt-dlp failed - {err_msg}"
                     else:
                         return "Error: yt-dlp failed with an unknown error."
                 return "Error: Download failed, could not find output file."
                 
             latest_file = max(list_of_files, key=os.path.getctime)
             # Check if the file was created recently (e.g., within the last 5 minutes)
             if time.time() - os.path.getctime(latest_file) < 300:
                 logging.warning(f"yt-dlp fallback: Using latest file found: {latest_file}")
                 if os.path.getsize(latest_file) > 50 * 1024 * 1024:
                     logging.warning(f"Downloaded file {latest_file} exceeds 50MB Telegram limit.")
                     # return "Error: File size exceeds 50MB limit."
                 return latest_file
             else:
                 logging.error("yt-dlp fallback search: No recently created file found matching pattern.")
                 return "Error: Download failed, could not find recent output file."

    except subprocess.TimeoutExpired:
        logging.error(f"yt-dlp timed out for {url}.")
        return "Error: Download timed out."
    except Exception as e:
        logging.error(f"An unexpected error occurred during yt-dlp download for {url}: {e}")
        return f"Error: An unexpected error occurred: {e}"

# Removed download_instagram function

def download_media(url):
    """Main function to download media based on URL."""
    platform = get_platform(url)
    logging.info(f"Detected platform: {platform} for URL: {url}")

    if platform == \'youtube\':
        return download_with_yt_dlp(url, \'youtube\')
    elif platform == \'x\':
        return download_with_yt_dlp(url, \'x\')
    elif platform == \'facebook\':
        # FB often requires cookies for yt-dlp, might fail otherwise
        logging.warning("Facebook downloads via yt-dlp might be unreliable without cookies.")
        return download_with_yt_dlp(url, \'facebook\')
    elif platform == \'instagram\':
        # Use yt-dlp directly for Instagram, skipping Instaloader
        logging.info("Using yt-dlp directly for Instagram download.")
        return download_with_yt_dlp(url, \'instagram\')
    else:
        logging.warning(f"Unsupported URL or platform: {url}")
        # Optionally, try yt-dlp as a generic fallback for unknown URLs
        logging.info("Attempting download with generic yt-dlp for unsupported URL...")
        result = download_with_yt_dlp(url, \'generic\')
        if isinstance(result, str) and result.startswith("Error:"):
             return "Error: Unsupported URL or download failed."
        elif result is None:
             return "Error: Unsupported URL or download failed."
        else:
             return result # Return path if generic download succeeded

if __name__ == "__main__":
    # Example usage for testing - Run this script directly to test
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ", # YouTube Video
        "https://x.com/SpaceX/status/1793719178710683863", # X (Twitter) Video
        "https://www.instagram.com/p/C7qahywRg44/", # Instagram Image Post (will use yt-dlp)
        "https://www.instagram.com/reel/C7g9zY8yQkQ/", # Instagram Reel Video (will use yt-dlp)
        "https://www.facebook.com/watch/?v=1118202089259010", # Facebook Watch (Likely needs cookies/login)
        "https://www.facebook.com/Meta/videos/1186598072789101/", # Facebook Video Post (Likely needs cookies/login)
        "https://invalid.url/test" # Invalid URL
    ]
    
    print("--- Starting Downloader Tests (Instaloader Removed) ---")
    for test_url in test_urls:
        print(f"\\nTesting URL: {test_url}")
        file_path_or_error = download_media(test_url)
        if isinstance(file_path_or_error, str) and file_path_or_error.startswith("Error:"):
            print(f"Download Failed: {file_path_or_error}")
        elif file_path_or_error and os.path.exists(file_path_or_error):
            print(f"Success! Downloaded file: {file_path_or_error}")
            print(f"File size: {os.path.getsize(file_path_or_error) / (1024*1024):.2f} MB")
            # Clean up test file immediately to avoid clutter
            try:
                os.remove(file_path_or_error)
                print(f"Cleaned up: {file_path_or_error}")
            except OSError as e:
                print(f"Error cleaning up {file_path_or_error}: {e}")
        else:
            print(f"Download Failed: Unknown reason or file path was None ({file_path_or_error})")
    print("--- Finished Downloader Tests ---")

