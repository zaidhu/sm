# bot.py
import logging
import os
import re
import asyncio
from telegram import Update, InputMediaDocument, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError

# Import the downloader functions
import downloader

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Replace 'YOUR_TELEGRAM_BOT_TOKEN' with the actual token
TELEGRAM_BOT_TOKEN = "7148443787:AAFfsFv5SmyJoyhWfMXiZVaYN2E2iDx2M5M" 
# Check if running in an environment where the token is set as an env variable
if os.environ.get("TELEGRAM_BOT_TOKEN"):
    TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
    logger.info("Using Telegram Bot Token from environment variable.")
else:
    logger.warning("Telegram Bot Token not found in environment variables. Using placeholder.")

# --- Helper Functions ---
def extract_urls(text):
    """Extracts URLs from a given text."""
    # Improved regex to capture more URL variations
    url_pattern = r'https?://\S+'
    return re.findall(url_pattern, text)

async def cleanup_file(file_path):
    """Removes a file if it exists."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Successfully cleaned up file: {file_path}")
        except OSError as e:
            logger.error(f"Error removing file {file_path}: {e}")

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Send me a link from YouTube, Instagram, X (Twitter), or Facebook, and I will try my best to download the media for you.",
    )

# --- Message Handlers ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text messages, extracts URLs, and attempts downloads."""
    message_text = update.message.text
    chat_id = update.effective_chat.id
    urls = extract_urls(message_text)

    if not urls:
        # If no URLs are found, check if it's a reply to the bot's request or just a casual message
        # For now, we'll just ignore messages without URLs unless we add more complex state handling
        logger.info(f"No URLs found in message from chat_id {chat_id}")
        # Optionally send a message back: await update.message.reply_text("Please send me a valid social media link.")
        return

    # Process the first valid URL found
    processed_url = False
    for url in urls:
        logger.info(f"Processing URL: {url} from chat_id {chat_id}")
        platform = downloader.get_platform(url)

        if platform:
            processed_url = True
            status_message = await update.message.reply_text(
                f"Detected {platform.capitalize()} link. Attempting to download... Please wait.",
                reply_to_message_id=update.message.message_id
            )
            
            downloaded_file_path = None # Initialize here for cleanup
            try:
                # Run the download in a separate thread to avoid blocking asyncio event loop
                downloaded_file_path = await asyncio.to_thread(downloader.download_media, url)

                if isinstance(downloaded_file_path, str) and downloaded_file_path.startswith("Error:"):
                    error_message = downloaded_file_path
                    logger.error(f"Download failed for {url}: {error_message}")
                    await context.bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text=f"Sorry, download failed: {error_message}")
                elif downloaded_file_path and os.path.exists(downloaded_file_path):
                    logger.info(f"Download successful: {downloaded_file_path}")
                    file_size_mb = os.path.getsize(downloaded_file_path) / (1024 * 1024)
                    logger.info(f"File size: {file_size_mb:.2f} MB")

                    # Send the file based on type
                    caption = "Here's your downloaded content\nRegards [ZaidHub](https://t.me/zaidHub)" # User requested caption
                    
                    # Edit status message before sending file
                    await context.bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text="Download complete! Sending file...")

                    try:
                        if downloaded_file_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                            await context.bot.send_video(chat_id=chat_id, video=open(downloaded_file_path, 'rb'), caption=caption, parse_mode=ParseMode.MARKDOWN_V2, write_timeout=120, read_timeout=120, connect_timeout=120)
                        elif downloaded_file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            await context.bot.send_photo(chat_id=chat_id, photo=open(downloaded_file_path, 'rb'), caption=caption, parse_mode=ParseMode.MARKDOWN_V2, write_timeout=120, read_timeout=120, connect_timeout=120)
                        else:
                            # Send as a document for other types or if unsure
                            await context.bot.send_document(chat_id=chat_id, document=open(downloaded_file_path, 'rb'), caption=caption, parse_mode=ParseMode.MARKDOWN_V2, write_timeout=120, read_timeout=120, connect_timeout=120)
                        logger.info(f"Successfully sent file {downloaded_file_path} to chat_id {chat_id}")
                        # Delete the status message after successful send
                        await context.bot.delete_message(chat_id=chat_id, message_id=status_message.message_id)

                    except TelegramError as e:
                        logger.error(f"Telegram API error sending file {downloaded_file_path}: {e}")
                        # Edit status message to show error
                        error_text = f"Sorry, failed to send the file. It might be too large or incompatible. Error: {e}"
                        if "Request Entity Too Large" in str(e) or "FILE_SIZE_INVALID" in str(e):
                             error_text = f"Sorry, failed to send the file. It's too large for Telegram (max 50MB for bots). File size: {file_size_mb:.2f} MB"
                        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text=error_text)
                    except Exception as e:
                        logger.error(f"Unexpected error sending file {downloaded_file_path}: {e}")
                        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text=f"Sorry, an unexpected error occurred while sending the file: {e}")

                else:
                    logger.error(f"Download function returned an unexpected value or file not found: {downloaded_file_path}")
                    await context.bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text="Sorry, the download failed for an unknown reason.")

            except Exception as e:
                logger.exception(f"An unexpected error occurred processing URL {url}: {e}")
                try:
                    await context.bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text=f"Sorry, an unexpected error occurred: {e}")
                except TelegramError as te:
                     logger.error(f"Failed to update status message after exception: {te}")
            finally:
                # Ensure cleanup happens even if errors occur during sending
                if downloaded_file_path and isinstance(downloaded_file_path, str) and not downloaded_file_path.startswith("Error:"):
                    await cleanup_file(downloaded_file_path)
            
            # Stop processing after the first valid URL is handled
            break 
        else:
            logger.info(f"URL not from a supported platform: {url}")
            # Optionally inform the user about the specific unsupported URL if multiple were sent
            # await update.message.reply_text(f"Skipping unsupported link: {url}")

    if not processed_url and urls:
        # This case means URLs were found, but none were from supported platforms
        await update.message.reply_text("Sorry, the link(s) you sent are not from a supported platform (YouTube, Instagram, X, Facebook).")

# --- Main Function ---
def main() -> None:
    """Starts the bot."""
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("CRITICAL: Telegram Bot Token is not set! Please set the TELEGRAM_BOT_TOKEN environment variable or replace the placeholder in bot.py.")
        # Ask user for token here before exiting or proceeding
        # For now, we exit if token is missing
        print("Bot cannot start without a Telegram Bot Token.")
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).read_timeout(30).write_timeout(30).connect_timeout(30).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Entity("url"), handle_message))
    # Add a handler for any text message if you want to catch messages without URLs too
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_no_url_message))

    logger.info("Bot starting...")
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Ensure download directory exists before starting
    if not os.path.exists(downloader.DOWNLOAD_DIR):
        os.makedirs(downloader.DOWNLOAD_DIR)
        logger.info(f"Created download directory: {downloader.DOWNLOAD_DIR}")
    main()

