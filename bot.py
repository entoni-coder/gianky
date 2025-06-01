import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# Configurazione
BOT_TOKEN = 'f1cfb261ef4423b9b862c737617c1b498fbce07ffd9416cc47f01e536dec7954'
ADMIN_WALLET = '7741434545:AAFMPM1ODtSvArOWwD31OhP_RK_82HekD2E'
GKY_VALUE_USD = 0.10  # Valore di 1 GKY in USD

# Inizializzazione database
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

# Funzioni database
def get_user(user_id):
    with sqlite3.connect('gianky_bot.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()

def save_user(user_id, name, wallet=None, free_spins=3, paid_spins=0, balance=0):
    with sqlite3.connect('gianky_bot.db') as conn:
        conn.execute(
            'INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, name, wallet, free_spins, paid_spins, balance)
        )

def update_spin_and_balance(user_id, spin_type, balance_change):
    with sqlite3.connect('gianky_bot.db') as conn:
        field = 'free_spins' if spin_type == 'free' else 'paid_spins'
        conn.execute(
            f'UPDATE users SET {field} = {field} - 1, balance = balance + ? WHERE user_id = ?',
            (balance_change, user_id)
        )

# Ruota di Gianky
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
    return GIANKY_WHEEL[0]  # Default

# Handlers
def start(update: Update, context: CallbackContext) -> None:
    user = get_user(update.effective_user.id)
    if not user:
        update.message.reply_text(
            "🌟 *Benvenuto in Gianky Bot!* 🌟\n"
            "Iniziamo con il tuo nome e cognome:\n"
            "(Esempio: _Mario Rossi_)",
            parse_mode='Markdown'
        )
    else:
        show_gianky_menu(update, user)

def handle_name(update: Update, context: CallbackContext) -> None:
    name = ' '.join(update.message.text.strip().split()[:2])
    save_user(update.effective_user.id, name)
    update.message.reply_text(
        f"Perfetto *{name}*! 🎉\n"
        "Ora inviami il tuo wallet GKY:",
        parse_mode='Markdown'
    )

def handle_wallet(update: Update, context: CallbackContext) -> None:
    wallet = update.message.text.strip()
    user_id = update.effective_user.id
    save_user(user_id, None, wallet)  # Aggiorna solo il wallet
    update.message.reply_text(
        "✅ *Wallet registrato!*\n"
        f"Hai *3 spin gratuiti* per iniziare!",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎡 GIOCA ORA", callback_data='spin')]
        ])
    )

def show_gianky_menu(update: Update, user):
    update.message.reply_text(
        f"👋 *Ciao {user[1]}!*\n\n"
        f"🎰 Spin gratis: *{user[3]}*\n"
        f"💰 Saldo: *{user[5]} GKY*\n\n"
        "Cosa vuoi fare?",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎡 Gira la ruota", callback_data='spin')],
            [InlineKeyboardButton("💎 Compra spin", callback_data='buy_spins')]
        ])
    )

def spin_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user = get_user(query.from_user.id)
    
    if not user[3] and not user[4]:
        query.answer("❌ Non hai spin! Acquista spin extra.")
        return
    
    spin_type = 'free' if user[3] else 'paid'
    result = spin_gianky_wheel()
    balance_change = result['value'] if result['type'] == 'win' else -result['value']
    
    update_spin_and_balance(user[0], spin_type, balance_change)
    
    query.edit_message_text(
        f"{result['emoji']} *Risultato:* {result['type'].upper()} {result['value']} GKY!\n\n"
        f"Nuovo saldo: *{user[5] + balance_change} GKY*\n"
        f"Spin gratis rimasti: *{user[3] - (1 if spin_type == 'free' else 0)}*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎡 Gioca ancora", callback_data='spin')],
            [InlineKeyboardButton("🏠 Menu", callback_data='menu')]
        ])
    )

def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.regex(r'^[A-Za-z ]+$'), handle_name))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.regex(r'^0x[a-fA-F0-9]{40}$'), handle_wallet))
    dp.add_handler(CallbackQueryHandler(spin_handler, pattern='^spin$'))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    print("🚀 Gianky Bot avviato!")
    main()