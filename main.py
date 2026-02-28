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
# SISTEMA CALIFICACIONES
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
    await bot.tree.sync()
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
        await interaction.response.send_message("❌ Usa este comando en el canal correspondiente.", ephemeral=True)
        return

    if ROL_STAFF_CALIFICABLE not in [r.id for r in staff.roles]:
        await interaction.response.send_message("❌ Solo puedes calificar staff oficiales.", ephemeral=True)
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

    embed = discord.Embed(
        title="📋 Registro Oficial de Evaluación",
        color=0x00BFFF
    )

    embed.add_field(name="Usuario", value=interaction.user.mention, inline=False)
    embed.add_field(name="Staff Evaluado", value=staff.mention, inline=False)
    embed.add_field(name="Calificación", value=estrellas, inline=False)
    embed.add_field(name="Opinión", value=f"```{nota}```", inline=False)
    embed.add_field(
        name="Estadísticas",
        value=f"Total: {total}\nPromedio: {promedio}/5",
        inline=False
    )

    canal = interaction.guild.get_channel(CANAL_CALIFICACIONES_ID)
    if canal:
        await canal.send(embed=embed)

    await interaction.response.send_message("✅ Calificación registrada.", ephemeral=True)

# ===============================
# SISTEMA TICKETS
# ===============================

class TicketButtons(discord.ui.View):
    def __init__(self, creador, tipo):
        super().__init__(timeout=None)
        self.creador = creador
        self.tipo = tipo
        self.claimed_by = None

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.red)
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

    @discord.ui.button(label="📌 Reclamar Ticket", style=discord.ButtonStyle.green)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):

        # 🔒 SOLO EL ROL 1466245030334435398 PUEDE RECLAMAR
        if STAFF_ROLE_ID_2 not in [r.id for r in interaction.user.roles]:
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

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Soporte General", emoji="🛠️"),
            discord.SelectOption(label="Reclamar Beneficios", emoji="🎁"),
            discord.SelectOption(label="Reportar Usuario", emoji="🚨"),
            discord.SelectOption(label="Reportar Moderador", emoji="⚖️")
        ]

        super().__init__(
            placeholder="🎟️ Selecciona el tipo de ticket...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        guild = interaction.guild
        user = interaction.user
        tipo = self.values[0]

        categoria = guild.get_channel(TICKET_CATEGORY_ID)

        nombre_canal = f"{tipo.lower().replace(' ', '-')}-{user.name}"

        canal = await guild.create_text_channel(
            name=nombre_canal,
            category=categoria
        )

        await canal.set_permissions(guild.default_role, read_messages=False)
        await canal.set_permissions(user, read_messages=True, send_messages=True)

        embed = discord.Embed(
            title=f"🎫 Ticket - {tipo}",
            description="Un miembro del staff te atenderá pronto.",
            color=discord.Color.green()
        )

        await canal.send(embed=embed, view=TicketButtons(user, tipo))

        await interaction.response.send_message("🎫 Ticket creado correctamente!", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ===============================
# COMANDO PANEL
# ===============================

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(
        title="🎟️ Centro de Soporte",
        description="Selecciona una categoría para abrir un ticket, Recuerda no abrir un ticket sin motivo.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())

# ===============================
# RUN
# ===============================

bot.run(os.getenv("TOKEN"))
