
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from telegram.error import TelegramError
import json 
import os 
# BOT_TOKEN = "8905958221:AAHaEet-d9dSTQttjymlfYuDDLA6WJhYRuc"
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is missing.")
# Your personal Telegram chat ID
ADMIN_ID = 1377058813

#TRADERS_FILE = "traders.json"
TRADERS_FILE = os.getenv(
    "TRADERS_FILE",
    "traders.json"
)

def load_traders():
    if not os.path.exists(TRADERS_FILE):
        return {}

    try:
        with open(TRADERS_FILE, "r", encoding="utf-8") as file:
            saved_data = json.load(file)

        return {
            int(trader_number): int(chat_id)
            for trader_number, chat_id in saved_data.items()
        }

    except (json.JSONDecodeError, OSError, ValueError) as error:
        print(f"Could not load traders: {error}")
        return {}


def save_traders():
    try:
        with open(TRADERS_FILE, "w", encoding="utf-8") as file:
            json.dump(TRADERS, file, indent=4)

    except OSError as error:
        print(f"Could not save traders: {error}")


TRADERS = load_traders()

ADMIN_KEYBOARD = [
    ["📢 Broadcast", "👥 View Traders"],
    ["📖 Help", "❌ Close Menu"]
]


# Register a trader using:
# /start 1
# /start 2
# /start 3
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id
    

    # Admin receives the button menu
    if chat_id == ADMIN_ID and not context.args:
        keyboard = ReplyKeyboardMarkup(
            ADMIN_KEYBOARD,
            resize_keyboard=True,
            one_time_keyboard=False
        )

        await update.message.reply_text(
            "Welcome, Admin.\n"
            "Choose an option:",
            reply_markup=keyboard
        )
        return

    # Trader must provide a trader number
    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/start <TraderNumber>\n\n"
            "Example:\n"
            "/start 1"
        )
        return

    try:
        trader_number = int(context.args[0])

        if trader_number < 1 or trader_number > 10:
            raise ValueError

    except ValueError:
        await update.message.reply_text(
            "Trader number must be a whole number from 1 to 10."
        )
        return

    # Check whether another account already registered this number
    existing_chat_id = TRADERS.get(trader_number)

    if existing_chat_id is not None and existing_chat_id != chat_id:
        await update.message.reply_text(
            f"Trader {trader_number} is already registered."
        )
        return

    # Prevent one Telegram account from using multiple trader numbers
    for registered_number, registered_chat_id in TRADERS.items():
        if (
            registered_chat_id == chat_id
            and registered_number != trader_number
        ):
            await update.message.reply_text(
                f"You are already registered as Trader "
                f"{registered_number}."
            )
            return

    TRADERS[trader_number] = chat_id
    save_traders()

    print(f"Registered Trader {trader_number}: {chat_id}")
    print("Current traders:", TRADERS)

    await update.message.reply_text(
        "Successfully registered.\n"
        f"Trader Number: {trader_number}"
    )


async def admin_button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    sender_id = update.effective_chat.id
    selected_button = update.message.text

    # Only the admin can use these buttons
    if sender_id != ADMIN_ID:
        return

    if selected_button == "📢 Broadcast":
        await update.message.reply_text(
            "Enter the broadcast command:\n\n"
            "/broadcast <BUY/SELL> <Instrument> <Entry> "
            "<LotSize> <StopLoss> <TakeProfit>\n\n"
            "BUY example:\n"
            "/broadcast BUY XAUUSD 2350 0.10 2340 2370\n\n"
            "SELL example:\n"
            "/broadcast SELL XAUUSD 2350 0.10 2360 2320"
        )

    elif selected_button == "👥 View Traders":
        if not TRADERS:
            await update.message.reply_text(
                "No traders are currently registered."
            )
            return

        trader_lines = []

        for trader_number, chat_id in sorted(TRADERS.items()):
            trader_lines.append(
                f"Trader {trader_number}: {chat_id}"
            )

        await update.message.reply_text(
            "👥 Registered Traders\n\n"
            + "\n".join(trader_lines)
        )

    elif selected_button == "📖 Help":
        await update.message.reply_text(
            "Admin Instructions\n\n"
            "📢 Broadcast — Shows the broadcast format\n"
            "👥 View Traders — Shows registered traders\n"
            "❌ Close Menu — Hides the buttons\n\n"
            "Send /start to reopen the menu."
        )

    elif selected_button == "❌ Close Menu":
        await update.message.reply_text(
            "Admin menu closed.\n"
            "Send /start to open it again.",
            reply_markup=ReplyKeyboardRemove()
        )


# Admin broadcasts adjusted trading instructions to all traders
async def broadcast(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    sender_id = update.effective_chat.id

    # Normal trader registration continues here
    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/start <TraderNumber>\n\n"
            "Example:\n"
            "/start 1"
        )
        return

    # Only the admin can use /broadcast
    if sender_id != ADMIN_ID:
        await update.message.reply_text(
            "You are not allowed to use this command."
        )
        return

    # Required command:
    # /broadcast BUY XAUUSD 2350 0.10 2340 2370
    if len(context.args) != 6:
        await update.message.reply_text(
            "Usage:\n"
            "/broadcast <BUY/SELL> <Instrument> <StartingEntry> "
            "<LotSize> <StopLoss> <TakeProfit>\n\n"
            "Examples:\n"
            "/broadcast BUY XAUUSD 2350 0.10 2340 2370\n"
            "/broadcast SELL XAUUSD 2350 0.10 2360 2320"
        )
        return

    direction = context.args[0].upper()
    instrument = context.args[1].upper()

    if direction not in {"BUY", "SELL"}:
        await update.message.reply_text(
            "Direction must be BUY or SELL."
        )
        return

    try:
        starting_entry = float(context.args[2])
        lot_size = float(context.args[3])
        starting_stop_loss = float(context.args[4])
        starting_take_profit = float(context.args[5])

        if starting_entry <= 0:
            raise ValueError("Entry price must be greater than 0.")

        if lot_size <= 0:
            raise ValueError("Lot size must be greater than 0.")

        if starting_stop_loss <= 0:
            raise ValueError("Stop loss must be greater than 0.")

        if starting_take_profit <= 0:
            raise ValueError("Take profit must be greater than 0.")

    except ValueError as error:
        await update.message.reply_text(
            f"Invalid trading value: {error}"
        )
        return

    # Check that the stop loss and take profit are correctly placed
    if direction == "BUY":
        if starting_stop_loss >= starting_entry:
            await update.message.reply_text(
                "For BUY, Stop Loss must be below the Entry Price."
            )
            return

        if starting_take_profit <= starting_entry:
            await update.message.reply_text(
                "For BUY, Take Profit must be above the Entry Price."
            )
            return

        # Each subsequent trader receives prices 0.25 lower
        adjustment = -0.25

    else:
        if starting_stop_loss <= starting_entry:
            await update.message.reply_text(
                "For SELL, Stop Loss must be above the Entry Price."
            )
            return

        if starting_take_profit >= starting_entry:
            await update.message.reply_text(
                "For SELL, Take Profit must be below the Entry Price."
            )
            return

        # Each subsequent trader receives prices 0.25 higher
        adjustment = 0.25

    if not TRADERS:
        await update.message.reply_text(
            "No traders have registered."
        )
        return

    sent_count = 0
    failed_traders = []

    # Send instructions in trader-number order
    sorted_traders = sorted(TRADERS.items())

    for position, (trader_number, chat_id) in enumerate(sorted_traders):
        price_adjustment = position * adjustment

        # Entry, SL and TP are all adjusted by the same amount
        trader_entry = starting_entry + price_adjustment
        trader_stop_loss = starting_stop_loss + price_adjustment
        trader_take_profit = starting_take_profit + price_adjustment

        message = (
            "📢 Trading Instruction\n\n"
            f"Trader Number: {trader_number}\n"
            f"Direction: {direction}\n"
            f"Instrument: {instrument}\n"
            f"Entry Price: {trader_entry:.2f}\n"
            f"Lot Size: {lot_size:.2f}\n"
            f"Stop Loss: {trader_stop_loss:.2f}\n"
            f"Take Profit: {trader_take_profit:.2f}"
        )

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message
            )
            sent_count += 1

        except TelegramError as error:
            print(
                f"Failed to send to Trader {trader_number}: {error}"
            )
            failed_traders.append(trader_number)

    confirmation = (
        "Broadcast completed.\n\n"
        f"Direction: {direction}\n"
        f"Instrument: {instrument}\n"
        f"Starting Entry Price: {starting_entry:.2f}\n"
        f"Starting Stop Loss: {starting_stop_loss:.2f}\n"
        f"Starting Take Profit: {starting_take_profit:.2f}\n"
        f"Lot Size: {lot_size:.2f}\n"
        f"Adjustment Per Trader: {adjustment:+.2f}\n"
        f"Successfully Sent: {sent_count}/{len(sorted_traders)}"
    )

    if failed_traders:
        failed_text = ", ".join(
            str(trader) for trader in failed_traders
        )
        confirmation += f"\nFailed Traders: {failed_text}"

    await update.message.reply_text(confirmation)


app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))


app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        admin_button_handler
    )
)


print("Bot running...")
print("Registered traders:", TRADERS)

app.run_polling()
