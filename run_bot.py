import asyncio
import os

import discord
from TikTokLive import TikTokLiveClient

import main as app

bot = app.bot
MEMBER_ROLE_ID = app.env_id("MEMBER_ROLE_ID")
TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME", "louis.hnvr157").lstrip("@")
TIKTOK_CHANNEL_ID = app.env_id("TIKTOK_CHANNEL_ID", 1570261943032479825)
TIKTOK_POLL_SECONDS = max(30, app.env_id("TIKTOK_POLL_SECONDS", 60))
TIKTOK_LIVE_URL = f"https://www.tiktok.com/@{TIKTOK_USERNAME}/live"
monitor_task: asyncio.Task | None = None


def has_member_role(member: discord.Member) -> bool:
    if MEMBER_ROLE_ID:
        return any(role.id == MEMBER_ROLE_ID for role in member.roles)
    return any(role.name.casefold() == "member" for role in member.roles)


async def on_message(message: discord.Message) -> None:
    if message.author.bot or message.guild is None:
        return
    if (
        isinstance(message.author, discord.Member)
        and has_member_role(message.author)
        and app.LINK_PATTERN.search(message.content)
    ):
        try:
            await message.delete()
            await message.channel.send(
                f"{message.author.mention}, Links sind für die Rolle Member nicht erlaubt.",
                delete_after=8,
            )
        except discord.Forbidden:
            pass
        return
    await bot.process_commands(message)


async def watch_tiktok_live() -> None:
    client = TikTokLiveClient(unique_id=TIKTOK_USERNAME)
    was_live = False
    while not bot.is_closed():
        try:
            is_live = await client.is_live()
            if is_live and not was_live:
                channel = bot.get_channel(TIKTOK_CHANNEL_ID)
                if channel is None:
                    channel = await bot.fetch_channel(TIKTOK_CHANNEL_ID)
                if isinstance(channel, discord.TextChannel):
                    await channel.send(
                        f"# LIVE Louis ist auf TikTok live kommt gerne rein: {TIKTOK_LIVE_URL}"
                    )
                else:
                    print(f"TikTok-Live-Channel {TIKTOK_CHANNEL_ID} ist kein Text-Channel.")
            was_live = is_live
        except Exception as error:
            # Keep polling after temporary TikTok/API/network failures.
            print(f"TikTok-Live-Überprüfung fehlgeschlagen: {error!r}")
        await asyncio.sleep(TIKTOK_POLL_SECONDS)


async def start_live_monitor() -> None:
    global monitor_task
    if monitor_task is None or monitor_task.done():
        monitor_task = asyncio.create_task(watch_tiktok_live())


# Replace the original global link filter with the role-specific version.
bot.on_message = on_message
bot.add_listener(start_live_monitor, "on_ready")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN fehlt. Lege eine .env-Datei an und trage dort dein Bot-Token ein.")
    bot.run(token)
