from dotenv import load_dotenv
import os

load_dotenv()

print("DEBUG: Current folder:", os.getcwd())
print("DEBUG: .env exists:", os.path.isfile(".env"))

TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
print("DEBUG: TOKEN =", TOKEN)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import requests

# ---- CONFIG ----
OWNER_ID = 6141979711
TEAM_CHAT_ID = 6141979711  # kept but not used for forwarding anymore

# ---- GOOGLE FORM ----
FORM_LINK = "https://forms.gle/PoFCvvGboz4E9dJv6"

# ---- QUERY CATEGORIES ----
query_categories = {
    "About Sentient": {
        "What is Sentient?": (
            "Open-source, community-driven Artificial General Intelligence (AGI).\n"
            "Focuses on 'Loyal AI' with tools like ROMA, GRID, and Sentient Chat, using blockchain for governance.\n"
            "For more detail you can check this thread:\nhttps://x.com/Zun2025/status/1972979253059666085."
        ),
        "How to connect with Sentient?": "You can join via our website:\nhttps://www.sentient.xyz/"
    },
    "Incentive": {
        "Is there any incentive program ongoing?": (
            "Yes, there is an incentive program for people who can contribute in Sentient from these 4 categories:\n"
            "1. Helper\n2. Builder\n3. Artist\n4. Educator\n\n"
            "You can check more about this from role option."
        )
    },
    "Role": {
        "How many Discord roles are there?": (
            "There are 4 types of roles in Discord and each role has its own level starting from L1, L2, L3,\n"
            "along with Early, Advance, and Sentient AGI role."
        ),
        "Can I apply for early AGI role without hitting level 3?": (
            "The answer is yes,\n"
            "If you think your contribution is worth it then go for it,\n"
            "Team will sure give you the role."
        )
    }
}

# ---- USER STATE ----
user_state = {}

# ---- START COMMAND ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Sentient Query", callback_data="sentient_query")],
        [InlineKeyboardButton("Live Crypto Prices", callback_data="crypto")]
    ]
    await update.message.reply_text(
        "Welcome to Sentient Helper Bot! Choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---- ADD Q&A COMMAND (admin only) ----
async def add_qa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Not authorized.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /add_qa <Category> <Question> <Answer>")
        return
    category = context.args[0]
    question = context.args[1]
    answer = " ".join(context.args[2:])
    if category not in query_categories:
        query_categories[category] = {}
    query_categories[category][question] = answer
    await update.message.reply_text(f"✅ Q&A added to category '{category}' successfully.")

# ---- BUTTON CALLBACK ----
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # Show category list + Google Form link
    if data == "sentient_query":
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat|{cat}")] for cat in query_categories]
        # Add the Google Form link as the last row
        keyboard.append([InlineKeyboardButton("Any other question (click here)", url=FORM_LINK)])
        await query.edit_message_text(
            "Select a category:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Show questions for a category, last row redirects to Google Form
    elif data.startswith("cat|"):
        category = data.split("|", 1)[1]
        keyboard = [[InlineKeyboardButton(q, callback_data=f"q|{category}|{q}")] for q in query_categories[category]]
        # Replace previous "Other Question" with direct form link
        keyboard.append([InlineKeyboardButton("Any other question (click here)", url=FORM_LINK)])
        await query.edit_message_text(
            f"Category: {category}\nSelect a question:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Show answer for a selected question
    elif data.startswith("q|"):
        _, category, question = data.split("|", 2)
        answer = query_categories[category][question]
        await query.edit_message_text(f"Q: {question}\n\nA: {answer}")

    # Live crypto flow: ask user to send symbol and set waiting state
    elif data == "crypto":
        await query.edit_message_text("Send the crypto symbol (e.g., BTC, ETH, DOGE). Use lowercase coin id like 'bitcoin'.")
        user_state[user_id] = "waiting_crypto"

# ---- MESSAGE HANDLER: handles only crypto replies (no forwarding anymore) ----
async def custom_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # Crypto price flow only
    if user_state.get(user_id) == "waiting_crypto":
        price = get_crypto_price(text.lower())
        if price is not None:
            await update.message.reply_text(f"💰 Current price of {text.upper()} is ${price}")
        else:
            await update.message.reply_text("❌ Sorry, I couldn't find that crypto symbol. Use lowercase coin id like 'bitcoin'.")
        user_state[user_id] = None
        return

    # If user types random text, guide them to /start
    await update.message.reply_text("Use /start and choose 'Sentient Query' or 'Live Crypto Prices'.")

# ---- CRYPTO PRICE FUNCTION ----
def get_crypto_price(symbol):
    coin_map = {
        'btc': 'bitcoin',
        'eth': 'ethereum',
        'bnb': 'binancecoin',
        'doge': 'dogecoin'
    }
    coin_id = coin_map.get(symbol, symbol)
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd'
    try:
        response = requests.get(url).json()
        return response[coin_id]['usd']
    except:
        return None

# ---- MAIN ----
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_qa", add_qa))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, custom_question))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()