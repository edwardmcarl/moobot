import asyncio

from moobot.discord import discord_bot


def run_discord_bot() -> None:
    asyncio.run(discord_bot.start())
