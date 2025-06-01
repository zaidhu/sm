# Telegram Social Media Downloader Bot

This bot downloads media (videos/images) from YouTube, Instagram, X (Twitter), and Facebook links sent to it via Telegram.

## Features

*   Supports YouTube (videos, shorts), Instagram (posts, reels - uses yt-dlp), X/Twitter (videos/images), Facebook (videos, reels - may require cookies for some content).
*   Receives a link via Telegram message.
*   Downloads the corresponding media file.
*   Sends the downloaded file back to the user with a custom caption.
*   Includes basic error handling and user feedback.

## Files

*   `bot.py`: The main Telegram bot application logic using `python-telegram-bot`.
*   `downloader.py`: Contains the functions for identifying platforms and downloading media using `yt-dlp` and `instaloader`.
*   `requirements.txt`: Lists the required Python libraries.
*   `README.md`: This file.

## Setup

1.  **Prerequisites:**
    *   Python 3.8 or higher.
    *   `pip` (Python package installer).
    *   `ffmpeg` (Required by `yt-dlp` for merging video and audio streams). Install it using your system's package manager (e.g., `sudo apt update && sudo apt install ffmpeg` on Debian/Ubuntu, `brew install ffmpeg` on macOS).

2.  **Clone the Repository (or download the files):**
    ```bash
    # If you create a Git repository
    # git clone <your-repo-url>
    # cd <your-repo-directory>
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Get a Telegram Bot Token:**
    *   Talk to `@BotFather` on Telegram.
    *   Use the `/newbot` command and follow the instructions.
    *   BotFather will give you a unique API token.

5.  **Configure the Bot Token:**
    *   **Option A (Recommended):** Set the token as an environment variable:
        ```bash
        export TELEGRAM_BOT_TOKEN="YOUR_ACTUAL_BOT_TOKEN"
        ```
    *   **Option B:** Directly edit the `bot.py` file and replace the placeholder token string with your actual token:
        ```python
        # Find this line in bot.py
        TELEGRAM_BOT_TOKEN = "YOUR_ACTUAL_BOT_TOKEN" 
        ```
        *(Note: The current `bot.py` in the zip has the token you provided hardcoded. For security, using environment variables is better, especially if you plan to share the code or host it publicly.)*

6.  **Run the Bot:**
    ```bash
    python bot.py 
    ```
    *(Use `python3` or `python3.11` if that's how Python is invoked on your system)*

## Usage

*   Start a chat with your bot on Telegram.
*   Send it a message containing a valid link from YouTube, Instagram, X (Twitter), or Facebook.
*   The bot will reply indicating it's downloading and then send the media file back with the configured caption.

## Notes

*   **Facebook/Instagram:** Downloads from these platforms can be unreliable, especially for private content or content requiring login. `yt-dlp` and `instaloader` might require cookies or login credentials for consistent access, which is not implemented in this basic version.
*   **X/Twitter:** Platform changes can sometimes break downloaders. Keeping `yt-dlp` updated (`pip install --upgrade yt-dlp`) is recommended.
*   **File Size Limits:** Telegram bots have a 50MB limit for sending files. The bot currently doesn't strictly enforce this before sending, but it logs a warning if the downloaded file exceeds this. Downloads might fail to send if they are too large.
*   **Error Handling:** Basic error handling is included, but more robust checks could be added.
*   **Temporary Files:** Downloaded files are stored temporarily in the `/home/ubuntu/downloads` directory (you might want to change this path in `downloader.py` if running elsewhere) and are deleted after being sent or if an error occurs during sending.

