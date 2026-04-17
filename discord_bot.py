from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import pytz
import requests

from config import get_settings


logger = logging.getLogger(__name__)


ET_TZ = pytz.timezone("US/Eastern")


def _format_volume(volume: int) -> str:
    return f"{volume:,.0f}"


def _get_embed_color(avg_change: float) -> int:
    # Green if avg change positive, red if negative
    if avg_change >= 0:
        return 0x43A047  # green
    return 0xE53935  # red


def send_mover_alert(movers: list[dict[str, Any]]) -> None:
    if not movers:
        logger.info("No movers to send; skipping Discord alert.")
        return

    settings = get_settings()

    now_et = datetime.now(ET_TZ)
    title_time = now_et.strftime("%Y-%m-%d %I:%M %p ET")

    changes = [float(m.get("change_pct", 0.0)) for m in movers]
    avg_change = (sum(changes) / len(changes)) if changes else 0.0
    color = _get_embed_color(avg_change)

    fields: list[dict[str, Any]] = []
    for mover in movers:
        ticker = str(mover.get("ticker", ""))
        change = float(mover.get("change_pct", 0.0))
        current_price = float(mover.get("current_price", 0.0))
        volume = int(mover.get("volume", 0))

        if change > 0:
            arrow = "🟢▲"
        elif change < 0:
            arrow = "🔴▼"
        else:
            arrow = "⚪"

        field_name = f"{ticker} {arrow}"
        field_value = (
            f"**Change:** {change:+.2f}%\n"
            f"**Price:** ${current_price:.2f}\n"
            f"**Volume:** {_format_volume(volume)}"
        )

        fields.append(
            {
                "name": field_name,
                "value": field_value,
                "inline": False,
            }
        )

    embed = {
        "title": f"Top Market Movers — {title_time}",
        "color": color,
        "fields": fields,
        "footer": {
            "text": "Updates at 09:00, 09:45, 12:30, 15:45 ET (trading days)",
        },
    }

    payload = {
        "embeds": [embed],
    }

    url = settings.discord_webhook_url

    for attempt in range(2):
        try:
            response = requests.post(url, json=payload, timeout=10)
        except requests.RequestException as exc:
            logger.error("Error posting to Discord webhook (attempt %s): %s", attempt + 1, exc)
            if attempt == 0:
                time.sleep(5)
            continue

        if 200 <= response.status_code < 300:
            logger.info("Successfully sent Discord mover alert.")
            return

        logger.error(
            "Discord webhook returned non-2xx status (attempt %s): %s - %s",
            attempt + 1,
            response.status_code,
            response.text,
        )

        if attempt == 0:
            time.sleep(5)

    logger.error("Failed to send Discord mover alert after 2 attempts.")

