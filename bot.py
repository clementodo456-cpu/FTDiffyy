import io
import logging
import os
import sys
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from utils.converter import format_txt_export, process_image_bytes

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_MAX_TEXT_LEN = 4000

START_TEXT = (
    "👋 Welcome to Image to Base64 Bot!\n\n"
    "🖼 Send me an image and I’ll convert it to Base64.\n"
    "You can use the Base64 output in websites, HTML, CSS, JavaScript, APIs, and development projects.\n\n"
    "📌 Send an image to get started."
)

HELP_TEXT = (
    "ℹ️ **How to Use FTDiffyybot**\n\n"
    "1. Send any photo directly or upload an image as a uncompressed file.\n"
    "2. Supported formats: **JPG, PNG, WEBP, GIF, BMP**.\n"
    "3. Maximum file size: **20 MB**.\n"
    "4. If the converted string is short, it will be displayed in the chat.\n"
    "5. For larger outputs, a downloadable `.txt` file containing the complete Base64 string and Data URI will be generated automatically.\n\n"
    "Commands:\n"
    "/start - Start the bot\n"
    "/help - Show instructions\n"
    "/about - About FTDiffyybot\n"
    "/cancel - Cancel active actions"
)

ABOUT_TEXT = (
    "🤖 **FTDiffyybot (@FTDiffyybot)**\n\n"
    "A fast, secure, memory-efficient Telegram bot designed to convert images into Base64 format and Data URIs.\n\n"
    "🔒 **Privacy First:** Images are processed entirely in-memory and deleted immediately after conversion."
)


def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🖼 Convert Image", callback_data="btn_convert")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="btn_help")],
        ]
    )


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Cancel", callback_data="btn_cancel")]]
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        START_TEXT, reply_markup=get_main_keyboard(), parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        HELP_TEXT, reply_markup=get_main_keyboard(), parse_mode="Markdown"
    )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        ABOUT_TEXT, reply_markup=get_main_keyboard(), parse_mode="Markdown"
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🚫 Operation canceled. Send an image whenever you are ready!"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "btn_convert":
        await query.message.reply_text(
            "🖼 Please send or upload the image you want to convert.",
            reply_markup=get_cancel_keyboard(),
        )
    elif query.data == "btn_help":
        await query.message.reply_text(
            HELP_TEXT, reply_markup=get_main_keyboard(), parse_mode="Markdown"
        )
    elif query.data == "btn_cancel":
        await query.message.reply_text("🚫 Operation canceled.")


async def handle_non_image_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.message.reply_text(
        "⚠️ Please send an image (as a photo or document file) to perform a conversion.",
        reply_markup=get_main_keyboard(),
    )


async def process_image_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.message
    status_msg = await message.reply_text("⏳ Converting your image to Base64...")

    try:
        telegram_file = None
        file_name = None
        file_size = 0

        if message.photo:
            photo = message.photo[-1]
            file_size = photo.file_size or 0
            file_name = f"photo_{photo.file_unique_id}.jpg"
            telegram_file = await photo.get_file()
        elif message.document:
            doc = message.document
            file_size = doc.file_size or 0
            file_name = doc.file_name or f"file_{doc.file_unique_id}"
            telegram_file = await doc.get_file()

        if file_size > 20 * 1024 * 1024:
            await status_msg.edit_text(
                "❌ This image is too large.\n"
                "Maximum supported size: 20 MB.\n"
                "Please send a smaller image."
            )
            return

        image_bytes = await telegram_file.download_as_bytearray()

        result = process_image_bytes(bytes(image_bytes), original_filename=file_name)

        size_kb = round(result["size_bytes"] / 1024, 2)
        caption = (
            f"✅ Image converted successfully!\n"
            f"📁 File: {result['filename']}\n"
            f"📦 Size: {size_kb} KB\n"
            f"🧩 Format: {result['format_name']}\n\n"
            f"Your Base64 result is ready below."
        )

        base64_str = result["base64"]
        data_uri = result["data_uri"]

        formatted_msg = (
            f"{caption}\n\n"
            f"**Data URI:**\n`{data_uri}`\n\n"
            f"**Base64 String:**\n`{base64_str}`"
        )

        if len(formatted_msg) <= TELEGRAM_MAX_TEXT_LEN:
            await status_msg.edit_text(formatted_msg, parse_mode="Markdown")
        else:
            txt_content = format_txt_export(result)
            txt_file = io.BytesIO(txt_content)
            txt_file.name = f"{os.path.splitext(result['filename'])[0]}_base64.txt"

            await status_msg.edit_text(
                f"{caption}\n\n"
                f"ℹ️ The output exceeded Telegram's message limit and was attached as a `.txt` file."
            )
            await message.reply_document(
                document=txt_file,
                filename=txt_file.name,
                caption="📄 Contains file details, Data URI, and raw Base64 string.",
            )

    except ValueError as ve:
        err_type = str(ve)
        if err_type == "SIZE_EXCEEDED":
            await status_msg.edit_text(
                "❌ This image is too large.\n"
                "Maximum supported size: 20 MB.\n"
                "Please send a smaller image."
            )
        elif err_type in ("INVALID_IMAGE", "UNSUPPORTED_FORMAT"):
            await status_msg.edit_text(
                "❌ Unsupported file type.\n"
                "Please send a JPG, PNG, WEBP, GIF, or BMP image."
            )
        else:
            await status_msg.edit_text(
                "⚠️ Something went wrong while processing your image. Please try again."
            )
    except Exception as e:
        logger.error(f"Unexpected error during image processing: {e}", exc_info=True)
        await status_msg.edit_text(
            "⚠️ Something went wrong while processing your image. Please try again."
        )


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.critical("BOT_TOKEN environment variable is missing!")
        sys.exit(1)

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, process_image_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_non_image_text,
        )
    )

    logger.info("Starting FTDiffyybot using long polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
