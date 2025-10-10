# SETUP + DEBUGGING 
from dotenv import load_dotenv
import os, requests, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from huggingface_hub import InferenceClient
from flask import Flask, request, jsonify
import threading

load_dotenv()

print("DEBUG: Current folder:", os.getcwd())
print("DEBUG: .env exists:", os.path.isfile(".env"))

TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
print("DEBUG: TOKEN =", TOKEN)

# HUGGING FACE DOBBY AI 
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

# QUILLCHECK ASYNC
def get_quillcheck_analysis(symbol):
    try:
        query = f"Give a short crypto analysis for {symbol.upper()} (trend, sentiment, major movements)."
        response = dobby_client.chat.completions.create(
            model="SentientAGI/Dobby-Mini-Unhinged-Llama-3.1-8B",
            messages=[
                {"role": "system", "content": "You are QuillCheck, the Sentient crypto analysis agent."},
                {"role": "user", "content": query}
            ],
            max_tokens=150,
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"Error getting analysis: {str(e)}"

async def get_quillcheck_analysis_async(symbol):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_quillcheck_analysis, symbol)

# USER STATE 
first_time_users = set()
user_state = {}
FORM_LINK = "https://forms.gle/PoFCvvGboz4E9dJv6"

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

# START COMMAND 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_state[user_id] = None

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

# BUTTON CALLBACK 
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "sentient_query":
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat|{cat}")] for cat in query_categories]
        keyboard.append([InlineKeyboardButton("Any other question (click here)", url=FORM_LINK)])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        await query.edit_message_text(
            "Select a category:", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("cat|"):
        category = data.split("|", 1)[1]
        keyboard = [[InlineKeyboardButton(q, callback_data=f"q|{category}|{q}")] for q in query_categories[category]]
        keyboard.append([InlineKeyboardButton("Any other question (click here)", url=FORM_LINK)])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="sentient_query")])
        await query.edit_message_text(
            f"Category: {category}\nSelect a question:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("q|"):
        _, category, question = data.split("|", 2)
        answer = query_categories[category][question]
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=f"cat|{category}")]]
        await query.edit_message_text(f"Q: {question}\n\nA: {answer}",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("Sentient Query", callback_data="sentient_query")],
            [InlineKeyboardButton("Ask Dobby AI Anything", callback_data="ask_dobby")],
            [InlineKeyboardButton("Live Crypto Prices", callback_data="crypto")]
        ]
        await query.edit_message_text("Welcome back to main menu! Choose an option:",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "ask_dobby":
        await query.edit_message_text("Ask me anything about Sentient! Type your question:")
        user_state[user_id] = "waiting_dobby"

    elif data == "crypto":
        await query.edit_message_text(
            "Send the crypto symbol (e.g., BTC, ETH, SOL, DOGE).\n💡 Tip: You can also use /price BTC for quick access!")
        user_state[user_id] = "waiting_crypto"

# MESSAGE HANDLER
async def custom_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_state.get(user_id) == "waiting_dobby":
        await update.message.reply_text("🤔 Thinking...")
        answer = get_dobby_response(text)
        await update.message.reply_text(f"Dobby says:\n\n{answer}")
        user_state[user_id] = None
        return

    if user_state.get(user_id) == "waiting_crypto":
        await update.message.reply_text("📊 Fetching crypto data...")
        crypto_data = get_crypto_price_with_analysis(text.lower())

        # Async QuillCheck AI analysis
        quill_analysis = await get_quillcheck_analysis_async(text.lower())
        if crypto_data:
            crypto_data['quillcheck_analysis'] = quill_analysis

        formatted_response = format_crypto_response(crypto_data)
        await update.message.reply_text(formatted_response, parse_mode='Markdown')

        keyboard = [
            [InlineKeyboardButton("Check Another Crypto", callback_data="crypto")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        await update.message.reply_text("What would you like to do next?",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
        user_state[user_id] = None
        return

    await update.message.reply_text("Use /start to begin!")

#CRYPTO HELPERS
def get_crypto_price_with_analysis(symbol):
    coin_map = {
        'btc': 'bitcoin', 'eth': 'ethereum', 'bnb': 'binancecoin', 'doge': 'dogecoin',
        'ada': 'cardano', 'dot': 'polkadot', 'matic': 'matic-network', 'sol': 'solana',
        'avax': 'avalanche-2', 'link': 'chainlink', 'atom': 'cosmos', 'xrp': 'ripple',
    }
    coin_id = coin_map.get(symbol.lower(), symbol.lower())
    url = f'https://api.coingecko.com/api/v3/coins/markets'
    params = {'vs_currency': 'usd', 'ids': coin_id, 'order': 'market_cap_desc',
              'sparkline': 'false', 'price_change_percentage': '24h,7d'}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data and len(data) > 0:
            coin_data = data[0]
            result = {
                'name': coin_data.get('name', 'Unknown'),
                'symbol': coin_data.get('symbol', '').upper(),
                'current_price': coin_data.get('current_price', 0),
                'price_change_24h': coin_data.get('price_change_percentage_24h', 0),
                'market_cap': coin_data.get('market_cap', 0),
                'total_volume': coin_data.get('total_volume', 0),
                'high_24h': coin_data.get('high_24h', 0),
                'low_24h': coin_data.get('low_24h', 0),
                'market_cap_rank': coin_data.get('market_cap_rank', 'N/A')
            }
            # Sentiment
            pc = result['price_change_24h']
            result['sentiment'] = '🚀 Very Bullish' if pc > 5 else '📈 Bullish' if pc > 2 else \
                                  '➕ Slightly Bullish' if pc > 0 else '➖ Slightly Bearish' if pc > -2 else \
                                  '📉 Bearish' if pc > -5 else '🔻 Very Bearish'
            return result
        else:
            return None
    except Exception as e:
        print(f"Error fetching crypto data: {e}")
        return None

def format_crypto_response(crypto_data):
    if not crypto_data:
        return "❌ Sorry, I couldn't find that crypto symbol. Try common ones like BTC, ETH, SOL, etc."

    def format_number(num):
        if num >= 1_000_000_000: return f"${num/1_000_000_000:.2f}B"
        elif num >= 1_000_000: return f"${num/1_000_000:.2f}M"
        elif num >= 1_000: return f"${num/1_000:.2f}K"
        else: return f"${num:.2f}"

    arrow = "↑" if crypto_data['price_change_24h'] > 0 else "↓" if crypto_data['price_change_24h'] < 0 else "→"
    response = f"""
📊 **{crypto_data['name']} ({crypto_data['symbol']})**
━━━━━━━━━━━━━━━━━━━━
💰 **Current Price:** ${crypto_data['current_price']:,.2f}
📈 **24h Change:** {arrow} {crypto_data['price_change_24h']:.2f}%
📊 **24h High/Low:** ${crypto_data['high_24h']:,.2f} / ${crypto_data['low_24h']:,.2f}
💎 **Market Cap:** {format_number(crypto_data['market_cap'])} (Rank #{crypto_data['market_cap_rank']})
📦 **24h Volume:** {format_number(crypto_data['total_volume'])}
━━━━━━━━━━━━━━━━━━━━
🎯 **Sentiment:** {crypto_data['sentiment']}
"""
    if 'quillcheck_analysis' in crypto_data:
        response += f"\n🧠 *QuillCheck Analysis:*\n{crypto_data['quillcheck_analysis']}\n"
    response += "\n💡 *Powered by Sentient Bot with real-time data*"
    return response

# PRICE COMMAND
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and len(context.args) > 0:
        symbol = context.args[0]
        await update.message.reply_text("📊 Fetching crypto data...")
        crypto_data = get_crypto_price_with_analysis(symbol.lower())
        quill_analysis = await get_quillcheck_analysis_async(symbol.lower())
        if crypto_data:
            crypto_data['quillcheck_analysis'] = quill_analysis
        formatted_response = format_crypto_response(crypto_data)
        await update.message.reply_text(formatted_response, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "Usage: /price [symbol]\nExample: /price BTC or /price ethereum"
        )

# for vps [rempve this part if you are running locally]

    from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

@app.route('/dobby', methods=['POST', 'GET'])
def dobby():
    data = request.json
    question = data.get("question", "")
    answer = f"Dobby says: You asked '{question}'"
    return jsonify({"answer": answer})

def run_flask():
    app.run(host="0.0.0.0", port=3000)

threading.Thread(target=run_flask).start()           

# MAIN

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, custom_question))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
