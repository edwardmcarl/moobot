from __future__ import annotations

import asyncio
import logging
import random
import re
import traceback
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Pattern

import discord
from discord import Member, Message, Reaction, User

from moobot.events import add_reaction_handlers, load_events_from_file
from moobot.settings import get_settings

settings = get_settings()
_logger = logging.getLogger(__name__)

_discord_bot_commands: dict[Pattern, Callable] = {}

AFFIRMATIONS = ["Okay", "Sure", "Sounds good", "No problem", "Roger that", "Got it"]
THANKS = [*AFFIRMATIONS, "Thanks", "Thank you"]
DEBUG_COMMAND_PREFIX = r"(d|debug) "


class ReactionAction(str, Enum):
    ADDED = "added"
    REMOVED = "removed"


ReactionHandler = Callable[[ReactionAction, Reaction, User | Member], Coroutine[None, Any, Any]]


class DiscordBot:
    def __init__(
        self,
        client: discord.Client,
        command_prefix: str | None = "$",
    ) -> None:

        self.client = client
        self.command_prefix = command_prefix

        self.reaction_handlers: dict[int, ReactionHandler] = {}  # message ID -> reaction handler

    def get_command_from_message(self, message: Message) -> str | None:
        """
        Get the bot command string from a raw Discord message.

        If the message is not a bot command, return None.
        """
        # all mentions are automatically interpreted as commands
        if self.client.user is not None and self.client.user.mentioned_in(message):
            mention_regex = rf"<@!?{self.client.user.id}>"
            command = re.sub(mention_regex, "", message.content, 1).strip()
            return command

        # alternatively, commands can be prefixed with a string to indicate they are for the bot
        elif self.command_prefix is not None and message.content.startswith(self.command_prefix):
            command = message.content[len(self.command_prefix) :].strip()
            return command

        return None

    async def on_message(self, message: Message) -> None:
        # if this bot sent the message, never do anything
        if message.author == self.client.user:
            return

        # check if the message is a command and pass it to the appropriate command handler
        command = self.get_command_from_message(message)
        if command is None:
            return

        _logger.info(f"Received command: {command}")
        for pattern in _discord_bot_commands:
            match = pattern.match(command)
            if match:
                try:
                    await _discord_bot_commands[pattern](self, message, match)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    await message.channel.send(
                        f"Sorry {message.author.mention}! Something went wrong while running your"
                        f" command.```{traceback.format_exc()[-1900:]}```"
                    )
                    raise
                break

    async def on_reaction_change(
        self, action: ReactionAction, reaction: Reaction, user: Member | User
    ) -> None:
        # if the reaction is on a message in a thread with an active interaction, pass it to the
        # interaction reaction handler
        message = reaction.message

        # check if there are any registered handlers for reactions on this message
        if message.id in self.reaction_handlers:
            await self.reaction_handlers[message.id](action, reaction, user)

    @staticmethod
    def command(r: str) -> Callable[..., Any]:
        """
        Decorator for defining bot commands matching a given regex.

        After receiving a command, the bot will call the first @command function whose regex
        matches the given command.
        """

        def deco(f: Callable[..., Any]) -> Callable[..., Any]:
            _discord_bot_commands[re.compile(r, re.IGNORECASE)] = f
            return f

        return deco

    def affirm(self) -> str:
        return random.choice(AFFIRMATIONS)

    def thank(self) -> str:
        return random.choice(THANKS)


async def start() -> None:
    loop = asyncio.get_running_loop()

    intents = discord.Intents(
        messages=True, guild_messages=True, message_content=True, guilds=True, reactions=True
    )
    client = discord.Client(intents=intents, loop=loop)
    discord_bot: DiscordBot = DiscordBot(client)

    @client.event
    async def on_ready() -> None:
        _logger.info(f"We have logged in as {client.user}")
        load_events_from_file(client, Path("moobloom_events.yml"))
        add_reaction_handlers(discord_bot)

    @client.event
    async def on_message(message: Message) -> None:
        await discord_bot.on_message(message)

    @client.event
    async def on_reaction_add(reaction: Reaction, user: Member | User) -> None:
        await discord_bot.on_reaction_change(ReactionAction.ADDED, reaction, user)

    @client.event
    async def on_reaction_removed(reaction: Reaction, user: Member | User) -> None:
        await discord_bot.on_reaction_change(ReactionAction.REMOVED, reaction, user)

    await client.start(settings.discord_token)
