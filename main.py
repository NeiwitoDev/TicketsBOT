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
    Thread(target=run).start()

# ================= DISCORD =================

import discord
from discord.ext import commands, tasks
import json

TOKEN = os.getenv("TOKEN")

CATEGORY_ID = 1466491475436245220
STAFF_ROLE_ID = 1466245030334435398

DATA_FILE = "data.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DATA =================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"count": 0, "open": {}}
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=4)

data = load_data()

# ================= STATUS =================

def setup_status():
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name="↪ developer neiwito."),
        discord.Game(name="↪ VCPRP")
    ]
    i = 0

    @tasks.loop(seconds=15)
    async def loop_status():
        nonlocal i
        await bot.change_presence(activity=statuses[i])
        i = (i + 1) % len(statuses)

    @loop_status.before_loop
    async def before():
        await bot.wait_until_ready()

    loop_status.start()

# ================= PANEL =================

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="📂 Selecciona una categoría",
        custom_id="ticket_select",
        options=[
            discord.SelectOption(label="Soporte General", emoji=discord.PartialEmoji(name="Soportegeneral", id=1478091664596664541)),
            discord.SelectOption(label="Soporte Tecnico", emoji=discord.PartialEmoji(name="developer", id=1478090349611057335)),
            discord.SelectOption(label="Reportar Usuario", emoji=discord.PartialEmoji(name="miembro", id=1478090498076835910)),
            discord.SelectOption(label="Reportar Moderador", emoji=discord.PartialEmoji(name="staffteam", id=1478090615056236697)),
            discord.SelectOption(label="Reclamar Beneficios", emoji=discord.PartialEmoji(name="Booster", id=1478090731288662186))
        ]
    )
    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        if user_id in data["open"]:
            return await interaction.response.send_message("❌ Ya tienes un ticket abierto.", ephemeral=True)

        data["count"] += 1
        ticket_id = f"{data['count']:03d}"

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{ticket_id}",
            category=interaction.guild.get_channel(CATEGORY_ID),
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True)
            }
        )

        data["open"][user_id] = channel.id
        save_data(data)

        embed = discord.Embed(
            title="🎟 Ticket Abierto",
            description=f"""
👋 Hola {interaction.user.mention}

📌 Un miembro del staff te atenderá pronto.

🗂 Categoría: **{interaction.data['values'][0]}**
""",
            color=0x2b2d31
        )

        await channel.send(
            content=interaction.guild.get_role(STAFF_ROLE_ID).mention,
            embed=embed,
            view=TicketButtons()
        )

        await interaction.response.send_message(f"✅ Ticket creado: {channel.mention}", ephemeral=True)

# ================= BOTONES =================

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send("🔒 Ticket cerrado")
        await interaction.channel.delete()

# ================= COMANDO PANEL =================

@bot.command(name="panel-send")
async def panel_send(ctx):

    # BORRA EL COMANDO
    try:
        await ctx.message.delete()
    except:
        pass

    embed = discord.Embed(
        title="🎫 Sistema de Tickets",
        description="""
📌 **Abre un ticket seleccionando una opción**

<:Soportegeneral:1478091664596664541> Soporte General  
<:developer:1478090349611057335> Soporte Tecnico  
<:miembro:1478090498076835910> Reportar Usuario  
<:staffteam:1478090615056236697> Reportar Moderador  
<:Booster:1478090731288662186> Reclamar Beneficios  

⚠ Usa el menú desplegable debajo
""",
        color=discord.Color.white()
    )

    embed.set_footer(text="Dev Neiwito • Sistema de Tickets")

    await ctx.send(embed=embed, view=TicketPanel())

# ================= FIX =================

@bot.event
async def on_message(message):
    await bot.process_commands(message)

@bot.event
async def on_ready():
    bot.add_view(TicketPanel())
    bot.add_view(TicketButtons())
    setup_status()
    print("Bot listo.")

# ================= RUN =================

keep_alive()
bot.run(TOKEN)
