from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
import logging
import requests
import os

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')  # Your Telegram bot token
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID'))  # Your Telegram user ID
JSON_URL = os.getenv('JSON_URL')  # URL where your JSON data is stored

# A global set to store unique user IDs
user_ids = set()

# Create FastAPI app instance
app = FastAPI()

# Initialize the Telegram application
telegram_app = Application.builder().token(BOT_TOKEN).build()

# Function to fetch movie data from JSON URL
def fetch_movie_data():
    try:
        response = requests.get(JSON_URL)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()  # Return the JSON data as a dictionary
    except requests.RequestException as e:
        logger.error(f"Error fetching data from JSON URL: {e}")
        return {}

# Function to search for the movie in the JSON data
async def search_movie_in_json(movie_name: str):
    try:
        movie_data = fetch_movie_data()
        buttons = []
        for key, value in movie_data.items():
            if movie_name.lower() in key.lower():
                buttons.append(InlineKeyboardButton(text=key, url=value))
        if buttons:
            return InlineKeyboardMarkup(inline_keyboard=[[button] for button in buttons])
        else:
            return "Movie not found! 😿 Please check the spelling or send the exact name."
    except Exception as e:
        logger.error(f"Error searching movie data: {e}")
        return "An error occurred while searching for the movie."

# Function to handle incoming webhook requests from Telegram
@app.post(f"/{BOT_TOKEN}")
async def handle_webhook(request: Request):
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, telegram_app.bot)
        await telegram_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing the update: {e}")
        return {"status": "error", "message": str(e)}

# Function to handle the '/start' command
async def start_command(update: Update, context: CallbackContext) -> None:
    about_button = InlineKeyboardButton(text="About🧑‍💻", callback_data='about')
    request_movie_button = InlineKeyboardButton(text="Request Movie😇", url='https://t.me/anonyms_middle_man_bot')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[about_button], [request_movie_button]])
    welcome_message = (
       "\tWelcome to the Movie Search Bot! 🎬🍿\n"
       "Search🔍 for your favorite movies easily!\n"
       "Type correct movie🍿 name or use the command:\n"
       "```\n/search <movie_name>\n```\n"
       "Enjoy your content😎"
    )
    await update.message.reply_text(welcome_message, reply_markup=keyboard)

# Function to search for a movie
async def search_movie(update: Update, context: CallbackContext) -> None:
    movie_name = update.message.text.strip()
    result = await search_movie_in_json(movie_name)

    if isinstance(result, InlineKeyboardMarkup):
        await update.message.reply_text(f"Search results for '{movie_name}' 🍿:", reply_markup=result)
    else:
        await update.message.reply_text(result)

# Function to handle button callbacks
async def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == 'about':
        about_message = (
            "🤖 *About the Bot*:\n"
            "This bot allows users to search for movies by name.\n"
            "*Developer*: [Harsh](https://t.me/Harsh_Raj1)\n"
            "Use the bot to find movie links and request movies!"
        )
        await query.edit_message_text(about_message, parse_mode="Markdown")

# Function to handle broadcasting messages
async def broadcast_message(update: Update, context: CallbackContext):
    if update.message.chat_id == ADMIN_USER_ID:
        message = " ".join(context.args)
        if message:
            for user_id in user_ids:
                try:
                    await context.bot.send_message(chat_id=user_id, text=message)
                except Exception as e:
                    logger.error(f"Failed to send message to {user_id}: {e}")
            await update.message.reply_text("Message broadcasted to all users!")
        else:
            await update.message.reply_text("Please provide a message to broadcast.")
    else:
        await update.message.reply_text("Unauthorized! Only the admin can use this command.")

# Function to handle user list display (admin only)
async def user_list_command(update: Update, context: CallbackContext):
    if update.message.chat_id == ADMIN_USER_ID:
        user_list = "\n".join([str(user_id) for user_id in user_ids])
        await update.message.reply_text(f"List of connected users:\n{user_list or 'No users connected.'}")

# Add handlers to the Telegram application
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("broadcast", broadcast_message))
telegram_app.add_handler(CommandHandler("userlist", user_list_command))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
telegram_app.add_handler(CallbackQueryHandler(button_callback))

# In your Vercel setup, you'll use this FastAPI app to handle webhooks
