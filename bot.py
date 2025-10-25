import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from datetime import datetime
import re

import os
from dotenv import load_dotenv, dotenv_values
load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN") or "Bot_Token_Not_Found"

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("MealTracker").sheet1

def get_or_create_row(date_str):
    """Find or create a row for today's date."""
    dates = sheet.col_values(1)
    if date_str in dates:
        return dates.index(date_str) + 1
    else:
        sheet.append_row([date_str])
        return len(dates) + 1

def get_or_create_column(name):
    """Find or create a column for user's name."""
    headers = sheet.row_values(1)
    if name in headers:
        return headers.index(name) + 1
    else:
        sheet.update_cell(1, len(headers) + 1, name)
        return len(headers) + 1

async def handle_meal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()  
    user = update.message.from_user.first_name.lower()
    match = re.search(r"meal\s+(\d+)", text)
    
    if match:
        meal_value = match.group(1)
        date_str = datetime.now().strftime("%Y-%m-%d")

        row = get_or_create_row(date_str)
        col = get_or_create_column(user)

        sheet.update_cell(row, col, meal_value)
        await update.message.reply_text(f"✅ Meal entry recorded for {user}: {meal_value}")
    else:
        await update.message.reply_text("⚠️ Format: `@MealBot meal <number>`")

async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN ).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_meal))
    await app.run_polling()

import asyncio
if __name__ == "__main__":
    asyncio.run(main())
