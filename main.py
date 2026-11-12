import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


def env_id(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    try:
        return int(value) if value else default
    except ValueError as error:
        raise RuntimeError(f"{name} muss eine gültige Discord-ID sein.") from error


WELCOME_CHANNEL_ID = env_id("WELCOME_CHANNEL_ID", 1570259898690961591)
AUTO_ROLE_ID = env_id("AUTO_ROLE_ID", 1570262416502030356)
TICKET_CATEGORY_NAME = os.getenv("TICKET_CATEGORY_NAME", "Tickets")
TICKET_CATEGORY_ID = env_id("TICKET_CATEGORY_ID")
TICKET_LOG_CHANNEL_ID = env_id("TICKET_LOG_CHANNEL_ID")
MEMBER_ROLE_ID = env_id("MEMBER_ROLE_ID")
TRANSCRIPTS_DIR = Path(os.getenv("TRANSCRIPTS_DIR", "transcripts"))

TEAM_ROLES_ORDERED = [
    (env_id("TRIAL_MOD_ROLE_ID", 1556047760355229696), "Trial Mod"),
    (env_id("MOD_ROLE_ID", 1556047760355229697), "Mod"),
    (env_id("LEAD_MOD_ROLE_ID", 1556047760355229698), "Lead of Mod"),
    (env_id("TRIAL_ADMIN_ROLE_ID", 1556047760355229700), "Trial Admin"),
    (env_id("ADMIN_ROLE_ID", 1556047760355229701), "Admin"),
    (env_id("LEAD_ADMIN_ROLE_ID", 1556047760355229702), "Lead of Admin"),
    (env_id("STV_TEAMLEITUNG_ROLE_ID", 1556047760359161948), "Stv Teamleitung"),
    (env_id("TEAMLEITUNG_ROLE_ID", 1556047760359161949), "Teamleitung"),
    (env_id("MANAGER_ROLE_ID", 1556047760359161951), "Manager"),
    (env_id("CO_OWNER_ROLE_ID", 1556047760359161953), "CO Owner"),
    (env_id("OWNER_ROLE_ID", 1556047760359161954), "Owner"),
]
TEAM_ROLE_INDEX = {role_id: index for index, (role_id, _) in enumerate(TEAM_ROLES_ORDERED) if role_id}
MANAGEMENT_ROLES = {
    role_id for role_id, _ in TEAM_ROLES_ORDERED[-5:] if role_id
}

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
LINK_PATTERN = re.compile(
    r"(?:https?://|www\.|discord\.gg/|discord(?:app)?\.com/invite/)", re.IGNORECASE
)


def ticket_owner_id(channel: discord.abc.GuildChannel) -> Optional[int]:
    match = re.search(r"ticket-owner:(\d+)", channel.topic or "")
    return int(match.group(1)) if match else None


def has_member_role(member: discord.Member) -> bool:
    if MEMBER_ROLE_ID:
        return any(role.id == MEMBER_ROLE_ID for role in member.roles)
    return any(role.name.casefold() == "member" for role in member.roles)


def highest_team_role(member: discord.Member) -> Optional[tuple[int, str]]:
    return next(
        (
            (role_id, name)
            for role_id, name in reversed(TEAM_ROLES_ORDERED)
            if role_id and any(role.id == role_id for role in member.roles)
        ),
        None,
    )


async def create_ticket_transcript(channel: discord.TextChannel) -> Path:
    """Export the ticket history to a UTF-8 text file before the channel is deleted."""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    path = TRANSCRIPTS_DIR / f"ticket-{channel.id}-{timestamp}.txt"
    lines = [
        f"Ticket-Transcript: #{channel.name}",
        f"Server: {channel.guild.name} ({channel.guild.id})",
        f"Channel-ID: {channel.id}",
        f"Erstellt: {channel.created_at.isoformat()}",
        "",
    ]
    async for message in channel.history(limit=None, oldest_first=True):
        created = message.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        author = f"{message.author} ({message.author.id})"
        lines.append(f"[{created}] {author}")
        if message.content:
            lines.append(message.content)
        for attachment in message.attachments:
            lines.append(f"[Anhang: {attachment.filename}] {attachment.url}")
        for embed in message.embeds:
            if embed.title:
                lines.append(f"[Embed-Titel: {embed.title}]")
            if embed.description:
                lines.append(f"[Embed: {embed.description}]")
        if not message.content and not message.attachments and not message.embeds:
            lines.append("[Keine Textnachricht]")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")

    log_channel = channel.guild.get_channel(TICKET_LOG_CHANNEL_ID) if TICKET_LOG_CHANNEL_ID else None
    if isinstance(log_channel, discord.TextChannel):
        try:
            await log_channel.send(
                content=f"📄 Ticket-Transcript für **#{channel.name}** (ID `{channel.id}`).",
                file=discord.File(path, filename=path.name),
            )
        except discord.HTTPException as error:
            print(f"Transcript konnte nicht in den Log-Channel gesendet werden: {error}")
    return path


async def close_ticket(interaction: discord.Interaction) -> None:
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel) or ticket_owner_id(channel) is None:
        await interaction.response.send_message("Das ist kein Ticket-Channel.", ephemeral=True)
        return
    if (
        interaction.user.id != ticket_owner_id(channel)
        and not interaction.user.guild_permissions.manage_channels
    ):
        await interaction.response.send_message(
            "Nur der Ticket-Ersteller oder die Serververwaltung kann schließen.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    try:
        transcript = await create_ticket_transcript(channel)
    except (discord.Forbidden, discord.HTTPException, OSError) as error:
        await interaction.followup.send(
            f"Transcript konnte nicht gespeichert werden; das Ticket bleibt offen. Fehler: {error}",
            ephemeral=True,
        )
        return
    try:
        await channel.delete(reason=f"Ticket geschlossen von {interaction.user}")
    except discord.HTTPException as error:
        await interaction.followup.send(
            f"Transcript gespeichert unter `{transcript}`; der Channel konnte aber nicht gelöscht werden: {error}",
            ephemeral=True,
        )
        return
    await interaction.followup.send(
        f"Ticket geschlossen. Transcript gespeichert unter `{transcript}`.", ephemeral=True
    )


class TicketCloseView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ticket schließen", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket:close"
    )
    async def close_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await close_ticket(interaction)


class TicketSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Wähle den Grund für dein Ticket …",
            custom_id="ticket:category",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Support", value="support", emoji="🛟", description="Ich brauche Hilfe."),
                discord.SelectOption(label="Spieler melden", value="report", emoji="🚨", description="Ein Regelverstoß soll gemeldet werden."),
                discord.SelectOption(label="Sonstiges", value="other", emoji="💬", description="Ein anderes Anliegen."),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Das funktioniert nur auf einem Server.", ephemeral=True)
            return
        existing = next(
            (channel for channel in guild.text_channels if ticket_owner_id(channel) == interaction.user.id),
            None,
        )
        if existing:
            await interaction.response.send_message(
                f"Du hast bereits ein offenes Ticket: {existing.mention}", ephemeral=True
            )
            return

        category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
        if category is not None and not isinstance(category, discord.CategoryChannel):
            category = None
        if category is None:
            category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if category is None:
            category = await guild.create_category(TICKET_CATEGORY_NAME, reason="Ticket-System")

        kind = self.values[0]
        label = {"support": "support", "report": "meldung", "other": "sonstiges"}[kind]
        safe_name = re.sub(r"[^a-z0-9-]", "", interaction.user.name.lower().replace(" ", "-"))[:40] or "user"
        bot_member = guild.me or guild.get_member(bot.user.id if bot.user else 0)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, attach_files=True
            ),
        }
        if bot_member:
            overwrites[bot_member] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, manage_channels=True
            )
        channel = await guild.create_text_channel(
            name=f"ticket-{label}-{safe_name}",
            category=category,
            overwrites=overwrites,
            topic=f"ticket-owner:{interaction.user.id}; ticket-type:{kind}",
            reason=f"Ticket erstellt von {interaction.user}",
        )
        titles = {"support": "Support", "report": "Spieler melden", "other": "Sonstiges"}
        embed = discord.Embed(
            title=f"🎫 {titles[kind]}",
            description=f"Hallo {interaction.user.mention}! Beschreibe dein Anliegen. Das Team meldet sich bei dir.",
            color=discord.Color.blurple(),
        )
        await channel.send(content=interaction.user.mention, embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"Dein Ticket wurde erstellt: {channel.mention}", ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


@bot.event
async def setup_hook() -> None:
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())
    await bot.tree.sync()


@bot.event
async def on_ready() -> None:
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Schaut Louis‘s Stream",
        )
    )
    print(f"Eingeloggt als {bot.user} — Slash-Commands synchronisiert.")


@bot.event
async def on_member_join(member: discord.Member) -> None:
    if AUTO_ROLE_ID:
        role = member.guild.get_role(AUTO_ROLE_ID)
        if role:
            try:
                await member.add_roles(role, reason="Automatische Join-Rolle")
            except discord.HTTPException as error:
                print(f"Join-Rolle konnte nicht vergeben werden: {error}")
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID) if WELCOME_CHANNEL_ID else None
    if isinstance(channel, discord.TextChannel):
        await channel.send(f"Willkommen {member.mention} auf **{member.guild.name}**! 🎉")


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot or message.guild is None:
        return
    if (
        isinstance(message.author, discord.Member)
        and has_member_role(message.author)
        and LINK_PATTERN.search(message.content)
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


@bot.tree.command(name="ticket-panel", description="Sendet das Ticket-Panel in diesen Channel.")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.guild_only()
async def ticket_panel(interaction: discord.Interaction) -> None:
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Dieser Channel unterstützt keine Tickets.", ephemeral=True)
        return
    embed = discord.Embed(
        title="🎫 Support-Tickets",
        description="Wähle im Menü aus, worum es geht. Der Bot erstellt einen privaten Channel für dich.",
        color=discord.Color.blurple(),
    )
    await interaction.channel.send(embed=embed, view=TicketPanelView())
    await interaction.response.send_message("Ticket-Panel wurde erstellt.", ephemeral=True)


@bot.tree.command(name="close-ticket", description="Schließt dein Ticket und speichert ein Transcript.")
@app_commands.guild_only()
async def close_ticket_command(interaction: discord.Interaction) -> None:
    await close_ticket(interaction)


@bot.tree.command(name="ping", description="Zeigt Bot-Latenz und Online-Status.")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(f"Pong! 🏓 Latenz: {round(bot.latency * 1000)} ms")


@bot.tree.command(name="server", description="Zeigt Infos über diesen Server.")
@app_commands.guild_only()
async def server_info(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    await interaction.response.send_message(
        f"**{guild.name}**\nMitglieder: {guild.member_count}\nServer-ID: {guild.id}"
    )


@bot.tree.command(name="user", description="Zeigt Infos über einen Benutzer.")
@app_commands.describe(member="Benutzer (optional; standardmäßig du selbst)")
async def user_info(
    interaction: discord.Interaction, member: Optional[discord.User] = None
) -> None:
    user = member or interaction.user
    await interaction.response.send_message(
        f"**{user.display_name}**\nBenutzer-ID: {user.id}\nAccount erstellt: <t:{int(user.created_at.timestamp())}:D>"
    )


@bot.tree.command(name="hilfe", description="Zeigt die wichtigsten Bot-Befehle.")
async def help_command(interaction: discord.Interaction) -> None:
    embed = discord.Embed(title="🤖 Bot-Befehle", color=discord.Color.blurple())
    embed.description = (
        "`/ping` – Latenz und Online-Status\n"
        "`/server` – Server-Informationen\n"
        "`/user` – Benutzer-Informationen\n"
        "`/ticket-panel` – Ticket-Panel veröffentlichen (Serververwaltung)\n"
        "`/close-ticket` – Eigenes Ticket schließen und Transcript speichern"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def handle_rank_change(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role,
    reason: str,
    promote: bool,
) -> None:
    if member.bot or member.id == interaction.user.id:
        await interaction.response.send_message("Bots und dich selbst kannst du hier nicht ranken.", ephemeral=True)
        return
    old = highest_team_role(member)
    new_index = TEAM_ROLE_INDEX.get(role.id)
    actor = highest_team_role(interaction.user) if isinstance(interaction.user, discord.Member) else None
    if new_index is None:
        await interaction.response.send_message(
            "Die ausgewählte Rolle ist nicht in der konfigurierten Team-Hierarchie.", ephemeral=True
        )
        return
    old_index = TEAM_ROLE_INDEX.get(old[0], -1) if old else -1
    actor_index = TEAM_ROLE_INDEX.get(actor[0], -1) if actor else -1
    if (promote and new_index <= old_index) or (not promote and old is not None and new_index >= old_index):
        await interaction.response.send_message(
            "Die neue Rolle passt nicht zur gewählten Beförderung/Degradierung.", ephemeral=True
        )
        return
    if actor_index <= max(old_index, new_index):
        await interaction.response.send_message(
            "Du darfst diese Team-Rolle nicht verwalten (Rang-Hierarchie).", ephemeral=True
        )
        return
    await interaction.response.defer(ephemeral=True)
    old_role = interaction.guild.get_role(old[0]) if old else None
    try:
        if old_role and old_role in member.roles:
            await member.remove_roles(old_role, reason=f"Rangänderung von {interaction.user}: {reason}")
        await member.add_roles(role, reason=f"Rangänderung von {interaction.user}: {reason}")
    except discord.HTTPException:
        await interaction.followup.send(
            "Rolle konnte nicht geändert werden. Prüfe Rollen-Hierarchie und Bot-Berechtigungen.",
            ephemeral=True,
        )
        return
    await interaction.followup.send(
        f"Rolle geändert: {member.mention} → {role.mention} (Grund: {reason})", ephemeral=True
    )


@bot.tree.command(name="uprank", description="Befördert einen Team-User.")
@app_commands.checks.has_any_role(*MANAGEMENT_ROLES)
@app_commands.guild_only()
@app_commands.describe(member="Der User", rolle="Die neue höhere Team-Rolle", grund="Grund für die Beförderung")
async def uprank(interaction: discord.Interaction, member: discord.Member, rolle: discord.Role, grund: str) -> None:
    await handle_rank_change(interaction, member, rolle, grund, True)


@bot.tree.command(name="downrank", description="Degradiert einen Team-User.")
@app_commands.checks.has_any_role(*MANAGEMENT_ROLES)
@app_commands.guild_only()
@app_commands.describe(member="Der User", rolle="Die neue niedrigere Team-Rolle", grund="Grund für die Degradierung")
async def downrank(interaction: discord.Interaction, member: discord.Member, rolle: discord.Role, grund: str) -> None:
    await handle_rank_change(interaction, member, rolle, grund, False)


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    if isinstance(error, app_commands.MissingAnyRole):
        message = "Du hast keine Berechtigung für diesen Befehl."
    elif isinstance(error, app_commands.MissingPermissions):
        message = "Dir fehlen die nötigen Server-Berechtigungen."
    else:
        message = "Der Befehl ist fehlgeschlagen. Prüfe die Bot-Berechtigungen und Server-Konfiguration."
        print(f"Slash-Command-Fehler: {error!r}")
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN fehlt. Lege eine .env-Datei an und trage dort dein Bot-Token ein.")
    bot.run(token)
