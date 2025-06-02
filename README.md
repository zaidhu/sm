# Telegram Social Media Downloader Bot (Clean Version)

This Telegram bot downloads media (videos, images) from links provided by users for platforms like YouTube, Instagram, X (Twitter), and Facebook.

## Features

*   Downloads media using `yt-dlp`.
*   Supports YouTube (videos, shorts), Instagram (posts, reels - uses yt-dlp), X/Twitter (videos/images), Facebook (videos, reels).
*   Optional support for YouTube cookies to handle age-restricted/member content.
*   Shows a simple text animation while downloading.
*   Designed for deployment on platforms like Railway (using Procfile).

## Files

*   `bot.py`: Main Telegram bot script.
*   `downloader.py`: Handles media downloading using `yt-dlp`.
*   `requirements.txt`: Required Python libraries.
*   `Procfile`: Start command for deployment platforms.
*   `README.md`: This file.

## Setup

1.  **Clone Repository:** Clone the repository containing these files.
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Install `ffmpeg`:** `yt-dlp` often requires `ffmpeg` for merging video and audio. Install it using your system's package manager (e.g., `sudo apt update && sudo apt install ffmpeg` on Debian/Ubuntu).
4.  **Set Environment Variables:**
    *   `TELEGRAM_BOT_TOKEN`: **Required.** Your Telegram Bot token obtained from @BotFather.
    *   `YT_COOKIES_FILE`: **Optional.** Path to a Netscape-formatted cookies file (e.g., `cookies.txt`) if you want to use YouTube cookies. Place the file in the bot's directory or provide the full path.

## Running Locally

```bash
export TELEGRAM_BOT_TOKEN="YOUR_ACTUAL_BOT_TOKEN"
# Optional: export YT_COOKIES_FILE="/path/to/your/cookies.txt"
python bot.py
```

## Deployment (e.g., Railway)

1.  Push the code (including `Procfile`) to a GitHub repository.
2.  Create a new service on Railway, linking it to your GitHub repository.
3.  In the Railway service settings (Variables tab), add the `TELEGRAM_BOT_TOKEN` environment variable with your token.
4.  **Optional:** If using cookies, upload your `cookies.txt` file (e.g., using `railway run -- <command_to_upload>` or by adding it to your repo - **not recommended for sensitive cookies**) and set the `YT_COOKIES_FILE` environment variable to the path where the file will be accessible within the Railway container (e.g., `cookies.txt` if in the root).
5.  Railway should automatically detect the `Procfile` and start the bot using `python bot.py`.

## Notes

*   Download success depends on `yt-dlp`'s capabilities and platform restrictions.
*   Large file downloads might exceed Telegram's 50MB limit for bots.
*   Ensure only one instance of the bot runs with a specific token to avoid conflicts.

