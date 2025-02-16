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

import sqlite3
import datetime
from betterReq import getData



# Load the environment variables from the .env file
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
LOGS_CHANNEL_ID = os.getenv("LOGS_CHANNEL_ID")

conn = sqlite3.connect("./db/users.db")
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT
    )
    """
)
conn.commit()
conn.close()


# send logs to file and to logs channel
async def add_log(log, log_file, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    log = f"{now.strftime('%Y-%m-%d %H:%M:%S')} {log}"
    with open(f"./logs/{log_file}.log", "a") as f:
        f.write(log + "\n")
    
    # send the log to the logs channel
    await context.bot.send_message(chat_id=LOGS_CHANNEL_ID, text=log, parse_mode="Markdown", disable_notification=True)


# Define a simple command handler function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    # add user to the db using with statement
    with sqlite3.connect("./db/users.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
            (update.message.from_user.id, update.message.from_user.username),
        )
        conn.commit()

    await update.message.reply_text(
        f"שלום {update.message.from_user.first_name}, שלח לי מספר רכב ואני אבדוק לך את הפרטים שלו."
    )



    await add_log(f"User {update.message.from_user.username} ({update.message.from_user.id}) started the bot.", "start", context)


# Convert json to nice telegram message
def json_to_message(data):
    basic = data['basic']
    model = data['model']
    history = f"{data['history']} ק\"מ\n" if data['history'] != None else "לא ידוע"
    disabled = "כן" if data['disabled'] == 1 else "לא"

    # replace all None values with "לא ידוע"
    for key, value in basic.items():
        if value == None:
            basic[key] = "לא ידוע"

    message = (
        f"🚗 *תוצאות בדיקה לרכב:* {basic['mispar_rechev']}\n"
        f"🏭 *יצרן:* {basic['tozeret_nm']}\n"
        f"🚘 *דגם:* {basic['kinuy_mishari']}\n"
        f"🔢 *מספר דגם:* {basic['degem_nm']}\n"
        f"⚙️ *מנוע:* {basic['degem_manoa']}\n"
        f"🔩 *נפח מנוע:* {model['nefah_manoa']}\n"
        f"📅 *שנת ייצור:* `{basic['shnat_yitzur']}`\n"
        f"🛣 *תאריך עלייה לכביש:* `{basic['moed_aliya_lakvish']}`\n"
        f"🎨 *צבע:* {basic['tzeva_rechev']}\n"
        f"⛽ *סוג דלק:* {basic['sug_delek_nm']}\n"
        f"👤 *בעלות:* {basic['baalut']}\n"
        f"📝 *תוקף רישום:* `{basic['tokef_dt']}`\n"
        f"🔍 *מבחן אחרון:* `{basic['mivchan_acharon_dt']}`\n"
        f"📏 *קילומטראז':* `{history}`\n"
        f"♿ *תו נכה:* {disabled}\n\n"
        f"הופק על ידי @israelcarplatesbot\n"
    )

    return message

# check the plate number in the API and send the result to the user
async def check_plate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    plate = update.message.text
    user = update.message.from_user

    # check if plate is valid (between 6 and 8 numbers)
    if not plate.isdigit() or len(plate) < 6 or len(plate) > 8:
        await update.message.reply_text(
            "מספר רכב לא תקין, אנא הזן מספר רכב תקין."
        )
        await add_log(f"User {user.username} ({user.id}) entered an invalid message:", "lost", context)
        await update.message.forward(LOGS_CHANNEL_ID, disable_notification=True)
        return
    
    await update.message.reply_chat_action("typing")
    
    data = getData(plate)
    
    if  data == None:
        await update.message.reply_text("לא נמצאו תוצאות למספר רכב זה.")
        await add_log(f"User {user.username} ({user.id}) checked plate number {plate} but no results were found.", "lost", context)
        await update.message.forward(LOGS_CHANNEL_ID, disable_notification=True)
        return 
  
    result = json_to_message(data)
                            
    await update.message.reply_text(f"{result}", parse_mode="Markdown")
    await add_log(f"User {user.username} ({user.id}) checked plate number {plate}", "plates", context)
    await update.message.forward(LOGS_CHANNEL_ID, disable_notification=True)

        
# admin command to send a broadcast message to all users
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = " ".join(context.args)
    message = message.replace("\\n", "\n")  # Replace literal "\n" with a newline
    if str(update.message.from_user.id) != str(ADMIN_ID):
        log = f"Unauthorized user {update.message.from_user.username} ({update.message.from_user.id}) tried to send a broadcast message: {message}"
        await add_log(log, "security", context)
        await update.message.forward(LOGS_CHANNEL_ID, disable_notification=True)
        return

    # get all users from the db using with statement
    with sqlite3.connect("./db/users.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

    # Send the message to all the users
    for user in users:
        await context.bot.send_message(chat_id=user["id"], text=message, parse_mode="Markdown")

    await update.message.reply_text(f"Broadcast message sent to {len(users)} users.")

async def beta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = " ".join(context.args)
    message = message.replace("\\n", "\n")  # Replace literal "\n" with a newline
    if str(update.message.from_user.id) != str(ADMIN_ID):
        log = f"Unauthorized user {update.message.from_user.username} ({update.message.from_user.id}) tried to send a broadcast message: {message}"
        await add_log(log, "security", context)
        await update.message.forward(LOGS_CHANNEL_ID, disable_notification=True)
        return

    await context.bot.send_message(chat_id=ADMIN_ID, text=message, parse_mode="Markdown")


# Main function to set up and start the bot
def main():
    if TELEGRAM_TOKEN is None:
        print("Error: No token found in the .env file")
        return

    # Create the application object
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("beta", beta))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, check_plate)
    )

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()