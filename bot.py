#setup + debugging section
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
from huggingface_hub import InferenceClient

#Greeting msg send by bot
first_time_users = set()

# USER STATE [A dictionary (user_state = {}) that remembers what a user is currently doing]
user_state = {}

# HUGGING FACE DOBBY AI SETUP [Connects the bot to Hugging Face’s AI model Dobby]
HF_TOKEN = os.getenv("HF_TOKEN")

dobby_client = InferenceClient(
    model="SentientAGI/Dobby-Mini-Unhinged-Llama-3.1-8B",
    token=HF_TOKEN
)

def get_dobby_response(user_question):
    try:
        response = dobby_client.chat.completions.create(
            model="SentientAGI/Dobby-Mini-Unhinged-Llama-3.1-8B",
            messages=[
                {"role": "system", "content": "You are Dobby AI, assistant for Sentient community."},
                {"role": "user", "content": user_question}
            ],
            max_tokens=300,
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"Error: {str(e)}"

# CONFIG [Stores important IDs like bot owner TG id] [Not in use for now]
#OWNER_ID = 6141979711 

#GOOGLE FORM [Usecase for user: if any problem arises in bot answer or for other query]
FORM_LINK = "https://forms.gle/PoFCvvGboz4E9dJv6"

#QUERY CATEGORIES [Predefined FAQ database]
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

# START COMMAND [Defines /start command in tg bot]
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_state[user_id] = None

    #FIRST-TIME GREETING (appears only once per user)
    if user_id not in first_time_users:
        first_time_users.add(user_id)
        await update.message.reply_text(
            "👋 Hey there!\nThis is Sentient Bot (⚠️Unofficial).\n"
            "Type /start anytime to open the main menu."
        )


    keyboard = [
        [InlineKeyboardButton("Sentient Query", callback_data="sentient_query")],
        [InlineKeyboardButton("Ask Dobby AI Anything", callback_data="ask_dobby")],
        [InlineKeyboardButton("Live Crypto Prices", callback_data="crypto")]
    ]
    await update.message.reply_text(
        "Welcome to Sentient Helper Bot! Choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# BUTTON CALLBACK [Handles button clicks, this section control all the flow of command given to user]
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # Show category list + Google Form link
    if data == "sentient_query":
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat|{cat}")] for cat in query_categories]
        keyboard.append([InlineKeyboardButton("Any other question (click here)", url=FORM_LINK)])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        await query.edit_message_text(
            "Select a category:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Show questions for a category
    elif data.startswith("cat|"):
        category = data.split("|", 1)[1]
        keyboard = [[InlineKeyboardButton(q, callback_data=f"q|{category}|{q}")] for q in query_categories[category]]
        keyboard.append([InlineKeyboardButton("Any other question (click here)", url=FORM_LINK)])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="sentient_query")])
        await query.edit_message_text(
            f"Category: {category}\nSelect a question:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Show answer for a selected question using predefined FAQ
    elif data.startswith("q|"):
        _, category, question = data.split("|", 2)
        answer = query_categories[category][question]
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=f"cat|{category}")]]
        await query.edit_message_text(
            f"Q: {question}\n\nA: {answer}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Go back to main menu
    elif data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("Sentient Query", callback_data="sentient_query")],
            [InlineKeyboardButton("Ask Dobby AI Anything", callback_data="ask_dobby")],
            [InlineKeyboardButton("Live Crypto Prices", callback_data="crypto")]
        ]
        await query.edit_message_text("Welcome back to main menu! Choose an option:",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    # Ask Dobby anything flow
    elif data == "ask_dobby":
        await query.edit_message_text("Ask me anything about Sentient! Type your question:")
        user_state[user_id] = "waiting_dobby"

    # Live crypto flow
    elif data == "crypto":
        await query.edit_message_text("Send the crypto symbol (e.g., BTC, ETH, DOGE). Use lowercase coin id like 'bitcoin'.")
        user_state[user_id] = "waiting_crypto"

# MESSAGE HANDLER [Processes normal text messages from users]
async def custom_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # ---- Dobby AI flow ----
    if user_state.get(user_id) == "waiting_dobby":
        await update.message.reply_text("🤔 Thinking...")
        answer = get_dobby_response(text)
        await update.message.reply_text(f"Dobby says:\n\n{answer}")
        return

    # ---- Crypto price flow ----
    if user_state.get(user_id) == "waiting_crypto":
        price = get_crypto_price(text.lower())
        if price is not None:
            await update.message.reply_text(f"💰 Current price of {text.upper()} is ${price}")
        else:
            await update.message.reply_text("❌ Sorry, I couldn't find that crypto symbol.")
        user_state[user_id] = None
        return

    # ---- Default ----
    await update.message.reply_text("Use /start to begin!")

# CRYPTO PRICE FUNCTION (Uses CoinGecko API to fetch live USD price of a crypto)
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

#MAIN [Entry point of the bot] 
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, custom_question))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()