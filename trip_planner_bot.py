#!/usr/bin/env python3
"""
🗺️ Trip Planner Telegram Bot
A collaborative trip planning bot for groups.
"""

import json
import os
import re
import urllib.parse
from datetime import datetime
from typing import Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ─── Conversation states ───────────────────────────────────────────────────────
(
    AWAITING_TRIP_NAME,
    AWAITING_TRIP_CODE,
    AWAITING_DAY_DATE,
    AWAITING_DAY_NOTE,
    AWAITING_PLACE_NAME,
    AWAITING_PLACE_LOCATION,
    AWAITING_PLACE_NOTE,
    AWAITING_PLACE_TIME,
) = range(8)

# ─── Persistence (JSON file) ───────────────────────────────────────────────────
DATA_FILE = "trips_data.json"


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"trips": {}}


def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_trip_by_code(data: dict, code: str) -> Optional[dict]:
    return data["trips"].get(code.upper())


def google_maps_link(location: str) -> str:
    query = urllib.parse.quote_plus(location)
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def trip_summary(trip: dict) -> str:
    lines = [f"✈️ *{trip['name']}*", f"🔑 Code: `{trip['code']}`", ""]
    days = trip.get("days", [])
    if not days:
        lines.append("_No days planned yet. Use /addday to add one._")
    else:
        for day in sorted(days, key=lambda d: d["date"]):
            lines.append(f"📅 *{day['date']}*" + (f" — {day['note']}" if day.get("note") else ""))
            places = day.get("places", [])
            if not places:
                lines.append("  _No places yet._")
            for p in places:
                time_str = f"🕐 {p['time']} | " if p.get("time") else ""
                note_str = f"\n    📝 {p['note']}" if p.get("note") else ""
                maps_url = google_maps_link(p["location"])
                lines.append(
                    f"  📍 {time_str}*{p['name']}*{note_str}\n    [📌 Open in Maps]({maps_url})"
                )
            lines.append("")
    members = trip.get("members", [])
    if members:
        lines.append(f"👥 Members: {', '.join(members)}")
    return "\n".join(lines)


# ─── /start ────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🗺️ *Trip Planner Bot*\n\n"
        "Plan trips together with friends and family!\n\n"
        "*Commands:*\n"
        "🆕 /newtrip — Create a new trip\n"
        "🔗 /jointrip — Join an existing trip\n"
        "📋 /mytrips — View your trips\n"
        "📅 /addday — Add a day to a trip\n"
        "📍 /addplace — Add a place to a day\n"
        "🗺️ /view — View full trip itinerary\n"
        "❓ /help — Show this menu\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ─── /newtrip ──────────────────────────────────────────────────────────────────
async def newtrip_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆕 Let's create a new trip!\n\nWhat do you want to call this trip? (e.g. *Europe Summer 2025*)",
        parse_mode="Markdown",
    )
    return AWAITING_TRIP_NAME


async def newtrip_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Please enter a valid trip name.")
        return AWAITING_TRIP_NAME

    data = load_data()
    # Generate unique code
    import random, string
    while True:
        code = "".join(random.choices(string.ascii_uppercase, k=5))
        if code not in data["trips"]:
            break

    user = update.effective_user
    username = user.username or user.first_name or str(user.id)

    trip = {
        "code": code,
        "name": name,
        "creator": username,
        "members": [username],
        "days": [],
        "created_at": datetime.now().isoformat(),
    }
    data["trips"][code] = trip
    save_data(data)

    # Track user trips
    uid = str(user.id)
    if "user_trips" not in data:
        data["user_trips"] = {}
    data["user_trips"].setdefault(uid, [])
    if code not in data["user_trips"][uid]:
        data["user_trips"][uid].append(code)
    save_data(data)

    await update.message.reply_text(
        f"✅ Trip *{name}* created!\n\n"
        f"🔑 Share this code with your travel buddies: `{code}`\n\n"
        f"They can join with /jointrip\n\n"
        f"Now use /addday to start planning!",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


# ─── /jointrip ─────────────────────────────────────────────────────────────────
async def jointrip_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔗 Enter the 5-letter trip code to join:"
    )
    return AWAITING_TRIP_CODE


async def jointrip_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    data = load_data()
    trip = get_trip_by_code(data, code)
    if not trip:
        await update.message.reply_text("❌ Trip not found. Check the code and try again.")
        return AWAITING_TRIP_CODE

    user = update.effective_user
    username = user.username or user.first_name or str(user.id)
    uid = str(user.id)

    if username not in trip["members"]:
        trip["members"].append(username)

    data["user_trips"] = data.get("user_trips", {})
    data["user_trips"].setdefault(uid, [])
    if code not in data["user_trips"][uid]:
        data["user_trips"][uid].append(code)

    save_data(data)

    await update.message.reply_text(
        f"🎉 You joined *{trip['name']}*!\n\n" + trip_summary(trip),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
    return ConversationHandler.END


# ─── /mytrips ──────────────────────────────────────────────────────────────────
async def mytrips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    data = load_data()
    codes = data.get("user_trips", {}).get(uid, [])

    if not codes:
        await update.message.reply_text(
            "You haven't joined any trips yet.\nUse /newtrip to create one or /jointrip to join one!"
        )
        return

    buttons = []
    for code in codes:
        trip = data["trips"].get(code)
        if trip:
            buttons.append([InlineKeyboardButton(f"✈️ {trip['name']} ({code})", callback_data=f"view_{code}")])

    await update.message.reply_text(
        "📋 *Your Trips* — tap one to view:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )


async def view_trip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data.replace("view_", "")
    data = load_data()
    trip = get_trip_by_code(data, code)
    if not trip:
        await query.edit_message_text("❌ Trip not found.")
        return
    await query.edit_message_text(
        trip_summary(trip),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


# ─── /view ─────────────────────────────────────────────────────────────────────
async def view_trip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user = update.effective_user
    uid = str(user.id)
    data = load_data()
    codes = data.get("user_trips", {}).get(uid, [])

    if not codes:
        await update.message.reply_text("You're not in any trips yet. Use /newtrip or /jointrip.")
        return

    if args:
        code = args[0].upper()
    elif len(codes) == 1:
        code = codes[0]
    else:
        buttons = []
        for c in codes:
            trip = data["trips"].get(c)
            if trip:
                buttons.append([InlineKeyboardButton(f"✈️ {trip['name']} ({c})", callback_data=f"view_{c}")])
        await update.message.reply_text(
            "Which trip would you like to view?",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    trip = get_trip_by_code(data, code)
    if not trip:
        await update.message.reply_text("❌ Trip not found.")
        return

    await update.message.reply_text(
        trip_summary(trip),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


# ─── /addday ──────────────────────────────────────────────────────────────────
async def addday_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    data = load_data()
    codes = data.get("user_trips", {}).get(uid, [])

    if not codes:
        await update.message.reply_text("You're not in any trips. Use /newtrip or /jointrip first.")
        return ConversationHandler.END

    if len(codes) == 1:
        context.user_data["selected_trip"] = codes[0]
        await update.message.reply_text(
            f"📅 Adding a day to *{data['trips'][codes[0]]['name']}*\n\n"
            "What date? (e.g. `2025-07-14` or `July 14`)",
            parse_mode="Markdown",
        )
        return AWAITING_DAY_DATE

    buttons = []
    for c in codes:
        trip = data["trips"].get(c)
        if trip:
            buttons.append([InlineKeyboardButton(f"✈️ {trip['name']} ({c})", callback_data=f"picktrip_{c}")])
    await update.message.reply_text(
        "Which trip are you adding a day to?",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return AWAITING_DAY_DATE


async def addday_pick_trip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data.replace("picktrip_", "")
    context.user_data["selected_trip"] = code
    data = load_data()
    trip = data["trips"].get(code)
    await query.edit_message_text(
        f"📅 Adding a day to *{trip['name']}*\n\nWhat date? (e.g. `2025-07-14` or `July 14`)",
        parse_mode="Markdown",
    )
    return AWAITING_DAY_DATE


async def addday_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "selected_trip" not in context.user_data:
        await update.message.reply_text("Something went wrong. Please /addday again.")
        return ConversationHandler.END

    date_str = update.message.text.strip()
    context.user_data["day_date"] = date_str
    await update.message.reply_text(
        f"Got it — *{date_str}*! 🗓️\n\nAdd a note for this day (optional, or type `skip`):",
        parse_mode="Markdown",
    )
    return AWAITING_DAY_NOTE


async def addday_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text.strip()
    if note.lower() == "skip":
        note = ""

    code = context.user_data["selected_trip"]
    date_str = context.user_data["day_date"]
    data = load_data()
    trip = data["trips"].get(code)

    # Check if day already exists
    for day in trip["days"]:
        if day["date"] == date_str:
            await update.message.reply_text(
                f"⚠️ A day for *{date_str}* already exists. Use /addplace to add places to it.",
                parse_mode="Markdown",
            )
            context.user_data.clear()
            return ConversationHandler.END

    trip["days"].append({"date": date_str, "note": note, "places": []})
    save_data(data)

    context.user_data.clear()
    await update.message.reply_text(
        f"✅ Day *{date_str}* added to *{trip['name']}*!\n\nNow use /addplace to add destinations.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


# ─── /addplace ─────────────────────────────────────────────────────────────────
async def addplace_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    data = load_data()
    codes = data.get("user_trips", {}).get(uid, [])

    if not codes:
        await update.message.reply_text("You're not in any trips. Use /newtrip or /jointrip first.")
        return ConversationHandler.END

    # Build list of (code, day) pairs
    options = []
    for c in codes:
        trip = data["trips"].get(c)
        for day in trip.get("days", []):
            options.append((c, trip["name"], day["date"]))

    if not options:
        await update.message.reply_text(
            "No days found. Use /addday to add a day first."
        )
        return ConversationHandler.END

    buttons = [
        [InlineKeyboardButton(f"✈️ {tname} — {date}", callback_data=f"pickday_{code}_{date}")]
        for code, tname, date in options
    ]
    await update.message.reply_text(
        "📍 Which day are you adding a place to?",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return AWAITING_PLACE_NAME


async def addplace_pick_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, code, date = query.data.split("_", 2)
    context.user_data["place_trip"] = code
    context.user_data["place_day"] = date
    await query.edit_message_text(
        f"📍 Adding a place to *{date}*\n\nWhat's the name of the place? (e.g. *Eiffel Tower*)",
        parse_mode="Markdown",
    )
    return AWAITING_PLACE_NAME


async def addplace_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "place_trip" not in context.user_data:
        await update.message.reply_text("Something went wrong. Please /addplace again.")
        return ConversationHandler.END
    context.user_data["place_name"] = update.message.text.strip()
    await update.message.reply_text(
        "📌 What's the address or location?\n"
        "_(This is used to generate a Google Maps link, e.g. `Eiffel Tower, Paris` or `48.8584, 2.2945`)_",
        parse_mode="Markdown",
    )
    return AWAITING_PLACE_LOCATION


async def addplace_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["place_location"] = update.message.text.strip()
    await update.message.reply_text(
        "⏰ What time will you be there? (e.g. `10:00 AM`, or type `skip`)"
    )
    return AWAITING_PLACE_TIME


async def addplace_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_str = update.message.text.strip()
    context.user_data["place_time"] = "" if time_str.lower() == "skip" else time_str
    await update.message.reply_text(
        "📝 Any notes for this place? (e.g. *Book tickets in advance*, or type `skip`)",
        parse_mode="Markdown",
    )
    return AWAITING_PLACE_NOTE


async def addplace_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text.strip()
    if note.lower() == "skip":
        note = ""

    ud = context.user_data
    code = ud["place_trip"]
    date = ud["place_day"]
    place = {
        "name": ud["place_name"],
        "location": ud["place_location"],
        "time": ud.get("place_time", ""),
        "note": note,
    }

    data = load_data()
    trip = data["trips"].get(code)
    for day in trip["days"]:
        if day["date"] == date:
            day["places"].append(place)
            break

    save_data(data)
    maps_url = google_maps_link(place["location"])
    context.user_data.clear()

    await update.message.reply_text(
        f"✅ *{place['name']}* added to {date}!\n\n"
        f"[📌 Open in Google Maps]({maps_url})\n\n"
        f"Use /view to see the full itinerary.",
        parse_mode="Markdown",
        disable_web_page_preview=False,
    )
    return ConversationHandler.END


# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set.")
        print("   Set it with: export TELEGRAM_BOT_TOKEN='your_token_here'")
        return

    app = Application.builder().token(token).build()

    # /newtrip flow
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("newtrip", newtrip_start)],
        states={AWAITING_TRIP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, newtrip_name)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    # /jointrip flow
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("jointrip", jointrip_start)],
        states={AWAITING_TRIP_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, jointrip_code)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    # /addday flow
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("addday", addday_start)],
        states={
            AWAITING_DAY_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, addday_date),
                CallbackQueryHandler(addday_pick_trip, pattern=r"^picktrip_"),
            ],
            AWAITING_DAY_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addday_note)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    # /addplace flow
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("addplace", addplace_start)],
        states={
            AWAITING_PLACE_NAME: [
                CallbackQueryHandler(addplace_pick_day, pattern=r"^pickday_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, addplace_name),
            ],
            AWAITING_PLACE_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, addplace_location)],
            AWAITING_PLACE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addplace_time)],
            AWAITING_PLACE_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addplace_note)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    # Other commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("mytrips", mytrips))
    app.add_handler(CommandHandler("view", view_trip))
    app.add_handler(CallbackQueryHandler(view_trip_callback, pattern=r"^view_"))

    print("🗺️ Trip Planner Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
