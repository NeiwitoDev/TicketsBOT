import discord 
from discord.ext import commands
import os
import asyncio
import json
from discord.ext import tasks
import itertools
from discord import app_commands

# ===============================
# ⚙️ CONFIGURACIÓN
# ===============================

TICKET_CATEGORY_ID = 1466491475436245220

STAFF_ROLE_ID_1 = 1466244726796582964
STAFF_ROLE_ID_2 = 1466245030334435398

ALTO_MANDO_ROLE_ID = 1476595202813857857

# 🎯 CONFIG CALIFICACIONES
CANAL_COMANDO_ID = 1466231866041307187
CANAL_CALIFICACIONES_ID = 1466240831609638923
ROL_STAFF_CALIFICABLE = 1466245030334435398
DATA_FILE = "calificaciones.json"

# ===============================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

tickets_abiertos = {}

# ===============================
# SISTEMA JSON CALIFICACIONES
# ===============================

def cargar_datos():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def guardar_datos(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ===============================
# READY
# ===============================

estados = itertools.cycle([
    discord.Activity(type=discord.ActivityType.watching, name="↪ developer: neiwito."),
    discord.Activity(type=discord.ActivityType.playing, name="↪ Villa Carlos Paz RP")
])

@tasks.loop(seconds=15)
async def cambiar_estado():
    await bot.change_presence(activity=next(estados))

@bot.event
async def on_ready():
    cambiar_estado.start()

    try:
        synced = await bot.tree.sync()
        print(f"🔁 Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(e)

    print(f"✅ Bot conectado como {bot.user}")

# ===============================
# /calificar-staff
# ===============================

@bot.tree.command(name="calificar-staff", description="Calificar a un miembro del staff")
@app_commands.describe(
    staff="Selecciona el staff a calificar",
    calificacion="Puntuación del 1 al 5",
    nota="Comentario sobre el servicio"
)
@app_commands.choices(calificacion=[
    app_commands.Choice(name="⭐ 1", value=1),
    app_commands.Choice(name="⭐⭐ 2", value=2),
    app_commands.Choice(name="⭐⭐⭐ 3", value=3),
    app_commands.Choice(name="⭐⭐⭐⭐ 4", value=4),
    app_commands.Choice(name="⭐⭐⭐⭐⭐ 5", value=5),
])
async def calificar_staff(interaction: discord.Interaction,
                          staff: discord.Member,
                          calificacion: app_commands.Choice[int],
                          nota: str):

    if interaction.channel.id != CANAL_COMANDO_ID:
        await interaction.response.send_message(
            "❌ Este comando solo puede usarse en el canal correspondiente.",
            ephemeral=True
        )
        return

    if ROL_STAFF_CALIFICABLE not in [role.id for role in staff.roles]:
        await interaction.response.send_message(
            "❌ Solo puedes calificar a miembros oficiales del staff.",
            ephemeral=True
        )
        return

    data = cargar_datos()
    staff_id = str(staff.id)

    if staff_id not in data:
        data[staff_id] = {"total": 0, "suma": 0}

    data[staff_id]["total"] += 1
    data[staff_id]["suma"] += calificacion.value
    guardar_datos(data)

    total = data[staff_id]["total"]
    promedio = round(data[staff_id]["suma"] / total, 2)
    estrellas = "⭐" * calificacion.value

    canal_envio = interaction.guild.get_channel(CANAL_CALIFICACIONES_ID)

    embed = discord.Embed(
        title="📋 Registro Oficial de Evaluación",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Usuario:** {interaction.user.mention}\n"
            f"🛡️ **Staff Evaluado:** {staff.mention}\n"
            f"🌟 **Calificación:** {estrellas}\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x00BFFF
    )

    embed.add_field(
        name="💬 Opinión del Usuario",
        value=f"```{nota}```",
        inline=False
    )

    embed.add_field(
        name="📊 Estadísticas del Staff",
        value=(
            f"📝 Total de evaluaciones: **{total}**\n"
            f"📈 Promedio actual: **{promedio}/5**"
        ),
        inline=False
    )

    embed.set_thumbnail(url=staff.display_avatar.url)
    embed.set_footer(text="VCP • Villa Carlos Paz RP | Sistema Oficial")

    if canal_envio:
        await canal_envio.send(embed=embed)

    await interaction.response.send_message(
        "✅ Tu calificación fue registrada correctamente.",
        ephemeral=True
    )

# ===============================
# SISTEMA DE TICKETS
# ===============================

class VerTicketView(discord.ui.View):
    def __init__(self, canal):
        super().__init__(timeout=60)
        self.add_item(
            discord.ui.Button(
                label="🔎 Ver Ticket",
                style=discord.ButtonStyle.link,
                url=canal.jump_url
            )
        )

class TicketButtons(discord.ui.View):
    def __init__(self, creador, tipo):
        super().__init__(timeout=None)
        self.creador = creador
        self.tipo = tipo
        self.claimed_by = None

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.red)
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Selecciona el motivo del cierre:",
            ephemeral=True
        )

    @discord.ui.button(label="📌 Reclamar Ticket", style=discord.ButtonStyle.green)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):

        # 🔒 SOLO ROL 1466245030334435398 PUEDE RECLAMAR
        if STAFF_ROLE_ID_2 not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message(
                "❌ No tienes permiso para reclamar este ticket.",
                ephemeral=True
            )
            return

        if self.claimed_by:
            await interaction.response.send_message(
                f"⚠️ Ya fue reclamado por {self.claimed_by.mention}",
                ephemeral=True
            )
            return

        self.claimed_by = interaction.user

        embed = discord.Embed(
            description=f"📌 Ticket reclamado por {interaction.user.mention}",
            color=discord.Color.gold()
        )

        await interaction.response.send_message(embed=embed)

# ===============================
# RUN
# ===============================

bot.run(os.getenv("TOKEN"))
