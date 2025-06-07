# bot_new.py
import logging
import os
import asyncio
import re
from telegram import Update, InputMediaDocument, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError

# Import the new downloader
import downloader

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Get bot token from environment variable or hardcode (replace with env var ideally)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("Telegram Bot Token not found!")
    exit()

# --- Animation Constants ---
ANIMATION_FRAMES = ["Downloading.", "Downloading..", "Downloading..."]
ANIMATION_INTERVAL = 0.5 # seconds

# --- Helper Functions ---
def get_file_type(file_path):
    """Determine file type based on extension."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext in [".jpg", ".jpeg", ".png", ".webp"]:
        return "photo"
    elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
        return "video"
    else:
        return "document"

async def edit_message_with_animation(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, stop_event: asyncio.Event):
    """Edit the message periodically with animation frames."""
    frame_index = 0
    while not stop_event.is_set():
        try:
            await context.bot.edit_message_text(
                text=ANIMATION_FRAMES[frame_index % len(ANIMATION_FRAMES)],
                chat_id=chat_id,
                message_id=message_id
            )
            frame_index += 1
            await asyncio.sleep(ANIMATION_INTERVAL)
        except TelegramError as e:
            # Ignore errors like "Message is not modified" or if message is deleted
            if "Message is not modified" in str(e):
                await asyncio.sleep(ANIMATION_INTERVAL) # Still wait before next attempt
            else:
                logger.warning(f"Error editing message for animation: {e}")
                break # Stop animation on other errors
        except Exception as e:
            logger.error(f"Unexpected error in animation loop: {e}")
            break

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Send me a link from YouTube, Instagram, X, or Facebook, and I\ll try to download the media for you.",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Send me a social media link (YouTube, Instagram, X, Facebook) and I will download the video or image for you.")

# --- Message Handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages, look for URLs, and download media."""
    message_text = update.message.text
    chat_id = update.effective_chat.id

    # Simple URL extraction (can be improved)
    url_match = re.search(r"https?://\S+", message_text)
    if not url_match:
        # Ignore messages without URLs unless it\s a direct reply or specific command needed
        # await update.message.reply_text("Please send a valid social media link.")
        logger.info(f"Ignoring non-URL message from chat {chat_id}")
        return

    url = url_match.group(0)
    logger.info(f"Received URL: {url} from chat {chat_id}")

    # Send initial status message
    status_message = await update.message.reply_text("Processing link...")
    message_id = status_message.message_id

    # --- Start Animation Task ---
    stop_animation_event = asyncio.Event()
    animation_task = asyncio.create_task(
        edit_message_with_animation(context, chat_id, message_id, stop_animation_event)
    )

    downloaded_file_path = None
    error_message = None
    try:
        # Call the downloader function
        # Using run_in_executor to avoid blocking the asyncio event loop
        loop = asyncio.get_running_loop()
        downloaded_file_path_or_error = await loop.run_in_executor(
            None, # Use default executor (ThreadPoolExecutor)
            downloader_new.download_media, # Function to run
            url # Arguments to the function
        )

        if isinstance(downloaded_file_path_or_error, str) and downloaded_file_path_or_error.startswith("Error:"):
            error_message = downloaded_file_path_or_error
            logger.error(f"Download failed for {url}: {error_message}")
        elif downloaded_file_path_or_error and os.path.exists(downloaded_file_path_or_error):
            downloaded_file_path = downloaded_file_path_or_error
            logger.info(f"Successfully downloaded: {downloaded_file_path}")
        else:
            error_message = "Error: Download failed for an unknown reason."
            logger.error(f"Download failed for {url}: Unknown reason or path was None ({downloaded_file_path_or_error})")

    except Exception as e:
        logger.exception(f"An unexpected error occurred handling URL {url}: {e}")
        error_message = f"Error: An unexpected error occurred: {e}"
    finally:
        # --- Stop Animation Task ---
        stop_animation_event.set()
        await animation_task # Wait for the task to finish cleanly

    # --- Send Result ---
    caption = f"Here\s your downloaded content\nRegards [ZaidHub](https://t.me/zaidHub)" # User requested caption

    if downloaded_file_path:
        file_type = get_file_type(downloaded_file_path)
        try:
            logger.info(f"Sending {file_type}: {downloaded_file_path}")
            if file_type == "photo":
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=open(downloaded_file_path, "rb"),
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_to_message_id=update.message.message_id
                )
            elif file_type == "video":
                # Consider adding video dimensions/duration check if needed
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=open(downloaded_file_path, "rb"),
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_to_message_id=update.message.message_id,
                    # Increase timeouts for potentially large files
                    write_timeout=120, read_timeout=120, connect_timeout=120
                )
            else: # document
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=open(downloaded_file_path, "rb"),
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_to_message_id=update.message.message_id,
                    write_timeout=120, read_timeout=120, connect_timeout=120
                )
            # Delete the initial status message after successful send
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)

        except TelegramError as e:
            logger.error(f"Failed to send file {downloaded_file_path}: {e}")
            # Edit status message to show error instead
            await context.bot.edit_message_text(
                text=f"Sorry, failed to upload the downloaded file: {e}",
                chat_id=chat_id,
                message_id=message_id
            )
        except Exception as e:
             logger.exception(f"Unexpected error sending file {downloaded_file_path}: {e}")
             await context.bot.edit_message_text(
                text=f"Sorry, an unexpected error occurred during upload.",
                chat_id=chat_id,
                message_id=message_id
            )
        finally:
            # Clean up the downloaded file
            try:
                os.remove(downloaded_file_path)
                logger.info(f"Cleaned up file: {downloaded_file_path}")
            except OSError as e:
                logger.error(f"Error cleaning up file {downloaded_file_path}: {e}")

    elif error_message:
        # Edit status message to show the download error
        await context.bot.edit_message_text(
            text=f"Sorry, download failed: {error_message}",
            chat_id=chat_id,
            message_id=message_id
        )
    else:
         # Should not happen if logic is correct, but as a fallback
         await context.bot.edit_message_text(
            text="Sorry, something went wrong.",
            chat_id=chat_id,
            message_id=message_id
        )


# --- Main Function ---
def main() -> None:
    """Start the bot."""
    logger.info("Starting bot...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Message handler for URLs
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot started. Press Ctrl-C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

