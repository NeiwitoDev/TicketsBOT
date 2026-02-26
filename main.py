import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from io import BytesIO

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
    print(f"✅ {bot.user} conectado correctamente.")

# ==========================================
# VER TICKET
# ==========================================

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

# ==========================================
# SISTEMA CALIFICACIÓN
# ==========================================

class CalificacionModal(discord.ui.Modal, title="Calificar Staff"):
    nota = discord.ui.TextInput(
        label="¿Por qué esa calificación?",
        style=discord.TextStyle.paragraph,
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
        await interaction.response.send_message("✅ Calificación enviada.", ephemeral=True)

class EstrellasSelect(discord.ui.Select):
    def __init__(self, usuario, staff):
        self.usuario = usuario
        self.staff = staff

        options = [
            discord.SelectOption(label="⭐ 1 Estrella", value="1"),
            discord.SelectOption(label="⭐⭐ 2 Estrellas", value="2"),
            discord.SelectOption(label="⭐⭐⭐ 3 Estrellas", value="3"),
            discord.SelectOption(label="⭐⭐⭐⭐ 4 Estrellas", value="4"),
            discord.SelectOption(label="⭐⭐⭐⭐⭐ 5 Estrellas", value="5")
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
# BOTONES DEL TICKET
# ==========================================

class TicketButtons(discord.ui.View):
    def __init__(self, creador, tipo):
        super().__init__(timeout=None)
        self.creador = creador
        self.tipo = tipo
        self.claimed_by = None

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.red)
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MotivoView(self.creador, self.tipo)
        await interaction.response.send_message(
            "Selecciona el motivo:",
            view=view,
            ephemeral=True
        )

# ==========================================
# CIERRE + TXT + CALIFICACIÓN
# ==========================================

class MotivoSelect(discord.ui.Select):
    def __init__(self, creador, tipo):
        self.creador = creador
        self.tipo = tipo

        options = [
            discord.SelectOption(label="Ticket Resuelto"),
            discord.SelectOption(label="Ticket Cerrado Sin Motivo")
        ]

        super().__init__(placeholder="Motivo del cierre", options=options)

    async def callback(self, interaction: discord.Interaction):

        motivo = self.values[0]
        staff = interaction.user

        transcript = ""

        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            transcript += f"[{msg.created_at.strftime('%H:%M')}] {msg.author}: {msg.content}\n"

        archivo = discord.File(
            BytesIO(transcript.encode()),
            filename="transcripcion.txt"
        )

        embed_dm = discord.Embed(
            title="📩 Tu Ticket Fue Cerrado",
            description=f"**Categoría:** {self.tipo}\n"
                        f"**Motivo:** {motivo}\n"
                        f"**Staff Responsable:** {staff.mention}\n\n"
                        "¿Deseas calificar al staff?\nPresiona el botón abajo 👇",
            color=0xFFFFFF
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="⭐ Calificar Staff",
            style=discord.ButtonStyle.green,
            custom_id="calificar_btn"
        ))

        await self.creador.send(embed=embed_dm, file=archivo, view=CalificarView(self.creador, staff))

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
# PANEL CREAR TICKET
# ==========================================

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Soporte General", emoji="🛠️"),
            discord.SelectOption(label="Reclamar Beneficios", emoji="🎁"),
            discord.SelectOption(label="Reportar Usuario", emoji="🚨"),
            discord.SelectOption(label="Reportar Moderador", emoji="⚖️")
        ]

        super().__init__(placeholder="Selecciona categoría", options=options)

    async def callback(self, interaction: discord.Interaction):

        user = interaction.user
        tipo = self.values[0]

        if user.id not in tickets_abiertos:
            tickets_abiertos[user.id] = []

        if tipo in tickets_abiertos[user.id]:
            await interaction.response.send_message(
                "❌ Ya tienes un ticket de esta categoría abierto.",
                ephemeral=True
            )
            return

        tickets_abiertos[user.id].append(tipo)

        categoria = interaction.guild.get_channel(TICKET_CATEGORY_ID)
        canal = await interaction.guild.create_text_channel(
            name=f"{tipo.lower().replace(' ', '-')}-{user.name}",
            category=categoria
        )

        await canal.set_permissions(interaction.guild.default_role, read_messages=False)
        await canal.set_permissions(user, read_messages=True, send_messages=True)

        botones = TicketButtons(user, tipo)

        await canal.send(
            embed=discord.Embed(
                title=f"🎫 Ticket - {tipo}",
                description="Un staff te atenderá pronto.",
                color=discord.Color.green()
            ),
            view=botones
        )

        await interaction.response.send_message(
            "🎫 Ticket creado correctamente.",
            view=VerTicketView(canal),
            ephemeral=True
        )

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ==========================================
# COMANDO PANEL
# ==========================================

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(
        title="🎟️ Centro de Soporte",
        description="Selecciona una categoría para abrir un ticket, Recuerda no abrir 1 ticket sin motivo.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())

# ==========================================
# RUN
# ==========================================

bot.run(os.getenv("TOKEN"))
