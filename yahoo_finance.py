from __future__ import annotations

import logging
from typing import Any

import requests


logger = logging.getLogger(__name__)

YAHOO_SCREENER_URL = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
MIN_VOLUME = 500_000


def _raw(value: Any) -> float | int | None:
    """
    Yahoo sometimes returns either a primitive (number) or an object like:
    {"raw": 123, "fmt": "123"}.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, dict):
        raw = value.get("raw")
        if isinstance(raw, (int, float)):
            return raw
    return None


def _fetch_screens(screen_ids: list[str], count: int) -> dict[str, list[dict[str, Any]]]:
    headers = {
        # Helps avoid 403s in some environments.
        "User-Agent": "stock-mover-bot/1.0 (+https://discord.com)",
        "Accept": "application/json,text/plain,*/*",
    }

    def fetch_one(screen_id: str) -> list[dict[str, Any]] | None:
        params = {"scrIds": screen_id, "count": count, "start": 0}
        try:
            resp = requests.get(YAHOO_SCREENER_URL, params=params, headers=headers, timeout=20)
        except requests.RequestException as exc:
            logger.error("Yahoo request failed for %s: %s", screen_id, exc)
            return None

        if not (200 <= resp.status_code < 300):
            logger.error(
                "Yahoo returned non-2xx for %s: %s - %s",
                screen_id,
                resp.status_code,
                resp.text[:300],
            )
            return None

        try:
            payload = resp.json()
        except ValueError as exc:
            logger.error("Yahoo JSON decode failed for %s: %s", screen_id, exc)
            return None

        try:
            results = (payload.get("finance") or {}).get("result") or []
            if not results or not isinstance(results, list):
                return []
            first = results[0]
            if not isinstance(first, dict):
                return []
            q = first.get("quotes") or []
            if not isinstance(q, list):
                return []
            return [qq for qq in q if isinstance(qq, dict)]
        except Exception as exc:
            logger.error("Yahoo response parsing failed for %s: %s", screen_id, exc)
            return None

    out: dict[str, list[dict[str, Any]]] = {}
    for sid in screen_ids:
        quotes = fetch_one(str(sid))
        if quotes is None:
            return {}
        out[str(sid)] = quotes
    return out


def _normalize_quote(q: dict[str, Any]) -> dict[str, Any] | None:
    symbol = q.get("symbol")
    if not symbol:
        return None

    change_pct = _raw(q.get("regularMarketChangePercent"))
    current_price = _raw(q.get("regularMarketPrice"))
    volume = _raw(q.get("regularMarketVolume"))

    if change_pct is None or current_price is None or volume is None:
        return None

    try:
        change_pct_f = float(change_pct)
        current_price_f = float(current_price)
        volume_i = int(volume)
    except (TypeError, ValueError):
        return None

    if volume_i < MIN_VOLUME:
        return None

    return {
        "ticker": str(symbol),
        "change_pct": change_pct_f,
        "current_price": current_price_f,
        "volume": volume_i,
    }


def get_top_movers(n: int = 10) -> list[dict[str, Any]]:
    """
    Fetch day gainers and day losers from Yahoo Finance, normalize, filter,
    and return top n gainers + top n losers (20 total).

    On any Yahoo request failure, returns [] to skip the cycle.
    """
    # Fetch extra to compensate for MIN_VOLUME filtering.
    fetch_count = max(50, n * 6)

    screens = _fetch_screens(["day_gainers", "day_losers"], fetch_count)
    if not screens:
        logger.info("Yahoo returned empty response; skipping cycle.")
        return []

    gainers_quotes = screens.get("day_gainers") or []
    losers_quotes = screens.get("day_losers") or []
    if not gainers_quotes or not losers_quotes:
        logger.info("Yahoo returned empty quotes for gainers/losers; skipping cycle.")
        return []

    gainers: list[dict[str, Any]] = []
    losers: list[dict[str, Any]] = []

    for q in gainers_quotes:
        mover = _normalize_quote(q)
        if mover is None:
            continue
        if mover["change_pct"] > 0:
            gainers.append(mover)

    for q in losers_quotes:
        mover = _normalize_quote(q)
        if mover is None:
            continue
        if mover["change_pct"] < 0:
            losers.append(mover)

    gainers.sort(key=lambda m: m["change_pct"], reverse=True)
    losers.sort(key=lambda m: m["change_pct"])

    return gainers[:n] + losers[:n]

