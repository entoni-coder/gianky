import os
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Config
BOT_TOKEN = os.environ['BOT_TOKEN']
GKY_VALUE_USD = 0.10
ADMIN_WALLET = os.environ.get('ADMIN_WALLET')

# Database setup
def init_db():
    with sqlite3.connect('gianky_bot.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                wallet TEXT,
                free_spins INTEGER DEFAULT 3,
                paid_spins INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 0
            )
        ''')

init_db()

# Database helpers
def get_user(user_id):
    with sqlite3.connect('gianky_bot.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()

def save_user(user_id, name=None, wallet=None, free_spins=3, paid_spins=0, balance=0):
    with sqlite3.connect('gianky_bot.db') as conn:
        if name is not None:
            conn.execute('INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?)',
                         (user_id, name, wallet, free_spins, paid_spins, balance))
        elif wallet is not None:
            conn.execute('UPDATE users SET wallet = ? WHERE user_id = ?', (wallet, user_id))

def update_spin_and_balance(user_id, spin_type, balance_change):
    with sqlite3.connect('gianky_bot.db') as conn:
        field = 'free_spins' if spin_type == 'free' else 'paid_spins'
        conn.execute(
            f'UPDATE users SET {field} = {field} - 1, balance = balance + ? WHERE user_id = ?',
            (balance_change, user_id)
        )

# Ruota della fortuna
GIANKY_WHEEL = [
    {'type': 'loose', 'value': 10, 'prob': 0.30, 'emoji': '☄️'},
    {'type': 'loose', 'value': 20, 'prob': 0.25, 'emoji': '💥'},
    {'type': 'loose', 'value': 50, 'prob': 0.15, 'emoji': '🌪️'},
    {'type': 'win', 'value': 10, 'prob': 0.05, 'emoji': '🍒'},
    {'type': 'win', 'value': 100, 'prob': 0.01, 'emoji': '🎰'}
]

def spin_gianky_wheel():
    rand = random.random()
    cumulative = 0
    for segment in GIANKY_WHEEL:
        cumulative += segment['prob']
        if rand <= cumulative:
            return segment
    return GIANKY_WHEEL[0]

# Handlers asincroni
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "🌟 *Benvenuto in Gianky Bot!* 🌟\n"
            "Iniziamo con il tuo nome e cognome:\n"
            "(Esempio: _Mario Rossi_)", parse_mode='Markdown'
        )
    else:
        await show_gianky_menu(update, user)

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = ' '.join(update.message.text.strip().split()[:2])
    save_user(update.effective_user.id, name)
    await update.message.reply_text(
        f"Perfetto *{name}*! 🎉\nOra inviami il tuo wallet GKY:", parse_mode='Markdown'
    )

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet = update.message.text.strip()
    user_id = update.effective_user.id
    save_user(user_id, wallet=wallet)
    await update.message.reply_text(
        "✅ *Wallet registrato!*\nHai *3 spin gratuiti* per iniziare!",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎡 GIOCA ORA", callback_data='spin')]
        ])
    )

async def show_gianky_menu(update: Update, user):
    await update.message.reply_text(
        f"👋 *Ciao {user[1]}!*\n\n"
        f"🎰 Spin gratis: *{user[3]}*\n"
        f"💰 Saldo: *{user[5]} GKY*\n\nCosa vuoi fare?",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎡 Gira la ruota", callback_data='spin')],
            [InlineKeyboardButton("💎 Compra spin", callback_data='buy_spins')]
        ])
    )

async def spin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)

    if not user[3] and not user[4]:
        await query.edit_message_text("❌ Non hai spin! Acquista spin extra.")
        return

    spin_type = 'free' if user[3] else 'paid'
    result = spin_gianky_wheel()
    balance_change = result['value'] if result['type'] == 'win' else -result['value']
    update_spin_and_balance(user[0], spin_type, balance_change)

    await query.edit_message_text(
        f"{result['emoji']} *Risultato:* {result['type'].upper()} {result['value']} GKY!\n\n"
        f"Nuovo saldo: *{user[5] + balance_change} GKY*\n"
        f"Spin gratis rimasti: *{user[3] - (1 if spin_type == 'free' else 0)}*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎡 Gioca ancora", callback_data='spin')],
            [InlineKeyboardButton("🏠 Menu", callback_data='menu')]
        ])
    )

# Main
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 8443))
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^[A-Za-z ]+$'), handle_name)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^0x[a-fA-F0-9]{40}$'), handle_wallet)
    )
    application.add_handler(CallbackQueryHandler(spin_handler, pattern='^spin$'))

    application.run_webhook(
        listen='0.0.0.0',
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"https://your-service.onrender.com/{BOT_TOKEN}"
    )
 print("🤖 Bot avviato correttamente!")
