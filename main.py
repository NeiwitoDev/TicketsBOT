from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

import discord
from discord.ext import commands, tasks
from discord import app_commands
import json

TOKEN = os.getenv("TOKEN")

CATEGORY_ID = 1466491475436245220
STAFF_ROLE_ID = 1466245030334435398
ADMIN_RESET_ROLE = 1466440467204800597

CANAL_CALIFICAR = 1466231866041307187
CANAL_RESULTADOS = 1466240831609638923

DATA_FILE = "data.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ================= DATA =================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"count": 0, "open": {}, "claims": {}, "ratings": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=4)

data = load_data()

# ================= STATUS =================

def setup_status(bot):
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name="↪ developer neiwito."),
        discord.Game(name="↪ VCPRP")
    ]

    current = 0

    @tasks.loop(seconds=5)
    async def change_status():
        nonlocal current
        await bot.change_presence(activity=statuses[current])
        current = (current + 1) % len(statuses)

    @change_status.before_loop
    async def before():
        await bot.wait_until_ready()

    change_status.start()

# ================= PANEL =================

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Selecciona una categoría",
        custom_id="ticket_select",  # 👈 FIX
        options=[
            discord.SelectOption(label="Soporte General", emoji="<:Soportegeneral:1478091664596664541>"),
            discord.SelectOption(label="Soporte Tecnico", emoji="<:developer:1478090349611057335>"),
            discord.SelectOption(label="Reportar Usuario", emoji="<:miembro:1478090498076835910>"),
            discord.SelectOption(label="Reportar Moderador", emoji="<:staffteam:1478090615056236697>"),
            discord.SelectOption(label="Reclamar Beneficios", emoji="<:Booster:1478090731288662186>")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):

        user_id = str(interaction.user.id)

        if user_id in data["open"]:
            return await interaction.response.send_message(
                "❌ Ya tienes un ticket abierto.",
                ephemeral=True
            )

        data["count"] += 1
        ticket_number = f"{data['count']:03d}"
        channel_name = f"ticket-{ticket_number}"

        category = interaction.guild.get_channel(CATEGORY_ID)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await interaction.guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category
        )

        data["open"][user_id] = channel.id
        save_data(data)

        embed = discord.Embed(
            title="🎟 Ticket Abierto",
            description=f"""
Bienvenido {interaction.user.mention}

Un miembro del staff atenderá tu solicitud pronto.

📌 Categoría: **{select.values[0]}**
            """,
            color=0x2b2d31
        )

        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)

        await channel.send(
            content=staff_role.mention,
            embed=embed,
            view=TicketButtons()
        )

        await interaction.response.send_message(
            f"✅ Tu ticket fue creado: {channel.mention}",
            ephemeral=True
        )

# ================= BOTONES =================

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reclamar Ticket", style=discord.ButtonStyle.green, custom_id="claim_ticket")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):

        if STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("❌ Solo staff.", ephemeral=True)

        channel_id = str(interaction.channel.id)

        if channel_id in data["claims"]:

            if data["claims"][channel_id] == interaction.user.id:
                return await interaction.response.send_message(
                    "⚠️ Ya reclamaste este ticket.",
                    ephemeral=True
                )
            else:
                return await interaction.response.send_message(
                    "❌ Este ticket ya está reclamado por otro staff.",
                    ephemeral=True
                )

        data["claims"][channel_id] = interaction.user.id
        save_data(data)

        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
        for member in staff_role.members:
            if member.id != interaction.user.id:
                await interaction.channel.set_permissions(member, read_messages=False)

        embed = discord.Embed(
            title="🎯 Ticket Reclamado",
            description=f"<:staffteam:1478090615056236697> Staff asignado: {interaction.user.mention}",
            color=0x57F287
        )

        await interaction.channel.send(embed=embed)

        user_id = next((u for u, c in data["open"].items() if c == interaction.channel.id), None)
        if user_id:
            user = await bot.fetch_user(int(user_id))
            await user.send(embed=discord.Embed(
                title="📩 Tu ticket fue asignado",
                description=f"El staff {interaction.user} está atendiendo tu caso.",
                color=0x57F287
            ))

        await interaction.response.defer()

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        if STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("❌ Solo staff.", ephemeral=True)

        await interaction.response.send_message(
            "Selecciona el motivo de cierre:",
            view=CloseReason(),
            ephemeral=True
        )

# ================= MOTIVO =================

class CloseReason(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.select(
        placeholder="Selecciona motivo",
        custom_id="close_reason_select",  # 👈 FIX
        options=[
            discord.SelectOption(label="Ticket Resuelto"),
            discord.SelectOption(label="Ticket abierto sin motivo"),
            discord.SelectOption(label="Ticket con inactividad")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):

        motivo = select.values[0]

        user_id = next((u for u, c in data["open"].items() if c == interaction.channel.id), None)

        embed = discord.Embed(
            title="🔒 Ticket Cerrado",
            description=f"Motivo: **{motivo}**\nCerrado por: {interaction.user.mention}",
            color=0xED4245
        )

        await interaction.channel.send(embed=embed)

        if user_id:
            user = await bot.fetch_user(int(user_id))
            await user.send(embed=embed)
            del data["open"][user_id]

        if str(interaction.channel.id) in data["claims"]:
            del data["claims"][str(interaction.channel.id)]

        save_data(data)

        await interaction.channel.delete()

# ================= COMANDOS =================

@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🎫 Sistema Oficial de Tickets",
        description="""
<:Soportegeneral:1478091664596664541> **Soporte General**
<:developer:1478090349611057335> **Soporte Tecnico**
<:miembro:1478090498076835910> **Reportar Usuario**
<:staffteam:1478090615056236697> **Reportar Moderador**
<:Booster:1478090731288662186> **Reclamar Beneficios**

Selecciona una categoría.
        """,
        color=discord.Color.from_rgb(255, 255, 255)
    )
    embed.set_footer(text="Dev Neiwito! • Tickets System")
    await ctx.send(embed=embed, view=TicketPanel())

# ================= READY =================

@bot.event
async def on_ready():
    await tree.sync()
    bot.add_view(TicketButtons()) 
    setup_status(bot)
    print("Bot listo.")

# ================= RUN =================

keep_alive()
bot.run(TOKEN)
