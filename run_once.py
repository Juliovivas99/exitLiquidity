from __future__ import annotations

import argparse
import logging
from typing import Any

from discord_bot import send_mover_alert
from yahoo_finance import get_top_movers


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _fmt_change(change_pct: float) -> str:
    return f"{change_pct:+.2f}%"


def _fmt_price(price: float) -> str:
    return f"${price:,.2f}"


def _fmt_volume(vol: int) -> str:
    return f"{vol:,.0f}"


def _print_movers(movers: list[dict[str, Any]]) -> None:
    if not movers:
        print("No movers returned.")
        return

    rows: list[tuple[str, str, str, str]] = []
    for m in movers:
        rows.append(
            (
                str(m.get("ticker", "")),
                _fmt_change(float(m.get("change_pct", 0.0))),
                _fmt_price(float(m.get("current_price", 0.0))),
                _fmt_volume(int(m.get("volume", 0))),
            )
        )

    headers = ("TICKER", "CHANGE", "PRICE", "VOLUME")
    col_widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            col_widths[i] = max(col_widths[i], len(cell))

    def line(sep: str = "-") -> str:
        parts = [sep * w for w in col_widths]
        return f"{sep}{sep}".join(parts)

    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("  ".join("-" * col_widths[i] for i in range(len(headers))))
    for r in rows:
        print(
            "  ".join(
                [
                    r[0].ljust(col_widths[0]),
                    r[1].rjust(col_widths[1]),
                    r[2].rjust(col_widths[2]),
                    r[3].rjust(col_widths[3]),
                ]
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Yahoo mover fetch once and print to terminal.")
    parser.add_argument("--n", type=int, default=10, help="Top N gainers and top N losers (total up to 2N).")
    parser.add_argument(
        "--post-discord",
        action="store_true",
        help="Also send the mover alert to Discord (uses your existing webhook config).",
    )
    args = parser.parse_args()

    logger.info("Fetching top movers once (n=%s).", args.n)
    movers = get_top_movers(n=max(1, int(args.n)))

    _print_movers(movers)

    if args.post_discord:
        logger.info("Posting movers to Discord.")
        send_mover_alert(movers)


if __name__ == "__main__":
    main()

