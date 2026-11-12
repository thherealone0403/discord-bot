import os
import re
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
    except ValueError:
        raise RuntimeError(f"{name} muss eine gültige Discord-ID sein.")


# Bestehende Server-IDs können in .env überschrieben werden.
WELCOME_CHANNEL_ID = env_id("WELCOME_CHANNEL_ID", 1570259898690961591)
AUTO_ROLE_ID = env_id("AUTO_ROLE_ID", 1570262416502030356)
TICKET_CATEGORY_NAME = os.getenv("TICKET_CATEGORY_NAME", "Tickets")
TICKET_CATEGORY_ID = env_id("TICKET_CATEGORY_ID")

APPLY_PANEL_CHANNEL_ID = env_id("APPLY_PANEL_CHANNEL_ID", 1556047761164468238)
APPLY_APPS_CHANNEL_ID = env_id("APPLY_APPS_CHANNEL_ID", 1556047761412067417)
APPLY_ACCEPTED_CHANNEL_ID = env_id("APPLY_ACCEPTED_CHANNEL_ID", 1556262050743844904)
APPLY_REJECTED_CHANNEL_ID = env_id("APPLY_REJECTED_CHANNEL_ID", 1556262232818458724)
RANK_LOG_CHANNEL_ID = env_id("RANK_LOG_CHANNEL_ID", 1556047761412067410)

TRIAL_MOD_ROLE_ID = env_id("TRIAL_MOD_ROLE_ID", 1556047760355229696)
MOD_ROLE_ID = env_id("MOD_ROLE_ID", 1556047760355229697)
LEAD_MOD_ROLE_ID = env_id("LEAD_MOD_ROLE_ID", 1556047760355229698)
TRIAL_ADMIN_ROLE_ID = env_id("TRIAL_ADMIN_ROLE_ID", 1556047760355229700)
ADMIN_ROLE_ID = env_id("ADMIN_ROLE_ID", 1556047760355229701)
LEAD_ADMIN_ROLE_ID = env_id("LEAD_ADMIN_ROLE_ID", 1556047760355229702)
STV_TEAMLEITUNG_ROLE_ID = env_id("STV_TEAMLEITUNG_ROLE_ID", 1556047760359161948)
TEAMLEITUNG_ROLE_ID = env_id("TEAMLEITUNG_ROLE_ID", 1556047760359161949)
MANAGER_ROLE_ID = env_id("MANAGER_ROLE_ID", 1556047760359161951)
CO_OWNER_ROLE_ID = env_id("CO_OWNER_ROLE_ID", 1556047760359161953)
OWNER_ROLE_ID = env_id("OWNER_ROLE_ID", 1556047760359161954)
WARN1_ROLE_ID = env_id("WARN1_ROLE_ID", 1556047760334135331)
WARN2_ROLE_ID = env_id("WARN2_ROLE_ID", 1556047760334135330)

TEAM_ROLES_ORDERED = [
    (TRIAL_MOD_ROLE_ID, "Trial Mod"),
    (MOD_ROLE_ID, "Mod"),
    (LEAD_MOD_ROLE_ID, "Lead of Mod"),
    (TRIAL_ADMIN_ROLE_ID, "Trial Admin"),
    (ADMIN_ROLE_ID, "Admin"),
    (LEAD_ADMIN_ROLE_ID, "Lead of Admin"),
    (STV_TEAMLEITUNG_ROLE_ID, "Stv Teamleitung"),
    (TEAMLEITUNG_ROLE_ID, "Teamleitung"),
    (MANAGER_ROLE_ID, "Manager"),
    (CO_OWNER_ROLE_ID, "CO Owner"),
    (OWNER_ROLE_ID, "Owner"),
]
TEAM_ROLE_INDEX = {role_id: index for index, (role_id, _) in enumerate(TEAM_ROLES_ORDERED) if role_id}
MANAGEMENT_ROLES = {
    STV_TEAMLEITUNG_ROLE_ID, TEAMLEITUNG_ROLE_ID, MANAGER_ROLE_ID,
    CO_OWNER_ROLE_ID, OWNER_ROLE_ID,
} - {0}
REVIEW_ROLES = {
    LEAD_MOD_ROLE_ID, TRIAL_ADMIN_ROLE_ID, ADMIN_ROLE_ID, LEAD_ADMIN_ROLE_ID,
    STV_TEAMLEITUNG_ROLE_ID, TEAMLEITUNG_ROLE_ID, MANAGER_ROLE_ID,
    CO_OWNER_ROLE_ID, OWNER_ROLE_ID,
} - {0}

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
apply_enabled: dict[int, bool] = {}
pending_apply: dict[int, dict[str, str]] = {}


def has_any_role(member: discord.abc.User, role_ids: set[int]) -> bool:
    return isinstance(member, discord.Member) and any(role.id in role_ids for role in member.roles)


def highest_team_role(member: discord.Member) -> Optional[tuple[int, str]]:
    return next(
        ((role_id, name) for role_id, name in reversed(TEAM_ROLES_ORDERED)
         if role_id and any(role.id == role_id for role in member.roles)),
        None,
    )


def safe_text(value: str) -> str:
    return value.strip() or "Keine Angabe"


def ticket_owner_id(channel: discord.abc.GuildChannel) -> Optional[int]:
    match = re.search(r"ticket-owner:(\d+)", channel.topic or "")
    return int(match.group(1)) if match else None


class TicketCloseView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket schließen", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or ticket_owner_id(channel) is None:
            await interaction.response.send_message("Das ist kein Ticket-Channel.", ephemeral=True)
            return
        if interaction.user.id != ticket_owner_id(channel) and not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("Nur der Ticket-Ersteller oder die Serververwaltung kann schließen.", ephemeral=True)
            return
        await interaction.response.send_message("🔒 Ticket wird geschlossen.", ephemeral=True)
        await channel.delete(reason=f"Ticket geschlossen von {interaction.user}")


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
            await interaction.response.send_message(f"Du hast bereits ein offenes Ticket: {existing.mention}", ephemeral=True)
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
        name = re.sub(r"[^a-z0-9-]", "", interaction.user.name.lower().replace(" ", "-"))[:40] or "user"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True),
        }
        channel = await guild.create_text_channel(
            name=f"ticket-{label}-{name}",
            category=category,
            overwrites=overwrites,
            topic=f"ticket-owner:{interaction.user.id}; ticket-type:{kind}",
            reason=f"Ticket erstellt von {interaction.user}",
        )
        embed = discord.Embed(
            title=f"🎫 {dict(support='Support', report='Spieler melden', other='Sonstiges')[kind]}",
            description=f"Hallo {interaction.user.mention}! Beschreibe dein Anliegen. Das Team meldet sich bei dir.",
            color=discord.Color.blurple(),
        )
        await channel.send(content=interaction.user.mention, embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"Dein Ticket wurde erstellt: {channel.mention}", ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


class ApplyModal1(discord.ui.Modal, title="Trial Mod Bewerbung (1/2)"):
    roblox_user = discord.ui.TextInput(label="Roblox Username", placeholder="Dein Roblox-Username", max_length=64)
    spielminuten = discord.ui.TextInput(label="Spielminuten", placeholder="Wie viele Minuten hast du bereits im Spiel?", max_length=32)
    alter = discord.ui.TextInput(label="Alter", placeholder="Dein Alter", max_length=3)
    erfahrung = discord.ui.TextInput(label="Erfahrung mit Moderation?", style=discord.TextStyle.paragraph, max_length=500)
    warum = discord.ui.TextInput(label="Warum Trial Mod werden?", style=discord.TextStyle.paragraph, max_length=500)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        pending_apply[interaction.user.id] = {
            "roblox_user": self.roblox_user.value, "spielminuten": self.spielminuten.value,
            "alter": self.alter.value, "erfahrung": self.erfahrung.value, "warum": self.warum.value,
        }
        await interaction.response.send_modal(ApplyModal2())


class ApplyModal2(discord.ui.Modal, title="Trial Mod Bewerbung (2/2)"):
    warum_wir = discord.ui.TextInput(label="Warum sollten wir DICH nehmen?", style=discord.TextStyle.paragraph, max_length=500)
    streit = discord.ui.TextInput(label="Was machst du bei Streit?", style=discord.TextStyle.paragraph, max_length=500)
    provokation = discord.ui.TextInput(label="Was bei Provokation?", style=discord.TextStyle.paragraph, max_length=500)
    aktiv_roblox = discord.ui.TextInput(label="Aktivität Roblox (1-10)", max_length=2)
    aktiv_discord = discord.ui.TextInput(label="Aktivität Discord (1-10)", max_length=2)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        data = pending_apply.pop(interaction.user.id, None)
        if data is None:
            await interaction.response.send_message("Bewerbungsdaten fehlen. Bitte starte erneut.", ephemeral=True)
            return
        data.update({
            "warum_wir": self.warum_wir.value, "streit": self.streit.value,
            "provokation": self.provokation.value, "aktiv_roblox": self.aktiv_roblox.value,
            "aktiv_discord": self.aktiv_discord.value,
        })
        embed = discord.Embed(title="🛡️ Neue Trial Mod Bewerbung", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
        embed.set_author(name=f"{interaction.user} ({interaction.user.id})", icon_url=interaction.user.display_avatar.url)
        for title, key in [
            ("Roblox User", "roblox_user"), ("Spielminuten", "spielminuten"), ("Alter", "alter"),
            ("Erfahrung mit Moderation", "erfahrung"), ("Warum Trial Mod werden?", "warum"),
            ("Warum sollten wir dich nehmen?", "warum_wir"), ("Verhalten bei Streit", "streit"),
            ("Verhalten bei Provokation", "provokation"),
        ]:
            embed.add_field(name=title, value=safe_text(data[key])[:1024], inline=False)
        embed.add_field(name="Aktivität Roblox / Discord", value=f"{data['aktiv_roblox']}/10 · {data['aktiv_discord']}/10", inline=False)
        embed.set_footer(text=f"Bewerber-ID: {interaction.user.id}")
        channel = interaction.guild.get_channel(APPLY_APPS_CHANNEL_ID) if interaction.guild else None
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Bewerbungs-Channel nicht gefunden. Bitte Admin informieren.", ephemeral=True)
            return
        await channel.send(embed=embed, view=ReviewView())
        await interaction.response.send_message("✅ Deine Bewerbung wurde abgeschickt!", ephemeral=True)


class ApplyPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Jetzt bewerben", emoji="📝", style=discord.ButtonStyle.primary, custom_id="apply:start")
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not apply_enabled.get(interaction.guild_id, False):
            await interaction.response.send_message("Bewerbungen sind aktuell geschlossen.", ephemeral=True)
            return
        await interaction.response.send_modal(ApplyModal1())


class ReviewView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    def applicant_id(self, interaction: discord.Interaction) -> Optional[int]:
        if not interaction.message.embeds:
            return None
        footer = interaction.message.embeds[0].footer.text or ""
        match = re.search(r"Bewerber-ID:\s*(\d+)", footer)
        return int(match.group(1)) if match else None

    @discord.ui.button(label="Annehmen", emoji="✅", style=discord.ButtonStyle.success, custom_id="apply:accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not has_any_role(interaction.user, REVIEW_ROLES):
            await interaction.response.send_message("Keine Berechtigung.", ephemeral=True)
            return
        applicant_id = self.applicant_id(interaction)
        if applicant_id is None or interaction.guild is None:
            await interaction.response.send_message("Bewerber konnte nicht ermittelt werden.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        member = interaction.guild.get_member(applicant_id)
        if member is None:
            try:
                member = await interaction.guild.fetch_member(applicant_id)
            except discord.NotFound:
                member = None
        role = interaction.guild.get_role(TRIAL_MOD_ROLE_ID)
        granted = False
        if member and role:
            try:
                await member.add_roles(role, reason=f"Bewerbung angenommen von {interaction.user}")
                granted = True
            except discord.HTTPException:
                pass
        result_channel = interaction.guild.get_channel(APPLY_ACCEPTED_CHANNEL_ID)
        if isinstance(result_channel, discord.TextChannel):
            status = "Trial-Mod-Rolle vergeben." if granted else "Rolle konnte nicht vergeben werden."
            await result_channel.send(embed=discord.Embed(
                title="✅ Bewerbung angenommen",
                description=f"Bewerber: <@{applicant_id}>\nAngenommen von: {interaction.user.mention}\n{status}",
                color=discord.Color.green(), timestamp=discord.utils.utcnow(),
            ))
        embed = interaction.message.embeds[0]
        embed.title = "✅ BEWERBUNG ANGENOMMEN"
        embed.color = discord.Color.green()
        await interaction.message.edit(embed=embed, view=None)
        await interaction.followup.send("Bewerbung angenommen.", ephemeral=True)

    @discord.ui.button(label="Ablehnen", emoji="❌", style=discord.ButtonStyle.danger, custom_id="apply:reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not has_any_role(interaction.user, REVIEW_ROLES):
            await interaction.response.send_message("Keine Berechtigung.", ephemeral=True)
            return
        applicant_id = self.applicant_id(interaction)
        if applicant_id is None or interaction.guild is None:
            await interaction.response.send_message("Bewerber konnte nicht ermittelt werden.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        result_channel = interaction.guild.get_channel(APPLY_REJECTED_CHANNEL_ID)
        if isinstance(result_channel, discord.TextChannel):
            await result_channel.send(embed=discord.Embed(
                title="❌ Bewerbung abgelehnt",
                description=f"Bewerber: <@{applicant_id}>\nAbgelehnt von: {interaction.user.mention}",
                color=discord.Color.red(), timestamp=discord.utils.utcnow(),
            ))
        embed = interaction.message.embeds[0]
        embed.title = "❌ BEWERBUNG ABGELEHNT"
        embed.color = discord.Color.red()
        await interaction.message.edit(embed=embed, view=None)
        await interaction.followup.send("Bewerbung abgelehnt.", ephemeral=True)


@bot.event
async def setup_hook() -> None:
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())
    bot.add_view(ApplyPanelView())
    bot.add_view(ReviewView())
    await bot.tree.sync()


@bot.event
async def on_ready() -> None:
    print(f"Eingeloggt als {bot.user} — Slash-Commands synchronisiert.")


@bot.event
async def on_member_join(member: discord.Member) -> None:
    if AUTO_ROLE_ID:
        role = member.guild.get_role(AUTO_ROLE_ID)
        if role:
            try:
                await member.add_roles(role, reason="Automatische Join-Rolle")
            except discord.HTTPException:
                pass
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID) if WELCOME_CHANNEL_ID else None
    if isinstance(channel, discord.TextChannel):
        await channel.send(f"Willkommen {member.mention} auf **{member.guild.name}**! 🎉")


LINK_PATTERN = re.compile(r"(?:https?://|www\.|discord\.gg/|discord(?:app)?\.com/invite/)", re.IGNORECASE)


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot or message.guild is None:
        return
    if LINK_PATTERN.search(message.content):
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention}, Links sind hier nicht erlaubt.", delete_after=8)
        except discord.Forbidden:
            pass
        return
    await bot.process_commands(message)


@bot.tree.command(name="ticket-panel", description="Sendet das Ticket-Panel mit Dropdown in diesen Channel.")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.guild_only()
async def ticket_panel(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="🎫 Support-Tickets",
        description="Wähle im Menü unten aus, worum es geht. Der Bot erstellt einen privaten Channel für dich.",
        color=discord.Color.blurple(),
    )
    await interaction.channel.send(embed=embed, view=TicketPanelView())
    await interaction.response.send_message("Ticket-Panel wurde erstellt.", ephemeral=True)


@bot.tree.command(name="close-ticket", description="Schließt das aktuelle Ticket.")
@app_commands.guild_only()
async def close_ticket(interaction: discord.Interaction) -> None:
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel) or ticket_owner_id(channel) is None:
        await interaction.response.send_message("Das ist kein Ticket-Channel.", ephemeral=True)
        return
    if interaction.user.id != ticket_owner_id(channel) and not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Nur der Ticket-Ersteller oder die Serververwaltung kann schließen.", ephemeral=True)
        return
    await interaction.response.send_message("🔒 Ticket wird geschlossen.", ephemeral=True)
    await channel.delete(reason=f"Ticket geschlossen von {interaction.user}")


@bot.tree.command(name="ping", description="Zeigt, ob der Bot online ist.")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("Pong! 🏓")


@bot.tree.command(name="server", description="Zeigt Infos über diesen Server.")
@app_commands.guild_only()
async def server_info(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    await interaction.response.send_message(f"**{guild.name}**\nMitglieder: {guild.member_count}\nServer-ID: {guild.id}")


@bot.tree.command(name="user", description="Zeigt Infos über dich.")
async def user_info(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(f"**{interaction.user.display_name}**\nBenutzer-ID: {interaction.user.id}")


@bot.tree.command(name="apply-panel", description="Sendet das Bewerbungs-Panel in den konfigurierten Channel.")
@app_commands.checks.has_any_role(*REVIEW_ROLES)
@app_commands.guild_only()
async def apply_panel(interaction: discord.Interaction) -> None:
    channel = interaction.guild.get_channel(APPLY_PANEL_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Bewerbungs-Panel-Channel nicht gefunden.", ephemeral=True)
        return
    embed = discord.Embed(
        title="🛡️ Trial-Mod-Bewerbung",
        description="Klicke auf **Jetzt bewerben**, um das Formular auszufüllen. Bewerbungen müssen vorher mit `/apply-on` geöffnet werden.",
        color=discord.Color.blue(),
    )
    await channel.send(embed=embed, view=ApplyPanelView())
    await interaction.response.send_message("Bewerbungs-Panel gesendet.", ephemeral=True)


@bot.tree.command(name="apply-on", description="Öffnet Bewerbungen für Trial Mods.")
@app_commands.checks.has_any_role(*REVIEW_ROLES)
@app_commands.guild_only()
async def apply_on(interaction: discord.Interaction) -> None:
    apply_enabled[interaction.guild_id] = True
    channel = interaction.guild.get_channel(APPLY_PANEL_CHANNEL_ID)
    if isinstance(channel, discord.TextChannel):
        await channel.send("Bewerbungen für Trial Mods sind jetzt geöffnet! 🎉")
    await interaction.response.send_message("Bewerbungen aktiviert.", ephemeral=True)


@bot.tree.command(name="apply-off", description="Schließt Bewerbungen für Trial Mods.")
@app_commands.checks.has_any_role(*REVIEW_ROLES)
@app_commands.guild_only()
async def apply_off(interaction: discord.Interaction) -> None:
    apply_enabled[interaction.guild_id] = False
    await interaction.response.send_message("Bewerbungen deaktiviert.", ephemeral=True)


async def handle_rank_change(
    interaction: discord.Interaction, member: discord.Member, role: discord.Role, reason: str, promote: bool,
) -> None:
    if member.bot or member.id == interaction.user.id:
        await interaction.response.send_message("Bots und dich selbst kannst du hier nicht ranken.", ephemeral=True)
        return
    old = highest_team_role(member)
    new_index = TEAM_ROLE_INDEX.get(role.id)
    actor = highest_team_role(interaction.user) if isinstance(interaction.user, discord.Member) else None
    if new_index is None:
        await interaction.response.send_message("Die ausgewählte Rolle ist nicht in der konfigurierten Team-Hierarchie.", ephemeral=True)
        return
    old_index = TEAM_ROLE_INDEX.get(old[0], -1) if old else -1
    actor_index = TEAM_ROLE_INDEX.get(actor[0], -1) if actor else -1
    if (promote and new_index <= old_index) or (not promote and old is not None and new_index >= old_index):
        await interaction.response.send_message("Die neue Rolle passt nicht zur gewählten Beförderung/Degradierung.", ephemeral=True)
        return
    if actor_index <= max(old_index, new_index):
        await interaction.response.send_message("Du darfst diese Team-Rolle nicht verwalten (Rang-Hierarchie).", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    old_role = interaction.guild.get_role(old[0]) if old else None
    try:
        if old_role and old_role in member.roles:
            await member.remove_roles(old_role, reason=f"Rangänderung von {interaction.user}: {reason}")
        await member.add_roles(role, reason=f"Rangänderung von {interaction.user}: {reason}")
    except discord.HTTPException:
        await interaction.followup.send("Rolle konnte nicht geändert werden. Prüfe Rollen-Hierarchie und Bot-Berechtigungen.", ephemeral=True)
        return
    log = interaction.guild.get_channel(RANK_LOG_CHANNEL_ID) if RANK_LOG_CHANNEL_ID else None
    if isinstance(log, discord.TextChannel):
        embed = discord.Embed(title="⬆️ UPRANK" if promote else "⬇️ DOWNRANK", color=discord.Color.green() if promote else discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Wer", value=member.mention)
        embed.add_field(name="Grund", value=reason[:1024])
        embed.add_field(name="Rolle davor", value=old[1] if old else "Keine")
        embed.add_field(name="Rolle danach", value=role.mention)
        embed.add_field(name="Von wem", value=interaction.user.mention)
        await log.send(embed=embed)
    await interaction.followup.send(f"Rolle geändert: {member.mention} → {role.mention}", ephemeral=True)


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


@bot.tree.command(name="warn", description="Verwarnt einen User: Warn 1 → Warn 2.")
@app_commands.checks.has_any_role(*MANAGEMENT_ROLES)
@app_commands.guild_only()
@app_commands.describe(member="Der zu verwarnende User", grund="Grund für die Verwarnung")
async def warn(interaction: discord.Interaction, member: discord.Member, grund: str) -> None:
    if member.bot or member.id == interaction.user.id:
        await interaction.response.send_message("Bots und dich selbst kannst du nicht verwarnen.", ephemeral=True)
        return
    warn1, warn2 = interaction.guild.get_role(WARN1_ROLE_ID), interaction.guild.get_role(WARN2_ROLE_ID)
    if warn1 is None or warn2 is None:
        await interaction.response.send_message("Warn-Rollen nicht gefunden. Bitte IDs prüfen.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        if warn2 in member.roles:
            result = "hat bereits Warn 2."
        elif warn1 in member.roles:
            await member.remove_roles(warn1, reason=f"Warn 2 von {interaction.user}: {grund}")
            await member.add_roles(warn2, reason=f"Warn 2 von {interaction.user}: {grund}")
            result = "erhält Warn 2."
        else:
            await member.add_roles(warn1, reason=f"Warn 1 von {interaction.user}: {grund}")
            result = "erhält Warn 1."
    except discord.HTTPException:
        await interaction.followup.send("Warn-Rolle konnte nicht vergeben werden. Prüfe die Bot-Berechtigungen.", ephemeral=True)
        return
    try:
        await member.send(f"Du wurdest auf **{interaction.guild.name}** verwarnt: {grund}")
    except discord.Forbidden:
        pass
    await interaction.followup.send(f"{member.mention} {result} Grund: {grund}", ephemeral=True)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
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
