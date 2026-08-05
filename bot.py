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
from utils.requestAPI import getData



# Load the environment variables from the .env file
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
LOGS_CHANNEL_ID = os.getenv("LOGS_CHANNEL_ID")

# connect to the database and create table if missing
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

# /start function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    # add user to the db using with statement
    with sqlite3.connect("./db/users.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
            (update.message.from_user.id, update.message.from_user.username),
        )
        conn.commit()

    await update.message.reply_chat_action('typing')
    await update.message.reply_text(
        f"שלום {update.message.from_user.first_name}, שלח לי מספר רכב ואני אבדוק לך את הפרטים שלו."
    )
    await add_log(f"User {update.message.from_user.username} ({update.message.from_user.id}) started the bot.", "start", context)


# Convert json to nice telegram message
def json_to_message(data):
    if not isinstance(data, dict):
        return "לא נמצאו נתונים תקינים."

    basic = data.get('basic') or {}
    model = data.get('model') or {}
    is_dead = data.get('is_dead', False)

    def clean(val):
        return str(val).strip() if val is not None and str(val).strip() != "" else None

    # עיבוד דגם משולב
    kinuy = clean(basic.get('kinuy_mishari'))
    degem = clean(basic.get('degem_nm'))
    if kinuy and degem and kinuy != degem:
        model_display = f"{kinuy} / {degem}"
    else:
        model_display = kinuy or degem or "לא ידוע"

    # טיפול בשדה סוג יבוא - יוצג רק אם קיים
    sug_yevu = clean(basic.get('sug_yevu'))
    yevu_line = f"🚢 *סוג יבוא:* {sug_yevu}\n" if sug_yevu else ""

    # רכב מבוטל - הצגת אזהרה ותאריך ביטול
    bitul_dt = clean(basic.get('bitul_dt'))
    if bitul_dt:
        # trim time part if present (e.g. "2020-07-13 00:00:00" -> "2020-07-13")
        bitul_dt = bitul_dt.split(" ")[0]
    dead_banner = f"🚫 *ירד מהכביש \ עבר ביטול סופי* 🚫\n *החל מהתאריך:* `{bitul_dt or 'לא ידוע'}`\n\n" if is_dead else ""

    carId = str(basic.get('mispar_rechev', ''))
    history = f"{data.get('kilometers')} ק\"מ" if data.get('kilometers') is not None else "לא ידוע"
    disabled = "כן" if data.get('is_disabled') == 1 else "לא"
    reRegistration = "⚠️ *רכב רשום מחדש* ⚠️\n" if carId.startswith("9") and carId.endswith("01") else ''

    engine_capacity = model.get('nefah_manoa') or basic.get('nefach_manoa')
    horse_power = model.get('koah_sus') or "לא ידוע"

    message = (
        f"{dead_banner}"
        f"🚗 *תוצאות בדיקה לרכב:* {carId}\n"
        f"🏭 *יצרן:* {clean(basic.get('tozeret_nm')) or 'לא ידוע'}\n"
        f"🚘 *דגם:* {model_display}\n"
        f"{yevu_line}"
        f"⚙️ *מנוע:* {clean(basic.get('degem_manoa')) or 'לא ידוע'}\n"
        f"🔩 *נפח מנוע:* {clean(engine_capacity) or 'לא ידוע'}\n"
        f"🐎 *כוח סוס:* {horse_power} כ\"ס\n"
        f"📅 *שנת ייצור:* `{clean(basic.get('shnat_yitzur')) or 'לא ידוע'}`\n"
        f"🛣 *תאריך עלייה לכביש:* `{clean(basic.get('moed_aliya_lakvish')) or 'לא ידוע'}`\n"
        f"🎨 *צבע:* {clean(basic.get('tzeva_rechev')) or 'לא ידוע'}\n"
        f"⛽ *סוג דלק:* {clean(basic.get('sug_delek_nm')) or 'לא ידוע'}\n"
        f"👤 *בעלות:* {clean(basic.get('baalut')) or 'לא ידוע'}\n"
        f"📝 *תוקף רישום:* `{clean(basic.get('tokef_dt')) or 'לא ידוע'}`\n"
        f"🔍 *מבחן אחרון:* `{clean(basic.get('mivchan_acharon_dt')) or 'לא ידוע'}`\n"
        f"📏 *קילומטראז':* `{history}`\n"
        f"{reRegistration}"
        f"♿ *תו נכה:* {disabled}\n\n"
        f"הופק על ידי @israelcarplatesbot"
    )

    return message

# check the plate number in the API and send the result to the user
async def check_plate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    # Ignore updates without a message (e.g., channel posts, edited messages, callbacks)
    if update.message is None or update.message.text is None:
        return
    plate = update.message.text
    user = update.message.from_user

    # check if plate is valid (between 6 and 8 numbers)
    if not plate.isdigit() or len(plate) < 6 or len(plate) > 8:
        await update.message.reply_text(
           " אנא הזן מספר רכב תקין."
        )
        await add_log(f"User {user.username} ({user.id}) entered an invalid message:", "lost", context)
        await update.message.forward(LOGS_CHANNEL_ID, disable_notification=True)
        return
    
    await update.message.reply_chat_action("typing")
    
    data = await getData(plate)
    
    if  data == None:
        await update.message.reply_text("לא נמצאו תוצאות למספר רכב זה.")
        await add_log(f"User {user.username} ({user.id}) checked plate number {plate} but no results were found.", "lost", context)
        await update.message.forward(LOGS_CHANNEL_ID, disable_notification=True)
        return 
  
    result = json_to_message(data)
                            
    await update.message.reply_text(f"{result}", parse_mode="Markdown")
    await add_log(f"User {user.username} ({user.id}) checked a plate: \n{result}", "plates", context)

        
# /broadcast admin command - send a broadcast message to all users
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

# /beta admin command to test broadcast messages 
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