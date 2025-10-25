import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from datetime import datetime
import re
import json
import os

# ========== CONFIG ==========
ADMIN_IDS = [123456789]  # Replace with your Telegram user ID(s)
CONFIG_FILE = "config.json"
CREDENTIALS_FILE = "credentials.json"

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)

# ========== UTILS ==========

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"sheet_id": ""}, f)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

def get_sheet():
    config = load_config()
    sheet_id = config.get("sheet_id", "")
    if not sheet_id:
        raise ValueError("No Google Sheet linked. Admin must use /update <link> first.")
    spreadsheet = client.open_by_key(sheet_id)
    return spreadsheet.get_worksheet(1)  # 2nd sheet (index = 1)

def extract_sheet_id(link: str) -> str:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", link)
    return match.group(1) if match else None

def get_or_create_row(sheet, date_str):
    dates = sheet.col_values(1)
    if date_str in dates:
        return dates.index(date_str) + 1
    else:
        sheet.append_row([date_str])
        return len(dates) + 1

def get_or_create_column(sheet, name):
    headers = sheet.row_values(1)
    if name in headers:
        return headers.index(name) + 1
    else:
        sheet.update_cell(1, len(headers) + 1, name)
        return len(headers) + 1

# ========== COMMANDS ==========

async def update_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to update the sheet.")
        return
    
    if len(context.args) == 0:
        await update.message.reply_text("⚠️ Usage: /update <Google Sheet link>")
        return

    link = context.args[0]
    sheet_id = extract_sheet_id(link)
    if not sheet_id:
        await update.message.reply_text("⚠️ Invalid Google Sheet link.")
        return

    config = load_config()
    config["sheet_id"] = sheet_id
    save_config(config)

    await update.message.reply_text("✅ Google Sheet link updated successfully! Using 2nd sheet now.")

async def handle_meal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user = update.message.from_user.first_name.lower()
    match = re.search(r"meal\s+(\d+)", text)

    if not match:
        return  # Ignore non-meal messages

    meal_value = match.group(1)
    date_str = datetime.now().strftime("%Y-%m-%d")

    try:
        sheet = get_sheet()
    except Exception as e:
        await update.message.reply_text(f"⚠️ {str(e)}")
        return

    row = get_or_create_row(sheet, date_str)
    col = get_or_create_column(sheet, user)
    sheet.update_cell(row, col, meal_value)

    await update.message.reply_text(f"✅ Meal entry recorded for {user}: {meal_value}")

# ========== MAIN ==========

async def main():
    app = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
    app.add_handler(CommandHandler("update", update_sheet))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_meal))
    await app.run_polling()

import asyncio
if __name__ == "__main__":
    asyncio.run(main())
