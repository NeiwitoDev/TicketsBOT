from flask import Flask
from threading import Thread
import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import json

# ================= KEEP ALIVE =================

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

# ================= CONFIG =================

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
        custom_id="ticket_select",
        options=[
            discord.SelectOption(label="Soporte General"),
            discord.SelectOption(label="Soporte Tecnico"),
            discord.SelectOption(label="Reportar Usuario"),
            discord.SelectOption(label="Reportar Moderador"),
            discord.SelectOption(label="Reclamar Beneficios")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):

        user_id = str(interaction.user.id)

        if user_id in data["open"]:
            return await interaction.response.send_message("❌ Ya tienes un ticket abierto.", ephemeral=True)

        data["count"] += 1
        ticket_number = f"{data['count']:03d}"

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
            interaction.guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True)
        }

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{ticket_number}",
            overwrites=overwrites,
            category=interaction.guild.get_channel(CATEGORY_ID)
        )

        data["open"][user_id] = channel.id
        save_data(data)

        await channel.send(
            content=interaction.guild.get_role(STAFF_ROLE_ID).mention,
            embed=discord.Embed(
                title="🎟 Ticket Abierto",
                description=f"{interaction.user.mention}\nCategoría: {select.values[0]}"
            ),
            view=TicketButtons()
        )

        await interaction.response.send_message(f"✅ {channel.mention}", ephemeral=True)

# ================= BOTONES =================

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reclamar Ticket", style=discord.ButtonStyle.green, custom_id="claim_ticket")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🎯 Ticket reclamado.", ephemeral=True)

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Selecciona motivo:", view=CloseReason(), ephemeral=True)

# ================= CLOSE =================

class CloseReason(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.select(
        placeholder="Selecciona motivo",
        custom_id="close_reason",
        options=[
            discord.SelectOption(label="Resuelto"),
            discord.SelectOption(label="Sin motivo"),
            discord.SelectOption(label="Inactividad")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.channel.send(f"🔒 Cerrado: {select.values[0]}")
        await interaction.channel.delete()

# ================= COMANDO =================

@bot.command()
async def panel(ctx):
    await ctx.send("Panel de tickets", view=TicketPanel())

# ================= READY =================

@bot.event
async def on_ready():
    await tree.sync()
    bot.add_view(TicketPanel())
    bot.add_view(TicketButtons())
    setup_status(bot)
    print("Bot listo.")

# ================= RUN =================

keep_alive()
bot.run(TOKEN)
