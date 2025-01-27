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
import sqlite3
import datetime

# Load the environment variables from the .env file
load_dotenv()

# Get the Telegram bot token from the environment variable
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# connect to the database, create a table if it doesn't exist

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

# send logs to ./logs/security.log or plates.log
def add_log(log, log_file):
    now = datetime.datetime.now()
    log = f"{now.strftime('%Y-%m-%d %H:%M:%S')} {log}"
    with open(f"./logs/{log_file}.log", "a") as f:
        f.write(log + "\n")



# Define a simple command handler function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # add user to the db using with statement
    with sqlite3.connect("./db/users.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (id, username) VALUES (?, ?)",
            (update.message.from_user.id, update.message.from_user.username),
        )
        conn.commit()

    await update.message.reply_text(
        f"Hello! {update.message.from_user.username} send me a plate number!"
    )

    # send a silent message to the admin
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"User {update.message.from_user.username} started the bot.",
        disable_notification=True,
    )


# Convert json to nice telegram message
def json_to_message(data):
    #     {
    #      "_id": 3845250,
    #      "mispar_rechev": 1515766,
    #      "tozeret_cd": 588,
    #      "sug_degem": "P",
    #      "tozeret_nm": "מזדה יפן",
    #      "degem_cd": 201,
    #      "degem_nm": "DE145",
    #      "ramat_gimur": "DYNAMIC",
    #      "ramat_eivzur_betihuty": null,
    #      "kvutzat_zihum": 15,
    #      "shnat_yitzur": 2008,
    #      "degem_manoa": "ZY",
    #      "mivchan_acharon_dt": "2025-01-19",
    #      "tokef_dt": "2026-01-20",
    #      "baalut": "פרטי",
    #      "misgeret": "JMZDE1455-80116998",
    #      "tzeva_cd": 30,
    #      "tzeva_rechev": "כחול",
    #      "zmig_kidmi": "185/55R15",
    #      "zmig_ahori": "185/55R15",
    #      "sug_delek_nm": "בנזין",
    #      "horaat_rishum": null,
    #      "moed_aliya_lakvish": null,
    #      "kinuy_mishari": "MAZDA 2",
    #      "rank": 0.0573088
    # }
    message = (
        f"*תוצאות בדיקה למספר רכב: {data[0]['mispar_rechev']}\n*"
        f"*יצרן:* {data[0]['tozeret_nm']}\n"
        f"*דגם:* {data[0]['kinuy_mishari']}\n"
        f"*מספר דגם:* {data[0]['degem_nm']}\n"
        f"*מנוע:* {data[0]['degem_manoa']}\n"
        f"*שנת יצור:* {data[0]['shnat_yitzur']}\n"
        f"*תאריך עלייה לכביש:* {data[0]['moed_aliya_lakvish']}\n"
        f"*צבע:* {data[0]['tzeva_rechev']}\n"
        f"*סוג דלק:* {data[0]['sug_delek_nm']}\n"
        f"*בעלות:* {data[0]['baalut']}\n"
        f"*תוקף רישום:* {data[0]['tokef_dt']}\n"
        f"*מבחן אחרון:* {data[0]['mivchan_acharon_dt']}\n"
        f"-------------------\n"
    )

    return message


# check the plate number in the API and send the result to the user
async def check_plate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    plate = update.message.text
    # check if plate is valid (between 6 and 8 numbers)
    if not plate.isdigit() or len(plate) < 6 or len(plate) > 8:
        await update.message.reply_text(
            "Invalid plate number! Please enter a valid plate number."
        )
        add_log(f"User {update.message.from_user.username} ({update.message.from_user.id}) entered an invalid plate number {plate}", "lost")
        return

    url = f"https://data.gov.il/api/3/action/datastore_search?resource_id=053cea08-09bc-40ec-8f7a-156f0677aff3&q={plate}"
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the response as JSON
        data = response.json()
        if data["result"]["total"] == 0:
            await update.message.reply_text("אין תוצאות למספר רכב זה")
            add_log(f"User {update.message.from_user.username} ({update.message.from_user.id}) entered a non existing plate number {plate}", "lost")
            return
        result = json_to_message(data["result"]["records"])
        await update.message.reply_text(f"{result}", parse_mode="Markdown")
        add_log(f"User {update.message.from_user.username} ({update.message.from_user.id}) checked plate number {plate}", "plates")
    else:
        await update.message.reply_text(
            "שגיאת תקשורת, אנא נסה שוב מאוחר יותר."
        )
        add_log(f"User {update.message.from_user.username} ({update.message.from_user.id}) tried to check plate number {plate} but got an error", "lost")
        


# admin command to send a broadcast message to all users
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.from_user.id) != str(ADMIN_ID):
        log = f"Unauthorized user {update.message.from_user.username} ({update.message.from_user.id}) tried to send a broadcast message."
        add_log(log, "security")
        return

    # get all users from the db using with statement
    with sqlite3.connect("./db/users.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

    # Send the message to all the users
    for user in users:
        await context.bot.send_message(chat_id=user["id"], text=context.args[0])

    await update.message.reply_text(f"Broadcast message sent to {len(users)} users.")


# Main function to set up and start the bot
def main():
    if TELEGRAM_TOKEN is None:
        print("Error: No token found in the .env file")
        return

    # Create the application object
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, check_plate)
    )

    # Start the bot
    application.run_polling()


if __name__ == "__main__":
    main()
