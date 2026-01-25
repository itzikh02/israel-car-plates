# Israel Car Plates Telegram Bot

A Telegram bot that receives Israeli car plate numbers as input and generates a detailed report with almost all possible information extracted from public government databases. This includes registration dates, technical specifications, and more.

---

## Features

- Input car plate numbers via Telegram.
- Fetch and display:
  - Registration dates
  - Vehicle specifications (make, model, engine type, year, etc.)
  - Any publicly available governmental information related to the vehicle
- Quick, concise reports for each vehicle
- Easy to use through Telegram chat interface

---

## Requirements

- Any running server
- Telegram account and bot from BotFather
- Python 3.11
- `python-telegram-bot` Python library

---

## Installation

1. Clone the repository and navigate into it:

```bash
git clone https://github.com/yourusername/israel-car-plates.git
cd israel-car-plates
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables (.env file):

- `TELEGRAM_TOKEN` — Your Telegram bot token from BotFather
- `LOGS_CHANNEL_ID` - Telegram channel id, will be used as logs channel.
   - Don't forget to add the bot and give him messages prmissions.
- `ADMIN_ID` - Your account id to use as admin.

---

## Usage

1. Run the bot:

```bash
python bot.py
```

2. Open Telegram and start a chat with your bot.
3. Send an Israeli car plate number (e.g., `1234567`).
4. Receive a detailed report about the vehicle.

---

## Bot commands



`/start` - Start the bot

`/broadcast <Message>` - Send a broadcast to all the bot subscribers

`/beta <Message>` - Send a test broadcast to view the message as a subscriber.

---

## Security & Privacy

- This bot only fetches information available in public government records.
- Do not share sensitive personal information in the chat.
- Ensure Telegram keys and tokens are kept secret.

---

## Contributing

Contributions are welcome! You can:

- Add support for more detailed vehicle data
- Improve report formatting
- Add caching to reduce API calls

Please submit pull requests or open issues for suggestions.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
