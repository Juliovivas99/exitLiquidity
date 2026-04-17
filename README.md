## Stock Mover Discord Bot (Yahoo Screener)

Python bot that posts **top day gainers + top day losers** to a Discord channel using a **Discord webhook**, powered by the Yahoo Finance *predefined screener* endpoint.

### What it does

- **Fetches** movers from Yahoo’s predefined screens:
  - `day_gainers`
  - `day_losers`
- **Normalizes + filters** results (e.g. volume threshold)
- **Formats** a Discord **embed** with price, % change, and volume
- **Posts** the embed to your Discord channel via webhook
- **Runs on a schedule** in US/Eastern time and skips weekends + NYSE holidays

### Schedule

The scheduler in `main.py` posts at these times (US/Eastern):

- **09:00** — premarket
- **09:45** — open recap
- **12:30** — midday
- **15:45** — close recap

It will **skip**:

- **Weekends**
- **NYSE market holidays** (via `pandas_market_calendars`)

### Requirements

- **Python**: 3.11+ recommended
- **Discord**: a channel webhook URL (see setup below)

Python dependencies are pinned in `requirements.txt`.

### Quick start (local)

1) Create a virtual environment (recommended).

```bash
python -m venv .venv
source .venv/bin/activate
```

2) Install dependencies.

```bash
pip install -r requirements.txt
```

3) Configure environment variables.

```bash
cp .env.example .env
```

Edit `.env` and set:

- **`DISCORD_WEBHOOK_URL`**: your Discord webhook URL

4) Run the scheduler.

```bash
python main.py
```

### One-shot run (recommended for testing)

Use `run_once.py` to fetch movers once and print them to your terminal (optionally also post to Discord).

- **Print movers only**:

```bash
python run_once.py --n 10
```

- **Print and post to Discord**:

```bash
python run_once.py --n 10 --post-discord
```

### Configuration

#### Environment variables

Loaded via `python-dotenv` in `config.py`.

- **`DISCORD_WEBHOOK_URL`** (required): Discord webhook URL used to post embeds.

If `DISCORD_WEBHOOK_URL` is missing, the bot raises a runtime error with a clear message.

#### Mover filtering logic

Defined in `yahoo_finance.py`.

- **Volume filter**: moves with volume below `MIN_VOLUME` are dropped.
  - Current default: **500,000** (`MIN_VOLUME = 500_000`)
- **Returned list**: top \(n\) gainers **plus** top \(n\) losers (up to **2n** total)

### Discord message format

Implemented in `discord_bot.py`:

- Uses **Discord embeds** with one field per ticker
- Adds a direction marker:
  - gainers: `🟢▲`
  - losers: `🔴▼`
  - unchanged: `⚪`
- Embed color is based on the **average** change across movers (green if positive, red if negative)

### Operational notes

- **Request strategy**: each cycle fetches `day_gainers` and `day_losers` from Yahoo and then filters locally.
- **Retry behavior**:
  - Discord post: up to **2 attempts** with a short sleep between attempts
  - Yahoo fetch: on request/parse failure, the cycle returns `[]` and the scheduler skips posting
- **Loop interval**: the scheduler checks the clock every ~20 seconds (to hit the exact minute)

### Troubleshooting

#### Discord posts aren’t showing up

- Confirm you set **`DISCORD_WEBHOOK_URL`** in `.env`
- Make sure the webhook still exists (Discord can invalidate old webhooks)
- Check terminal logs for non-2xx responses (the code logs status + response text)

#### Yahoo request failures / 403s

The Yahoo screener endpoint can be flaky or restrictive in some environments.

- This project sets a **User-Agent** header to reduce 403s
- If you still see 403s, try:
  - running from a different network/IP
  - reducing frequency / testing with `run_once.py`
  - waiting and retrying later (Yahoo can rate-limit)

#### “Weekend; skipping cycle.” / “Market holiday; skipping cycle.”

That’s expected behavior:

- Weekends are always skipped
- NYSE holidays are detected via `pandas_market_calendars`

### Security

- **Do not commit real webhook URLs**. Keep secrets in `.env` (which should be ignored by git).
- If a real webhook URL was ever committed or shared, **rotate it** in Discord (create a new webhook and delete the old one).

### Repo map

- `main.py`: scheduler loop + trading-day checks + posting times
- `run_once.py`: fetch once, print to terminal, optional Discord post
- `yahoo_finance.py`: Yahoo screener fetch + normalize/filter + top movers selection
- `discord_bot.py`: Discord embed formatting + webhook POST
- `config.py`: env var loading + validation
- `.env.example`: template for required environment variables
- `requirements.txt`: pinned Python dependencies

