import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import requests
import json


# Load the environment variables from the .env file
load_dotenv()

# Get the Telegram bot token from the environment variable
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# Define a simple command handler function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Hello! {update.message.from_user.username} send me a plate number!")
    
    # send a silent message to the admin
    await context.bot.send_message(
        chat_id=os.getenv("ADMIN__ID"),
        # text = username
        text=f"User {update.message.from_user.username} started the bot.",
        disable_notification=True,
    )


# Define a message handler function to receive and respond to text messages
async def check_plate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    plate = update.message.text
    # check if plate is valid (between 6 and 8 numbers)
    if not plate.isdigit() or len(plate) < 6 or len(plate) > 8:
        await update.message.reply_text(
            "Invalid plate number! Please enter a valid plate number."
        )
        return

    url = f"https://data.gov.il/api/3/action/datastore_search?resource_id=053cea08-09bc-40ec-8f7a-156f0677aff3&q={plate}"
    response = requests.get(url)


# Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the response as JSON
        data = response.json()
        data = data['result']['records']
        result = json.dumps(data[0], indent=5, ensure_ascii=False)
        await update.message.reply_text(f"{result}")
        
    else:
        print(f"Request failed with status code {response.status_code}")


# Main function to set up and start the bot
def main():
    if TELEGRAM_TOKEN is None:
        print("Error: No token found in the .env file")
        return

    # Create the application object
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add a handler for the /start command
    application.add_handler(CommandHandler("start", start))
    # Add a handler for receiving text messages
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, check_plate)
    )

    # Start the bot
    application.run_polling()


if __name__ == "__main__":
    main()
