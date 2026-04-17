import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    discord_webhook_url: str


def get_settings() -> Settings:
    discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    missing = []
    if not discord_webhook_url:
        missing.append("DISCORD_WEBHOOK_URL")

    if missing:
        missing_vars = ", ".join(missing)
        raise RuntimeError(
            f"Missing required environment variable(s): {missing_vars}. "
            "Please create a .env file with these keys."
        )

    return Settings(discord_webhook_url=discord_webhook_url)

