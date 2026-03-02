import discord
from discord.ext import commands
from discord import app_commands
import os
import json
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

# =========================
# CONFIG
# =========================

STAFF_ROLE_ID = 1466245030334435398
ADMIN_RESET_ROLE = 1466440467204800597

CANAL_CALIFICAR = 1466231866041307187
CANAL_RESULTADOS = 1466240831609638923

DATA_FILE = "tickets_data.json"

# =========================
# BOT
# =========================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# =========================
# DATA
# =========================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "count": 0,
            "open_tickets": {},
            "staff_ratings": {}
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# =========================
# SLASH: CALIFICAR STAFF
# =========================

@tree.command(name="calificar-staff", description="Calificar atención del staff")
async def calificar_staff(
    interaction: discord.Interaction,
    staff: discord.Member,
    calificacion: app_commands.Range[int, 1, 10],
    nota: str
):

    if interaction.channel.id != CANAL_CALIFICAR:
        return await interaction.response.send_message(
            "❌ Usa este comando en el canal correspondiente.",
            ephemeral=True
        )

    # Verificar que tenga rol staff
    if STAFF_ROLE_ID not in [r.id for r in staff.roles]:
        return await interaction.response.send_message(
            "❌ Solo puedes calificar miembros del Staff.",
            ephemeral=True
        )

    staff_id = str(staff.id)

    # Guardar calificación
    if staff_id not in data["staff_ratings"]:
        data["staff_ratings"][staff_id] = []

    data["staff_ratings"][staff_id].append(calificacion)

    # Calcular promedio
    ratings = data["staff_ratings"][staff_id]
    promedio = sum(ratings) / len(ratings)

    save_data(data)

    canal = bot.get_channel(CANAL_RESULTADOS)

    embed = discord.Embed(
        title="📊 Nueva Evaluación de Staff",
        description="Sistema de valoración automática",
        color=0x5865F2
    )

    embed.add_field(name="👮 Staff", value=staff.mention, inline=False)
    embed.add_field(name="👤 Usuario", value=interaction.user.mention, inline=True)
    embed.add_field(name="⭐ Calificación", value=f"{calificacion}/10", inline=True)
    embed.add_field(name="📈 Promedio Actual", value=f"{promedio:.2f}/10", inline=True)
    embed.add_field(name="📝 Opinión", value=nota, inline=False)

    embed.set_footer(text=f"Total de evaluaciones: {len(ratings)} • Dev Neiwito!")

    await canal.send(embed=embed)

    await interaction.response.send_message(
        "✅ Tu evaluación fue enviada correctamente.",
        ephemeral=True
    )

# =========================
# SLASH: RESET COUNT
# =========================

@tree.command(name="reset-count", description="Resetear contador de tickets")
async def reset_count(interaction: discord.Interaction):

    if ADMIN_RESET_ROLE not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message(
            "❌ No tienes permiso.",
            ephemeral=True
        )

    data["count"] = 0
    save_data(data)

    await interaction.response.send_message(
        "✅ Contador reiniciado a Ticket-001.",
        ephemeral=True
    )

# =========================
# READY
# =========================

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot conectado como {bot.user}")

bot.run(TOKEN)
