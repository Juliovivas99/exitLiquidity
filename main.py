import logging
import time
from datetime import date, datetime

import pytz
import pandas_market_calendars as mcal

from discord_bot import send_mover_alert
from yahoo_finance import get_top_movers


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

ET_TZ = pytz.timezone("US/Eastern")
NYSE = mcal.get_calendar("NYSE")

POST_TIMES_ET: dict[str, str] = {
    "premarket": "09:00",
    "open_recap": "09:45",
    "midday": "12:30",
    "close_recap": "15:45",
}


def _now_et() -> datetime:
    return datetime.now(ET_TZ)


def _is_weekday(dt: datetime) -> bool:
    return dt.weekday() < 5


def _is_trading_day(d: date) -> bool:
    valid = NYSE.valid_days(start_date=d.isoformat(), end_date=d.isoformat())
    return len(valid) > 0


def run_cycle(label: str = "scheduled") -> None:
    now_et = _now_et()
    logger.info("Cycle start (%s) at %s", label, now_et.strftime("%Y-%m-%d %I:%M:%S %p ET"))

    if not _is_weekday(now_et):
        logger.info("Weekend; skipping cycle.")
        return

    if not _is_trading_day(now_et.date()):
        logger.info("Market holiday; skipping cycle.")
        return

    movers = get_top_movers(n=10)
    if not movers:
        logger.info("No movers returned; nothing to send.")
        return

    send_mover_alert(movers)
    logger.info("Cycle end (%s)", label)


def main() -> None:
    logger.info("Starting Stock Mover Bot (Yahoo screener).")
    last_sent: dict[tuple[str, str], datetime] = {}

    while True:
        try:
            now_et = _now_et()

            # Hard skip weekends/holidays without doing any Yahoo requests.
            if _is_weekday(now_et) and _is_trading_day(now_et.date()):
                hm = now_et.strftime("%H:%M")
                for label, target in POST_TIMES_ET.items():
                    if hm != target:
                        continue

                    key = (now_et.date().isoformat(), label)
                    if key in last_sent:
                        continue

                    _safe_run_cycle(label)
                    last_sent[key] = now_et
        except Exception:
            logger.exception("Unexpected error in scheduler loop; continuing.")
        time.sleep(20)


def _safe_run_cycle(label: str) -> None:
    try:
        run_cycle(label=label)
    except Exception:
        logger.exception("Unexpected error in cycle; continuing.")


if __name__ == "__main__":
    main()