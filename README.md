# 🗺️ Trip Planner Telegram Bot

A collaborative trip planning bot for Telegram. Plan destinations day-by-day with friends, add Google Maps links, notes, and times — all inside Telegram.

---

## ✨ Features

- **Create trips** with a shareable 5-letter code
- **Invite friends** — anyone with the code can join
- **Add days** to your trip itinerary (by date)
- **Add places** to each day with:
  - Place name
  - Address/location → auto-generates a Google Maps link
  - Arrival time
  - Notes (book tickets in advance, dress code, etc.)
- **View full itinerary** anytime with clickable map links

---

## 🚀 Setup

### 1. Get a Telegram Bot Token

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow the prompts — choose a name and username
4. Copy the token it gives you (looks like `123456:ABC-DEF1234...`)

### 2. Install dependencies

```bash
pip install python-telegram-bot
```

### 3. Set your token and run

```bash
export TELEGRAM_BOT_TOKEN="your_token_here"
python3 trip_planner_bot.py
```

---

## 💬 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Show help menu |
| `/newtrip` | Create a new trip |
| `/jointrip` | Join a trip using a code |
| `/mytrips` | List your trips |
| `/addday` | Add a day to a trip |
| `/addplace` | Add a place to a day |
| `/view` | View a trip's full itinerary |
| `/cancel` | Cancel current action |

---

## 🧳 Example Flow

1. Alice creates a trip: `/newtrip` → names it "Barcelona 2025" → gets code `VKTRP`
2. Bob joins: `/jointrip` → enters `VKTRP`
3. Alice adds a day: `/addday` → picks trip → enters `July 15`
4. Bob adds a place: `/addplace` → picks July 15 → enters:
   - Name: `Sagrada Família`
   - Location: `Sagrada Familia, Barcelona`
   - Time: `10:00 AM`
   - Note: `Book tickets online beforehand!`
5. Anyone runs `/view` to see the full itinerary with a clickable Google Maps link

---

## 📂 Data Storage

Trip data is saved locally in `trips_data.json`. For production use, consider replacing the JSON file with a real database (SQLite, PostgreSQL, etc.).

---

## ☁️ Deploying 24/7

To keep the bot always online, deploy it to:
- **Railway** — [railway.app](https://railway.app) (free tier)
- **Render** — [render.com](https://render.com) (free tier)
- **Fly.io** — [fly.io](https://fly.io)
- **A VPS** — Any $5/month server (DigitalOcean, Hetzner, etc.)

Set the `TELEGRAM_BOT_TOKEN` environment variable on your hosting platform.
