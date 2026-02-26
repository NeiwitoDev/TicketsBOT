import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from io import StringIO

# ================= CONFIG =================

TICKET_CATEGORY_ID = 1466491475436245220

STAFF_ROLE_ID_1 = 1466244726796582964
STAFF_ROLE_ID_2 = 1466245030334435398
ALTO_MANDO_ROLE_ID = 123456789012345678

CANAL_COMANDO_CALIFICAR = 1466231866041307187
CANAL_LOGS_CALIFICACIONES = 1466240831609638923

# ==========================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tickets_abiertos = {}

# ==========================================
# READY
# ==========================================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} conectado.")

# ==========================================
# SISTEMA DE CALIFICACIÓN
# ==========================================

class CalificacionModal(discord.ui.Modal, title="Calificación del Staff"):
    nota = discord.ui.TextInput(
        label="¿Por qué esa calificación?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    def __init__(self, usuario, staff, estrellas):
        super().__init__()
        self.usuario = usuario
        self.staff = staff
        self.estrellas = estrellas

    async def on_submit(self, interaction: discord.Interaction):

        canal_logs = interaction.guild.get_channel(CANAL_LOGS_CALIFICACIONES)

        estrellas_visual = "⭐" * self.estrellas

        embed = discord.Embed(
            title="📊 Nueva Calificación de Staff",
            color=0xFFFFFF
        )

        embed.add_field(name="👤 Usuario", value=self.usuario.mention, inline=False)
        embed.add_field(name="🛡️ Staff", value=self.staff.mention, inline=False)
        embed.add_field(name="⭐ Calificación", value=estrellas_visual, inline=False)
        embed.add_field(name="📝 Nota", value=self.nota.value, inline=False)

        await canal_logs.send(embed=embed)

        await interaction.response.send_message("✅ Calificación enviada correctamente.", ephemeral=True)

class EstrellasSelect(discord.ui.Select):
    def __init__(self, usuario, staff):
        self.usuario = usuario
        self.staff = staff

        options = [
            discord.SelectOption(label="1 Estrella", value="1"),
            discord.SelectOption(label="2 Estrellas", value="2"),
            discord.SelectOption(label="3 Estrellas", value="3"),
            discord.SelectOption(label="4 Estrellas", value="4"),
            discord.SelectOption(label="5 Estrellas", value="5")
        ]

        super().__init__(placeholder="¿Cuántas estrellas le das?", options=options)

    async def callback(self, interaction: discord.Interaction):
        estrellas = int(self.values[0])
        await interaction.response.send_modal(
            CalificacionModal(self.usuario, self.staff, estrellas)
        )

class CalificarView(discord.ui.View):
    def __init__(self, usuario, staff):
        super().__init__(timeout=120)
        self.add_item(EstrellasSelect(usuario, staff))

# ==========================================
# CIERRE CON TXT + BOTÓN CALIFICAR
# ==========================================

class MotivoSelect(discord.ui.Select):
    def __init__(self, creador, tipo):
        self.creador = creador
        self.tipo = tipo

        options = [
            discord.SelectOption(label="Ticket Resuelto"),
            discord.SelectOption(label="Ticket Cerrado Sin Motivo")
        ]

        super().__init__(placeholder="Selecciona el motivo...", options=options)

    async def callback(self, interaction: discord.Interaction):

        motivo = self.values[0]
        staff = interaction.user

        # 📜 Transcripción TXT
        buffer = StringIO()

        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            buffer.write(f"[{msg.created_at.strftime('%H:%M')}] {msg.author}: {msg.content}\n")

        buffer.seek(0)
        archivo = discord.File(fp=StringIO(buffer.getvalue()), filename="transcripcion.txt")

        embed_dm = discord.Embed(
            title="📩 Ticket Cerrado",
            description=f"**Categoría:** {self.tipo}\n"
                        f"**Motivo:** {motivo}\n"
                        f"**Staff Responsable:** {staff.mention}\n\n"
                        "¿Deseas calificar al staff?\nAdelante 👇",
            color=0xFFFFFF
        )

        view = CalificarView(self.creador, staff)

        try:
            await self.creador.send(embed=embed_dm, file=archivo, view=view)
        except:
            pass

        if self.creador.id in tickets_abiertos:
            if self.tipo in tickets_abiertos[self.creador.id]:
                tickets_abiertos[self.creador.id].remove(self.tipo)

        await interaction.response.send_message("🔒 Cerrando ticket...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

class MotivoView(discord.ui.View):
    def __init__(self, creador, tipo):
        super().__init__()
        self.add_item(MotivoSelect(creador, tipo))

# ==========================================
# SLASH COMMAND
# ==========================================

@bot.tree.command(name="calificar-staff", description="Califica a un staff")
@app_commands.describe(staff="Miembro del staff", calificacion="1 a 5", nota="Motivo")
async def calificar_staff(interaction: discord.Interaction, staff: discord.Member, calificacion: int, nota: str):

    if interaction.channel.id != CANAL_COMANDO_CALIFICAR:
        await interaction.response.send_message("❌ Este comando solo puede usarse en el canal designado.", ephemeral=True)
        return

    if calificacion < 1 or calificacion > 5:
        await interaction.response.send_message("❌ La calificación debe ser entre 1 y 5.", ephemeral=True)
        return

    canal_logs = interaction.guild.get_channel(CANAL_LOGS_CALIFICACIONES)
    estrellas_visual = "⭐" * calificacion

    embed = discord.Embed(
        title="📊 Nueva Calificación de Staff",
        color=0xFFFFFF
    )

    embed.add_field(name="👤 Usuario", value=interaction.user.mention, inline=False)
    embed.add_field(name="🛡️ Staff", value=staff.mention, inline=False)
    embed.add_field(name="⭐ Calificación", value=estrellas_visual, inline=False)
    embed.add_field(name="📝 Nota", value=nota, inline=False)

    await canal_logs.send(embed=embed)
    await interaction.response.send_message("✅ Calificación enviada.", ephemeral=True)

# ==========================================
# RUN
# ==========================================

bot.run(os.getenv("TOKEN"))
