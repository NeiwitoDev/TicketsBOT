import discord
from discord.ext import commands
from discord.ui import View
import json
import os
from dotenv import load_dotenv

# =========================
# CARGAR .ENV
# =========================

load_dotenv()
TOKEN = os.getenv("TOKEN")

# =========================
# INTENTS
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# SISTEMA PERSISTENTE
# =========================

COUNTER_FILE = "ticket_counter.json"

def get_ticket_number():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w") as f:
            json.dump({"last_ticket": 0}, f)

    with open(COUNTER_FILE, "r") as f:
        data = json.load(f)

    data["last_ticket"] += 1

    with open(COUNTER_FILE, "w") as f:
        json.dump(data, f, indent=4)

    return data["last_ticket"]

# =========================
# CREAR TICKET
# =========================

class TicketPanel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ver-ticket",
        style=discord.ButtonStyle.green,
        emoji="🎫",
        custom_id="create_ticket_button"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        ticket_number = get_ticket_number()
        ticket_name = f"TICKET-{ticket_number:03d}"

        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        category = interaction.channel.category

        channel = await guild.create_text_channel(
            name=ticket_name,
            overwrites=overwrites,
            category=category
        )

        embed = discord.Embed(
            title="📩 Ticket Creado",
            description=f"{interaction.user.mention} tu ticket fue creado correctamente.\n\nUn staff te atenderá pronto.",
            color=0x2ecc71
        )

        embed.add_field(name="🆔 ID", value=f"`{ticket_name}`")
        embed.set_footer(text="Stars Solutions Studios • Sistema de Soporte")

        await channel.send(embed=embed, view=CloseTicket())

        await interaction.response.send_message(
            f"✅ Ticket creado: {channel.mention}",
            ephemeral=True
        )

# =========================
# CERRAR TICKET
# =========================

class CloseTicket(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Cerrar Ticket",
        style=discord.ButtonStyle.red,
        emoji="🔒",
        custom_id="close_ticket_button"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        user = interaction.user
        channel = interaction.channel

        try:
            await user.send(f"🔒 Tu ticket `{channel.name}` fue cerrado por el staff.")
        except:
            pass

        await interaction.response.send_message("🗑 Cerrando ticket...", ephemeral=True)
        await channel.delete()

# =========================
# PANEL
# =========================

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):

    embed = discord.Embed(
        title="🎟 Sistema de Tickets",
        description=(
            "¿Necesitas ayuda?\n\n"
            "Presiona el botón **ver-ticket** para abrir un ticket privado."
        ),
        color=0x3498db
    )

    embed.add_field(name="⏱ Tiempo estimado", value="5 - 30 minutos", inline=False)
    embed.add_field(name="📜 Reglas", value="No abuses del sistema.", inline=False)
    embed.set_footer(text="Stars Solutions Studios")

    await ctx.send(embed=embed, view=TicketPanel())

# =========================
# READY
# =========================

@bot.event
async def on_ready():
    bot.add_view(TicketPanel())
    bot.add_view(CloseTicket())
    print(f"✅ Bot listo como {bot.user}")

# =========================
# INICIAR BOT
# =========================

if TOKEN is None:
    print("❌ ERROR: No se encontró el TOKEN en el .env")
else:
    bot.run(TOKEN)
