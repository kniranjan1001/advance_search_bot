from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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

# Create FastAPI app
app = FastAPI()

# A global set to store unique user IDs
user_ids = set()

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
        # Fetch movie data from the JSON URL
        movie_data = fetch_movie_data()

        # Initialize a list to hold button objects
        buttons = []

        # Iterate through movie data and create buttons
        for key, value in movie_data.items():
            if movie_name.lower() in key.lower():
                buttons.append(InlineKeyboardButton(text=key, url=value))

        # Create the inline keyboard markup
        if buttons:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[button] for button in buttons])
            return keyboard
        else:
            return "Movie not found! 😿 \n👉 Please check the spelling or send the exact name.\n👉 If it's still missing, kindly search @cc_new_movie 🎬"
    except Exception as e:
        logger.error(f"Error searching movie data: {e}")
        return "An error😿 occurred while searching for the movie."

# Function to handle movie search requests
async def search_movie(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id not in user_ids:
        user_ids.add(user_id)
        logger.info(f"New user added: {user_id}")

    movie_name = update.message.text.strip()

    # Show 'typing' action to indicate loading
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action='typing')

    # Send a creative message with simulated loading
    loading_message = await update.message.reply_text("🔍 Searching the movie vaults... 🍿 Hang tight while we find your movie! 🎬")

    # Search for the movie in the JSON data
    result = await search_movie_in_json(movie_name)

    if isinstance(result, InlineKeyboardMarkup):
        # Edit the loading message with the result
        await loading_message.edit_text(f"Search🔍 results for '{movie_name}' 🍿 :", reply_markup=result)
    else:
        # Edit the loading message with the error message
        await loading_message.edit_text(result)

# Function to handle the '/search <movie_name>' command
async def search_command(update: Update, context: CallbackContext) -> None:
    if context.args:
        movie_name = " ".join(context.args).strip()
        await search_movie(update, context)
    else:
        await update.message.reply_text("Please provide a movie name. Usage: /search <movie_name>")

# Function to handle the '/start' command
async def start_command(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id not in user_ids:
        user_ids.add(user_id)
        logger.info(f"New user added: {user_id}")

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

# Initialize the application
application = Application.builder().token(BOT_TOKEN).build()

# Add command handlers
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("search", search_command))

# Add message handler for text messages
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))

# Add callback query handler for button presses
application.add_handler(CallbackQueryHandler(button_callback))

# Set webhook
@app.post(f'/{BOT_TOKEN}')
async def webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, application.bot)
    application.update_queue.put(update)
    return JSONResponse(content={"status": "ok"})

if __name__ == "__main__":
    # Run the FastAPI application
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
